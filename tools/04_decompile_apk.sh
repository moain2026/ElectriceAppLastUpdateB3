#!/usr/bin/env bash
# =============================================================================
#  04_decompile_apk.sh
#  Decompile the Android APK into:
#    - reverse_engineering/apk_decompiled/resources/  ← apktool d
#    - reverse_engineering/apk_decompiled/sources/    ← jadx
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APK="${REPO_ROOT}/binaries/ElectricCollector26.apk"
OUT_DIR="${REPO_ROOT}/reverse_engineering/apk_decompiled"
JADX="${REPO_ROOT}/tools/bin/jadx/bin/jadx"
APKTOOL="${REPO_ROOT}/tools/bin/apktool"

log()  { printf "\033[1;34m[apk]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[apk]\033[0m %s\n" "$*"; }

if [ ! -f "${APK}" ]; then
    echo "[!] APK not found at ${APK}" >&2
    exit 1
fi

# --- jadx → Java sources -----------------------------------------------------
if [ -x "${JADX}" ]; then
    log "jadx decompile → sources/"
    rm -rf "${OUT_DIR}/sources"
    "${JADX}" \
        --show-bad-code \
        --threads-count 4 \
        -d "${OUT_DIR}/sources" \
        "${APK}" \
        > "${OUT_DIR}/jadx.stdout.log" \
        2> "${OUT_DIR}/jadx.stderr.log" || \
        warn "jadx returned non-zero — partial decompile saved; see jadx.*.log"
else
    warn "jadx not installed — skipping Java decompile"
fi

# --- apktool → resources -----------------------------------------------------
if [ -x "${APKTOOL}" ]; then
    log "apktool d → resources/"
    rm -rf "${OUT_DIR}/resources"
    "${APKTOOL}" d -f -o "${OUT_DIR}/resources" "${APK}" \
        > "${OUT_DIR}/apktool.stdout.log" \
        2> "${OUT_DIR}/apktool.stderr.log" || \
        warn "apktool returned non-zero — see apktool.*.log"
else
    warn "apktool not installed — skipping resource extract"
fi

log "done. Inspect: ${OUT_DIR}"
