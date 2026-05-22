# 00 — Executive Overview

> **Status:** 🟡 updated after Phase 3. Will be finalised in Phase 8.
> **Audience:** the AbbasiTahseel React-Native rewrite team (`app1`).
> **Reading time (current state):** ~7 minutes.

---

## TL;DR

`ElectricCollector` is a field-collection app for an electrical utility. A
technician walks meters, reads them, issues bonds/receipts to customers, and
syncs everything against a central **Oracle DB** through a **self-hosted WCF
service** authenticated by **JWT**.

| Layer | Tech | File |
|-------|------|------|
| Mobile client (current)    | Android (Java, LoopJ/Volley?)        | `binaries/ElectricCollector26.apk` |
| Mobile client (target)     | React Native (rewrite)               | _separate repo `app1`_ |
| Service host               | Windows-Service + WinForms hybrid    | `binaries/OracleServiceMobile.exe` |
| Business logic             | .NET Framework 4.5.1 class library   | `binaries/MProgService.dll` |
| Licensing (legacy / disused?) | VB.NET 2014, .NET 4 Client Profile  | `binaries/License.dll` |
| Auth                       | JWT (jose-jwt)                       | `binaries/jose-jwt.dll` (OSS) |
| Data persistence           | Oracle DB via ODP.NET 1.102.3.0      | `binaries/Oracle.DataAccess.dll` (vendor) |

---

## Confirmed facts (after Phase 2)

### Build / runtime
- **Target runtime:** .NET Framework **4.5.1** (TargetFrameworkAttribute on both MProgService and OracleServiceMobile).
- **Built:** **2024** (AssemblyCopyrightAttribute).
- **Vendor:** **YDsoft-773035387** (AssemblyCompanyAttribute).
- **Assembly GUIDs:**
  - `MProgService`: `91bfb504-3851-4ccd-a30e-29ba41ac7ba6`
  - `OracleServiceMobile`: `1429d5b4-d928-48f2-bd53-f38f3b3b15ae`
- **Oracle client:** **ODP.NET 1.102.3.0** (Oracle 11g/12c-era binary). Implies the back-end DB is **Oracle 11g R2 or 12c** (forward-compat to 19c).
- **License.dll:** an older artefact (2014, VB.NET, .NET 4 Client Profile) — see Phase-2 finding below.

### Service surface — TWO contracts, not one
- `MProgService.IService1`         → 27 operations (legacy contract)
- `MProgServiceElect.IServiceElect` → **33 operations** (modern contract; the one the APK uses)
- Both share the same host process; full table in [`01_WCF_ENDPOINTS.md`](./01_WCF_ENDPOINTS.md).
- 21 operations are common between the two contracts.

### Data layer
- **27 DTOs** under `MProgService.models` — every one confirmed via metadata (no inference needed). Property names exactly match what the legacy brief listed; some had **missed fields** the brief didn't know about (e.g. `Users.error_msg`, `Users.date_server`).
- The DAL is `DataBaseHelper`/`DatabaseManager` inside `MProgService.dll`. Method bodies are **obfuscated** — SQL strings not recoverable from this binary.

### Auth
- **JWT pipeline** is in `MProgService` namespace:
  - `IService1` / `IServiceElect` → declare `[ServiceContract]`.
  - `TokenValidationBehaviorExtension` registers the WCF behaviour.
  - `TokenValidationServiceBehavior` adds…
  - `TokenValidationInspector` (an `IDispatchMessageInspector`) that runs **per request**.
  - Validation delegates to `DatabaseTokenValidator` (impl of `ITokenValidator`).
  - Token construction at login goes `Login → AuthTokenService → DatabaseTokenBuilder` → JWT signed via `jose-jwt`.
  - **`Authenticate` body is obfuscated** — exact algorithm & key recovered in Phase 4 via APK reverse, not from this binary.

### Multi-tenant
- The DTO/method evidence is overwhelming: **every operation takes `appId: string`** as a parameter. **`appId` is the tenant id.**
- The legacy brief's mention of `Dictionary<int, string> ConnetionStrings` is the **server-side** mapping from `appId` → connection string; we expect to find it in `OracleServiceMobile.exe.config` or in a registry-backed config helper (`IdealRegistry` class is suggestive).
- See [`07_MULTI_TENANT.md`](./07_MULTI_TENANT.md).

### Permissions
- 7 flag properties on `Users`: **`NOA, ED, DE, S_K, S_S, REP, SYS`** — all `Int32`.
- Where each is checked = bodies in `Service1.cs` / `ServiceElect.cs` — partially obfuscated. Phase 6 dissects this by combining metadata + client-side hints from the APK.

### Licensing (Phase-2 finding)
- `License.dll` is **clear / unobfuscated** VB.NET from 2014. It contains 3 static methods:
  - `GetHDDSerialN(DriveLetter)` — reads disk volume serial via WMI.
  - `PrimaryKey(HDDSerial)` — deterministic char-by-char transform.
  - `GetFinalKey(PrimaryKey)` — second deterministic transform.
- **No keys / secrets** are hardcoded; everything derives from the HDD serial.
- **However**, `OracleServiceMobile.exe`'s `Defence` class (14 methods) is the *current* anti-tamper / activation layer — its bodies **are** obfuscated. Names visible: `MashineSerialNumber`, `AddKey`, `clear_key`, `d_r` (date-read?), `data_demo`, `bool_to_oct`, `oct_to_bool`, `val_to_bool`, `bool_to_val`, `cut_str`, `text_out`, `ErrorReport2`.
- **Decision:** in line with project rule #3, we **document the algorithm names** and do **not** attempt to reverse the obfuscated bodies. For the rewrite, the licence check is a deployment concern — not a client concern.

### Obfuscation (Phase-2 finding)
- **ConfuserEx confirmed** — `ConfusedByAttribute` type is *defined* (but never *applied*) in both MProgService.dll and OracleServiceMobile.exe.
- **Scope:** selective body tampering on 4 methods in `MProgService.dll`, 3 methods in `OracleServiceMobile.exe`, plus all bodies in `Defence`. The rest of the binaries decompile cleanly.
- **Mitigation:** our custom `MetaExtract` tool reads metadata only and bypasses body tampering entirely. 100% of the public surface is therefore recoverable.
- Full detail in [`09_OBFUSCATION_NOTES.md`](./09_OBFUSCATION_NOTES.md).

### API contracts (Phase-3 finding)
- **60 endpoints** documented end-to-end (33 modern + 27 legacy) with HTTP verb, URI template, body style, request/response format, fault contracts, parameter location (query vs body) and return type — all recovered from binary metadata, **no manual transcription**.
- **HTTP verb distribution** (modern contract): **GET** 22 (66%), **POST** 7 (21%), **PUT** 2 (6%), **DELETE** 2 (6%).
- **Auth boundary:** 30 of 33 operations require `Authorization: Bearer <jwt>`; the 3 public ops are `Authenticate`, `Login`, `test`.
- **FaultContract:** every non-bootstrap op declares `MProgService.models.ServiceFault` — the response envelope for business errors (Phase 3 deliverable: `ServiceFault` schema landed in `api_contracts/openapi.yaml`).
- **Deliverables:** `api_contracts/openapi.yaml` (OpenAPI 3.0.3, validates clean), `api_contracts/postman_collection.json` (Postman v2.1 with JWT auto-inject on Login/Authenticate), `for_main_repo/endpoints.ts` (TS 5 `--strict` compiles clean).
- Full per-endpoint detail in [`01_WCF_ENDPOINTS.md`](./01_WCF_ENDPOINTS.md).

---

## Open questions (live)

| # | Question | Where it will be answered |
|---|----------|---------------------------|
| 1 | JWT signing algorithm + key source | Phase 4 (cross-check with APK login flow) |
| 2 | Exact SQL queries (table names, joins) | Phase 5 + APK client SQLite mirror + DBA |
| 3 | `appId → connectionString` mapping mechanism | Phase 7 (APK) + post-mortem of `.exe.config` |
| 4 | Base URL of the WCF host (`Service1.svc` mounting path) | Phase 7 (APK) |
| 5 | Is `IService1` still routed or only `IServiceElect`? | Phase 7 (which one does the APK call?) |
| 6 | Meaning of `NOA` (number-of-accounts vs no-account boolean) | Phase 6 — search for usages |

---

## Phase-by-phase outcomes

| Phase | Key deliverable | Status | Confidence |
|-------|-----------------|:------:|:----------:|
| 1 | Lab structure + tooling                                                  | 🟢 done    | 95% |
| 2 | C# decompile + metadata extraction for 3 priority assemblies             | 🟢 done    | 95% |
| 3 | 60/60 endpoints documented; OpenAPI 3.0 (valid); Postman v2.1; endpoints.ts | 🟢 done    | 95% |
| 4 | JWT scheme + interceptor template                                        | ⚪ next    | — |
| 5 | 27 models + Oracle DDL + ERD + TS types                                  | ⚪         | — |
| 6 | Permissions matrix                                                       | ⚪         | — |
| 7 | APK v26 deep dive                                                        | ⚪         | — |
| 8 | `for_main_repo/` packaged + executive summary                            | ⚪         | — |
