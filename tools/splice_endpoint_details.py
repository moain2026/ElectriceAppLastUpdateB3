#!/usr/bin/env python3
"""
splice_endpoint_details.py
==========================
Idempotently splice the output of `generate_endpoint_details.py` into
`analysis/01_WCF_ENDPOINTS.md` between the sentinels

    <!-- BEGIN PHASE-3 AUTOGEN ... -->
    ...
    <!-- END PHASE-3 AUTOGEN -->

If the sentinels do not yet exist, the new section is appended at the
end of the file. Re-running the script always produces the same final
output for a given `endpoints.json` (idempotent).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOC  = REPO / "analysis" / "01_WCF_ENDPOINTS.md"
GEN  = REPO / "tools" / "generate_endpoint_details.py"

SENTINEL_BEGIN = "<!-- BEGIN PHASE-3 AUTOGEN"
SENTINEL_END   = "<!-- END PHASE-3 AUTOGEN -->"
PATTERN = re.compile(
    r"<!-- BEGIN PHASE-3 AUTOGEN[\s\S]*?<!-- END PHASE-3 AUTOGEN -->\n?",
    re.MULTILINE,
)


def main() -> int:
    if not DOC.exists():
        print(f"ERROR: {DOC} missing.", file=sys.stderr); return 1
    if not GEN.exists():
        print(f"ERROR: {GEN} missing.", file=sys.stderr); return 1

    rendered = subprocess.check_output([sys.executable, str(GEN)], text=True)
    if not rendered.endswith("\n"):
        rendered += "\n"

    doc = DOC.read_text()
    if SENTINEL_BEGIN in doc:
        new_doc = PATTERN.sub(rendered, doc, count=1)
        if new_doc == doc:
            # Pattern matched but produced identical content → still idempotent
            print(f"{DOC.relative_to(REPO)}: already up-to-date (no change)")
        else:
            DOC.write_text(new_doc)
            print(f"{DOC.relative_to(REPO)}: re-spliced (replaced sentinel block)")
    else:
        # Append, ensuring two trailing newlines before the new block
        sep = "\n" if doc.endswith("\n") else "\n\n"
        DOC.write_text(doc + sep + "\n---\n\n" + rendered)
        print(f"{DOC.relative_to(REPO)}: appended new sentinel block")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
