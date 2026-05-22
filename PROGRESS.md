# 📋 Progress Tracker

> Updated continuously by the RE engineer. Each phase ships its own PR.

## Phases

- [x] **Phase 1: Setup & Repository Structure** — branch `phase-1-setup`, [PR #1](https://github.com/moain2026/ElectriceAppLastUpdateB3/pull/1) ✅ merged (commit `4239839`)
- [x] **Phase 2: Decompile All DLLs**           — branch `phase-2-decompile`, PR #2 ✅ merged (commit `1e07df2`)
- [x] **Phase 3: WCF Endpoints Deep Analysis**  — branch `phase-3-endpoints`, [PR #3](https://github.com/moain2026/ElectriceAppLastUpdateB3/pull/3) ✅ merged (commit `562096d`)
- [x] **Phase 4: JWT Authentication System**    — branch `phase-4-auth-jwt`, PR #4 (in review)
- [ ] **Phase 5: Data Models + Oracle Schema**  — branch `phase-5-models`, PR #5
- [ ] **Phase 6: Permissions System Forensics** — branch `phase-6-permissions`, PR #6
- [ ] **Phase 7: APK v26 Analysis**             — branch `phase-7-apk`, PR #7
- [ ] **Phase 8: Final Deliverables**           — branch `phase-8-deliverables`, PR #8

## Current status

| Field | Value |
|---|---|
| Active phase  | **Phase 4 — JWT Authentication System** ✅ pushed |
| % complete    | 100% of Phase-4 scope; awaiting PR #4 review |
| Last update   | 2026-05-22 |
| Next step     | Once PR #4 merges → branch `phase-5-models`, DTO precision pass + Oracle-DDL inference + dtos.ts |
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
- [x] Tools verified (monodis ✓, ilspycmd 8.2 ✓, jadx 1.5.1 ✓, apktool 2.9.3 ✓)
- [x] PR #1 opened — https://github.com/moain2026/ElectriceAppLastUpdateB3/pull/1
- [x] PR #1 merged (`4239839`)

## Phase 2 deliverables checklist

- [x] Sync local `main` after PR #1 merge
- [x] Create branch `phase-2-decompile`
- [x] Run `bash tools/03_decompile_dlls.sh` against `MProgService.dll`,
      `OracleServiceMobile.exe`, `License.dll` (Newtonsoft + Oracle.DataAccess
      skipped — OSS, identified by reference table only)
- [x] Inspect ilspycmd output — identify 4 tampered methods in MProgService
      and 3 (+ entire `Defence` class) in OracleServiceMobile
- [x] Author **custom `MetaExtract` .NET 8 tool** (System.Reflection.Metadata)
      to bypass ConfuserEx body tampering — `tools/metadata_extractor/`
- [x] Extract metadata JSON for all 3 proprietary binaries
      → `reverse_engineering/metadata/{MProgService,OracleServiceMobile,License}.json`
- [x] Author **`tools/parse_webinvoke.py`** to decode `[WebInvoke]`/`[WebGet]`
      attribute blobs (ECMA-335 spec) — recovers the 60-endpoint table
- [x] Confirm `ConfusedByAttribute` defined-but-not-applied (evasion technique)
- [x] Confirm target runtime: **.NET Framework 4.5.1**
- [x] Confirm build year **2024**, vendor `YDsoft-773035387`, GUIDs captured
- [x] Survey **68 types** in MProgService (IService1 27 endpoints =
      26 `[OperationContract]` + 1 bare `[WebGet]` root route `Index`,
      IServiceElect 33 operations, 27 DTOs, full JWT pipeline)
- [x] Survey **24 types** in OracleServiceMobile (Defence 14 methods,
      CryptoHelper, AppSetting, IdealRegistry, WinForms hybrid)
- [x] Survey **11 types** in License.dll — confirmed clear VB.NET 2014,
      no ConfuserEx
- [x] Rewrite `analysis/09_OBFUSCATION_NOTES.md` (per-binary damage table)
- [x] Rewrite `analysis/01_WCF_ENDPOINTS.md` (full 60-endpoint table)
- [x] Rewrite `analysis/00_OVERVIEW.md` (Phase-2 confirmed facts)
- [x] Rewrite `analysis/06_LICENSE_SYSTEM.md` (License.dll reverse + Defence names)
- [x] Rewrite `analysis/07_MULTI_TENANT.md` (`appId` mechanism)
- [x] Trim ilspycmd stderr logs to essentials
- [x] Update `PROGRESS.md` and `ANALYSIS_INDEX.md`
- [x] Atomic commits + push `phase-2-decompile`
- [x] Open PR #2

## Phase 3 deliverables checklist

- [x] Switch to branch `phase-3-endpoints` from updated `main`
- [x] Author `tools/generate_phase3.py` — parses `MProgService.json` + decodes
      `[WebInvoke]`/`[WebGet]` blobs into a single structured
      `reverse_engineering/metadata/endpoints.json` (80 KB, 60 ops, 27 DTOs)
- [x] Author `tools/generate_artifacts.py` — single source emits OpenAPI +
      Postman + endpoints.ts (DRY: change mapping once, regenerate all 3)
- [x] Author `tools/generate_endpoint_details.py` — appends per-endpoint
      detail blocks into `analysis/01_WCF_ENDPOINTS.md` (sentinel-bracketed)
- [x] Emit `api_contracts/openapi.yaml` — **OpenAPI 3.0.3, validates clean**
      (via `openapi-spec-validator`)
- [x] Emit `api_contracts/postman_collection.json` — **Postman v2.1,
      validates clean** against the upstream JSON Schema; 11 folders × 60
      requests; JWT auto-inject pre-request on `Login`/`Authenticate`
- [x] Emit `for_main_repo/endpoints.ts` — **compiles clean under TS 5
      `--strict`**; const-asserted, typed by `EndpointDescriptor`
- [x] Expand `analysis/01_WCF_ENDPOINTS.md` — 60 per-endpoint blocks with
      contract/route/auth/params/returns/confidence/source citation
- [x] Update `analysis/00_OVERVIEW.md` — Phase-3 API contracts section,
      verbs distribution, auth boundary, fault-contract count
- [x] Update `ANALYSIS_INDEX.md` (status icons + new tool rows)
- [x] Update `PROGRESS.md` (this section)
- [x] Atomic commits + push `phase-3-endpoints`
- [x] Open PR #3

## Phase 4 deliverables checklist

- [x] Sync local `main` after PR #3 merge (commit `562096d`)
- [x] Create branch `phase-4-auth-jwt`
- [x] Confirm `ilspycmd` cannot read auth-class bodies (`OverflowException`/`Read out of bounds`) → ConfuserEx selective tampering on the auth path
- [x] Author **custom `UserStringDump` .NET 8 tool** (`tools/userstrings_extract/`) — walks the ECMA-335 `#US` heap directly, bypasses tampered IL
- [x] Extract `#US` heap for all 3 proprietary binaries: 390 + 116 + 5 = 511 literals
- [x] **Apply redaction policy** to embedded credential strings (1 in MProgService + 3 in OracleServiceMobile) — structural skeleton preserved, secret material not transcribed
- [x] Survey 20 auth-related types in metadata (AuthTokenService, ITokenBuilder/Validator/CredentialsValidator, DatabaseTokenBuilder/Validator/CredentialsValidator, BasicAuth + 4 ctors, TokenValidationInspector + 5 methods, BehaviorExtension + ServiceBehavior, 4 DTOs)
- [x] Confirm JWT claim names in `#US`: `iat`, `typ`, `UserId` (no `exp` / `sub` / `iss` / `aud`)
- [x] Confirm header presentation: `Authorization: Bearer ` (trailing space at `+0x596e`)
- [x] Document why JWT algorithm name is not in `#US` (jose-jwt enum constant → `ldc.i4` not `ldstr`)
- [x] Document 4 security findings (P0: hard-coded DB creds × 4 copies, P0: SQL injection on auth path, P1: no `exp` claim, P2: `UserId` PK leak)
- [x] Author **`analysis/02_JWT_AUTHENTICATION.md`** — full reconstruction with mermaid sequence diagram, per-claim confidence ratings, aggregate 87.5%
- [x] Author **`for_main_repo/jwt_interceptor.ts`** — Axios interceptor template, single-retry on 401, type-safe `call()` wrapper, compiles clean under `tsc --strict`
- [x] Re-validate `api_contracts/openapi.yaml` (60 paths) + Postman (11 folders) — no regressions from Phase 3
- [x] Update `analysis/00_OVERVIEW.md` — Phase-4 confirmed-facts section
- [x] Update `ANALYSIS_INDEX.md` — 02 + tool row
- [x] Update `PROGRESS.md` (this section)
- [x] Atomic commits (3 commits: tool, dumps, docs) + push `phase-4-auth-jwt`
- [x] Open PR #4

## Discoveries summary (cumulative)

| Category | Count | Confidence |
|---|---:|:---:|
| WCF endpoints documented (surface: name + verb + URI + formats)  | **60 / 60** (27 legacy endpoints [26 ops + 1 root `[WebGet]`] + 33 modern operations) | 95% |
| WCF endpoints with full per-endpoint detail blocks               | **60 / 60** | 95% |
| OpenAPI 3.0 spec emitted + validated                             | ✅ `api_contracts/openapi.yaml` | 95% |
| Postman v2.1 collection emitted + validated                      | ✅ `api_contracts/postman_collection.json` (11 folders × 60 req) | 95% |
| `for_main_repo/endpoints.ts` emitted + strict-TS-checks          | ✅ TS 5 strict-mode clean | 95% |
| HTTP verbs in modern contract                                    | GET 22 · POST 7 · PUT 2 · DELETE 2 | 100% |
| Public operations (no JWT) — total across both contracts          | **7** (modern: `Authenticate`, `Login`, `test`, `GetCallerIdentity`, `Index`; legacy aliases: `Login`, `Authenticate`) | 100% |
| `FaultContract<ServiceFault>` coverage (modern)                  | 32 / 33 | 100% |
| Data models discovered (TypeDef names + fields)                  | **27 / 27** | 95% |
| Permissions decoded (semantics)                                  | 0 / 7   | — |
| SQL queries extracted (bodies obfuscated)                        | 0       | — |
| JWT pipeline classes identified                                  | 5 / 5 (AuthTokenService, DatabaseTokenBuilder, DatabaseTokenValidator, TokenValidationInspector, TokenValidationBehaviorExtension) | 95% |
| JWT signing algorithm                                            | HS-family (85%), most likely HS256 (60%) — `jose-jwt` enum constant in tampered IL; resolution path documented in `02_JWT_AUTHENTICATION.md` §5 | 60–85% |
| JWT claim set                                                    | `iat`, `typ`, `UserId` (no `exp` — server-side TTL via `DatabaseTokenValidator.IsExpired`) | 95% |
| JWT header format                                                | `Authorization: Bearer <token>` (prefix with trailing space — confirmed at `#US +0x596e`) | 100% |
| 🔴 Hard-coded Oracle credentials in shipped binaries             | 4 copies (1 in MProgService.dll, 3 in OracleServiceMobile.exe) — **redacted in repo**, flagged as P0 finding | 100% |
| 🔴 SQL injection on `/Login` + `/ChangePassword`                 | Raw string concat at `#US +0x4c7a` / `+0x4cc2` / `+0x4cf8` — flagged as P0 finding | 100% |
| APK strings extracted                                            | 0       | — |
| Binaries fingerprinted                                           | 7 / 7   | 100% |
| External assembly refs identified                                | 4 (mscorlib, Oracle.DataAccess 1.102.3.0, System.Data, System.ServiceModel) + Newtonsoft.Json, jose-jwt | 95% |
| Target runtime confirmed                                         | **.NET Framework 4.5.1** | 100% |
| Obfuscation confirmed                                            | **ConfuserEx** (via `ConfusedByAttribute` TypeDef + junk-opcode tampering) | 100% |
| Tampered methods catalogued                                      | 7 (MProgService: 4, OracleServiceMobile: 3 + entire Defence) | 100% |
| Multi-tenancy mechanism                                          | **`appId: string` on every WCF operation** | 100% |
| License.dll status                                               | Clear VB.NET 2014, not referenced by modern assemblies → legacy artifact | 95% |
| HDD-serial license algorithm                                     | WMI `Win32_LogicalDisk.VolumeSerialNumber` → `PrimaryKey` (Caesar shifts) → `GetFinalKey` | 95% |

## Open questions (live)

1. ~~Is the JWT symmetric (HS256) or asymmetric (RS256)?~~ → **resolved partially in Phase 4: HS-family with 85% conf, most likely HS256 with 60% conf. Full resolution requires capturing a live token (`Jose.JWT.Headers(jwt)`)** — see `02_JWT_AUTHENTICATION.md §5`.
2. Is `NOA` really "number of allowed accounts" or "no-account" boolean? → Phase 6
3. ~~Are routes defined per-method via `WebGet/WebInvoke`, or via `<endpoint>` config?~~ → **resolved: per-method** (see `01_WCF_ENDPOINTS.md`)
4. What is the license enforcement strategy — call-counter? expiry date? → Phase 6/7 (mostly Phase 7 from APK)
5. What is the exact SQL emitted by `DataBaseHelper`? → Phase 5/7. **Partial answer in Phase 4**: the AUTH-path SQL is recovered verbatim from `#US` (`select * from USER_R where NAME_U='`, `' and PASS='`, `Update USER_R set PASS=`). Phase 5 will catalogue the remainder.
6. What is the base URL of the WCF host? → Phase 7 (`strings.xml` in APK)
7. How is `appId` sourced on the client side? → Phase 7
8. What does `secureId` (added on `IServiceElect.Login`) carry? → Phase 5/7
9. ~~What is the response shape of `Authenticate`/`Login`?~~ → **resolved in Phase 4: the response body is the raw JWT string** (not wrapped in JSON). `Login` returns `Users` and `Authenticate` returns `String` per metadata; the `String` IS the JWT. See `02_JWT_AUTHENTICATION.md §3.4`.
10. **NEW**: `InsertMessage` takes 8 body parameters but declares no `FaultContract` — odd. Phase 5 will inspect the body to confirm whether it's a fire-and-forget or returns a tracking id.
11. **NEW (Phase 4)**: ⚠️ The shipped binaries contain **hard-coded Oracle credentials** (in `#US` heap, redacted in repo). The engineering team must rotate these before any production rollout. See `02_JWT_AUTHENTICATION.md §6.1`.
12. **NEW (Phase 4)**: ⚠️ `/Login` and `/ChangePassword` use raw SQL string concatenation → SQL injection. Server-side patch required. See `02_JWT_AUTHENTICATION.md §6.2`.

(Each question gets answered or escalated as phases progress.)
