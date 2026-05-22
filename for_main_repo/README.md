# 🎁 `for_main_repo/` — Drop-in Artefacts for `app1`

> **Status:** 🟢 complete — all 7 phases of forensic reverse-engineering finished.
> **Audience:** the engineer building the React-Native rewrite (`app1`) of the
> legacy `ElectricCollector28` system.
>
> This folder is the **only** thing the `app1` team needs to look at.
> Everything else in this repository is *evidence* and *reasoning* — this folder
> is the **answer**.

---

## TL;DR

```
for_main_repo/
├── README.md             ← you are here
├── endpoints.ts          ← 60 endpoints, const-asserted, typed (TS 5 strict ✅)
├── dtos.ts               ← 27 DTOs as TS interfaces (TS 5 strict ✅)
├── jwt_interceptor.ts    ← Axios interceptor template (TS 5 strict ✅)
└── permissions_matrix.md ← Tier-A + Tier-B permission gating for RN UI
```

Copy these 4 files into `app1`, install `axios` + `zod` (optional), and you
have the entire API surface ready to use.

---

## 1. Copy guide

```bash
# From the cloned ElectriceAppLastUpdateB3 repo root:
cp for_main_repo/endpoints.ts          path/to/app1/src/api/endpoints.ts
cp for_main_repo/dtos.ts               path/to/app1/src/api/dtos.ts
cp for_main_repo/jwt_interceptor.ts    path/to/app1/src/api/jwt.ts
cp for_main_repo/permissions_matrix.md path/to/app1/docs/permissions.md
```

Then in `app1`:

```bash
cd path/to/app1
yarn add axios
# Optional but recommended:
yarn add zod react-native-mmkv
```

---

## 2. The 4 artefacts in detail

### 2.1 `endpoints.ts` — the full API surface

- **What:** A const-asserted `ENDPOINTS` map covering **all 60 server endpoints**
  (33 modern `IServiceElect` ops + 27 legacy `IService1` aliases). Each entry has:
  - `name`, `verb` (`GET`/`POST`/`PUT`/`DELETE`), `path`, `requestStyle`,
    `responseStyle`, `bodyType?`, `isPublic` (true for the 7 no-JWT endpoints).
- **How to use:**
  ```ts
  import { ENDPOINTS, EndpointDescriptor } from './api/endpoints';
  // ENDPOINTS.GetListAccounts.path === '/GetListAccounts'
  // ENDPOINTS.GetListAccounts.verb === 'GET'
  // ENDPOINTS.GetListAccounts.isPublic === false
  ```
- **Source:** Phase 3 — emitted by `tools/generate_artifacts.py` from
  `reverse_engineering/metadata/endpoints.json`. Stays in lock-step with the
  shipped `api_contracts/openapi.yaml` (OpenAPI 3.0.3, validates clean) and
  `api_contracts/postman_collection.json` (Postman v2.1).
- **TypeScript:** Compiles clean under TS 5 `--strict`.

### 2.2 `dtos.ts` — all 27 data models

- **What:** 27 TypeScript interfaces, one per server DTO (`Users`, `Accounts`,
  `ItemBonds`, `ItemReading`, `UserPlaces`, `AuthData`, `Credentials`,
  `Token`, `ServiceFault`, …). Optionality follows the original `[DataMember]`
  / Newtonsoft serialization contract precisely:
  - **Mandatory** = property carried `[DataMember]` in the .NET source.
  - **Optional (`?`)** = Newtonsoft default serialization with no attribute.
- **Special types:**
  ```ts
  export type WcfDateTime = string;  // ISO-8601 over the wire
  ```
- **How to use:**
  ```ts
  import type { Users, ItemBonds, ItemReading } from './api/dtos';

  const me: Users | null = await login(creds);
  if (me) { console.log(me.NAME_U, me.access_token); }
  ```
- **Source:** Phase 5 — emitted by `tools/generate_phase5.py` from
  `reverse_engineering/metadata/MProgService.json` (the 27 DTOs in the
  `MProgService.models` namespace).
- **TypeScript:** Compiles clean under TS 5 `--strict`.

### 2.3 `jwt_interceptor.ts` — drop-in Axios interceptor

- **What:** A reusable interceptor pair (`request` adds `Authorization: Bearer
  <token>`; `response` retries once on 401 after refreshing the token).
- **API:**
  ```ts
  installJwtInterceptors(client, {
    getToken,         // () => Promise<string | null>
    setToken,         // (t: string) => Promise<void>
    reauth,           // () => Promise<string | null>  — calls /Authenticate again
    onUnrecoverable,  // () => void  — wipe token + redirect to LoginScreen
  });
  ```
  Plus a typed `call<E>(client, endpoint, args)` wrapper that uses
  `ENDPOINTS[E]` for verb/path/auth rules — and skips the Bearer header on the
  7 `isPublic: true` endpoints (`Authenticate`, `Login`, `test`,
  `GetCallerIdentity`, `Index`, plus legacy aliases).
- **Source:** Phase 4 — based on the reconstructed WCF + JWT pipeline
  (`analysis/02_JWT_AUTHENTICATION.md`).
- **TypeScript:** Compiles clean under TS 5 `--strict`.

### 2.4 `permissions_matrix.md` — Tier-A + Tier-B gating

- **What:** A short, RN-ready document on:
  1. The **7 Tier-A capability flags** on `Users` (`NOA, ED, DE, S_K, S_S, REP, SYS`).
  2. The **Tier-B per-place ACL** via `UserPlaces` / `USER_MNATK` (`RED`, `SDAD`).
  3. A `can(me, permission)` TS helper ready to paste into
     `app1/src/auth/permissions.ts`.
  4. The endpoint↔flag map (so any 403 is debuggable in seconds).
- **Source:** Phase 6 — derives from
  `analysis/04_PERMISSIONS_SYSTEM.md` (86 % conf).

---

## 3. End-to-end wiring example

Putting the 4 artefacts together in `app1`:

```ts
// app1/src/api/client.ts
import axios from 'axios';
import { ENDPOINTS } from './endpoints';
import { installJwtInterceptors, call } from './jwt';
import type { Users, Accounts } from './dtos';
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV();

export const apiClient = axios.create({
  baseURL: storage.getString('baseUrl') ?? 'http://192.168.0.100:3000/',
  timeout: 30000,
});

installJwtInterceptors(apiClient, {
  getToken:  async () => storage.getString('jwt') ?? null,
  setToken:  async (t) => storage.set('jwt', t),
  reauth:    async () => { /* call Authenticate again */ return null; },
  onUnrecoverable: () => { storage.delete('jwt'); /* navigate to LoginScreen */ },
});

// Type-safe endpoint call:
export const getAccounts = (appId: string, secureId: string) =>
  call<'GetListAccounts'>(apiClient, 'GetListAccounts', { appId, secureId });
```

```tsx
// app1/src/screens/AccountsScreen.tsx
import { can } from '../auth/permissions';
import { getAccounts } from '../api/client';

export const AccountsScreen = ({ me }: { me: Users }) => {
  if (!can(me, 'view_accounts')) return <NoPermissionView />;
  // … fetch with getAccounts(), render
};
```

---

## 4. Production-readiness checklist (for the `app1` engineer)

| Concern                                | Status from forensics                            | Action in `app1`                                                                 |
|-----------------------------------------|--------------------------------------------------|----------------------------------------------------------------------------------|
| **Cleartext HTTP** (SEC-NET-001, P0)    | Production uses `http://192.168.0.100:3000/`     | Gateway MUST move to HTTPS. Use self-signed CA on-prem if no public DNS.         |
| **Embedded DB credentials** (SEC-AUTH-002, P0) | Oracle TNS string in shipped binaries        | Rotate Oracle credentials before any production rollout. Use secret store.       |
| **SQL injection on `/Login`** (SEC-AUTH-001, P0) | Raw string concat                           | Gateway must use bind variables.                                                  |
| **Tier-B SQL injection** (SEC-AUTH-003, P0) | `USER_MNATK` subqueries glue caller NOU       | Same fix — bind variables.                                                        |
| **No `exp` JWT claim** (SEC-AUTH-004, P1) | Server-side TTL only                            | RN client must handle 401 → re-auth (the `jwt_interceptor.ts` already does this). |
| **`UserId` PK leak** (SEC-AUTH-005, P2)  | JWT carries the raw user DB id                  | Defer — backward-compatible with current server.                                  |
| **Privacy: IMEI usage**                 | v26 client reads `READ_PHONE_STATE`              | `app1` should use `UUID.randomUUID()` only — never request `READ_PHONE_STATE`.   |
| **Pagination**                          | None (whole result sets returned)                | `app1` gateway should add `ROW_NUMBER() OVER` pagination per endpoint.            |
| **Arabic UX**                            | Server returns Arabic in `error_msg`             | i18n catalogues client-side; don't depend on server-composed Arabic.              |
| **`NOA` overload**                       | Capability flag + till-account-id collide       | `app1` should split: `me.tillAccountId` + `me.canListAccounts`.                  |
| **Multi-tenant `appId`**                 | Persisted in `Preferences._appId`                | `app1` stores it in MMKV / SecureStore.                                           |

> All P0/P1 findings are documented with verbatim source citations under
> `analysis/02_JWT_AUTHENTICATION.md §6` and `analysis/10_APK_V26_ANALYSIS.md §8`.

---

## 5. Reference (where each fact comes from)

| Artifact in this folder           | Authoritative analysis doc                                  | Phase | Aggregate conf. |
|------------------------------------|--------------------------------------------------------------|:-----:|:---------------:|
| `endpoints.ts`                     | [`analysis/01_WCF_ENDPOINTS.md`](../analysis/01_WCF_ENDPOINTS.md) | 3     | 95 %            |
| `jwt_interceptor.ts`               | [`analysis/02_JWT_AUTHENTICATION.md`](../analysis/02_JWT_AUTHENTICATION.md) | 4 | 87.5 %         |
| `dtos.ts`                          | [`analysis/03_DATA_MODELS.md`](../analysis/03_DATA_MODELS.md) | 5     | 92 %            |
| `dtos.ts` (Oracle context)         | [`analysis/05_ORACLE_INTEGRATION.md`](../analysis/05_ORACLE_INTEGRATION.md) | 5 | 91 %         |
| `permissions_matrix.md`            | [`analysis/04_PERMISSIONS_SYSTEM.md`](../analysis/04_PERMISSIONS_SYSTEM.md) | 6 | 86 %            |
| End-to-end APK context             | [`analysis/10_APK_V26_ANALYSIS.md`](../analysis/10_APK_V26_ANALYSIS.md) | 7 | 88 %            |
| Executive overview                 | [`analysis/00_OVERVIEW.md`](../analysis/00_OVERVIEW.md)      | all   | —               |

---

## 6. Validation checklist (already run on the artefacts in this folder)

| Check                                                              | Status |
|--------------------------------------------------------------------|:------:|
| `endpoints.ts` compiles under TS 5 `--strict`                       | ✅     |
| `dtos.ts` compiles under TS 5 `--strict`                             | ✅     |
| `jwt_interceptor.ts` compiles under TS 5 `--strict`                  | ✅     |
| `api_contracts/openapi.yaml` validates via `openapi-spec-validator` | ✅     |
| `api_contracts/postman_collection.json` validates via Postman schema | ✅     |
| All claims have source citations + confidence ratings               | ✅     |
| No secrets transcribed                                              | ✅     |

You can re-run them by:

```bash
# From the repo root:
python3 -m openapi_spec_validator api_contracts/openapi.yaml
# Plus tsc --strict on the 3 TS files — see PROGRESS.md
```

— end of `for_main_repo/README.md` —
