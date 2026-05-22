#!/usr/bin/env python3
"""
generate_phase3.py
==================
Phase 3 generator. Consumes Phase 2 metadata dumps and emits:

  1. reverse_engineering/metadata/endpoints.json
        Structured per-operation map for both IServiceElect (modern) and
        IService1 (legacy) — used as the single source of truth for
        OpenAPI, Postman, endpoints.ts, and the per-endpoint markdown
        section.

  2. (when imported) helpers that other generator scripts call to obtain
        the same structured representation without re-parsing blobs.

Run:
    python3 tools/generate_phase3.py

All decisions are driven by:
    - reverse_engineering/metadata/MProgService.json
        (from Phase 2's MetaExtract .NET 8 tool)
    - the ECMA-335 CustomAttribute blob layout (per parse_webinvoke.py)

NO source-line guessing. NO method-body reading. ConfuserEx-safe.
"""
from __future__ import annotations

import base64
import json
import re
import struct
import sys
from pathlib import Path

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

REPO       = Path(__file__).resolve().parent.parent
META_DIR   = REPO / "reverse_engineering" / "metadata"
OUT_JSON   = META_DIR / "endpoints.json"

WEB_MSG_FMT    = {0: "Xml", 1: "Json"}
WEB_BODY_STYLE = {0: "Bare", 1: "Wrapped", 2: "WrappedRequest", 3: "WrappedResponse"}

# Map .NET primitive names that appear in MetaExtract Signature strings
# to JSON Schema / TS / OpenAPI primitives.
DOTNET_TO_OPENAPI = {
    "String":   ("string",  "string",  None),
    "Boolean":  ("boolean", "boolean", None),
    "Int16":    ("integer", "number",  "int32"),
    "Int32":    ("integer", "number",  "int32"),
    "Int64":    ("integer", "number",  "int64"),
    "UInt32":   ("integer", "number",  "int32"),
    "Decimal":  ("number",  "number",  "double"),
    "Double":   ("number",  "number",  "double"),
    "Single":   ("number",  "number",  "float"),
    "Byte":     ("integer", "number",  "uint8"),
    "DateTime": ("string",  "string",  "date-time"),
    "Object":   ("object",  "unknown", None),
    "Stream":   ("string",  "string",  "binary"),     # System.IO.Stream
    "Void":     (None,      "void",    None),
}


# ----------------------------------------------------------------------------
# Blob decoding (re-uses parse_webinvoke.py's logic, inlined for one-shot use)
# ----------------------------------------------------------------------------

def read_packed_len(buf: bytes, off: int) -> tuple[int, int]:
    if off >= len(buf):
        raise IndexError("EOF")
    b0 = buf[off]
    if b0 == 0xFF:
        return -1, off + 1
    if (b0 & 0x80) == 0:
        return b0, off + 1
    if (b0 & 0xC0) == 0x80:
        return ((b0 & 0x3F) << 8) | buf[off + 1], off + 2
    return (
        ((b0 & 0x1F) << 24)
        | (buf[off + 1] << 16)
        | (buf[off + 2] << 8)
        | buf[off + 3]
    ), off + 4


def read_ser_string(buf: bytes, off: int) -> tuple[str | None, int]:
    n, off = read_packed_len(buf, off)
    if n == -1:
        return None, off
    s = buf[off : off + n].decode("utf-8", errors="replace")
    return s, off + n


def parse_named_args(buf: bytes, start: int) -> dict[str, object]:
    out: dict[str, object] = {}
    if start + 2 > len(buf):
        return out
    num_named = buf[start] | (buf[start + 1] << 8)
    off = start + 2
    for _ in range(num_named):
        if off >= len(buf):
            break
        try:
            _fop = buf[off]; off += 1
            ttype = buf[off]; off += 1
            if ttype == 0x55:  # ENUM
                _type_name, off = read_ser_string(buf, off)
                name,       off = read_ser_string(buf, off)
                if off + 4 > len(buf):
                    break
                v = struct.unpack_from("<i", buf, off)[0]
                off += 4
                if name in ("RequestFormat", "ResponseFormat"):
                    out[name] = WEB_MSG_FMT.get(v, str(v))
                elif name == "BodyStyle":
                    out[name] = WEB_BODY_STYLE.get(v, str(v))
                else:
                    out[name] = v
            elif ttype == 0x0E:  # STRING
                name, off = read_ser_string(buf, off)
                val,  off = read_ser_string(buf, off)
                out[name] = val
            else:
                break
        except Exception:
            break
    return out


# ----------------------------------------------------------------------------
# Signature parsing
# ----------------------------------------------------------------------------

GENERIC_RE  = re.compile(r"^System\.Collections\.Generic\.List`1<(.+)>$")
ARRAY_RE    = re.compile(r"^(.+)\[\]$")

def normalise_type(t: str) -> str:
    """Convert a fully-qualified .NET type from the metadata Signature
    field into a short canonical form used in our analysis docs."""
    t = t.strip()
    t = t.replace("MProgService.models.", "")
    t = t.replace("System.IO.Stream", "Stream")
    m = GENERIC_RE.match(t)
    if m:
        return f"List<{normalise_type(m.group(1))}>"
    return t


def split_sig(sig: str) -> tuple[str, list[str]]:
    """Split 'Return (Param1, Param2)' from MetaExtract signature.
    The .NET FullName parser can produce nested parens for generics, but
    in the data we have, generics always use angle brackets (because that
    is how System.Reflection.Metadata renders List<T>). So a single split
    on ' (' is safe."""
    if " (" not in sig:
        return sig.strip(), []
    ret, rest = sig.split(" (", 1)
    rest = rest.rstrip(")").strip()
    if not rest:
        return ret.strip(), []
    # Split top-level commas only (no nested commas inside <...>)
    parts: list[str] = []
    depth = 0
    cur   = ""
    for ch in rest:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return ret.strip(), parts


# ----------------------------------------------------------------------------
# Endpoint extraction
# ----------------------------------------------------------------------------

def extract_operation(meth: dict) -> dict | None:
    """Return a dict describing one [OperationContract] method, or None
    if this method is not exposed via WebInvoke/WebGet."""
    web_attr: dict[str, object] = {}
    fault_contracts: list[str] = []
    has_operation_contract = False

    for a in meth.get("CustomAttributes", []):
        ctor = a.get("Ctor", "")
        blob = base64.b64decode(a.get("BlobBase64", ""))

        if "OperationContractAttribute" in ctor:
            has_operation_contract = True

        if "WebInvokeAttribute" in ctor:
            web_attr = parse_named_args(blob, 2)
            # WebInvoke defaults: Method=POST when not set explicitly.
            web_attr.setdefault("Method", "POST")
            web_attr["_kind"] = "WebInvoke"
        elif "WebGetAttribute" in ctor:
            web_attr = parse_named_args(blob, 2)
            web_attr["Method"] = "GET"
            web_attr["_kind"] = "WebGet"

        if "FaultContractAttribute" in ctor:
            # The blob carries the fully-qualified type name (leading length byte).
            # Cheap extraction: trust BlobStrings if available.
            bs = a.get("BlobStrings", [])
            if bs:
                fault_contracts.append(bs[0].strip())

    if not has_operation_contract and not web_attr:
        return None

    ret, ptypes = split_sig(meth["Signature"])
    pnames = [p["Name"] for p in meth.get("Parameters", [])]
    # Sanity: align by sequence number if mismatched
    if len(pnames) != len(ptypes):
        # Best-effort align — Parameters are 1-indexed by SequenceNumber.
        # If counts differ, fall back to names; types stay as-is.
        pass
    parameters: list[dict] = []
    for i in range(max(len(pnames), len(ptypes))):
        parameters.append({
            "name":  pnames[i] if i < len(pnames) else f"arg{i+1}",
            "type":  normalise_type(ptypes[i]) if i < len(ptypes) else "?",
            "in":    "body",  # default; refined below for GET/UriTemplate
            "required": True,
        })

    uri_template = (web_attr.get("UriTemplate") or "").strip() if isinstance(web_attr.get("UriTemplate"), str) else ""
    method       = str(web_attr.get("Method", "")).upper() or "POST"

    # If GET or UriTemplate uses {name} placeholders, those params are query/path
    if uri_template:
        # All {name} substitutions are query parameters for these contracts
        # (uri_templates never contain a path segment beyond the operation name).
        qnames = set(re.findall(r"\{([^{}]+)\}", uri_template))
        for p in parameters:
            if p["name"] in qnames:
                p["in"] = "query"

    if method == "GET":
        for p in parameters:
            if p["in"] == "body":
                p["in"] = "query"

    return {
        "name":            meth["Name"],
        "httpMethod":      method,
        "uriTemplate":     uri_template,
        "requestFormat":   web_attr.get("RequestFormat", "Json"),
        "responseFormat":  web_attr.get("ResponseFormat", "Json"),
        "bodyStyle":       web_attr.get("BodyStyle", "Wrapped" if method != "GET" else "Bare"),
        "returnType":      normalise_type(ret),
        "parameters":      parameters,
        "faultContracts":  fault_contracts,
        "webAttrKind":     web_attr.get("_kind", ""),
    }


def extract_contract(meta: dict, ns: str, type_name: str) -> dict:
    t = next(
        (x for x in meta["Types"] if x["Namespace"] == ns and x["Name"] == type_name),
        None,
    )
    if not t:
        return {"namespace": ns, "type": type_name, "operations": [], "missing": True}

    ops: list[dict] = []
    for meth in t["Methods"]:
        op = extract_operation(meth)
        if op:
            ops.append(op)

    return {
        "namespace": ns,
        "type":      type_name,
        "operations": ops,
    }


# ----------------------------------------------------------------------------
# DTO extraction (for OpenAPI components / TS types)
# ----------------------------------------------------------------------------

def extract_dtos(meta: dict) -> list[dict]:
    out = []
    for t in meta["Types"]:
        if t["Namespace"] != "MProgService.models":
            continue
        props = []
        for p in t.get("Properties", []):
            # Signature looks like "Int32 ()" — getter return type.
            sig_ret, _ = split_sig(p["Signature"])
            props.append({
                "name": p["Name"],
                "type": normalise_type(sig_ret),
            })
        out.append({
            "name":  t["Name"],
            "fullName": f"{t['Namespace']}.{t['Name']}",
            "properties": props,
        })
    return out


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> int:
    meta_path = META_DIR / "MProgService.json"
    if not meta_path.exists():
        print(f"ERROR: {meta_path} not found — run Phase 2 first.", file=sys.stderr)
        return 1
    meta = json.loads(meta_path.read_text())

    bundle = {
        "schemaVersion": 1,
        "source":        "reverse_engineering/metadata/MProgService.json",
        "generator":     "tools/generate_phase3.py",
        "contracts": {
            "modern":     extract_contract(meta, "MProgServiceElect", "IServiceElect"),
            "legacy":     extract_contract(meta, "MProgService",      "IService1"),
        },
        "dtos":          extract_dtos(meta),
    }

    # Stats
    m_ops = len(bundle["contracts"]["modern"]["operations"])
    l_ops = len(bundle["contracts"]["legacy"]["operations"])
    n_dto = len(bundle["dtos"])
    print(f"IServiceElect (modern): {m_ops} operations")
    print(f"IService1 (legacy):     {l_ops} operations")
    print(f"DTOs (MProgService.models): {n_dto}")

    OUT_JSON.write_text(json.dumps(bundle, indent=2, ensure_ascii=False))
    print(f"Wrote {OUT_JSON.relative_to(REPO)} ({OUT_JSON.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
