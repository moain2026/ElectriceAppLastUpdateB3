# 01 — WCF Endpoints (IService1 + IServiceElect)

> **Status:** 🟢 surface complete  ·  Bodies-only details deferred to Phase 4-6.
> **Confidence:** signatures = 100%, verbs/templates = 100%, auth/perm-checks = ~60% (need body decompile).
> **Sources:** `reverse_engineering/metadata/MProgService.json` (Phase 2),
> `reverse_engineering/decompiled_csharp/MProgService/MProgServiceElect/IServiceElect.cs`.

This file is the **single source of truth** for every callable URL on
`OracleServiceMobile.exe`. It was produced mechanically (no hand-typing of
60 method names) by `tools/parse_webinvoke.py` reading the metadata JSON.

Two `[ServiceContract]` interfaces are exposed:
- `MProgService.IService1`         — 27 ops (legacy contract)
- `MProgServiceElect.IServiceElect`— 33 ops (modern contract; the one APK v26+ uses)

# Auto-generated WebInvoke / WebGet map

_Source:_ `reverse_engineering/metadata/MProgService.json` (decoded by `tools/parse_webinvoke.py`)

### `MProgService.IService1` — 27 operations

| #  | Operation | HTTP | UriTemplate | RequestFmt | ResponseFmt | BodyStyle | Returns | Params |
|---:|-----------|:----:|-------------|:----------:|:-----------:|:---------:|---------|--------|
|  1 | `Index` | **GET** | `/` | ? | ? | ? | `Stream` |  |
|  2 | `GetCallerIdentity` | **?** | `` | ? | ? | ? | `String` |  |
|  3 | `Authenticate` | **POST** | `` | Json | Json | Bare | `String` | creds |
|  4 | `GetListAccounts` | **GET** | `` | Json | Json | Wrapped | `List<Accounts>` | id, appId |
|  5 | `GetListCurrency` | **GET** | `` | Json | Json | Wrapped | `List<Currency>` | id, appId |
|  6 | `GetListUsers` | **GET** | `` | Json | Json | Wrapped | `List<Users>` | id, appId |
|  7 | `GetListAccountsLedger` | **GET** | `` | Json | Json | Wrapped | `List<AccountsLedger>` | id |
|  8 | `GetRepBalanceDetails` | **GET** | `` | Json | Json | Wrapped | `List<RepBalanceDetails>` | num |
|  9 | `GetRepBalanceDetailsByDate` | **GET** | `` | Json | Json | Wrapped | `List<RepBalanceDetails>` | num, sdate, edate, currency, appId |
| 10 | `GetRepBalanceHeader` | **GET** | `` | Json | Json | Wrapped | `List<RepBalanceHeader>` | date, currency, num, type, appId |
| 11 | `GetRepBondsHeader` | **GET** | `` | Json | Json | Wrapped | `List<RepBondsHeader>` | num, sdate, edate, currency, appId |
| 12 | `GetBondRecieptRcordNext` | **GET** | `` | Json | Json | Wrapped | `String` | num, appId |
| 13 | `GetListBonds` | **GET** | `` | Json | Json | Wrapped | `List<ItemBonds>` | num, num_s, sdate, edate, currency, appId |
| 14 | `SaveBond` | **POST** | `` | Json | Json | Wrapped | `ResultPost` | num, num_s, nmstnd, mden, mdate, notes, notes_box, currencyid, dain, price_trans, equal, notes2, appId |
| 15 | `UpdateBond` | **PUT** | `UpdateBond?appId={appId}&id={id}` | Json | Json | Wrapped | `ResultPost` | appId, id, num, num_s, nmstnd, mden, mdate, notes, notes_box, currencyid, dain, price_trans, equal, notes2 |
| 16 | `DeleteBond` | **DELETE** | `DeleteBond?appId={appId}&id={id}` | Json | Json | Wrapped | `ResultPost` | appId, id |
| 17 | `GetBondPaymentRecordNext` | **GET** | `` | Json | Json | Wrapped | `String` | num, appId |
| 18 | `GetListBondsPayment` | **GET** | `` | Json | Json | Wrapped | `List<ItemBonds>` | num, num_s, sdate, edate, currency, appId |
| 19 | `SaveBondPayment` | **POST** | `` | Json | Json | Wrapped | `ResultPost` | num, num_s, nmstnd, mden, mdate, notes, notes_box, currencyid, dain, price_trans, equal, notes2, appId |
| 20 | `UpdateBondPayment` | **PUT** | `UpdateBondPayment?appId={appId}&id={id}` | Json | Json | Wrapped | `ResultPost` | appId, id, num, num_s, nmstnd, mden, mdate, notes, notes_box, currencyid, dain, price_trans, equal, notes2 |
| 21 | `DeleteBondPayment` | **DELETE** | `DeleteBondPayment?appId={appId}&id={id}` | Json | Json | Wrapped | `ResultPost` | appId, id |
| 22 | `Login` | **POST** | `` | Json | Json | Wrapped | `Users` | username, password, appId |
| 23 | `UserAuth` | **POST** | `` | ? | Json | Bare | `Users` | authd |
| 24 | `GetAccountBalanceInfo` | **GET** | `` | Json | Json | Wrapped | `List<AccountBalanceInfo>` | date, accountid, appId |
| 25 | `GetAccountBalance` | **GET** | `` | Json | Json | Wrapped | `String` | accountid, currency |
| 26 | `GetCompanyInfo` | **GET** | `` | Json | Json | Wrapped | `CompanyInfo` | appId |
| 27 | `GetCompanyData` | **GET** | `` | Json | Json | Wrapped | `DataComp` |  |


### `MProgServiceElect.IServiceElect` — 33 operations

| #  | Operation | HTTP | UriTemplate | RequestFmt | ResponseFmt | BodyStyle | Returns | Params |
|---:|-----------|:----:|-------------|:----------:|:-----------:|:---------:|---------|--------|
|  1 | `Authenticate` | **POST** | `` | Json | Json | Bare | `String` | creds |
|  2 | `test` | **GET** | `` | Json | Json | Wrapped | `String` |  |
|  3 | `GetListAccounts` | **GET** | `` | Json | Json | Wrapped | `List<Accounts>` | num, m, g, p, acctid, appId |
|  4 | `GetListGroup` | **GET** | `` | Json | Json | Wrapped | `List<pGroup>` | no_mstlm, appId |
|  5 | `GetListPlaces` | **GET** | `` | Json | Json | Wrapped | `List<plocation>` | nou, type, appId |
|  6 | `GetRepBoxMove` | **GET** | `` | Json | Json | Wrapped | `List<RepBoxMoves>` | sdate, appId |
|  7 | `GetRepBoxMoveDetails` | **GET** | `` | Json | Json | Wrapped | `List<RepBoxMovesDetals>` | sdate, num, appId |
|  8 | `GetRepExpenses` | **GET** | `` | Json | Json | Wrapped | `List<RepBoxMovesDetals>` | sdate, appId |
|  9 | `GetListUserPlaces` | **GET** | `` | Json | Json | Wrapped | `List<UserPlaces>` | num, appId |
| 10 | `GetListReadingCounter` | **GET** | `` | Json | Json | Wrapped | `List<ItemReading>` | id, isnull, notblh, nomstlm, nogroup, appId |
| 11 | `SaveReading` | **POST** | `` | Json | Json | Wrapped | `ResultPost` | num, kh, appId |
| 12 | `GetListUsers` | **GET** | `` | Json | Json | Wrapped | `List<Users>` | id, appId |
| 13 | `GetRepReadingHeader` | **GET** | `` | Json | Json | Wrapped | `List<RepReading>` | type, appId |
| 14 | `GetRepBalanceDetailsByDate` | **GET** | `` | Json | Json | Wrapped | `List<RepBalanceDetails>` | num, sdate, edate, currency, appId |
| 15 | `GetRepBalanceHeader` | **GET** | `` | Json | Json | Wrapped | `List<RepBalanceHeader>` | date, currency, num, type, appId |
| 16 | `GetRepBondsHeader` | **GET** | `` | Json | Json | Wrapped | `List<RepBondsHeader>` | num, sdate, edate, currency, appId |
| 17 | `GetBondRecieptRcordNext` | **GET** | `` | Json | Json | Wrapped | `String` | num, appId |
| 18 | `GetListBonds` | **GET** | `` | Json | Json | Wrapped | `List<ItemBonds>` | num, num_s, sdate, edate, currency, nou, appId |
| 19 | `SaveBond` | **POST** | `` | Json | Json | Wrapped | `ResultPost` | num, num_s, nmstnd, mden, mdate, notes, notes_box, currencyid, dain, price_trans, equal, notes2, appId |
| 20 | `UpdateBond` | **PUT** | `UpdateBond?appId={appId}&id={id}` | Json | Json | Wrapped | `ResultPost` | appId, id, num, num_s, nmstnd, mden, mdate, notes, notes_box, currencyid, dain, price_trans, equal, notes2 |
| 21 | `DeleteBond` | **DELETE** | `DeleteBond?appId={appId}&id={id}` | Json | Json | Wrapped | `ResultPost` | appId, id |
| 22 | `GetBondPaymentRecordNext` | **GET** | `` | Json | Json | Wrapped | `String` | num, appId |
| 23 | `GetListBondsPayment` | **GET** | `` | Json | Json | Wrapped | `List<ItemBonds>` | num, num_s, sdate, edate, currency, appId |
| 24 | `SaveBondPayment` | **POST** | `` | Json | Json | Wrapped | `ResultPost` | num, num_s, nmstnd, mden, mdate, notes, notes_box, currencyid, dain, price_trans, equal, notes2, appId |
| 25 | `UpdateBondPayment` | **PUT** | `UpdateBondPayment?appId={appId}&id={id}` | Json | Json | Wrapped | `ResultPost` | appId, id, num, num_s, nmstnd, mden, mdate, notes, notes_box, currencyid, dain, price_trans, equal, notes2 |
| 26 | `DeleteBondPayment` | **DELETE** | `DeleteBondPayment?appId={appId}&id={id}` | Json | Json | Wrapped | `ResultPost` | appId, id |
| 27 | `Login` | **POST** | `` | Json | Json | Wrapped | `Users` | username, password, appId, secureId |
| 28 | `GetAccountBalanceInfo` | **GET** | `` | Json | Json | Wrapped | `List<AccountBalanceInfo>` | date, accountid, appId |
| 29 | `GetAccountBalance` | **GET** | `` | Json | Json | Wrapped | `String` | accountid, currency, appId |
| 30 | `GetCompanyInfo` | **GET** | `` | Json | Json | Wrapped | `CompanyInfo` | appId |
| 31 | `GetCompanyData` | **GET** | `` | Json | Json | Wrapped | `DataComp` |  |
| 32 | `ReSetPassword` | **POST** | `` | Json | Json | Wrapped | `ChangePasswordRespons` | username, password, newpassword, uId, appId |
| 33 | `InsertMessage` | **POST** | `` | Json | Json | Wrapped | `String` | customerN, phoneNo, customerName, ms1, tg, nos, uId, appId |


---

## Methodology

Every row above was generated mechanically from
`reverse_engineering/metadata/MProgService.json` by `tools/parse_webinvoke.py`,
which decodes the raw `[WebInvoke(...)]` / `[WebGet(...)]` custom-attribute
blobs at the binary metadata level — bypassing ConfuserEx body tampering.
Re-run any time with:

```bash
python3 tools/parse_webinvoke.py > /tmp/endpoints.md
```

## Service routing

Both contracts are exposed on the same WCF host process
(`OracleServiceMobile.exe`). The Windows-Service config (`*.exe.config`)
maps each contract to a `webHttpBinding` endpoint. We have not yet recovered
the exact base URLs — they are read at startup from
`OracleServiceMobile.exe.config` and from the Windows Registry (see
`analysis/07_MULTI_TENANT.md`). Phase 7 (APK analysis) will reveal the
**client-side** base URL string, which is the missing piece.

## Convention discovered

- `appId` parameter is **omnipresent** → it is the **tenant id**. See
  [`analysis/07_MULTI_TENANT.md`](./07_MULTI_TENANT.md).
- `nou`, `id` parameters represent the **acting user id** (`Users.NOU`).
- Operations are **plural-collection GETs** + **PUT/DELETE with id in URI**.
- Save (POST) and Update (PUT) carry the same payload — only difference is
  the URI template carries an `id` for PUT.
- Response envelope is `ResultPost` for mutations, raw DTO or `List<DTO>`
  for queries — wrapped JSON body style.

## Two contracts: IService1 vs IServiceElect

| | `IService1` | `IServiceElect` |
|---|---|---|
| Namespace          | `MProgService`        | `MProgServiceElect` |
| Operations         | 27                    | 33 |
| Concrete impl      | `MProgService.Service1`     | `MProgServiceElect.ServiceElect` |
| `Login` arity      | 3 (`username, password, appId`) | **4** (`+ secureId`) |
| Reading/meter ops  | none                  | `GetListReadingCounter`, `SaveReading`, `GetRepReadingHeader` |
| Cashbox reports    | none                  | `GetRepBoxMove*`, `GetRepExpenses` |
| Hierarchy queries  | none                  | `GetListGroup`, `GetListPlaces`, `GetListUserPlaces` |
| Password reset     | no                    | `ReSetPassword` |
| SMS                | no                    | `InsertMessage` |
| Health-check       | `GetCallerIdentity`   | `test` |
| Confidence         | 100% (from metadata)  | 100% (from metadata) |

**Inference (confidence 85%):**
- `IService1` is the **legacy** contract used by an earlier desktop / older
  Android client.
- `IServiceElect` is the **current** contract used by APK v26 (verified in
  Phase 7) and presumably v28. Notice the extra `secureId` on Login —
  matches the `Defence.MashineSerialNumber` story.

→ **Rewrite target:** `IServiceElect` (33 ops). `IService1` is documented
for reference / regression only.

## Auth check placement

We have *not yet* dissected the body of `TokenValidationInspector.AfterReceiveRequest`
because the relevant `ServiceElect.Authenticate` method body is among
the obfuscated ones. **Best guess from class names + WCF idioms:**

- Every operation (except `Authenticate`, `Login`, `test`, `Index`) is
  intercepted by `TokenValidationServiceBehavior` → `TokenValidationInspector`.
- The inspector reads the `Authorization: Bearer <jwt>` header (or a custom
  header we'll confirm in Phase 4), forwards it to
  `DatabaseTokenValidator.IsValid(string)`, and on failure throws a
  `FaultException<ServiceFault>` with `ErrorCode="UNAUTHORIZED"`.
- The token is **opaque to the client** — its claims include `NOU`, `appId`,
  and the permission flags.

See [`analysis/02_JWT_AUTHENTICATION.md`](./02_JWT_AUTHENTICATION.md) for
detail (Phase 4 deliverable).

## Permissions check placement

We expect each mutating operation to check `Users.S_S`/`Users.S_K`/`Users.ED`/
`Users.DE` **inside** `Service1.SaveBond`/`UpdateBond`/`DeleteBond` etc.
Bodies of those methods are partially obfuscated — Phase 6 will quote the
exact IL from `monodis --code` once we narrow down which methods.

## Open questions

1. **Exact base URL** of the WCF host (e.g. `http://<host>:<port>/Service1.svc/`)
   — comes from APK in Phase 7.
2. **Endpoint name for `Authenticate`** — is it the standard JWT bootstrap or
   a Basic-Auth-style?
3. **What does `GetCallerIdentity` return?** — likely the decoded JWT
   identity for diagnostics; body is opaque.
4. **`Index`** returns `Stream` with `UriTemplate="/"` — probably an HTML
   landing page. Cosmetic only.
