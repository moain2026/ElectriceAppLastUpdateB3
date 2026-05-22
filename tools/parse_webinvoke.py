#!/usr/bin/env python3
"""
parse_webinvoke.py
------------------
Parse the [WebInvoke(...)]/[WebGet(...)] custom-attribute blobs from
the MetaExtract JSON dump and emit a clean Markdown table of:

   contract → method → HTTP verb → UriTemplate → RequestFormat → BodyStyle

The blob layout for a CustomAttribute is:
    PROLOG (2 bytes: 01 00)
    FixedArgs ...
    NumNamed   (2 bytes, little-endian)
    NamedArgs[NumNamed]  (each: FIELD_OR_PROPERTY(1) | type(1) | name(serString) | value)

For WebInvoke / WebGet the FixedArgs portion is empty (no positional ctor
args used). All settings come via NamedArgs:
    Method         (string,   e.g. "POST")
    UriTemplate    (string,   e.g. "UpdateBond?appId={appId}&id={id}")
    RequestFormat  (enum int, 0 = Xml, 1 = Json)
    ResponseFormat (enum int, 0 = Xml, 1 = Json)
    BodyStyle      (enum int, 0 = Bare, 1 = Wrapped, 2 = WrappedRequest, 3 = WrappedResponse)

ECMA-335 SerString:  PackedLen (1, 2, or 4 bytes compressed unsigned) + UTF-8 bytes.
A length byte of 0xFF means "null".

This script is intentionally tiny and only handles the named-arg cases we
actually encounter (string + enum int). Failures degrade to a best-effort
report.
"""
from __future__ import annotations
import base64
import json
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
META_DIR = REPO / "reverse_engineering" / "metadata"

# WCF Web message format enum
WEB_MSG_FMT = {0: "Xml", 1: "Json"}
# WCF Web message body style enum
WEB_BODY_STYLE = {0: "Bare", 1: "Wrapped", 2: "WrappedRequest", 3: "WrappedResponse"}


def read_packed_len(buf: bytes, off: int) -> tuple[int, int]:
    """Read an ECMA-335 compressed unsigned int. Returns (value, new_offset)."""
    if off >= len(buf):
        raise IndexError("unexpected EOF")
    b0 = buf[off]
    if b0 == 0xFF:  # null marker for strings
        return -1, off + 1
    if (b0 & 0x80) == 0:
        return b0, off + 1
    if (b0 & 0xC0) == 0x80:
        return ((b0 & 0x3F) << 8) | buf[off + 1], off + 2
    # 0xE0..0xEF → 4-byte form
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
    """Parse named args of a CustomAttribute blob, starting just after the
    fixed-args section. We don't know the position of NamedArgsCount perfectly
    for every ctor; so we *scan* — try to read 2 bytes as 'num named' and
    proceed; if anything looks corrupt we abort and return partial dict.

    Layout per named arg:
        FIELD_OR_PROPERTY:1   (0x53 = Field, 0x54 = Property)
        TYPE_TAG:1            (0x0E = string, 0x55 = enum, ...)
        TypeName (only if enum) :  SerString of full type name
        Name :  SerString
        Value :  (depends on type)
    """
    out: dict[str, object] = {}
    if start + 2 > len(buf):
        return out
    num_named = buf[start] | (buf[start + 1] << 8)
    off = start + 2
    for _ in range(num_named):
        if off >= len(buf):
            break
        try:
            fop = buf[off]
            off += 1
            ttype = buf[off]
            off += 1

            if ttype == 0x55:  # ENUM — typename string then enum value
                type_name, off = read_ser_string(buf, off)
                name, off = read_ser_string(buf, off)
                # Enum values for WCF Web are Int32 (4 bytes LE)
                if off + 4 > len(buf):
                    break
                v = struct.unpack_from("<i", buf, off)[0]
                off += 4
                # Friendlier rendering for the formats we know
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
                # Unsupported — bail out, keep what we have.
                break
        except Exception:
            break
    return out


def render_contract(meta: dict, ns: str, type_name: str) -> str:
    t = next(
        (t for t in meta["Types"] if t["Namespace"] == ns and t["Name"] == type_name),
        None,
    )
    if t is None:
        return f"### {ns}.{type_name}\n\n_(not found in metadata)_\n"

    lines = []
    lines.append(f"### `{ns}.{type_name}` — {len(t['Methods'])} operations\n")
    lines.append(
        "| #  | Operation | HTTP | UriTemplate | RequestFmt | ResponseFmt | BodyStyle | Returns | Params |"
    )
    lines.append(
        "|---:|-----------|:----:|-------------|:----------:|:-----------:|:---------:|---------|--------|"
    )
    for i, m in enumerate(t["Methods"], 1):
        verb = "?"
        uri = ""
        req = "?"
        resp = "?"
        bstyle = "?"
        for a in m.get("CustomAttributes", []):
            ctor = a["Ctor"]
            if "WebInvokeAttribute" in ctor or "WebGetAttribute" in ctor:
                blob = base64.b64decode(a["BlobBase64"])
                # blob[0:2] = 01 00 (prolog). FixedArgs = none for these ctors.
                args = parse_named_args(blob, 2)
                method = str(args.get("Method", ""))
                if "WebGetAttribute" in ctor and not method:
                    method = "GET"
                if method:
                    verb = method
                if "UriTemplate" in args:
                    uri = str(args["UriTemplate"] or "")
                if "RequestFormat" in args:
                    req = str(args["RequestFormat"])
                if "ResponseFormat" in args:
                    resp = str(args["ResponseFormat"])
                if "BodyStyle" in args:
                    bstyle = str(args["BodyStyle"])

        # Pretty up the return type (it's the part before " (" in Signature)
        sig = m["Signature"]
        if " (" in sig:
            ret, _ = sig.split(" (", 1)
        else:
            ret = sig
        # Trim long generic notation
        ret = (
            ret.replace("System.Collections.Generic.List`1<", "List<")
            .replace("MProgService.models.", "")
            .replace("System.IO.Stream", "Stream")
            .replace(",MProgService", ", MProgService")
        )
        params = ", ".join(
            p["Name"] for p in m["Parameters"] if p.get("Name")
        )
        lines.append(
            f"| {i:2d} | `{m['Name']}` | **{verb}** | `{uri}` | {req} | {resp} | {bstyle} | `{ret}` | {params} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    meta = json.loads((META_DIR / "MProgService.json").read_text())
    out = []
    out.append("# Auto-generated WebInvoke / WebGet map")
    out.append("")
    out.append(
        "_Source:_ `reverse_engineering/metadata/MProgService.json`"
        " (decoded by `tools/parse_webinvoke.py`)"
    )
    out.append("")
    out.append(render_contract(meta, "MProgService", "IService1"))
    out.append("")
    out.append(render_contract(meta, "MProgServiceElect", "IServiceElect"))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
