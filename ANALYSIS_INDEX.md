# 📑 Analysis Index

> Master index for every artifact produced by the RE lab.
> This file is updated at the end of every phase.

---

## 📊 Analysis documents (`analysis/`)

| # | Document | Phase | Status |
|---|----------|:-----:|:------:|
| 00 | [`00_OVERVIEW.md`](./analysis/00_OVERVIEW.md)                 | all | 🟢 Phase-2 facts landed |
| 01 | [`01_WCF_ENDPOINTS.md`](./analysis/01_WCF_ENDPOINTS.md)        | 3   | 🟢 full 60-endpoint table + per-endpoint detail blocks (Phase 3) |
| 02 | [`02_JWT_AUTHENTICATION.md`](./analysis/02_JWT_AUTHENTICATION.md) | 4 | 🟢 full WCF auth pipeline reconstructed · jose-jwt v5.0.0.0 · claims `iat`/`typ`/`UserId` confirmed · 4 security findings (Phase 4) |
| 03 | [`03_DATA_MODELS.md`](./analysis/03_DATA_MODELS.md)            | 5   | 🟢 27/27 DTOs catalogued · TS optionality from `[DataMember]` · 92 % conf (Phase 5) |
| 04 | [`04_PERMISSIONS_SYSTEM.md`](./analysis/04_PERMISSIONS_SYSTEM.md) | 6 | 🟢 7 Tier-A flags + Tier-B `USER_MNATK` ACL · endpoint map · 86 % conf (Phase 6) |
| 05 | [`05_ORACLE_INTEGRATION.md`](./analysis/05_ORACLE_INTEGRATION.md) | 5 | 🟢 ODP.NET 1.102.3.0 · 12 inferred tables · FK graph · ~75 SQL templates · 91 % conf (Phase 5) |
| 06 | [`06_LICENSE_SYSTEM.md`](./analysis/06_LICENSE_SYSTEM.md)      | 2-3 | 🟢 License.dll fully reversed · Defence names listed |
| 07 | [`07_MULTI_TENANT.md`](./analysis/07_MULTI_TENANT.md)          | 3   | 🟡 appId confirmed · resolution path inferred |
| 08 | [`08_ERROR_HANDLING.md`](./analysis/08_ERROR_HANDLING.md)      | 3   | ⚪ pending |
| 09 | [`09_OBFUSCATION_NOTES.md`](./analysis/09_OBFUSCATION_NOTES.md) | 2  | 🟢 ConfuserEx confirmed · per-binary damage table |
| 10 | [`10_APK_V26_ANALYSIS.md`](./analysis/10_APK_V26_ANALYSIS.md)  | 7   | 🟢 manifest decoded · baseUrl pinned · loopj HTTP · 185 yd classes · 88 % conf (Phase 7) |

Status legend: ⚪ pending  · 🟡 stub/WIP  · 🟢 complete · 🔵 reviewed

---

## 🔬 Raw reverse-engineering output (`reverse_engineering/`)

| Path | Source | Tool | Phase |
|------|--------|------|:-----:|
| `il_dumps/MProgService.il`       | `binaries/MProgService.dll`      | monodis    | 2 |
| `il_dumps/OracleServiceMobile.il`| `binaries/OracleServiceMobile.exe` | monodis  | 2 |
| `il_dumps/License.il`            | `binaries/License.dll`            | monodis   | 2 |
| `metadata/dtos.json`             | 27-DTO catalogue (is_datacontract, property_count, datamember_count, properties[], oracle_table_hint) — Phase-5 codegen source-of-truth. | `generate_phase5.py` | 5 |
| `decompiled_csharp/MProgService/`        | `binaries/MProgService.dll`       | ilspycmd | 2 |
| `decompiled_csharp/OracleServiceMobile/` | `binaries/OracleServiceMobile.exe`| ilspycmd | 2 |
| `decompiled_csharp/License/`             | `binaries/License.dll`            | ilspycmd | 2 |
| `apk_decompiled/`                | `binaries/ElectricCollector26.apk`| JADX      | 7 |
| `apk_decompiled/endpoint_strings.txt` | `binaries/ElectricCollector26.apk` `classes*.dex` | `strings` + grep | 7 |
| `apk_decompiled/yd_classes.txt`     | `binaries/ElectricCollector26.apk` `classes*.dex` | `strings` + grep | 7 |
| `userstrings/MProgService.userstrings.json`     | `binaries/MProgService.dll`        | `UserStringDump` (.NET 8) — `#US` heap walker | 4 |
| `userstrings/OracleServiceMobile.userstrings.json` | `binaries/OracleServiceMobile.exe` | `UserStringDump`                              | 4 |
| `userstrings/License.userstrings.json`          | `binaries/License.dll`             | `UserStringDump`                              | 4 |

---

## 🗄️ Schemas (`schemas/`)

| File | Description | Phase | Status |
|------|-------------|:-----:|:------:|
| `inferred_oracle_schema.sql`  | 12 inferred Oracle `CREATE TABLE`s + indexes + FK suggestions, derived from `#US`-recovered SQL + DTO projections. | 5 | 🟢 |
| `erd.mermaid`                 | Entity-relationship diagram (Mermaid `erDiagram`).             | 5 | 🟢 |
| `tables_relationships.md`     | DTO ↔ table ↔ endpoint mapping matrix w/ confidence + source signal. | 5 | 🟢 |

---

## 📡 API contracts (`api_contracts/`)

| File | Description | Phase | Status |
|------|-------------|:-----:|:------:|
| `openapi.yaml`           | OpenAPI 3.0.3 spec for all 60 WCF endpoints (33 modern + 27 deprecated). **Validates clean** via `openapi-spec-validator`. | 3 | 🟢 |
| `postman_collection.json`| Postman v2.1 collection — 11 folders × 60 requests, `{{baseUrl}}/{{appId}}/{{token}}/{{secureId}}` variables, JWT auto-inject pre-request on Login/Authenticate. | 3 | 🟢 |
| `typescript_types.ts`    | TypeScript types from C# DTOs (see `for_main_repo/dtos.ts`) | 5 | 🟢 emitted as `for_main_repo/dtos.ts` |

---

## 🎁 For main repo (`for_main_repo/`)

| File | Purpose | Phase | Status |
|------|---------|:-----:|:------:|
| `README.md`              | How to copy artefacts into `app1` | 8 | ⚪ |
| `endpoints.ts`           | Const map of all 60 endpoints + `EndpointDescriptor` interface. Compiles clean under TS 5 `--strict`. | 3 | 🟢 |
| `jwt_interceptor.ts`     | Axios interceptor template — Bearer header attach, single-retry 401 reauth, typed `call()` wrapper, compiles clean under `tsc --strict` | 4 | 🟢 |
| `permissions_matrix.md`  | RN-ready Tier-A flag table + endpoint map + Tier-B helper + TS `can(me, perm)` helper | 6 | 🟢 |
| `dtos.ts`                | All 27 TS interfaces (Users, Accounts, ItemBonds, ItemReading, AuthData, Credentials, …). Optionality follows `[DataMember]` (mandatory) vs Newtonsoft default (optional). `WcfDateTime = string` alias for ISO-8601 wire format. Compiles clean under TS 5 `--strict`. | 5 | 🟢 |

---

## 🛠️ Tools (`tools/`)

| Script | Purpose |
|--------|---------|
| `01_setup_tools.sh`        | Install monodis, ilspycmd, jadx, apktool, python deps. Idempotent. |
| `02_extract_il.sh`         | Dump IL for every `.dll`/`.exe` in `binaries/`. |
| `03_decompile_dlls.sh`     | Decompile DLLs/EXE to C# via `ilspycmd`. |
| `04_decompile_apk.sh`      | Decompile the APK via JADX + extract resources via apktool. |
| `05_generate_typescript.py`| Convert C# DTOs to TypeScript interfaces. |
| `metadata_extractor/`      | Custom .NET 8 tool — reads ECMA-335 metadata tables to bypass ConfuserEx body tampering (added Phase 2). |
| `parse_webinvoke.py`       | ECMA-335 custom-attribute blob decoder for `[WebInvoke]`/`[WebGet]` (added Phase 2). |
| `generate_phase3.py`       | Parses MProgService.json + decodes blobs into a structured `reverse_engineering/metadata/endpoints.json` (added Phase 3). |
| `generate_artifacts.py`    | Single source emits `api_contracts/openapi.yaml` + `api_contracts/postman_collection.json` + `for_main_repo/endpoints.ts` from `endpoints.json` (added Phase 3). |
| `generate_endpoint_details.py` | Emits per-endpoint detail blocks (modern + legacy) for `01_WCF_ENDPOINTS.md` (added Phase 3). |
| `splice_endpoint_details.py`   | Idempotently splices the output of `generate_endpoint_details.py` between sentinels in `01_WCF_ENDPOINTS.md` (added Phase 3). |
| `userstrings_extract/`         | Custom .NET 8 tool — walks the ECMA-335 `#US` (UserString) heap directly to recover every `ldstr`-able literal even when method bodies are damaged by ConfuserEx (added Phase 4). |
| `generate_phase5.py`           | Single-source Phase-5 codegen: reads `metadata/MProgService.json` + `metadata/endpoints.json` + `userstrings/MProgService.userstrings.json` → emits `metadata/dtos.json`, `for_main_repo/dtos.ts`, `schemas/inferred_oracle_schema.sql`, `schemas/tables_relationships.md`, `schemas/erd.mermaid` (added Phase 5). |

---

## 🔑 Cross-references

Whenever an analysis document quotes IL or C#, it links back to the exact
file/line under `reverse_engineering/`. Whenever a SQL hypothesis is made,
it links to the model in `analysis/03_DATA_MODELS.md`.

---

## 📜 Confidence baseline

We track **per-claim confidence** in each analysis doc. Aggregate confidence
is reported in `PROGRESS.md → Discoveries summary`. Target average ≥ 85%.
