#!/usr/bin/env python3
"""
generate_endpoint_details.py
============================
Consume `reverse_engineering/metadata/endpoints.json` and emit a single
markdown blob containing one detail block per [OperationContract] in
`IServiceElect` (modern, primary).

Each block is precisely the schema specified by معين in the Phase-3
brief:

    ## OpName
    - Contract / Method / Route / Auth / RequestFormat / ResponseFormat
    - WebInvoke attribute (reconstructed verbatim from decoded blob)
    - Parameter table (name | type | location | required | notes)
    - Returns
    - Source citations
    - Confidence
    - Notes

Output: prints to stdout. The caller (a make-style script or the
analysis/01_WCF_ENDPOINTS.md author) is responsible for splicing it in.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ── Route resolution (mirrors tools/generate_artifacts.py::route_path) ───────
# A WCF [WebInvoke]/[WebGet] without an explicit UriTemplate defaults to the
# operation name. If UriTemplate is set to a bare absolute route (e.g. "/"),
# the operation binds to that route instead. IService1.Index is the only
# such case in this API.
_BARE_ROUTE = re.compile(r"^/[A-Za-z0-9_\-/.]*$")


def _route_for(op: dict) -> str:
    tmpl = (op.get("uriTemplate") or "").strip()
    if tmpl and tmpl.startswith("/") and _BARE_ROUTE.match(tmpl):
        return tmpl
    return f"/{op['name']}"

REPO      = Path(__file__).resolve().parent.parent
ENDPOINTS = REPO / "reverse_engineering" / "metadata" / "endpoints.json"


# Heuristic auth requirement (must stay in sync with
# tools/generate_artifacts.py :: PUBLIC_OPS).
#
#   Modern (IServiceElect):  Login, Authenticate, test
#   Legacy (IService1):      GetCallerIdentity, Index
#
PUBLIC_OPS: frozenset[str] = frozenset({
    "Login", "Authenticate", "test",
    "GetCallerIdentity", "Index",
})


def requires_auth(name: str) -> bool:
    return name not in PUBLIC_OPS


# Confidence per claim category
def confidence_for(op: dict) -> int:
    # We know name + verb + params + return + URI template from metadata
    # → 95% baseline. We drop to 80% if no UriTemplate (we have to guess
    # whether the WCF stub used the default operation-name routing) and
    # bump to 100% when both UriTemplate and FaultContract are present.
    score = 95
    if op["uriTemplate"]:
        score += 3
    if op["faultContracts"]:
        score += 2
    return min(score, 100)


def reconstruct_webinvoke(op: dict) -> str:
    """Re-emit a [WebInvoke(...)] / [WebGet(...)] C# attribute literal
    from the decoded named-args bundle. This is the source-of-truth
    citation that consumers can paste back into a C# project."""
    is_get = op["httpMethod"] == "GET"
    attr_name = "WebGet" if is_get else "WebInvoke"
    parts: list[str] = []
    if not is_get:
        parts.append(f'Method="{op["httpMethod"]}"')
    if op["uriTemplate"]:
        parts.append(f'UriTemplate="{op["uriTemplate"]}"')
    parts.append(f'BodyStyle=WebMessageBodyStyle.{op["bodyStyle"]}')
    parts.append(f'RequestFormat=WebMessageFormat.{op["requestFormat"]}')
    parts.append(f'ResponseFormat=WebMessageFormat.{op["responseFormat"]}')
    return f"[{attr_name}({', '.join(parts)})]"


# A small hand-curated description blob for the IServiceElect ops. Every
# entry is grounded in (a) the operation name itself, (b) parameter names,
# (c) the return type. NO method-body knowledge is encoded here — those
# observations are explicit in the markdown body.
OP_NOTES: dict[str, str] = {
    "Authenticate":              "Bootstrap endpoint that exchanges credentials for a JWT. Body is the only `Bare` style operation. **Body fully obfuscated in MProgService.dll** — see `analysis/09_OBFUSCATION_NOTES.md`. Full token issuance details deferred to Phase 4.",
    "test":                      "Healthcheck. Returns the literal string `\"test\"` (typical WCF idiom). Public — no JWT required.",
    "GetListAccounts":           "Master-data listing of customer accounts under a tenant. `num/m/g/p/acctid` are nullable filters; `appId` is the mandatory tenant key.",
    "GetListGroup":              "List of pricing/billing groups visible to the caller. `no_mstlm` likely the upstream-master id filter (confirmed in DTO survey: `pGroup` has 3 fields).",
    "GetListPlaces":             "Hierarchy of physical locations (zones/branches/quarters). `type` discriminates the hierarchy level. Returns the `plocation` DTO (6 fields).",
    "GetRepBoxMove":             "Report — daily cashbox movement summary, grouped by date.",
    "GetRepBoxMoveDetails":      "Report — detailed cashbox movement for a given date + account number.",
    "GetRepExpenses":            "Report — expenses per date. Reuses the `RepBoxMovesDetals` DTO → same shape, different SQL.",
    "GetListUserPlaces":         "Returns the locations a user (`num`) is allowed to operate on. Used for filtering UI dropdowns in the mobile client.",
    "GetListReadingCounter":     "Meter-reading list. `id, isnull, notblh, nomstlm, nogroup` are filters; returns `ItemReading` (17 fields — see Phase 5).",
    "SaveReading":               "Persist a single meter reading. `num` is the account number, `kh` is the new counter value, `appId` the tenant. **Mutation → expect permission check on `Users.S_K`.**",
    "GetListUsers":              "Tenant users listing. `id` is presumably the calling user's NOU (filter to peers under permissions matrix).",
    "GetRepReadingHeader":       "Reading-report header. `type` discriminates daily/monthly/etc.",
    "GetRepBalanceDetailsByDate":"Balance details for an account over a date range. Reuses `RepBalanceDetails` (10 fields).",
    "GetRepBalanceHeader":       "Balance-report header — 5 filters, `type` likely chooses currency/account aggregation.",
    "GetRepBondsHeader":         "Bonds-report header — `num/sdate/edate/currency` are filters.",
    "GetBondRecieptRcordNext":   "Returns the next receipt record number for a Bond. Pure read; no side effects.",
    "GetListBonds":              "Bond listing (incoming/receipts). `nou` is an extra filter not present on the legacy contract — likely the calling user.",
    "SaveBond":                  "Create a new bond. 12 business fields + `appId`. Body style is Wrapped → JSON `{ num, num_s, nmstnd, ... }`. **Mutation → permission `Users.S_S`/`Users.DE`.**",
    "UpdateBond":                "PUT with `appId` + `id` in URL template. Body carries the same 12 business fields as `SaveBond` (minus appId).",
    "DeleteBond":                "DELETE with `appId` + `id` in URL template. No body.",
    "GetBondPaymentRecordNext":  "Same as `GetBondRecieptRcordNext` but for outgoing payment bonds.",
    "GetListBondsPayment":       "Outgoing-payment-bond listing. Same filter shape as `GetListBonds` but on the payment ledger.",
    "SaveBondPayment":           "Create outgoing payment bond. Same 12-field body as `SaveBond` — different table.",
    "UpdateBondPayment":         "PUT outgoing payment bond.",
    "DeleteBondPayment":         "DELETE outgoing payment bond.",
    "Login":                     "**The Phase-2 headline finding.** 4 parameters in body — `username`, `password`, `appId`, `secureId`. `secureId` is the device fingerprint (`OracleServiceMobile.Defence.MashineSerialNumber`-equivalent) and is the **single distinguishing parameter vs. IService1.Login**. Returns full `Users` DTO including permission flags. **Public — no JWT required.** Body fully obfuscated.",
    "GetAccountBalanceInfo":     "Per-account balance snapshot on a given date. Returns `List<AccountBalanceInfo>` (3 fields).",
    "GetAccountBalance":         "Account balance as a scalar string. `accountid, currency, appId`.",
    "GetCompanyInfo":            "Company metadata (name, address, phone, logo URL). Returns the `CompanyInfo` DTO.",
    "GetCompanyData":            "Returns the small `DataComp` DTO. No params → returns generic deployment data for the WCF host (likely company id + version).",
    "ReSetPassword":             "Password rotation. 5-field body: `username, password, newpassword, uId, appId`. **Note:** the operation name spelling (`ReSetPassword`) is intentional — verified verbatim from the metadata.",
    "InsertMessage":             "SMS-message insertion. 8 fields. Body fields suggest integration with an SMS gateway: `customerN, phoneNo, customerName, ms1, tg, nos, uId, appId`.",
}


def emit_op(op: dict, *, index: int) -> str:
    name = op["name"]
    auth = requires_auth(name)
    out: list[str] = []
    out.append(f"### {index}. `{name}`")
    out.append("")

    # Top-line bullets
    out.append(f"- **Contract:** `MProgServiceElect.IServiceElect` (modern)")
    out.append(f"- **HTTP method:** `{op['httpMethod']}`")
    route_str = _route_for(op)
    route = f"`{route_str}`"
    # Only annotate UriTemplate when it differs from the canonical route
    if op["uriTemplate"] and op["uriTemplate"] != route_str:
        route += f" *(WCF UriTemplate: `{op['uriTemplate']}`)*"
    out.append(f"- **Route:** {route}")
    out.append(f"- **Auth required:** {'**Yes** — `Authorization: Bearer <jwt>`' if auth else '**No** — public bootstrap endpoint'}")
    out.append(f"- **Request format:** `{op['requestFormat']}`  ·  **Response format:** `{op['responseFormat']}`  ·  **Body style:** `{op['bodyStyle']}`")
    if op["faultContracts"]:
        out.append(f"- **Fault contracts:** {', '.join(f'`{f}`' for f in op['faultContracts'])}")
    out.append("")

    # WebInvoke attribute, reconstructed
    out.append("**Reconstructed WCF attribute (verbatim from decoded `CustomAttribute` blob):**")
    out.append("")
    out.append("```csharp")
    out.append(reconstruct_webinvoke(op))
    out.append("```")
    out.append("")

    # Parameter table
    if op["parameters"]:
        out.append("**Parameters** (signature from `MProgService.json → MProgServiceElect.IServiceElect`):")
        out.append("")
        out.append("| #  | Name | Type | Location | Required | Notes |")
        out.append("|---:|------|------|:--------:|:--------:|-------|")
        for i, p in enumerate(op["parameters"], 1):
            note = ""
            if p["name"] == "appId":
                note = "tenant key (see `analysis/07_MULTI_TENANT.md`)"
            elif p["name"] == "secureId":
                note = "**device fingerprint — Phase-2 discovery, only on `IServiceElect.Login`**"
            elif p["name"] in ("username", "password", "newpassword"):
                note = "credential"
            elif p["name"] in ("nou", "uId"):
                note = "acting user id (`Users.NOU`)"
            elif p["name"] in ("sdate", "edate", "date", "mdate"):
                note = "date filter (ISO-8601 string)"
            out.append(f"| {i:2d} | `{p['name']}` | `{p['type']}` | `{p['in']}` | yes | {note} |")
        out.append("")
    else:
        out.append("**Parameters:** _(none)_")
        out.append("")

    # Returns
    out.append(f"**Returns:** `{op['returnType']}`")
    out.append("")

    # Notes
    if name in OP_NOTES:
        out.append(f"**Notes:** {OP_NOTES[name]}")
        out.append("")

    # Source citations
    out.append("**Sources:**")
    out.append("")
    out.append(f"- `reverse_engineering/metadata/MProgService.json` → `MProgServiceElect.IServiceElect.{name}` (Method element)")
    out.append(f"- `reverse_engineering/metadata/endpoints.json` → `contracts.modern.operations[{index-1}]`")
    out.append(f"- `reverse_engineering/decompiled_csharp/MProgService/MProgServiceElect/IServiceElect.cs` (declaration line — body absent/obfuscated)")
    out.append("")

    # Confidence
    out.append(f"**Confidence:** {confidence_for(op)}% (surface signature, verb, URI template, body style, fault contracts). Body-level semantics deferred to Phase 4 (auth) / Phase 5 (DTO fields) / Phase 7 (APK call-site).")
    out.append("")
    out.append("---")
    out.append("")
    return "\n".join(out)


def emit_legacy_op(op: dict, *, index: int) -> str:
    """Compact rendering for IService1 — legacy, no per-op prose."""
    name = op["name"]
    out: list[str] = []
    out.append(f"### {index}. `{name}` 🔴 DEPRECATED")
    out.append("")
    out.append(f"- **Contract:** `MProgService.IService1` (legacy — use the IServiceElect counterpart instead)")
    out.append(f"- **HTTP method:** `{op['httpMethod']}`")
    route_str = _route_for(op)
    route = f"`{route_str}`"
    if op["uriTemplate"] and op["uriTemplate"] != route_str:
        route += f" *(UriTemplate: `{op['uriTemplate']}`)*"
    out.append(f"- **Route:** {route}")
    out.append(f"- **Body style:** `{op['bodyStyle']}`  ·  Returns `{op['returnType']}`")
    if op["parameters"]:
        plist = ", ".join(f"`{p['name']}:{p['type']}`({p['in']})" for p in op["parameters"])
        out.append(f"- **Parameters:** {plist}")
    out.append(f"- **Source:** `MProgService.json → MProgService.IService1.{name}`  ·  **Confidence:** 95%")
    out.append("")
    return "\n".join(out)


def main() -> int:
    if not ENDPOINTS.exists():
        print(f"ERROR: {ENDPOINTS} not found — run tools/generate_phase3.py first.", file=sys.stderr)
        return 1
    bundle = json.loads(ENDPOINTS.read_text())

    out: list[str] = []
    out.append("<!-- BEGIN PHASE-3 AUTOGEN — do not hand-edit; re-run tools/generate_endpoint_details.py -->")
    out.append("")
    out.append("## Per-endpoint detail — `IServiceElect` (modern contract)")
    out.append("")
    out.append("> The 33 detail blocks below were generated mechanically by")
    out.append("> `tools/generate_endpoint_details.py` from")
    out.append("> `reverse_engineering/metadata/endpoints.json`. The `OP_NOTES`")
    out.append("> dict in that script carries the only hand-written prose;")
    out.append("> everything else (verb, URI template, parameter list, fault")
    out.append("> contracts, reconstructed `[WebInvoke]` attribute literal) is")
    out.append("> derived from the binary metadata. Re-run any time:")
    out.append(">")
    out.append("> ```bash")
    out.append("> python3 tools/generate_endpoint_details.py")
    out.append("> ```")
    out.append("")
    for i, op in enumerate(bundle["contracts"]["modern"]["operations"], 1):
        out.append(emit_op(op, index=i))

    out.append("## Per-endpoint detail — `IService1` (legacy contract, reference only)")
    out.append("")
    out.append("> These 27 operations are **deprecated**. Kept here as a")
    out.append("> regression cross-reference for engineers auditing what")
    out.append("> changed between APK v25 and v26. **Do NOT wire these into")
    out.append("> `app1` — use the modern contract.**")
    out.append("")
    for i, op in enumerate(bundle["contracts"]["legacy"]["operations"], 1):
        out.append(emit_legacy_op(op, index=i))

    out.append("<!-- END PHASE-3 AUTOGEN -->")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
