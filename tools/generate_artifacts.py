#!/usr/bin/env python3
"""
generate_artifacts.py
=====================
Consumes `reverse_engineering/metadata/endpoints.json` (produced by
`tools/generate_phase3.py`) and emits the three Phase-3 deliverables:

    api_contracts/openapi.yaml
    api_contracts/postman_collection.json
    for_main_repo/endpoints.ts

The mapping rules (single source of truth — change them here, regenerate):

  * .NET return type   → OpenAPI media-type schema
  * List<X>            → array of $ref X
  * MProgService.models.X → $ref to component schema X
  * String/Int32/Decimal/Boolean/DateTime → JSON primitives (see
    DOTNET_TO_OPENAPI in generate_phase3.py).
  * Path-style routes  → operations live under /Service/{name} (no
    REST path params at the routing level; UriTemplate query placeholders
    surface as query params).

The server URL is intentionally left as a variable (`{baseUrl}`).
Phase 7 will lock it down to the real value found in APK strings.xml.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml  # PyYAML

REPO     = Path(__file__).resolve().parent.parent
ENDPOINTS = REPO / "reverse_engineering" / "metadata" / "endpoints.json"
OPENAPI   = REPO / "api_contracts" / "openapi.yaml"
POSTMAN   = REPO / "api_contracts" / "postman_collection.json"
TS_OUT    = REPO / "for_main_repo" / "endpoints.ts"


# Primitive .NET → JSON Schema / TS
DOTNET_TO_SCHEMA = {
    "String":   {"type": "string"},
    "Boolean":  {"type": "boolean"},
    "Int16":    {"type": "integer", "format": "int32"},
    "Int32":    {"type": "integer", "format": "int32"},
    "Int64":    {"type": "integer", "format": "int64"},
    "UInt32":   {"type": "integer", "format": "int32"},
    "Decimal":  {"type": "number",  "format": "double"},
    "Double":   {"type": "number",  "format": "double"},
    "Single":   {"type": "number",  "format": "float"},
    "Byte":     {"type": "integer", "format": "uint8"},
    "DateTime": {"type": "string",  "format": "date-time"},
    "Object":   {"type": "object",  "additionalProperties": True},
    "Stream":   {"type": "string",  "format": "binary"},
    "Void":     None,  # represented as 204 No Content
}

DOTNET_TO_TS = {
    "String":   "string",
    "Boolean":  "boolean",
    "Int16":    "number",
    "Int32":    "number",
    "Int64":    "number",
    "UInt32":   "number",
    "Decimal":  "number",
    "Double":   "number",
    "Single":   "number",
    "Byte":     "number",
    "DateTime": "string",
    "Object":   "unknown",
    "Stream":   "Blob",
    "Void":     "void",
}


# ----------------------------------------------------------------------------
# Type → schema helpers
# ----------------------------------------------------------------------------

LIST_RE = re.compile(r"^List<(.+)>$")


def is_known_dto(name: str, dto_names: set[str]) -> bool:
    return name in dto_names


def dotnet_to_openapi_schema(t: str, dto_names: set[str]) -> dict:
    """Map a normalised .NET type (as emitted by generate_phase3) to an
    OpenAPI 3.0 Schema Object."""
    m = LIST_RE.match(t)
    if m:
        inner = m.group(1).strip()
        return {"type": "array", "items": dotnet_to_openapi_schema(inner, dto_names)}
    if t in DOTNET_TO_SCHEMA and DOTNET_TO_SCHEMA[t] is not None:
        return dict(DOTNET_TO_SCHEMA[t])
    if is_known_dto(t, dto_names):
        return {"$ref": f"#/components/schemas/{t}"}
    # Unknown — fall back to opaque object with description
    return {"type": "object", "description": f"Unrecognised .NET type `{t}` (Phase 3 best-effort)"}


def dotnet_to_ts_type(t: str, dto_names: set[str]) -> str:
    m = LIST_RE.match(t)
    if m:
        inner = m.group(1).strip()
        return f"{dotnet_to_ts_type(inner, dto_names)}[]"
    if t in DOTNET_TO_TS:
        return DOTNET_TO_TS[t]
    if is_known_dto(t, dto_names):
        return t
    return "unknown"


# ----------------------------------------------------------------------------
# Feature folder classification (for Postman folders)
# ----------------------------------------------------------------------------

def folder_for(op_name: str) -> str:
    n = op_name.lower()
    if n in ("authenticate", "login", "test", "resetpassword"):
        return "Auth"
    if "bond" in n:
        return "Bonds"
    if "reading" in n:
        return "Readings"
    if "balance" in n or "expense" in n or "boxmove" in n or "rep" in n:
        return "Reports"
    if "account" in n or "user" in n or "place" in n or "group" in n or "company" in n or "currency" in n:
        return "Master Data"
    if "message" in n:
        return "Messaging"
    return "Other"


# ----------------------------------------------------------------------------
# OpenAPI generation
# ----------------------------------------------------------------------------

def build_openapi(bundle: dict) -> dict:
    dto_names = {d["name"] for d in bundle["dtos"]}

    schemas: dict = {}
    for dto in bundle["dtos"]:
        properties: dict = {}
        required: list[str] = []
        for p in dto["properties"]:
            properties[p["name"]] = dotnet_to_openapi_schema(p["type"], dto_names)
            # .NET DataMember doesn't expose IsRequired in our blob extraction
            # → conservatively mark all as not required; Phase 5 will refine.
        schemas[dto["name"]] = {
            "type": "object",
            "description": f"DTO `{dto['fullName']}` — auto-generated from MProgService.json metadata.",
            "properties": properties,
        }
        if required:
            schemas[dto["name"]]["required"] = required

    paths: dict = {}

    def add_operation(op: dict, *, contract: str, deprecated: bool):
        path = f"/{op['name']}"
        method = op["httpMethod"].lower()
        method_obj = {
            "operationId": f"{contract}_{op['name']}",
            "summary": f"{contract} :: {op['name']}",
            "tags": [contract],
            "deprecated": deprecated,
            "x-wcf-contract": contract,
            "x-wcf-uri-template": op["uriTemplate"] or None,
            "x-wcf-body-style": op["bodyStyle"],
            "x-wcf-request-format": op["requestFormat"],
            "x-wcf-response-format": op["responseFormat"],
            "x-wcf-fault-contracts": op["faultContracts"],
        }
        # Strip None values from extensions
        method_obj = {k: v for k, v in method_obj.items() if v is not None and v != []}

        # Security — Login & Authenticate don't require a token; everything else does.
        if op["name"] not in ("Login", "Authenticate", "test", "GetCallerIdentity"):
            method_obj["security"] = [{"bearerAuth": []}]
        else:
            method_obj["security"] = []  # explicitly public

        # Parameters
        parameters = []
        body_props: dict = {}
        body_required: list[str] = []
        for p in op["parameters"]:
            if p["in"] == "query":
                parameters.append({
                    "name": p["name"],
                    "in": "query",
                    "required": True,
                    "schema": dotnet_to_openapi_schema(p["type"], dto_names),
                })
            else:  # body
                body_props[p["name"]] = dotnet_to_openapi_schema(p["type"], dto_names)
                body_required.append(p["name"])

        if parameters:
            method_obj["parameters"] = parameters

        if body_props and op["httpMethod"] in ("POST", "PUT", "DELETE"):
            # Wrapped style: body is { paramName: value, ... }
            schema_obj: dict = {"type": "object", "properties": body_props}
            if body_required:
                schema_obj["required"] = body_required
            method_obj["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {"schema": schema_obj},
                },
            }

        # Response
        resp_schema = None
        if op["returnType"] not in ("Void", ""):
            resp_schema = dotnet_to_openapi_schema(op["returnType"], dto_names)

        responses = {}
        if resp_schema is not None:
            responses["200"] = {
                "description": "Success",
                "content": {"application/json": {"schema": resp_schema}},
            }
        else:
            responses["204"] = {"description": "No content"}

        if op["faultContracts"]:
            responses["500"] = {
                "description": "Service fault — see x-wcf-fault-contracts",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ServiceFault"}}},
            }

        method_obj["responses"] = responses
        paths.setdefault(path, {})[method] = method_obj

    for op in bundle["contracts"]["modern"]["operations"]:
        add_operation(op, contract="IServiceElect", deprecated=False)
    for op in bundle["contracts"]["legacy"]["operations"]:
        # Use a /legacy prefix to avoid clobbering modern path/method pairs
        # when both contracts expose the same operation under the same name.
        modern_names = {o["name"] for o in bundle["contracts"]["modern"]["operations"]}
        if op["name"] in modern_names:
            # Park under /legacy/{name}
            saved = op["name"]
            op2 = dict(op)
            op2["name"] = f"legacy/{saved}"
            add_operation(op2, contract="IService1", deprecated=True)
        else:
            add_operation(op, contract="IService1", deprecated=True)

    spec = {
        "openapi": "3.0.3",
        "info": {
            "title":       "ElectricCollector28 — Reverse-engineered WCF API",
            "version":     "0.3.0",
            "description": (
                "OpenAPI 3.0 spec auto-generated by `tools/generate_artifacts.py` "
                "from `reverse_engineering/metadata/endpoints.json` (which itself "
                "is derived from MetaExtract metadata dumps of `MProgService.dll`).\n\n"
                "* `IServiceElect` (modern contract, primary) — 33 operations.\n"
                "* `IService1` (legacy contract, deprecated) — 27 operations.\n\n"
                "Base URL placeholder (`{baseUrl}`) will be locked down to the real "
                "value in Phase 7 (APK strings.xml). Authentication uses JWT via the "
                "`Authorization: Bearer ...` header — see `analysis/02_JWT_AUTHENTICATION.md` "
                "(Phase 4).\n\n"
                "Vendor extensions (`x-wcf-*`) preserve the WCF metadata we recovered:\n"
                "* `x-wcf-contract` — `IServiceElect` or `IService1`\n"
                "* `x-wcf-uri-template` — original UriTemplate (when set)\n"
                "* `x-wcf-body-style` — `Wrapped` / `Bare` / `WrappedRequest` / `WrappedResponse`\n"
                "* `x-wcf-request-format` / `x-wcf-response-format` — `Json` / `Xml`\n"
                "* `x-wcf-fault-contracts` — list of FaultContract types\n"
                "* `x-wcf-metadata-token` — original .NET MetadataToken for traceability"
            ),
        },
        "servers": [{"url": "{baseUrl}", "variables": {"baseUrl": {"default": "https://example.invalid", "description": "Locked down in Phase 7 from APK strings.xml"}}}],
        "tags": [
            {"name": "IServiceElect", "description": "Modern contract (primary, all new clients)."},
            {"name": "IService1",     "description": "Legacy contract — deprecated, kept for reference."},
        ],
        "components": {
            "schemas": schemas,
            "securitySchemes": {
                "bearerAuth": {
                    "type":         "http",
                    "scheme":       "bearer",
                    "bearerFormat": "JWT",
                    "description":  "JWT token returned by IServiceElect.Authenticate; see Phase 4.",
                },
            },
        },
        "paths": paths,
    }
    return spec


# ----------------------------------------------------------------------------
# YAML emission (minimal, deterministic — no external dependency)
# ----------------------------------------------------------------------------

def yaml_emit(obj, indent: int = 0) -> str:
    """Tiny deterministic YAML emitter (sufficient for our spec shape).
    No anchors, no flow style, strings always plain-quoted when needed."""
    sp = "  " * indent
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, (int, float)):
        return repr(obj)
    if isinstance(obj, str):
        return yaml_str(obj)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        out = []
        for item in obj:
            v = yaml_emit(item, indent + 1)
            if "\n" in v:
                # First line gets "- ", rest gets sp + "  "
                lines = v.split("\n")
                out.append(f"{sp}- {lines[0].lstrip()}")
                for ln in lines[1:]:
                    out.append(f"{sp}  {ln.lstrip()}" if ln.strip() else "")
            else:
                out.append(f"{sp}- {v}")
        return "\n".join(out)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        out = []
        for k, v in obj.items():
            key = yaml_str(str(k))
            ev = yaml_emit(v, indent + 1)
            if isinstance(v, (dict, list)) and v:
                out.append(f"{sp}{key}:")
                out.append(ev)
            else:
                out.append(f"{sp}{key}: {ev}")
        return "\n".join(out)
    return yaml_str(str(obj))


SAFE_PLAIN = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-./]*$")


def yaml_str(s: str) -> str:
    if s == "":
        return "''"
    # Multiline strings → folded block
    if "\n" in s:
        lines = s.split("\n")
        return "|-\n" + "\n".join("  " + ln for ln in lines)
    if SAFE_PLAIN.match(s) and s not in ("true", "false", "null", "yes", "no", "on", "off", "~"):
        return s
    # Default: single-quoted with escaping
    return "'" + s.replace("'", "''") + "'"


# ----------------------------------------------------------------------------
# Postman collection
# ----------------------------------------------------------------------------

def build_postman(bundle: dict) -> dict:
    dto_names = {d["name"] for d in bundle["dtos"]}
    folders: dict[str, list[dict]] = {}

    def make_request(op: dict, *, contract: str, deprecated: bool) -> dict:
        # Query params with placeholders → fill with {{paramName}}
        query = []
        body_obj = {}
        for p in op["parameters"]:
            if p["in"] == "query":
                placeholder = f"{{{{{p['name']}}}}}"
                if p["name"] == "appId":
                    placeholder = "{{appId}}"
                query.append({"key": p["name"], "value": placeholder})
            else:
                v = ""
                if p["name"] == "appId":
                    v = "{{appId}}"
                elif p["name"] == "secureId":
                    v = "{{secureId}}"
                elif p["name"] == "username":
                    v = "{{username}}"
                elif p["name"] == "password":
                    v = "{{password}}"
                body_obj[p["name"]] = v

        url = {
            "raw":  "{{baseUrl}}/" + op["name"] + (("?" + "&".join(f"{q['key']}={q['value']}" for q in query)) if query else ""),
            "host": ["{{baseUrl}}"],
            "path": [op["name"]],
            "query": query,
        }

        body = None
        if body_obj and op["httpMethod"] in ("POST", "PUT", "DELETE"):
            body = {
                "mode": "raw",
                "raw":  json.dumps(body_obj, indent=2, ensure_ascii=False),
                "options": {"raw": {"language": "json"}},
            }

        headers = [
            {"key": "Content-Type", "value": "application/json", "type": "text"},
        ]
        if op["name"] not in ("Login", "Authenticate", "test", "GetCallerIdentity"):
            headers.append({"key": "Authorization", "value": "Bearer {{token}}", "type": "text"})

        req = {
            "name": op["name"] + (" [LEGACY]" if deprecated else ""),
            "request": {
                "method": op["httpMethod"],
                "header": headers,
                "url":    url,
            },
            "response": [],
        }
        if body is not None:
            req["request"]["body"] = body

        # Auto-inject auth token from Login response on the Login request
        if op["name"] in ("Login", "Authenticate"):
            req["event"] = [{
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        "// Auto-inject JWT into {{token}} on successful login.",
                        "// Phase 4 will lock down the exact response shape.",
                        "if (pm.response.code === 200) {",
                        "    try {",
                        "        var body = pm.response.json();",
                        "        // Heuristic: top-level string or { token } field.",
                        "        var token = (typeof body === 'string')",
                        "            ? body",
                        "            : (body.token || body.access_token || body.JWT || body.Token);",
                        "        if (token) {",
                        "            pm.collectionVariables.set('token', token);",
                        "            console.log('Stored token into {{token}}');",
                        "        }",
                        "    } catch (e) { console.log('Login parse error:', e); }",
                        "}",
                    ],
                },
            }]
        return req

    for op in bundle["contracts"]["modern"]["operations"]:
        folders.setdefault(folder_for(op["name"]), []).append(
            make_request(op, contract="IServiceElect", deprecated=False)
        )
    for op in bundle["contracts"]["legacy"]["operations"]:
        folders.setdefault(f"Legacy/{folder_for(op['name'])}", []).append(
            make_request(op, contract="IService1", deprecated=True)
        )

    items = []
    for name in sorted(folders.keys()):
        items.append({"name": name, "item": folders[name]})

    return {
        "info": {
            "_postman_id":   "5b9f0e2c-0000-0000-0000-electriccollector",
            "name":          "ElectricCollector28 — RE WCF API (Phase 3)",
            "description":   "Auto-generated by tools/generate_artifacts.py from endpoints.json. JWT auto-injection lives on the Login & Authenticate requests. Phase 4 will refine.",
            "schema":        "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
        "variable": [
            {"key": "baseUrl",  "value": "https://example.invalid", "type": "string"},
            {"key": "appId",    "value": "PUT_TENANT_ID_HERE",       "type": "string"},
            {"key": "username", "value": "",                          "type": "string"},
            {"key": "password", "value": "",                          "type": "string"},
            {"key": "secureId", "value": "",                          "type": "string"},
            {"key": "token",    "value": "",                          "type": "string"},
        ],
    }


# ----------------------------------------------------------------------------
# TypeScript endpoints map
# ----------------------------------------------------------------------------

def build_ts(bundle: dict) -> str:
    dto_names = {d["name"] for d in bundle["dtos"]}

    lines: list[str] = []
    lines.append("/**")
    lines.append(" * endpoints.ts — Auto-generated by tools/generate_artifacts.py")
    lines.append(" *")
    lines.append(" * Single source of truth for every WCF operation exposed by the")
    lines.append(" * legacy ElectricCollector28 backend. Drop this file straight into")
    lines.append(" * `app1/src/api/` and reference it from your Axios layer.")
    lines.append(" *")
    lines.append(" * Source data: reverse_engineering/metadata/endpoints.json")
    lines.append(" * DO NOT EDIT MANUALLY — re-run `python3 tools/generate_artifacts.py`.")
    lines.append(" */")
    lines.append("")
    lines.append("/* eslint-disable @typescript-eslint/no-explicit-any */")
    lines.append("")
    lines.append("export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';")
    lines.append("")
    lines.append("export type WcfContract = 'IServiceElect' | 'IService1';")
    lines.append("")
    lines.append("export type WcfBodyStyle = 'Bare' | 'Wrapped' | 'WrappedRequest' | 'WrappedResponse';")
    lines.append("")
    lines.append("export interface EndpointDescriptor {")
    lines.append("  readonly method:     HttpMethod;")
    lines.append("  readonly path:       string;             // relative to baseUrl, no leading slash trimmed by Axios")
    lines.append("  readonly contract:   WcfContract;")
    lines.append("  readonly auth:       boolean;            // true ⇒ Authorization: Bearer {token}")
    lines.append("  readonly bodyStyle:  WcfBodyStyle;")
    lines.append("  readonly queryParams: ReadonlyArray<string>;")
    lines.append("  readonly bodyParams:  ReadonlyArray<string>;")
    lines.append("  readonly returnsList: boolean;")
    lines.append("  readonly returns:     string;            // canonical .NET type name (List<X> | X | primitive)")
    lines.append("  readonly faultContracts: ReadonlyArray<string>;")
    lines.append("  readonly deprecated:  boolean;")
    lines.append("  readonly uriTemplate?: string;           // original WCF UriTemplate, when set")
    lines.append("}")
    lines.append("")

    def emit_one(op: dict, *, contract: str, deprecated: bool, key: str) -> str:
        auth = op["name"] not in ("Login", "Authenticate", "test", "GetCallerIdentity")
        q = [p["name"] for p in op["parameters"] if p["in"] == "query"]
        b = [p["name"] for p in op["parameters"] if p["in"] == "body"]
        returns_list = op["returnType"].startswith("List<")
        d = {
            "method":          op["httpMethod"],
            "path":            f"/{op['name']}",
            "contract":        contract,
            "auth":            auth,
            "bodyStyle":       op["bodyStyle"],
            "queryParams":     q,
            "bodyParams":      b,
            "returnsList":     returns_list,
            "returns":         op["returnType"],
            "faultContracts":  op["faultContracts"],
            "deprecated":      deprecated,
        }
        if op["uriTemplate"]:
            d["uriTemplate"] = op["uriTemplate"]
        # Order keys deterministically
        ordered = [
            "method", "path", "contract", "auth", "bodyStyle",
            "queryParams", "bodyParams",
            "returnsList", "returns", "faultContracts", "deprecated",
            "uriTemplate",
        ]
        body_lines: list[str] = []
        body_lines.append(f"  {ts_key(key)}: {{")
        for k in ordered:
            if k not in d:
                continue
            v = d[k]
            if isinstance(v, str):
                body_lines.append(f"    {k}: {ts_lit(v)},")
            elif isinstance(v, bool):
                body_lines.append(f"    {k}: {'true' if v else 'false'},")
            elif isinstance(v, list):
                if v:
                    body_lines.append(f"    {k}: [{', '.join(ts_lit(x) for x in v)}],")
                else:
                    body_lines.append(f"    {k}: [],")
        body_lines.append("  },")
        return "\n".join(body_lines)

    lines.append("export const ENDPOINTS = {")
    # Modern first
    lines.append("  // ───────── IServiceElect (modern, primary) ─────────")
    for op in bundle["contracts"]["modern"]["operations"]:
        key = camel_case(op["name"])
        lines.append(emit_one(op, contract="IServiceElect", deprecated=False, key=key))
    # Legacy
    lines.append("")
    lines.append("  // ───────── IService1 (legacy, deprecated) ─────────")
    modern_keys = {camel_case(o["name"]) for o in bundle["contracts"]["modern"]["operations"]}
    for op in bundle["contracts"]["legacy"]["operations"]:
        key = camel_case(op["name"])
        if key in modern_keys:
            key = f"legacy_{key}"
        lines.append(emit_one(op, contract="IService1", deprecated=True, key=key))
    lines.append("} as const satisfies Record<string, EndpointDescriptor>;")
    lines.append("")
    lines.append("export type EndpointKey = keyof typeof ENDPOINTS;")
    lines.append("")
    lines.append("/** Tiny helper used in our Axios layer (Phase 4 will own the full client). */")
    lines.append("export function endpointFor(key: EndpointKey): EndpointDescriptor {")
    lines.append("  return ENDPOINTS[key];")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def camel_case(s: str) -> str:
    if not s:
        return s
    # Strip the leading capital
    return s[0].lower() + s[1:]


def ts_lit(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def ts_key(s: str) -> str:
    # Valid identifier? otherwise quote.
    if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", s):
        return s
    return ts_lit(s)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> int:
    if not ENDPOINTS.exists():
        print(f"ERROR: {ENDPOINTS} not found — run tools/generate_phase3.py first.", file=sys.stderr)
        return 1

    bundle = json.loads(ENDPOINTS.read_text())

    OPENAPI.parent.mkdir(parents=True, exist_ok=True)
    TS_OUT.parent.mkdir(parents=True, exist_ok=True)

    spec = build_openapi(bundle)
    OPENAPI.write_text(
        yaml.dump(
            spec,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=120,
        )
    )
    print(f"  wrote {OPENAPI.relative_to(REPO)} ({OPENAPI.stat().st_size:,} bytes)")

    coll = build_postman(bundle)
    POSTMAN.write_text(json.dumps(coll, indent=2, ensure_ascii=False) + "\n")
    print(f"  wrote {POSTMAN.relative_to(REPO)} ({POSTMAN.stat().st_size:,} bytes)")

    ts = build_ts(bundle)
    TS_OUT.write_text(ts)
    print(f"  wrote {TS_OUT.relative_to(REPO)} ({TS_OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
