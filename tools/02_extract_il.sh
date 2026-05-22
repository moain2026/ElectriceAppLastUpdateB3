#!/usr/bin/env bash
# =============================================================================
#  02_extract_il.sh
#  Dump IL (Intermediate Language) for every .NET binary in binaries/.
#  Output → reverse_engineering/il_dumps/<name>.il
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${REPO_ROOT}/binaries"
OUT_DIR="${REPO_ROOT}/reverse_engineering/il_dumps"
mkdir -p "${OUT_DIR}"

log()  { printf "\033[1;34m[il]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[il]\033[0m %s\n" "$*"; }

# Skip OSS / vendor binaries — we don't analyze them.
SKIP_REGEX='^(Newtonsoft\.Json|Oracle\.DataAccess|jose-jwt)\.dll$'

if ! command -v monodis >/dev/null 2>&1; then
    echo "[!] monodis not in PATH. Run tools/01_setup_tools.sh first." >&2
    exit 1
fi

for f in "${BIN_DIR}"/*.dll "${BIN_DIR}"/*.exe; do
    base="$(basename "$f")"
    if [[ "$base" =~ $SKIP_REGEX ]]; then
        warn "skip (OSS/vendor): $base"
        continue
    fi
    name="${base%.*}"
    out="${OUT_DIR}/${name}.il"
    log "monodis $base → ${out#${REPO_ROOT}/}"
    monodis --output="${out}" "$f" 2>/dev/null || {
        warn "monodis failed on $base — possibly heavy ConfuserEx. Continuing."
        monodis "$f" > "${out}" 2>/dev/null || true
    }
    wc -l "${out}" | awk '{printf "        %d lines written\n", $1}'
done

log "done."
