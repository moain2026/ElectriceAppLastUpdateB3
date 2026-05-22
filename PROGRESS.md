# 📋 Progress Tracker

> Updated continuously by the RE engineer. Each phase ships its own PR.

## Phases

- [x] **Phase 1: Setup & Repository Structure** — branch `phase-1-setup`, PR #1
- [ ] **Phase 2: Decompile All DLLs**           — branch `phase-2-decompile`, PR #2
- [ ] **Phase 3: WCF Endpoints Deep Analysis**  — branch `phase-3-endpoints`, PR #3
- [ ] **Phase 4: JWT Authentication System**    — branch `phase-4-jwt`, PR #4
- [ ] **Phase 5: Data Models + Oracle Schema**  — branch `phase-5-models`, PR #5
- [ ] **Phase 6: Permissions System Forensics** — branch `phase-6-permissions`, PR #6
- [ ] **Phase 7: APK v26 Analysis**             — branch `phase-7-apk`, PR #7
- [ ] **Phase 8: Final Deliverables**           — branch `phase-8-deliverables`, PR #8

## Current status

| Field | Value |
|---|---|
| Active phase  | **Phase 1 — Setup** |
| % complete    | ~85% (waiting on tool install + first PR merge) |
| Last update   | 2026-05-22 |
| Next step     | Install tools, verify they work, open PR #1 |
| Blockers      | None |

## Phase 1 deliverables checklist

- [x] Clone repo / verify state
- [x] Create branch `phase-1-setup`
- [x] Create folder hierarchy (`analysis/`, `reverse_engineering/`, `schemas/`,
      `api_contracts/`, `for_main_repo/`, `tools/`, `binaries/`)
- [x] `git mv` 7 binaries into `binaries/`
- [x] SHA-256 hashes captured (`binaries/SHA256SUMS.txt`)
- [x] `README.md`
- [x] `PROGRESS.md`
- [x] `ANALYSIS_INDEX.md`
- [x] `tools/01_setup_tools.sh`
- [x] `.gitignore`
- [ ] Tools verified working (monodis, ilspycmd, jadx)
- [ ] PR #1 opened
- [ ] PR #1 merged

## Discoveries summary (cumulative)

| Category | Count | Confidence |
|---|---:|:---:|
| WCF endpoints documented   | 0 / 27  | — |
| Data models documented     | 0 / 27  | — |
| Permissions decoded        | 0 / 7   | — |
| SQL queries extracted      | 0       | — |
| JWT details                | partial | 30% |
| APK strings extracted      | 0       | — |
| Binaries fingerprinted     | 7 / 7   | 100% |
| External assembly refs identified | 4 (mscorlib, Oracle.DataAccess 1.102.3.0, System.Data, System.ServiceModel) | 95% |
| Target runtime confirmed   | .NET Framework 4.x | 95% |
| Obfuscation confirmed      | yes (monodis crashes on all 3 proprietary DLLs) | 95% |

## Open questions (live)

1. Is the JWT symmetric (HS256) or asymmetric (RS256)?
2. Is `NOA` really "number of allowed accounts" or "no-account" boolean?
3. Are routes defined per-method via `WebGet/WebInvoke`, or via
   `<endpoint>` config?
4. What is the licence enforcement strategy — call-counter? expiry date?

(Each question gets answered or escalated as phases progress.)
