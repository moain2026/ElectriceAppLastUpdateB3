# 🛠️ tools/

Reproducible scripts for the analysis pipeline. Every script is **idempotent**
— re-running it is safe.

| Script | When | What |
|--------|:----:|------|
| `01_setup_tools.sh`        | once | Install mono-utils, .NET SDK, ilspycmd, jadx, apktool, de4dot, python deps. |
| `02_extract_il.sh`         | Phase 2 | Dump IL via `monodis` for every relevant .NET binary. |
| `03_decompile_dlls.sh`     | Phase 2 | Decompile to C# via `ilspycmd` (with optional `de4dot` pre-pass). |
| `04_decompile_apk.sh`      | Phase 7 | `jadx` + `apktool` over `ElectricCollector26.apk`. |
| `05_generate_typescript.py`| Phase 5 | Emit TypeScript interfaces from decompiled C# DTOs. |

## Usage

```bash
# First time only:
bash tools/01_setup_tools.sh
source ~/.bashrc       # picks up dotnet tools PATH

# Phase 2 — produces reverse_engineering/{il_dumps,decompiled_csharp}
bash tools/02_extract_il.sh
bash tools/03_decompile_dlls.sh

# Phase 7 — produces reverse_engineering/apk_decompiled
bash tools/04_decompile_apk.sh

# Phase 5 — produces api_contracts/typescript_types.ts
python3 tools/05_generate_typescript.py
```

## Notes

- `tools/bin/` holds bundled binaries (jadx, apktool, de4dot). It is excluded
  from version control via `.gitignore`. Re-run `01_setup_tools.sh` to refill.
- OSS / vendor assemblies (`Newtonsoft.Json.dll`, `Oracle.DataAccess.dll`,
  `jose-jwt.dll`) are **skipped** by the decompile scripts; they are kept in
  `binaries/` only for traceability.
- `03_decompile_dlls.sh` writes per-binary stdout/stderr logs alongside the
  output (`_ilspycmd.stdout.log`, `_ilspycmd.stderr.log`) so partial failures
  are debuggable.
