#!/usr/bin/env bash
# =============================================================================
#  03_decompile_dlls.sh
#  Decompile every .NET binary in binaries/ to C# using ilspycmd.
#  Output → reverse_engineering/decompiled_csharp/<name>/
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${REPO_ROOT}/binaries"
OUT_BASE="${REPO_ROOT}/reverse_engineering/decompiled_csharp"
mkdir -p "${OUT_BASE}"

# Make sure ilspycmd is in PATH (installed by 01_setup_tools.sh)
export PATH="${HOME}/.dotnet/tools:${HOME}/.dotnet:${PATH}"

log()  { printf "\033[1;34m[cs ]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[cs ]\033[0m %s\n" "$*"; }

if ! command -v ilspycmd >/dev/null 2>&1; then
    echo "[!] ilspycmd not in PATH. Run tools/01_setup_tools.sh first." >&2
    exit 1
fi

# Skip OSS / vendor binaries.
SKIP_REGEX='^(Newtonsoft\.Json|Oracle\.DataAccess|jose-jwt)\.dll$'

# Optional: try to de-obfuscate first with de4dot. If it succeeds, decompile
# the cleaned copy; if not, fall back to the original.
DE4DOT="${REPO_ROOT}/tools/bin/de4dot/de4dot.exe"

decompile_one() {
    local src="$1"
    local base="$(basename "$src")"
    local name="${base%.*}"
    local out_dir="${OUT_BASE}/${name}"
    local work_dir="${REPO_ROOT}/tools/bin/work"
    mkdir -p "${out_dir}" "${work_dir}"

    local target="${src}"

    # Try de-obfuscation (non-fatal).
    if [ -f "${DE4DOT}" ] && command -v mono >/dev/null 2>&1; then
        log "  attempting de4dot on ${base}"
        local cleaned="${work_dir}/${name}-cleaned.${base##*.}"
        if mono "${DE4DOT}" "${src}" -o "${cleaned}" >"${work_dir}/${name}-de4dot.log" 2>&1; then
            target="${cleaned}"
            log "  using cleaned: $(basename "${cleaned}")"
        else
            warn "  de4dot failed (see ${work_dir}/${name}-de4dot.log); using original"
        fi
    fi

    log "ilspycmd → ${out_dir#${REPO_ROOT}/}"
    # -p: split per-type into files for diff-friendly review.
    # We pipe stderr to a log so a partial failure doesn't kill the loop.
    if ! ilspycmd -p -o "${out_dir}" "${target}" \
            > "${out_dir}/_ilspycmd.stdout.log" \
            2> "${out_dir}/_ilspycmd.stderr.log"; then
        warn "  ilspycmd returned non-zero — see logs in ${out_dir#${REPO_ROOT}/}"
    fi

    # Also produce a single-file dump for grep-friendliness.
    ilspycmd -o "${out_dir}/_singlefile" "${target}" >/dev/null 2>&1 || true
}

for f in "${BIN_DIR}"/*.dll "${BIN_DIR}"/*.exe; do
    base="$(basename "$f")"
    if [[ "$base" =~ $SKIP_REGEX ]]; then
        warn "skip (OSS/vendor): $base"
        continue
    fi
    decompile_one "$f"
done

log "done. Inspect: ${OUT_BASE}"
