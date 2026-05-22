#!/usr/bin/env bash
# =============================================================================
#  01_setup_tools.sh
#  Install every CLI tool we need for reverse-engineering this lab.
#  Idempotent — safe to re-run.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_BIN="${REPO_ROOT}/tools/bin"
mkdir -p "${TOOLS_BIN}"

log()  { printf "\033[1;34m[setup]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn ]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[ ok  ]\033[0m %s\n" "$*"; }
fail() { printf "\033[1;31m[fail ]\033[0m %s\n" "$*"; }

# -----------------------------------------------------------------------------
# 1) APT packages (mono-utils → monodis/pedump; openjdk for jadx/apktool; unzip)
# -----------------------------------------------------------------------------
log "Installing apt packages (mono-utils, openjdk-17, unzip, curl, wget)…"
if command -v sudo >/dev/null 2>&1; then SUDO=sudo; else SUDO=; fi
DEBIAN_FRONTEND=noninteractive ${SUDO} apt-get update -y >/dev/null
DEBIAN_FRONTEND=noninteractive ${SUDO} apt-get install -y --no-install-recommends \
    mono-utils \
    mono-devel \
    openjdk-17-jre-headless \
    unzip \
    curl \
    wget \
    ca-certificates \
    python3 \
    python3-pip \
    >/dev/null
ok "apt packages installed"

# -----------------------------------------------------------------------------
# 2) .NET SDK (only if missing) — needed for `ilspycmd` (dotnet tool)
# -----------------------------------------------------------------------------
if ! command -v dotnet >/dev/null 2>&1; then
    log "Installing .NET SDK 8 (Microsoft installer script)…"
    curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
    bash /tmp/dotnet-install.sh --channel 8.0 --install-dir "${HOME}/.dotnet"
    export DOTNET_ROOT="${HOME}/.dotnet"
    export PATH="${HOME}/.dotnet:${HOME}/.dotnet/tools:${PATH}"
    ok "dotnet $(dotnet --version) installed"
else
    ok "dotnet already installed ($(dotnet --version))"
fi

# ilspycmd 8.x targets net6.0 — install the .NET 6 runtime alongside.
if ! ls "${HOME}/.dotnet/shared/Microsoft.NETCore.App/6."* >/dev/null 2>&1; then
    log "Installing .NET 6 runtime (needed by ilspycmd 8.x)…"
    [ -f /tmp/dotnet-install.sh ] || \
        curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
    bash /tmp/dotnet-install.sh --channel 6.0 --runtime dotnet --install-dir "${HOME}/.dotnet"
    ok ".NET 6 runtime installed"
else
    ok ".NET 6 runtime already present"
fi

# Persist PATH for future shells (idempotent grep-add).
PROFILE="${HOME}/.bashrc"
grep -q 'dotnet/tools' "${PROFILE}" 2>/dev/null || {
    cat >> "${PROFILE}" <<'EOF'

# >>> ReverseEngineering Lab dotnet PATH
export DOTNET_ROOT="${HOME}/.dotnet"
export PATH="${HOME}/.dotnet:${HOME}/.dotnet/tools:${PATH}"
# <<<
EOF
}
export DOTNET_ROOT="${HOME}/.dotnet"
export PATH="${HOME}/.dotnet:${HOME}/.dotnet/tools:${PATH}"

# -----------------------------------------------------------------------------
# 3) ilspycmd (.NET decompiler CLI)
# -----------------------------------------------------------------------------
if ! command -v ilspycmd >/dev/null 2>&1; then
    # Pin to 8.2.x — the last published ilspycmd that ships a valid
    # DotnetToolSettings.xml. Newer 9.x / 10.x packages currently fail
    # `dotnet tool install` with "Settings file not found".
    log "Installing ilspycmd 8.2.0.7535 (dotnet global tool)…"
    dotnet tool install -g ilspycmd --version 8.2.0.7535 \
        || dotnet tool update -g ilspycmd --version 8.2.0.7535
    ok "ilspycmd installed"
else
    ok "ilspycmd already present ($(ilspycmd --version 2>&1 | head -n1))"
fi

# -----------------------------------------------------------------------------
# 4) jadx (APK to Java decompiler) — fetch the release zip into tools/bin
# -----------------------------------------------------------------------------
if [ ! -x "${TOOLS_BIN}/jadx/bin/jadx" ]; then
    log "Installing jadx 1.5.1 (GitHub release)…"
    JADX_VER="1.5.1"
    JADX_URL="https://github.com/skylot/jadx/releases/download/v${JADX_VER}/jadx-${JADX_VER}.zip"
    mkdir -p "${TOOLS_BIN}/jadx"
    curl -fsSL "${JADX_URL}" -o "${TOOLS_BIN}/jadx.zip"
    unzip -q -o "${TOOLS_BIN}/jadx.zip" -d "${TOOLS_BIN}/jadx"
    rm -f "${TOOLS_BIN}/jadx.zip"
    chmod +x "${TOOLS_BIN}/jadx/bin/jadx" "${TOOLS_BIN}/jadx/bin/jadx-gui" 2>/dev/null || true
    ok "jadx installed at ${TOOLS_BIN}/jadx/bin/jadx"
else
    ok "jadx already present"
fi

# -----------------------------------------------------------------------------
# 5) apktool (resource decoder) — fetch wrapper + jar
# -----------------------------------------------------------------------------
if [ ! -x "${TOOLS_BIN}/apktool" ]; then
    log "Installing apktool 2.9.3…"
    APKTOOL_VER="2.9.3"
    curl -fsSL https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool \
        -o "${TOOLS_BIN}/apktool"
    curl -fsSL "https://github.com/iBotPeaches/Apktool/releases/download/v${APKTOOL_VER}/apktool_${APKTOOL_VER}.jar" \
        -o "${TOOLS_BIN}/apktool.jar"
    chmod +x "${TOOLS_BIN}/apktool"
    ok "apktool installed"
else
    ok "apktool already present"
fi

# -----------------------------------------------------------------------------
# 6) de4dot (de-obfuscator for ConfuserEx) — only if not yet downloaded
# -----------------------------------------------------------------------------
if [ ! -f "${TOOLS_BIN}/de4dot/de4dot.exe" ]; then
    log "Fetching de4dot (community fork: dnSpyEx)…"
    mkdir -p "${TOOLS_BIN}/de4dot"
    # The original de4dot/de4dot repo no longer publishes releases.
    # The actively-maintained fork is dnSpyEx/de4dot. We try a couple of
    # known-good URLs; if all fail, this is non-fatal (we have monodis).
    DE4DOT_URLS=(
        "https://github.com/dnSpyEx/de4dot/releases/download/v3.1.41592.5/de4dot-3.1.41592.5-net472.zip"
        "https://github.com/de4dot/de4dot/archive/refs/heads/master.zip"
    )
    INSTALLED=0
    for url in "${DE4DOT_URLS[@]}"; do
        if curl -fsSL --max-time 30 "${url}" -o "${TOOLS_BIN}/de4dot.zip"; then
            unzip -q -o "${TOOLS_BIN}/de4dot.zip" -d "${TOOLS_BIN}/de4dot" 2>/dev/null || continue
            rm -f "${TOOLS_BIN}/de4dot.zip"
            INSTALLED=1
            break
        fi
    done
    if [ "$INSTALLED" = "1" ]; then ok "de4dot installed";
    else warn "Could not download de4dot — Phase 2 will fall back to monodis-only."
    fi
else
    ok "de4dot already present"
fi

# -----------------------------------------------------------------------------
# 7) Python deps used by tools/05_generate_typescript.py
# -----------------------------------------------------------------------------
log "Installing Python deps (pefile, pyjwt)…"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet pefile pyjwt cryptography
ok "Python deps installed"

# -----------------------------------------------------------------------------
# 8) Symlink jadx & apktool into tools/bin for easy PATH-ing
# -----------------------------------------------------------------------------
ln -sf "${TOOLS_BIN}/jadx/bin/jadx" "${TOOLS_BIN}/jadx-cli" 2>/dev/null || true

# -----------------------------------------------------------------------------
# Final report
# -----------------------------------------------------------------------------
echo
log "=== Tool versions ==="
command -v monodis  >/dev/null && monodis  --help 2>&1 | head -n1 || warn "monodis missing"
command -v ilspycmd >/dev/null && ilspycmd --version  | head -n1 || warn "ilspycmd missing"
"${TOOLS_BIN}/jadx/bin/jadx" --version 2>/dev/null   || warn "jadx missing"
[ -x "${TOOLS_BIN}/apktool" ] && "${TOOLS_BIN}/apktool" --version 2>/dev/null \
                                                       || warn "apktool missing"

echo
ok "Setup complete. Add to your shell:"
echo "    export PATH=\"${TOOLS_BIN}:\${HOME}/.dotnet/tools:\${PATH}\""
