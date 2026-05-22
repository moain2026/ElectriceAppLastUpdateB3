# 00 — Executive Overview

> **Status:** 🟡 updated after Phase 5. Will be finalised in Phase 8.
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
- `MProgService.IService1`         → **27 endpoints** (legacy contract): **26 `[OperationContract]`** + **1 bare `[WebGet]` root route** (`Index` bound to `GET /`)
- `MProgServiceElect.IServiceElect` → **33 operations** (modern contract; the one the APK uses) — all carry `[OperationContract]` **and** `[Web*Attribute]`
- Both share the same host process; full table in [`01_WCF_ENDPOINTS.md`](./01_WCF_ENDPOINTS.md).
- 21 operation names are common between the two contracts.

> **Terminology** — in this report:
> - **Operation** = a method carrying `[OperationContract]` (the formal WCF SOAP/REST contract surface).
> - **Endpoint** = any callable HTTP route on the host. Every operation is an endpoint, but a method can also be an endpoint via `[WebGet]`/`[WebInvoke]` alone (e.g. `IService1.Index`).
>
> When the binary distinction matters — e.g. when generating SOAP-style proxies or counting WSDL ops — use the **26 + 1** decomposition for `IService1`. For HTTP client work (Phase 4+) the 27 endpoints are what matters.

### Data layer
- **27 DTOs** under `MProgService.models` — every one confirmed via metadata (no inference needed). Property names exactly match what the legacy brief listed; some had **missed fields** the brief didn't know about (e.g. `Users.error_msg`, `Users.date_server`).
- The DAL is `DataBaseHelper`/`DatabaseManager` inside `MProgService.dll`. Method bodies are **obfuscated** in IL — but Phase 4's `#US`-heap mining recovered **~75 SQL templates** verbatim, and Phase 5 turned them into an inferred Oracle DDL.

### Data layer — Phase 5 findings (new)
- **27 / 27 DTOs catalogued** in `analysis/03_DATA_MODELS.md` (15 row-shaped, 12 envelope/aggregate, 92 % aggregate confidence) and emitted as `for_main_repo/dtos.ts` (TS 5 `--strict` compiles clean).
- **12 Oracle tables inferred** end-to-end with PK candidates and JOIN-derived FK suggestions: `USER_R`, `USER_MNATK`, `data_acc`, `GRP`, `Mkb2`, `amlh`, `titl`, `DATA_D`, `DATA_M`, `data_H`, `SNDK_A`, `SNDS_A`, `red`, `sendsms`, `DATA_S`, `t_qyod` (+ view `V_ACCOUNT_D`). DDL in `schemas/inferred_oracle_schema.sql`, ER diagram in `schemas/erd.mermaid`.
- **ODP.NET 1.102.3.0** confirmed via `DataBaseHelper.con : Oracle.DataAccess.Client.OracleConnection`; multi-tenant routing via `DataBaseHelper.ConnetionStrings : Dictionary<Int32, String>` (the integer key is the `noc` / tenant id — same as `appId` story for the modern contract).
- **Two DALs coexist**: the *modern* `DatabaseManager` (parameterised `Dictionary<string,object>` binds) is *present in the binary* but the dominant production path is the *legacy* `DataBaseHelper` with string-concatenated SQL — this is the root cause of SEC-AUTH-001 (Login SQL injection) and the reason ~75 SQL fragments end in bare `=` / `IN(` / `<'`.
- **No application-tier pagination** (zero `ROWNUM` / `OFFSET FETCH`) — whole result sets returned. Action item for `app1` gateway: add pagination wrap.
- Full details in [`05_ORACLE_INTEGRATION.md`](./05_ORACLE_INTEGRATION.md) (91 % aggregate confidence).

### Auth
- **JWT pipeline** is in `MProgService` namespace:
  - `IService1` / `IServiceElect` → declare `[ServiceContract]`.
  - `TokenValidationBehaviorExtension` registers the WCF behaviour.
  - `TokenValidationServiceBehavior` adds…
  - `TokenValidationInspector` (an `IDispatchMessageInspector`) that runs **per request**.
  - Validation delegates to `DatabaseTokenValidator` (impl of `ITokenValidator`).
  - Token construction at login goes `Login → AuthTokenService → DatabaseTokenBuilder` → JWT signed via `jose-jwt` **v5.0.0.0**.
  - **`Authenticate` body is obfuscated** — see Phase 4 below for what we recovered through `#US`-heap mining.

### Auth — Phase-4 findings (new)
- **JWT library:** `jose-jwt v5.0.0.0` (confirmed via `AssemblyReferences[7]`).
- **Header presentation:** `Authorization: Bearer <token>` — confirmed in `#US` heap at offsets `+0x43` (`Authorization`) and `+0x596e` (`"Bearer "` with trailing space).
- **JWT claims confirmed:** `iat`, `typ`, `UserId` (offsets `+0xa0d` / `+0x5918` / `+0x5960`). **No `exp`** — TTL is enforced server-side by `DatabaseTokenValidator.IsExpired(Token)` using `DefaultSecondsUntilTokenExpires` against `Token.CreateDate`.
- **JWT algorithm:** HS-family with 85% confidence, most likely HS256 with 60% confidence. The algorithm enum is supplied via `ldc.i4` in the (tampered) IL, not `ldstr`, so it does not appear in `#US`. Definitive resolution requires capturing a live token. See `02_JWT_AUTHENTICATION.md §5`.
- **`BasicAuth` fallback:** `MProgService.Business.BasicAuth` (4 ctors, `Base64UrlDecode`) — shape consistent with RFC 7617 Basic Auth, presumably for the WinForms admin app. The RN client should never use this path.
- 🔴 **P0 security finding:** the Oracle TNS connection string (host, port, service name, user id, **plain password**) is embedded in `MProgService.dll` (`#US +0x52cb`, 1 copy) and `OracleServiceMobile.exe` (`#US +0x287`, `+0x3d0`, `+0x519`, 3 copies). The secret values are **redacted in this repo** per the RE golden rule, but the engineering team must rotate them before production rollout. See `02_JWT_AUTHENTICATION.md §6.1`.
- 🔴 **P0 security finding:** `/Login` and `/ChangePassword` use raw SQL string concatenation (templates at `#US +0x4c7a`, `+0x4cc2`, `+0x4cf8`) — classic SQL injection. Server-side patch required. See `02_JWT_AUTHENTICATION.md §6.2`.

### Multi-tenant
- The DTO/method evidence is overwhelming: **every operation takes `appId: string`** as a parameter. **`appId` is the tenant id.**
- The legacy brief's mention of `Dictionary<int, string> ConnetionStrings` is the **server-side** mapping from `appId` → connection string; we expect to find it in `OracleServiceMobile.exe.config` or in a registry-backed config helper (`IdealRegistry` class is suggestive).
- See [`07_MULTI_TENANT.md`](./07_MULTI_TENANT.md).

### Permissions
- 7 flag properties on `Users`: **`NOA, ED, DE, S_K, S_S, REP, SYS`** — all `Int32`.
- Where each is checked = bodies in `Service1.cs` / `ServiceElect.cs` — partially obfuscated. Phase 6 dissects this by combining metadata + client-side hints from the APK.

### Permissions — Phase 6 findings (new)
- **Two-tier model** discovered: **Tier-A** = 7 `Int32` capability flags on `USER_R` rows; **Tier-B** = per-place ACL via `USER_MNATK` junction table with `RED` (read) and `SDAD` (write) flags keyed by `(NOU, no_mstlm)`.
- Both tiers are AND-composed: `Effective(action) = Tier-A(flag) AND Tier-B(place)`. `SYS=1` short-circuits Tier-B (75 % conf).
- Flag→endpoint matrix produced (37 endpoint↔flag mappings) in `analysis/04_PERMISSIONS_SYSTEM.md §3.2`.
- 🔴 **`NOA` overload antipattern**: same column name = capability flag *and* till-account-id (`SNDK_A.no_box = USER_R.NOA`). `app1` must split semantics.
- 🔴 **Tier-B SQL injection** inherits from SEC-AUTH-001: the `USER_MNATK` subqueries concatenate caller's `NOU` as a string.
- Deliverables: `analysis/04_PERMISSIONS_SYSTEM.md` (86 % conf), `for_main_repo/permissions_matrix.md` (RN-ready, TS `can(me, perm)` helper).

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
- **60 endpoints** documented end-to-end (33 modern operations + 27 legacy endpoints = 26 legacy `[OperationContract]` + 1 legacy root `[WebGet]`) with HTTP verb, URI template, body style, request/response format, fault contracts, parameter location (query vs body) and return type — all recovered from binary metadata, **no manual transcription**.
- **HTTP verb distribution** (modern contract): **GET** 22 (66%), **POST** 7 (21%), **PUT** 2 (6%), **DELETE** 2 (6%).
- **Auth boundary:** 53 of 60 endpoints require `Authorization: Bearer <jwt>`. **The 7 public endpoints** are (modern) `Authenticate`, `Login`, `test`, `GetCallerIdentity`, `Index`; (legacy aliases) `Login`, `Authenticate`. Full rationale in `01_WCF_ENDPOINTS.md → Public endpoints rationale`.
- **FaultContract:** every non-bootstrap op declares `MProgService.models.ServiceFault` — the response envelope for business errors (Phase 3 deliverable: `ServiceFault` schema landed in `api_contracts/openapi.yaml`).
- **Deliverables:** `api_contracts/openapi.yaml` (OpenAPI 3.0.3, validates clean), `api_contracts/postman_collection.json` (Postman v2.1 with JWT auto-inject on Login/Authenticate), `for_main_repo/endpoints.ts` (TS 5 `--strict` compiles clean).
- Full per-endpoint detail in [`01_WCF_ENDPOINTS.md`](./01_WCF_ENDPOINTS.md).

---

## Open questions (live)

| # | Question | Where it will be answered |
|---|----------|---------------------------|
| 1 | ~~JWT signing algorithm + key source~~ | **Partial in Phase 4**: HS-family (85%), HS256 (60%); definitive answer needs a live-token capture. Key source: `DatabaseTokenBuilder.BuildSecureToken(TokenSize)` — symmetric secret regenerated server-side. |
| 2 | ~~Exact SQL queries (table names, joins)~~ | **Resolved Phase 5**: ~75 SQL templates recovered from `#US` heap, mapped to 12 tables + FK graph. See `05_ORACLE_INTEGRATION.md`. Live-DB validation still pending. |
| 3 | `appId → connectionString` mapping mechanism | Phase 7 (APK) + post-mortem of `.exe.config` |
| 4 | Base URL of the WCF host (`Service1.svc` mounting path) | Phase 7 (APK) |
| 5 | Is `IService1` still routed or only `IServiceElect`? | Phase 7 (which one does the APK call?) |
| 6 | ~~Meaning of `NOA` (number-of-accounts vs no-account boolean)~~ | **Resolved Phase 6**: `NOA` is overloaded — capability flag (`NOA > 0` ⇒ accounts visible) *and* till-account-id. App1 must split. |
| 7 | 🔴 Hard-coded DB credentials in distributed binaries | **Surfaced in Phase 4 §6.1** — escalate to engineering team |
| 8 | 🔴 SQL injection on `/Login`, `/ChangePassword` | **Surfaced in Phase 4 §6.2** — escalate to engineering team |

---

## Phase-by-phase outcomes

| Phase | Key deliverable | Status | Confidence |
|-------|-----------------|:------:|:----------:|
| 1 | Lab structure + tooling                                                  | 🟢 done    | 95% |
| 2 | C# decompile + metadata extraction for 3 priority assemblies             | 🟢 done    | 95% |
| 3 | 60/60 endpoints documented; OpenAPI 3.0 (valid); Postman v2.1; endpoints.ts | 🟢 done    | 95% |
| 4 | JWT scheme reconstructed + Axios interceptor template                    | 🟢 done    | 87.5% |
| 5 | 27 models + Oracle DDL + ERD + TS types                                  | 🟢 done    | 91.5% |
| 6 | Permissions matrix (Tier-A flags + Tier-B per-place ACL)                | 🟢 done    | 86%   |
| 7 | APK v26 deep dive                                                        | ⚪         | — |
| 8 | `for_main_repo/` packaged + executive summary                            | ⚪         | — |
