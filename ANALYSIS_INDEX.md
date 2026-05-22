# 📑 Analysis Index

> Master index for every artifact produced by the RE lab.
> This file is updated at the end of every phase.

---

## 📊 Analysis documents (`analysis/`)

| # | Document | Phase | Status |
|---|----------|:-----:|:------:|
| 00 | [`00_OVERVIEW.md`](./analysis/00_OVERVIEW.md)                 | all | 🟢 Phase-2 facts landed |
| 01 | [`01_WCF_ENDPOINTS.md`](./analysis/01_WCF_ENDPOINTS.md)        | 3   | 🟢 full 60-endpoint table (Phase 2 surface) · deep dive Phase 3 |
| 02 | [`02_JWT_AUTHENTICATION.md`](./analysis/02_JWT_AUTHENTICATION.md) | 4 | ⚪ pending |
| 03 | [`03_DATA_MODELS.md`](./analysis/03_DATA_MODELS.md)            | 5   | ⚪ pending |
| 04 | [`04_PERMISSIONS_SYSTEM.md`](./analysis/04_PERMISSIONS_SYSTEM.md) | 6 | ⚪ pending |
| 05 | [`05_ORACLE_INTEGRATION.md`](./analysis/05_ORACLE_INTEGRATION.md) | 5 | ⚪ pending |
| 06 | [`06_LICENSE_SYSTEM.md`](./analysis/06_LICENSE_SYSTEM.md)      | 2-3 | 🟢 License.dll fully reversed · Defence names listed |
| 07 | [`07_MULTI_TENANT.md`](./analysis/07_MULTI_TENANT.md)          | 3   | 🟡 appId confirmed · resolution path inferred |
| 08 | [`08_ERROR_HANDLING.md`](./analysis/08_ERROR_HANDLING.md)      | 3   | ⚪ pending |
| 09 | [`09_OBFUSCATION_NOTES.md`](./analysis/09_OBFUSCATION_NOTES.md) | 2  | 🟢 ConfuserEx confirmed · per-binary damage table |
| 10 | [`10_APK_V26_ANALYSIS.md`](./analysis/10_APK_V26_ANALYSIS.md)  | 7   | ⚪ pending |

Status legend: ⚪ pending  · 🟡 stub/WIP  · 🟢 complete · 🔵 reviewed

---

## 🔬 Raw reverse-engineering output (`reverse_engineering/`)

| Path | Source | Tool | Phase |
|------|--------|------|:-----:|
| `il_dumps/MProgService.il`       | `binaries/MProgService.dll`      | monodis    | 2 |
| `il_dumps/OracleServiceMobile.il`| `binaries/OracleServiceMobile.exe` | monodis  | 2 |
| `il_dumps/License.il`            | `binaries/License.dll`            | monodis   | 2 |
| `decompiled_csharp/MProgService/`        | `binaries/MProgService.dll`       | ilspycmd | 2 |
| `decompiled_csharp/OracleServiceMobile/` | `binaries/OracleServiceMobile.exe`| ilspycmd | 2 |
| `decompiled_csharp/License/`             | `binaries/License.dll`            | ilspycmd | 2 |
| `apk_decompiled/`                | `binaries/ElectricCollector26.apk`| JADX      | 7 |

---

## 🗄️ Schemas (`schemas/`)

| File | Description | Phase |
|------|-------------|:-----:|
| `inferred_oracle_schema.sql`  | Reverse-inferred Oracle DDL from C# DTOs | 5 |
| `erd.mermaid`                 | Entity-relationship diagram              | 5 |
| `tables_relationships.md`     | Narrative description of FKs/joins       | 5 |

---

## 📡 API contracts (`api_contracts/`)

| File | Description | Phase |
|------|-------------|:-----:|
| `openapi.yaml`           | OpenAPI 3.0 spec for the 27 WCF endpoints | 3 |
| `postman_collection.json`| Postman v2.1 collection                    | 3 |
| `typescript_types.ts`    | TypeScript types from C# DTOs              | 5 |

---

## 🎁 For main repo (`for_main_repo/`)

| File | Purpose | Phase |
|------|---------|:-----:|
| `README.md`              | How to copy artefacts into `app1` | 8 |
| `endpoints.ts`           | Const map of all endpoints + types | 3 |
| `jwt_interceptor.ts`     | Axios interceptor template | 4 |
| `permissions_matrix.md`  | Human reference for permission flags | 6 |
| `bond_dto.ts`            | Bond model | 5 |
| `reading_dto.ts`         | Reading model | 5 |
| `user_dto.ts`            | User model | 5 |

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

---

## 🔑 Cross-references

Whenever an analysis document quotes IL or C#, it links back to the exact
file/line under `reverse_engineering/`. Whenever a SQL hypothesis is made,
it links to the model in `analysis/03_DATA_MODELS.md`.

---

## 📜 Confidence baseline

We track **per-claim confidence** in each analysis doc. Aggregate confidence
is reported in `PROGRESS.md → Discoveries summary`. Target average ≥ 85%.
