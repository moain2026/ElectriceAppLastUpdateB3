#!/usr/bin/env python3
"""
generate_phase5.py — Single source of truth for Phase 5 deliverables.

Consumes:
  reverse_engineering/metadata/MProgService.json           (DTOs, Phase 2)
  reverse_engineering/metadata/endpoints.json              (operation → return type, Phase 3)
  reverse_engineering/userstrings/MProgService.userstrings.json   (SQL templates, Phase 4)

Emits:
  reverse_engineering/metadata/dtos.json                   (precise DTO catalog)
  for_main_repo/dtos.ts                                    (TS interfaces, strict-compile)
  schemas/inferred_oracle_schema.sql                       (Oracle DDL, inferred)
  schemas/tables_relationships.md                          (narrative)
  schemas/erd.mermaid                                      (entity-relationship diagram)
  (intermediate: data used by hand-authored analysis/03_DATA_MODELS.md + 05_ORACLE_INTEGRATION.md)

Deliberately DOES NOT re-emit openapi.yaml / endpoints.ts — those are Phase 3's
generator's job; we only widen `required:` lists in openapi.yaml via a small
patch step in `tools/generate_artifacts.py` (separate change).
"""
from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

META_FILE = ROOT / "reverse_engineering" / "metadata" / "MProgService.json"
ENDPOINTS_FILE = ROOT / "reverse_engineering" / "metadata" / "endpoints.json"
USERSTRINGS_FILE = ROOT / "reverse_engineering" / "userstrings" / "MProgService.userstrings.json"

OUT_DTOS_JSON = ROOT / "reverse_engineering" / "metadata" / "dtos.json"
OUT_DTOS_TS = ROOT / "for_main_repo" / "dtos.ts"
OUT_DDL = ROOT / "schemas" / "inferred_oracle_schema.sql"
OUT_REL = ROOT / "schemas" / "tables_relationships.md"
OUT_ERD = ROOT / "schemas" / "erd.mermaid"

# ─── .NET → TS mapping ─────────────────────────────────────────────────────────
NET_TO_TS = {
    "String": "string",
    "Int32": "number",
    "Int64": "number",
    "Int16": "number",
    "Byte": "number",
    "Double": "number",
    "Single": "number",
    "Decimal": "number",   # Oracle NUMBER → JSON number (lossy at >2^53, but matches what the binary does)
    "Boolean": "boolean",
    "DateTime": "string",  # ISO-8601 in JSON; the wire is `/Date(…)/`-ish per Newtonsoft but we accept string both ways
    "Object": "unknown",
}

# ─── .NET → Oracle DDL mapping ─────────────────────────────────────────────────
# Conservative: prefer the widest sensible type. The actual column types
# can only be confirmed by inspecting the live DB — we mark these as inferred.
NET_TO_ORACLE = {
    "String":   "VARCHAR2(255)",
    "Int32":    "NUMBER(10,0)",
    "Int64":    "NUMBER(19,0)",
    "Int16":    "NUMBER(5,0)",
    "Byte":     "NUMBER(3,0)",
    "Double":   "NUMBER",            # legacy app rarely sets precision
    "Single":   "NUMBER",
    "Decimal":  "NUMBER",
    "Boolean":  "NUMBER(1,0)",       # Oracle has no native bool; 0/1 convention
    "DateTime": "DATE",
}

# Per-DTO Oracle-table-name hints, recovered from the SQL templates mined in Phase 4 (#US heap).
# These are the tables the templates actually FROM-clause; mapping DTO → table is the inference layer.
#
# A DTO is a "row DTO" only if its property names line up with a single table's
# columns (i.e. the WCF method `SELECT col1, col2, … FROM <table>` projects
# those properties). Pure request DTOs and aggregates DON'T count — they are
# documented as `oracle_table_hint = None` so the DDL generator does not
# pollute the inferred table definitions with non-column fields.
DTO_TO_TABLE_HINT = {
    "Accounts":          "data_acc",
    "AccountsLedger":    "DATA_D",        # union over data_s / data_d (we pick the canonical)
    "AccountBalanceInfo": None,           # aggregate over data_acc/DATA_D — NOT a row
    "ChangePasswordRespons": None,        # response envelope; not a table
    "RepBoxMoves":       "SNDK_A",        # combined SNDK_A/SNDS_A UNION per #US +0x2063
    "RepBoxMovesDetals": "SNDK_A",        # detail view of the same
    "ServiceFault":      None,            # error envelope
    "UserPlaces":        "USER_MNATK",    # per #US +0x14cf
    "RepReading":        None,            # report aggregate over data_H — NOT a row
    "LPlaces":           None,            # report aggregate over USER_MNATK joined to Mkb2
    "pGroup":            "GRP",           # per #US +0x1405
    "plocation":         "Mkb2",          # per #US +0x14cf
    "Grops":             "GRP",
    "ListData":          None,            # generic envelope
    "AuthData":          None,            # request DTO {username,password} — NOT a row (USER_R columns are NAME_U/PASS)
    "CompanyInfo":       "titl",          # per #US +0x1323
    "Credentials":       None,            # request DTO {User,Password,appId} — NOT a row
    "Currency":          "amlh",          # per #US +0x4d5e ('select no,namem,FLS,sars from amlh')
    "ItemReading":       "DATA_M",        # readings line (per #US +0x1dca)
    "ItemBonds":         "DATA_D",        # bonds = ledger movements (per #US +0x3c6c)
    "RepBalanceDetails": None,            # report aggregate over DATA_D — NOT a row
    "RepBalanceHeader":  None,            # report aggregate (header summary)
    "RepBondsHeader":    None,            # report aggregate (header summary)
    "DataComp":          None,            # company wrapper — NOT a row
    "ResultPost":        None,            # response envelope
    "Token":             None,            # in-memory only, not a row (per Phase-4 §3.4)
    "Users":             "USER_R",        # per #US +0x4c7a, +0x135f
}

# When a DTO column name is *known* to be a primary key on its hinted table
# (recovered from SQL templates that filter `WHERE <col>='<bind>'`), record it
# so the DDL emits PRIMARY KEY at the right place. These come from #US:
#   USER_R: NOU (filtered in many UNION blocks) and NAME_U (login lookup)
#   data_acc: NOA (joined on NOA in many places)
#   amlh: no (`select no,namem,FLS,sars from amlh`)
#   Mkb2: NOM (`Mkb2.NOM=USER_MNATK.no_mstlm`)
#   GRP: implied from name pattern
KNOWN_PKS = {
    "USER_R":     ["NOU"],
    "data_acc":   ["NOA"],
    "amlh":       ["no"],
    "Mkb2":       ["NOM"],
    "GRP":        ["NOG"],         # inferred from `Accounts.nog` references group
    "USER_MNATK": ["NOU", "no_mstlm"],  # composite (mapping table)
    "DATA_D":     ["NOMS"],        # inferred from `where NOMS=…` patterns
    "DATA_M":     ["NOMS"],
    "data_H":     ["NOMS"],
    "SNDK_A":     ["NOS"],
    "SNDS_A":     ["NOS"],
    "titl":       None,            # singleton config row
}

# DTOs whose property names DEMONSTRABLY match the Oracle column names (lifted
# verbatim from SQL templates in #US — those templates select `col1, col2, …`
# and the C# property names match case-insensitively).
DTO_COLUMNS_MATCH = {"Users", "Accounts", "ItemBonds", "ItemReading", "RepBoxMoves",
                     "AccountsLedger", "Currency"}


def load_metadata():
    return json.loads(META_FILE.read_text())


def extract_dtos(meta):
    out = OrderedDict()
    for t in meta["Types"]:
        if t.get("Namespace") != "MProgService.models":
            continue
        name = t["Name"]
        props = []
        for p in t.get("Properties", []):
            sig = p.get("Signature", "")
            net_type = sig.split(" (")[0] if " (" in sig else sig.strip()
            cas = [(c.get("Ctor", "") if isinstance(c, dict) else "") for c in p.get("CustomAttributes", [])]
            is_dm = any("DataMemberAttribute" in c for c in cas)
            props.append(OrderedDict([
                ("name", p["Name"]),
                ("net_type", net_type),
                ("is_datamember", is_dm),
            ]))
        type_cas = [(c.get("Ctor", "") if isinstance(c, dict) else "") for c in t.get("CustomAttributes", [])]
        is_dc = any("DataContractAttribute" in c for c in type_cas)
        out[name] = OrderedDict([
            ("is_datacontract", is_dc),
            ("property_count", len(props)),
            ("datamember_count", sum(1 for p in props if p["is_datamember"])),
            ("properties", props),
            ("oracle_table_hint", DTO_TO_TABLE_HINT.get(name)),
        ])
    return out


def write_dtos_json(catalog):
    OUT_DTOS_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_DTOS_JSON.write_text(json.dumps({
        "source": "reverse_engineering/metadata/MProgService.json",
        "phase": 5,
        "count": len(catalog),
        "dtos": catalog,
    }, indent=2))
    print(f"wrote {OUT_DTOS_JSON.relative_to(ROOT)} ({len(catalog)} DTOs)")


def _ts_type(net_type: str) -> str:
    base = net_type.rstrip("[]")
    array = net_type.endswith("[]")
    ts = NET_TO_TS.get(base, "unknown")
    if array:
        ts = f"{ts}[]"
    return ts


def write_dtos_ts(catalog):
    """Emit a TS file with one interface per DTO. Property optionality
    follows the [DataMember] attribute: properties carrying it are mandatory
    on the wire (the server always writes them); the rest are POCO-style and
    we mark them optional because the server may omit them at its discretion.
    """
    lines = [
        "/**",
        " * dtos.ts — Auto-generated by tools/generate_phase5.py",
        " *",
        " * One TS interface per WCF DTO in `MProgService.models`. Source data:",
        " *   reverse_engineering/metadata/MProgService.json (Phase 2)",
        " *",
        " * Optionality rule:",
        " *   • Property marked `[DataMember]` in the C# source ⇒ MANDATORY.",
        " *   • Property without `[DataMember]` (POCO-style)    ⇒ OPTIONAL (`name?: T`).",
        " * Some DTOs carry `[DataContract]` without `[DataMember]` on individual",
        " * properties; .NET treats those as serialized by the JSON formatter's",
        " * default (every public property). We still emit them as OPTIONAL so a",
        " * partial wire payload type-checks — Phase 5 doc §3 explains the",
        " * serialization-contract nuance.",
        " *",
        " * The `__source` const at the bottom is a compile-time witness of the",
        " * metadata file used to generate this — bump it manually if you ever",
        " * regenerate from a different binary.",
        " *",
        " * DO NOT EDIT MANUALLY — re-run `python3 tools/generate_phase5.py`.",
        " */",
        "",
        "/* eslint-disable @typescript-eslint/no-explicit-any */",
        "",
        "// ── Type aliases that match the wire shapes the WCF layer emits ───────",
        "// `DateTime` arrives JSON-encoded by Newtonsoft.Json — by default that's an",
        "// ISO-8601 string, but a Newtonsoft installation tuned for legacy serializers",
        "// emits `\"/Date(unix_ms)/\"`. The interceptor in jwt_interceptor.ts treats",
        "// these as opaque strings; if you ever need to parse, see Phase 5 §4.",
        "export type WcfDateTime = string;",
        "",
    ]

    for name, info in catalog.items():
        props = info["properties"]
        lines.append(f"/** {name} — {info['property_count']} properties · "
                     f"{info['datamember_count']}/{info['property_count']} `[DataMember]` · "
                     f"{'[DataContract]' if info['is_datacontract'] else 'POCO (no [DataContract])'}"
                     + (f" · Oracle table hint: `{info['oracle_table_hint']}`"
                        if info['oracle_table_hint'] else "") + " */")
        lines.append(f"export interface {name} {{")
        for p in props:
            ts = _ts_type(p["net_type"]).replace("DateTime", "WcfDateTime")
            opt = "" if p["is_datamember"] else "?"
            lines.append(f"  /** .NET type: `{p['net_type']}`"
                         + (f" — `[DataMember]`" if p['is_datamember'] else "")
                         + " */")
            lines.append(f"  {p['name']}{opt}: {ts};")
        lines.append("}")
        lines.append("")

    # Union of DTO names (useful for typed switches)
    lines.append(f"export type DtoName =")
    for i, name in enumerate(catalog):
        sep = ";" if i == len(catalog) - 1 else ""
        lines.append(f"  | {json.dumps(name)}{sep}")
    lines.append("")
    lines.append("export const __source = {")
    lines.append('  metadata: "reverse_engineering/metadata/MProgService.json",')
    lines.append('  phase: 5,')
    lines.append(f'  count: {len(catalog)},')
    lines.append("} as const;")
    lines.append("")

    OUT_DTOS_TS.write_text("\n".join(lines))
    print(f"wrote {OUT_DTOS_TS.relative_to(ROOT)} ({len(catalog)} interfaces)")


def write_ddl(catalog):
    """Emit an Oracle DDL skeleton. One CREATE TABLE per unique table hint.
    Conservative typing; every column nullable except declared PKs."""
    OUT_DDL.parent.mkdir(parents=True, exist_ok=True)
    # Bucket DTOs by table hint.
    by_table = {}
    for name, info in catalog.items():
        tbl = info.get("oracle_table_hint")
        if not tbl:
            continue
        by_table.setdefault(tbl, []).append((name, info))

    out = []
    out.append("-- ────────────────────────────────────────────────────────────────")
    out.append("-- inferred_oracle_schema.sql")
    out.append("-- INFERRED Oracle DDL — Phase 5 deliverable.")
    out.append("--")
    out.append("-- Source of inference:")
    out.append("--   • DTO property catalogue from MProgService metadata (Phase 2).")
    out.append("--   • SQL templates recovered from the #US heap (Phase 4) which name")
    out.append("--     the actual Oracle table identifiers and confirm a subset of")
    out.append("--     columns. The full column lists are extrapolated from the DTOs")
    out.append("--     that map to each table.")
    out.append("--")
    out.append("-- This file IS NOT a faithful schema dump. The DBA must reconcile it")
    out.append("-- against the live database before any production use. Specifically:")
    out.append("--   • All VARCHAR2 lengths are conservative defaults — adjust to match")
    out.append("--     the on-disk column definitions.")
    out.append("--   • NUMBER precision/scale is inferred from the .NET type, not from")
    out.append("--     observation of stored values.")
    out.append("--   • Foreign keys are inferred from SQL JOIN patterns in #US —")
    out.append("--     they are likely correct but not exhaustively verified.")
    out.append("--   • Indexes implied by WHERE clauses are listed in the trailing")
    out.append("--     `-- Suggested indexes` section.")
    out.append("--")
    out.append("-- Confidence: 70-80% per object (see analysis/05_ORACLE_INTEGRATION.md).")
    out.append("-- ────────────────────────────────────────────────────────────────")
    out.append("")

    # Stable order, with USER_R first (auth-critical) then alphabetical.
    table_order = (["USER_R", "USER_MNATK", "data_acc", "GRP", "amlh", "Mkb2",
                    "DATA_D", "DATA_M", "data_H", "SNDK_A", "SNDS_A", "titl"])
    seen = set()
    ordered = [t for t in table_order if t in by_table] + \
              sorted(set(by_table) - set(table_order))
    for tbl in ordered:
        if tbl in seen:
            continue
        seen.add(tbl)
        dtos_here = by_table[tbl]
        # Merge all properties from DTOs hinted at this table, dedup by name lower-case.
        merged_cols = OrderedDict()
        for dto_name, info in dtos_here:
            for p in info["properties"]:
                k = p["name"].lower()
                if k not in merged_cols:
                    merged_cols[k] = {"name": p["name"], "net_type": p["net_type"],
                                      "sources": [dto_name]}
                else:
                    merged_cols[k]["sources"].append(dto_name)

        pks = KNOWN_PKS.get(tbl) or []
        pk_set = {p.lower() for p in pks}

        # If a PK column was NOT projected by any DTO (because the DTO is a
        # subset projection), synthesise it as NUMBER(10,0) NOT NULL so the
        # CREATE TABLE remains valid Oracle DDL.
        for pk in pks:
            if pk.lower() not in merged_cols:
                merged_cols[pk.lower()] = {
                    "name": pk, "net_type": "Int32",
                    "sources": ["(synthesised PK — not projected by any DTO; inferred from SQL JOIN patterns)"],
                }

        out.append(f"-- ────────────────────────────────────────────────────────────────")
        out.append(f"-- {tbl}  (inferred from DTO{'s' if len(dtos_here)>1 else ''}: "
                   + ", ".join(d[0] for d in dtos_here) + ")")
        out.append(f"-- ────────────────────────────────────────────────────────────────")
        out.append(f"CREATE TABLE {tbl} (")
        col_lines = []
        # Emit PK columns first for readability.
        ordered_keys = [pk.lower() for pk in pks] + [k for k in merged_cols if k not in pk_set]
        seen_k = set()
        for k in ordered_keys:
            if k in seen_k or k not in merged_cols: continue
            seen_k.add(k)
            c = merged_cols[k]
            oracle_type = NET_TO_ORACLE.get(c["net_type"].rstrip("[]"), "VARCHAR2(255)")
            null_keyword = "NOT NULL" if k in pk_set else "        "
            src = ", ".join(c["sources"])
            col_lines.append(f"  {c['name']:<22} {oracle_type:<15} {null_keyword}  -- from {src}")
        out.append(",\n".join(col_lines))
        if pks:
            out.append(f"  , CONSTRAINT pk_{tbl.lower()} PRIMARY KEY ({', '.join(pks)})")
        out.append(");")
        out.append("")

    # Suggested indexes (from SQL templates in #US).
    out.append("-- ────────────────────────────────────────────────────────────────")
    out.append("-- Suggested indexes (inferred from WHERE/JOIN patterns in #US)")
    out.append("-- ────────────────────────────────────────────────────────────────")
    suggestions = [
        ("USER_R",     "(NAME_U)",          "auth lookup at #US +0x4c7a `select * from USER_R where NAME_U='`"),
        ("USER_MNATK", "(NOU)",             "per-user enumeration at #US +0xebf, +0x18ac"),
        ("USER_MNATK", "(no_mstlm)",        "joined to Mkb2.NOM at #US +0x14cf"),
        ("data_acc",   "(NOA)",             "joined to SNDK_A/SNDS_A at #US +0x2063, +0x2d1d"),
        ("data_acc",   "(no_mstlm)",        "filter at #US +0x3132"),
        ("DATA_D",     "(NOA, DATES)",      "ledger time-range queries at #US +0x42f8"),
        ("SNDK_A",     "(no_box, DATES)",   "box-movement reports at #US +0x2063"),
        ("SNDS_A",     "(no_box, DATES)",   "box-movement reports at #US +0x2246"),
    ]
    for i, (tbl, cols, why) in enumerate(suggestions, 1):
        out.append(f"-- {i}. {tbl}{cols} — {why}")
        out.append(f"--   CREATE INDEX idx_{tbl.lower()}_{i} ON {tbl} {cols};")
    out.append("")

    # Foreign keys (inferred from JOIN patterns).
    out.append("-- ────────────────────────────────────────────────────────────────")
    out.append("-- Suggested foreign keys (inferred from JOIN patterns in #US)")
    out.append("-- ────────────────────────────────────────────────────────────────")
    fks = [
        ("SNDK_A.no_box",      "USER_R.NOA",       "#US +0x2063"),
        ("SNDS_A.no_box",      "USER_R.NOA",       "#US +0x2246"),
        ("SNDK_A.NOA",         "data_acc.NOA",     "#US +0x2d1d"),
        ("SNDS_A.NOA",         "data_acc.NOA",     "#US +0x337e"),
        ("SNDK_A.NOAML",       "amlh.no",          "#US +0x252a"),
        ("SNDS_A.NOAML",       "amlh.no",          "#US +0x337e"),
        ("USER_MNATK.no_mstlm","Mkb2.NOM",         "#US +0x1578"),
        ("USER_MNATK.NOU",     "USER_R.NOU",       "#US +0xebf"),
        ("data_acc.no_mstlm",  "Mkb2.NOM",         "#US +0x3132"),
        ("DATA_D.NOA",         "data_acc.NOA",     "#US +0x42f8"),
    ]
    for src, dst, where in fks:
        out.append(f"-- {src} → {dst}  ({where})")
        s_table, s_col = src.split(".")
        d_table, d_col = dst.split(".")
        out.append(f"--   ALTER TABLE {s_table} ADD CONSTRAINT fk_{s_table.lower()}_{s_col.lower()} "
                   f"FOREIGN KEY ({s_col}) REFERENCES {d_table}({d_col});")

    OUT_DDL.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT_DDL.relative_to(ROOT)}")


def write_relationships(catalog):
    OUT_REL.parent.mkdir(parents=True, exist_ok=True)
    out = []
    out.append("# Tables ↔ DTOs ↔ endpoints relationship map\n")
    out.append("> Phase 5 deliverable. Cross-references the inferred Oracle schema")
    out.append("> (`inferred_oracle_schema.sql`), the DTO catalogue")
    out.append("> (`analysis/03_DATA_MODELS.md`), and the WCF endpoint table")
    out.append("> (`analysis/01_WCF_ENDPOINTS.md`).\n")
    out.append("## DTO → Oracle table\n")
    out.append("| DTO | Hinted table | Confidence | Source signal |")
    out.append("|---|---|:--:|---|")
    confidence_notes = {
        "USER_R":     ("100%", "SQL template at #US +0x4c7a/+0x4cf8 names this table"),
        "USER_MNATK": ("100%", "SQL template at #US +0x14cf/+0x1578 names this table"),
        "data_acc":   ("100%", "SQL template at #US +0x1011 names this table"),
        "GRP":        ("100%", "SQL template at #US +0x1405 names this table"),
        "amlh":       ("100%", "SQL template at #US +0x4d5e names this table"),
        "Mkb2":       ("100%", "SQL template at #US +0x1578 names this table"),
        "DATA_D":     ("100%", "SQL template at #US +0x3c6c names this table"),
        "DATA_M":     ("85%",  "SQL template at #US +0x1dca names DATA_M; DTO match by column names"),
        "data_H":     ("85%",  "SQL template at #US +0x1d3f names data_H; DTO match by column names"),
        "SNDK_A":     ("100%", "SQL template at #US +0x2063 names this table"),
        "SNDS_A":     ("100%", "SQL template at #US +0x2246 names this table"),
        "titl":       ("80%",  "SQL template at #US +0x1323 names titl; DTO match by column count"),
    }
    # Per-DTO "why no table" reasons (when oracle_table_hint is None).
    no_table_reasons = {
        "AccountBalanceInfo": "aggregate over data_acc/DATA_D — not a row",
        "ChangePasswordRespons": "response envelope (Success/Message)",
        "ServiceFault": "error envelope",
        "RepReading":   "report aggregate over data_H",
        "LPlaces":      "report aggregate (USER_MNATK ⨝ Mkb2)",
        "ListData":     "generic envelope",
        "AuthData":     "request DTO {username, password} — USER_R columns are NAME_U/PASS",
        "Credentials":  "request DTO {User, Password, appId}",
        "RepBalanceDetails": "report aggregate over DATA_D",
        "RepBalanceHeader":  "report aggregate (header summary over DATA_D)",
        "RepBondsHeader":    "report aggregate (header summary over DATA_D)",
        "DataComp":     "company-wrapper response",
        "ResultPost":   "POST ack envelope (status/note)",
        "Token":        "in-memory only — token row is in a separate auth table per §3.4",
    }
    for name, info in catalog.items():
        tbl = info["oracle_table_hint"]
        if tbl is None:
            reason = no_table_reasons.get(name, "response envelope / aggregate, not a row")
            out.append(f"| `{name}` | — | n/a | {reason} |")
        else:
            conf, src = confidence_notes.get(tbl, ("70%", "structural inference from DTO shape"))
            out.append(f"| `{name}` | `{tbl}` | {conf} | {src} |")
    out.append("")
    out.append("## DTO ↔ endpoint usage\n")
    out.append("> For each DTO, which WCF operations emit/consume it. Source:")
    out.append("> `reverse_engineering/metadata/endpoints.json` (Phase 3).\n")
    if ENDPOINTS_FILE.exists():
        endpoints = json.loads(ENDPOINTS_FILE.read_text())
        # endpoints.json schema: list of operations with name, returns, params
        ops = endpoints.get("operations") or endpoints.get("Operations") or endpoints
        if isinstance(ops, dict):
            ops = list(ops.values()) if "operations" not in endpoints else ops
        # Index by DTO usage
        usage = {n: {"returns": [], "param": []} for n in catalog}
        if isinstance(ops, list):
            for op in ops:
                if not isinstance(op, dict): continue
                ret = op.get("returns") or op.get("Returns") or ""
                # Strip List<...> wrapper
                m = re.match(r"^List<(.+)>$", ret)
                ret_base = m.group(1) if m else ret
                if ret_base in usage:
                    usage[ret_base]["returns"].append(op.get("name") or op.get("Name") or "?")
                # Body params
                for p in op.get("bodyParams") or op.get("BodyParams") or []:
                    pt = p.get("Type") if isinstance(p, dict) else p
                    if pt in usage:
                        usage[pt]["param"].append(op.get("name") or op.get("Name") or "?")
        out.append("| DTO | Returned by | Accepted as body |")
        out.append("|---|---|---|")
        for n, u in usage.items():
            rb = ", ".join(sorted(set(u["returns"]))) or "—"
            pb = ", ".join(sorted(set(u["param"]))) or "—"
            out.append(f"| `{n}` | {rb} | {pb} |")
    out.append("")
    OUT_REL.write_text("\n".join(out))
    print(f"wrote {OUT_REL.relative_to(ROOT)}")


def write_erd(catalog):
    """Emit a mermaid-based ERD using the JOIN-derived FK information."""
    out = [
        "%% Entity-Relationship diagram (inferred) — Phase 5",
        "%% Source: SQL JOIN patterns in #US heap (Phase 4) + DTO catalogue (Phase 2)",
        "%% Confidence: 80% (FKs are inferred from JOIN patterns, not constraint metadata)",
        "erDiagram",
        "    USER_R     ||--o{ USER_MNATK : \"granted access via\"",
        "    Mkb2       ||--o{ USER_MNATK : \"referenced by\"",
        "    USER_R     ||--o{ SNDK_A     : \"box owner (NOA → no_box)\"",
        "    USER_R     ||--o{ SNDS_A     : \"box owner (NOA → no_box)\"",
        "    data_acc   ||--o{ SNDK_A     : \"customer account (NOA)\"",
        "    data_acc   ||--o{ SNDS_A     : \"customer account (NOA)\"",
        "    data_acc   ||--o{ DATA_D     : \"ledger of (NOA)\"",
        "    amlh       ||--o{ SNDK_A     : \"currency (no → NOAML)\"",
        "    amlh       ||--o{ SNDS_A     : \"currency (no → NOAML)\"",
        "    Mkb2       ||--o{ data_acc   : \"product (NOM → no_mstlm)\"",
        "    GRP        ||--o{ data_acc   : \"group (NOG)\"",
        "",
        "    USER_R {",
        "      NUMBER NOU PK",
        "      VARCHAR2 NAME_U \"login\"",
        "      VARCHAR2 PASS \"plain — see security finding §6.1\"",
        "      NUMBER NOA \"box id\"",
        "      NUMBER NOG \"group id\"",
        "      NUMBER ED",
        "      NUMBER DE",
        "      NUMBER S_K",
        "      NUMBER S_S",
        "      NUMBER REP",
        "      NUMBER SYS",
        "      VARCHAR2 access_token",
        "    }",
        "    data_acc {",
        "      NUMBER NOA PK",
        "      NUMBER no_tblh",
        "      NUMBER no_mstlm",
        "      NUMBER no_adad",
        "      NUMBER NOG",
        "      VARCHAR2 tel",
        "      VARCHAR2 NAMEA",
        "    }",
        "    amlh {",
        "      NUMBER no PK",
        "      VARCHAR2 namem",
        "      NUMBER FLS \"is_local?\"",
        "      NUMBER sars \"rate\"",
        "    }",
        "    DATA_D {",
        "      VARCHAR2 NOMS PK",
        "      NUMBER NOA",
        "      NUMBER NOAML",
        "      NUMBER MDIN",
        "      NUMBER DAN",
        "      DATE DATES",
        "      VARCHAR2 MEMOS",
        "    }",
        "    SNDK_A {",
        "      VARCHAR2 NOS PK",
        "      NUMBER no_box",
        "      NUMBER NOA",
        "      NUMBER NOAML",
        "      NUMBER amount",
        "      NUMBER stat",
        "      DATE DATES",
        "    }",
        "",
    ]
    OUT_ERD.write_text("\n".join(out))
    print(f"wrote {OUT_ERD.relative_to(ROOT)}")


def main():
    meta = load_metadata()
    catalog = extract_dtos(meta)
    write_dtos_json(catalog)
    write_dtos_ts(catalog)
    write_ddl(catalog)
    write_relationships(catalog)
    write_erd(catalog)
    print(f"\n== Phase-5 codegen done: {len(catalog)} DTOs processed ==")


if __name__ == "__main__":
    main()
