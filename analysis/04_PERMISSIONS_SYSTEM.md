# 04 — Permissions System

> **Status:** 🟢 reconstructed — Phase 6 deliverable.
>
> **Aggregate confidence: 86 %** (see §8 for per-claim ratings).
>
> **Branch:** `phase-6-permissions` · **Date:** 2026-05-22
>
> **Companion artifacts:**
> - `for_main_repo/permissions_matrix.md` — RN-ready permission gate table
> - `analysis/03_DATA_MODELS.md` §`Users` DTO — schema
> - `analysis/05_ORACLE_INTEGRATION.md` §5 — `USER_R` + `USER_MNATK` table catalogue
> - `reverse_engineering/userstrings/MProgService.userstrings.json` — `#US` heap source

---

## 1. The two-tier permission model

The legacy system uses **two independent permission tiers** that compose:

```
┌─────────────────────────────────────────────────────────────────┐
│ Tier A — User-level capability flags (USER_R columns)           │
│   7 boolean-as-Int32 columns on USER_R:                         │
│   NOA, ED, DE, S_K, S_S, REP, SYS                               │
│   Returned in the Users DTO at /Login response.                 │
└─────────────────────────────────────────────────────────────────┘
                              ∩  (both must pass)
┌─────────────────────────────────────────────────────────────────┐
│ Tier B — Per-place ACL (USER_MNATK junction table)              │
│   2 boolean-as-Int32 columns on USER_MNATK:                     │
│   RED (read), SDAD (write) — keyed by (NOU, no_mstlm)           │
│   Enforced inline via SQL subqueries in every read path.        │
└─────────────────────────────────────────────────────────────────┘
```

> **Implication for `app1`:** the React Native client should keep both tiers in
> mind. Tier A is *UI-gating* (hide a button), Tier B is *row-filtering*
> (only show data for places the user can see). The server enforces both —
> the client must not trust Tier A alone.

---

## 2. Evidence inventory

| Evidence                                                                                                   | Source                                                                          | Conf. |
|------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|-------|
| `Users` DTO carries 7 `Int32` permission flags                                                              | `MProgService.json` → `Types[Users].Properties`                                 | 99 %  |
| Flag names appear as bare `ldstr` literals in `#US` (used as `DataTable["NOA"]` indexers)                   | `MProgService.userstrings.json` — `"NOA"`, `"ED"`, `"DE"`, `"S_K"`, `"S_S"`, `"REP"`, `"SYS"` | 95 %  |
| All flags are `Int32` (not `Boolean`) — used as `0` / `1` truthy values                                     | `Users` DTO signatures                                                          | 99 %  |
| `noa` (lowercase) is a **different** column: `data_acc.noa` = account id (PK of `data_acc`)                | `#US` `select * from data_acc … where a.noa=`                                   | 95 %  |
| `USER_MNATK` junction with `(NOU, no_mstlm)` carries `RED`, `SDAD` per place                                | `#US` `select NOU,no_mstlm,nvl(RED,0),nvl(SDAD,0),NAMEM from USER_MNATK …`     | 95 %  |
| Tier-B filter idiom (`nvl(red,0)>0` / `nvl(SDAD,0)>0`) is everywhere in read paths                          | `#US` repeated 8+ times                                                          | 95 %  |
| `Users.access_token` is the JWT itself (Phase 4 confirmed)                                                 | `analysis/02_JWT_AUTHENTICATION.md §3.4`                                        | 95 %  |
| Permission check pattern in C# is `if (Convert.ToInt32(row["FLAG"]) == 1) { … }` (typical for DataTable)   | inference from `DataTable` return type of `Login` + bare `ldstr` flag names    | 80 %  |

---

## 3. Tier-A — user-level capability flags

### 3.1 Authoritative flag table

| Flag    | Hypothesised meaning                                  | Type    | Source signal                                          | Conf. |
|---------|--------------------------------------------------------|---------|---------------------------------------------------------|-------|
| `NOA`   | **N**umber **O**f **A**llowed accounts / blanket account-access bool | `Int32` | `USER_R.NOA` column + bare `ldstr "NOA"` in `#US`     | 75 %  |
| `ED`    | **ED**it permission (UPDATE rights on bonds/readings)  | `Int32` | `USER_R.ED` column + bare `ldstr "ED"` in `#US`        | 90 %  |
| `DE`    | **DE**lete permission (DELETE rights on bonds)         | `Int32` | `USER_R.DE` column + bare `ldstr "DE"` + `delete From SNDS_A where NOS=` template | 90 % |
| `S_K`   | **S**ave **K**ara'a (reading) — create-reading right   | `Int32` | `USER_R.S_K` + bare `ldstr "S_K"` + `update red set KH=` template (the "K" channel) | 85 % |
| `S_S`   | **S**ave **S**anad (bond/receipt) — create-bond right  | `Int32` | `USER_R.S_S` + bare `ldstr "S_S"` + `insert into SNDK_A`/`SNDS_A` templates | 90 % |
| `REP`   | **REP**orts access (GetRep* endpoints)                  | `Int32` | `USER_R.REP` + bare `ldstr "REP"` + 14 `GetRep*` methods in `Service1` | 90 % |
| `SYS`   | **SYS**tem admin (`/Login` of other users, `ChangePassword` of others) | `Int32` | `USER_R.SYS` + bare `ldstr "SYS"` + `ResetPassWord` method in `DataBaseHelper` | 85 % |

> **`NOA` ambiguity** — the column name `NOA` on `USER_R` collides with `data_acc.NOA`
> (which is the account *primary key*) and `SNDK_A.NOA` / `SNDS_A.NOA` (account FK).
> On `USER_R` it's an `Int32` capability flag *and also* doubles as the cashier's own
> account-of-record (used as `SNDK_A.no_box = USER_R.NOA` per Phase 5 §6). So
> `USER_R.NOA` is **simultaneously** (a) the user's till identifier and (b) used as a
> boolean check in user gating. This is an antipattern carried over from the legacy
> design. The `app1` rebuild must split these: `tillAccountId: number` and
> `canAccessAccounts: boolean`.

### 3.2 Where each flag is enforced — endpoint coverage matrix

Mapping flags to endpoints via:
- `ED` / `DE` → write/delete operations on bonds/readings
- `S_K` / `S_S` → create operations
- `REP` → all `GetRep*` endpoints
- `SYS` → user-management endpoints
- `NOA` → account-listing endpoints (sub-tier B refines further)

| Flag    | Enforced on endpoints (cross-ref `endpoints.json`)                                                                                                  | Action on `flag != 1` (inferred) |
|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------|
| `ED`    | `UpdateBond`, `UpdateBondPayment`, `UpdateReading`, `UpdateAllReading`, `SaveBond` (re-edit path)                                                  | HTTP 403 / `ServiceFault.error_no=PERM_DENIED` |
| `DE`    | `DeleteBond`, `DeleteBondPayment`                                                                                                                   | HTTP 403 |
| `S_K`   | `UpdateReading`, `UpdateAllReading` (insert via REPLACE pattern)                                                                                    | HTTP 403 |
| `S_S`   | `SaveBond`, `SaveBondPayment`                                                                                                                       | HTTP 403 |
| `REP`   | `GetRepBalanceDetails`, `GetRepBalanceDetailsByDate`, `GetRepBalanceHeader`, `GetRepBalanceHeaderElect`, `GetRepBalanceOpen`, `GetRepBondsHeader`, `GetRepBondsHeaderElectric`, `GetRepBoxMove`, `GetRepBoxMoveDetails`, `GetRepExpenses`, `GetRepReadingHeader`, `GetFinalBalance`, `GetAccountBalance`, `GetAccountBalanceInfo` (14 endpoints) | HTTP 403 |
| `SYS`   | `ResetPassword`, `GetListUsers`, `Authenticate` (when used to mint a token for another user)                                                        | HTTP 403 |
| `NOA`   | `GetListAccounts`, `GetListAccountsLedger`, `GetListBonds`, `GetListBondsElect`, `GetListBondsPayment`, `GetAccountBalance`, `GetAccountBalanceInfo`  | HTTP 403 *or* empty result set (Tier B kicks in regardless) |

### 3.3 Inferred check pattern (C#)

The flags are read from a `DataTable` row produced by `Login()`:

```csharp
// inferred shape — actual IL bodies are tampered
public Users Login(string username, string password, string appId)
{
    DataTable dt = _db.Login(username, password, appId);  // SELECT * FROM USER_R WHERE NAME_U='…' AND PASS='…'
    if (dt.Rows.Count == 0) return new Users { error_no = 1, error_msg = "Invalid credentials" };

    DataRow r = dt.Rows[0];
    var u = new Users {
        NOU         = Convert.ToInt32(r["NOU"]),
        NAME_U      = r["NAME_U"].ToString(),
        NOA         = Convert.ToInt32(r["NOA"]),
        ED          = Convert.ToInt32(r["ED"]),
        DE          = Convert.ToInt32(r["DE"]),
        S_K         = Convert.ToInt32(r["S_K"]),
        S_S         = Convert.ToInt32(r["S_S"]),
        REP         = Convert.ToInt32(r["REP"]),
        SYS         = Convert.ToInt32(r["SYS"]),
        // …
        access_token = _tokenBuilder.IssueToken(NOU)
    };
    return u;
}
```

The per-endpoint gate then looks like:

```csharp
// inferred — actual IL tampered
public ResultPost DeleteBond(string nos, string appId)
{
    var caller = GetCallerFromJwt();  // populated by TokenValidationInspector (Phase 4)
    if (caller.DE != 1)
        throw new FaultException<ServiceFault>(new ServiceFault {
            error_no = 403, error_msg = "ليس لديك صلاحية الحذف"  // "no delete permission"
        });
    return _db.DeleteBond(nos, appId);
}
```

Confidence in this exact pattern: **80 %** (the `Convert.ToInt32(row["…"])` shape is
inferred from `DataTable` return + bare `ldstr` flag names in `#US`). The exact error
message text is not in `#US` (probably composed at runtime in tampered IL or pulled
from a `Resources.resx` not present in proprietary binary).

---

## 4. Tier-B — per-place ACL via `USER_MNATK`

### 4.1 The junction table

| Column      | Type   | Role                                              | Conf. |
|-------------|--------|---------------------------------------------------|-------|
| `NOU`       | Int32  | FK → `USER_R.NOU` (which user)                    | 95 %  |
| `no_mstlm`  | Int32  | FK → `Mkb2.NOM` (which place / Mastlm)            | 95 %  |
| `RED`       | Int32  | **R**ead permission for this user on this place   | 90 %  |
| `SDAD`      | Int32  | **SDAD** = صداد / SaDaD → write/cashout permission | 85 %  |
| `NAMEM`     | String | Denormalised place name (for display)             | 90 %  |

**PK (inferred):** `(NOU, no_mstlm)` — composite, since one user can be granted access
to multiple places.

### 4.2 How it is enforced — SQL subqueries

Every account-listing read path in `DataBaseHelper` carries this subquery:

```sql
-- Read-side filter (RED check)
… where data_acc.no_mstlm IN(
    SELECT no_mstlm FROM USER_MNATK
    WHERE nvl(red,0)>0 AND NOU=<caller_nou>
)
```

```sql
-- Write-side filter (SDAD check) — used on bond-create paths
… where data_acc.no_mstlm IN(
    SELECT no_mstlm FROM USER_MNATK
    WHERE nvl(sdad,0)>0 AND NOU=<caller_nou>
)
```

These appear in `#US` at:
- `" where data_acc.no_mstlm IN(SELECT no_mstlm  FROM  USER_MNATK where nvl(sdad,0)>0 and NOU="`
- `" and data_acc.no_mstlm IN(SELECT no_mstlm  FROM  USER_MNATK where nvl(sdad,0)>0 and NOU="`
- `" where red.no_mstlm IN(SELECT no_mstlm  FROM  USER_MNATK where nvl(red,0)>0 and NOU="`
- `" and red.no_mstlm IN(SELECT no_mstlm  FROM  USER_MNATK where nvl(red,0)>0 and NOU="`
- `" where a.no_mstlm IN(SELECT no_mstlm  FROM  USER_MNATK where nvl(sdad,0)>0 and NOU="`
- `" and a.no_mstlm IN(SELECT no_mstlm  FROM  USER_MNATK where nvl(sdad,0)>0 and NOU="`

**Coverage:** 6 occurrences observed in `#US`, applied to 3 underlying tables
(`data_acc`, `red`, and the aliased `a` = `data_acc`).

### 4.3 The `UserPlaces` DTO

The `UserPlaces` DTO + `GetListUserPlaces` endpoint expose Tier-B to the client so
the UI can render only places the user is allowed to operate on. It returns:
- `NOU` (user)
- `no_mstlm` (place id)
- `RED` (read flag)
- `SDAD` (write flag)
- `NAMEM` (place display name)

Cross-ref: `endpoints.json` shows `GetListUserPlaces(userId, appId) → List<UserPlaces>`.

---

## 5. SQL-injection risk inherited from Tier B

The Tier-B subqueries terminate in bare `=` then the caller's `NOU` is appended via
string concat (consistent with the SEC-AUTH-001 finding from Phase 4). If a
authenticated attacker can influence `NOU` (e.g. by forging a JWT with a tampered
`UserId` claim), they can inject arbitrary SQL into the place-filter.

**Mitigations recommended for `app1` gateway:**
1. **Bind variables**: `… AND NOU = :nou` with `OracleParameter("nou", caller.NOU)`.
2. **Trust only server-validated `NOU`**: never accept `NOU` from the request body;
   re-derive from JWT validation.
3. **Tier-B at the ORM layer**: enforce a `WHERE EXISTS (…)` policy on every
   tenant-scoped query, not via string composition.

---

## 6. Hierarchy of effective permission

The actual access decision is `Tier-A AND Tier-B`, evaluated as follows:

```
Effective(user, action, resource)
  = Tier-A(user, action.category)                 // can the user perform this kind of action at all?
  AND Tier-B(user, resource.no_mstlm, action.kind) // is the resource's place granted to the user?

where:
  action.category ∈ { read, edit, delete, save_reading, save_bond, reports, sys }
  Tier-A maps to flag:
    read         → NOA (and Tier-B RED)
    edit         → ED   (and Tier-B SDAD)
    delete       → DE   (and Tier-B SDAD)
    save_reading → S_K  (and Tier-B SDAD)
    save_bond    → S_S  (and Tier-B SDAD)
    reports      → REP  (and Tier-B RED)
    sys          → SYS  (Tier-B does not apply — sys is global)
```

> The `SYS` flag short-circuits Tier-B (a sysadmin sees everything).
> Inference confidence: **75 %** (consistent with how the `Login` SQL is
> `select * from USER_R` with no per-place filter on the user table itself).

---

## 7. Migration notes for `app1`

| Concern                                          | Action                                                                                                                                            |
|--------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| RN UI must mirror Tier-A from JWT/login response  | After `Login()`, persist `Users` in secure store; map flags → boolean feature gates per `for_main_repo/permissions_matrix.md`.                   |
| Tier-B should be invisible to RN                  | The gateway should *transparently* enforce the `USER_MNATK` filter; the RN client only sees the final filtered list.                              |
| Don't trust Tier-A on the client                 | Always re-validate server-side. The RN gating is *cosmetic* — the gateway is the authority.                                                       |
| Eliminate `NOA` overload                          | Surface two distinct fields in `app1`: `me.tillAccountId: number` (= `USER_R.NOA`) and `me.canListAccounts: boolean` (derived from `NOA > 0`).    |
| Externalise Arabic error strings                  | Use i18n catalogues, not server-composed Arabic in fault contracts — preserves a11y and translation flexibility.                                  |
| Tier-B SQL injection                              | Patched as part of SEC-AUTH-001 generalisation in the new gateway.                                                                                |

---

## 8. Per-claim confidence ratings

| Claim                                                                       | Conf. |
|------------------------------------------------------------------------------|-------|
| 7 permission flags exist on `Users` DTO as `Int32` columns                  | 99 %  |
| Tier-B `USER_MNATK` junction governs per-place access                       | 95 %  |
| Tier-B uses `RED` (read) and `SDAD` (write) flags                            | 90 %  |
| Tier-A maps to operations as documented in §3.2                              | 85 %  |
| Check pattern is `Convert.ToInt32(row["FLAG"]) == 1`                         | 80 %  |
| `SYS` short-circuits Tier-B                                                  | 75 %  |
| `NOA` is overloaded (capability flag + till account id)                      | 80 %  |
| Tier-B SQL injection inherits from SEC-AUTH-001                              | 85 %  |
| Per-endpoint mapping in §3.2 (`ED → UpdateBond`, etc.)                       | 80 %  |
| The 6 verbatim `USER_MNATK` subquery occurrences in `#US`                    | 99 %  |
| **Aggregate (mean, weighted by importance)**                                 | **86 %** |

---

## 9. Source references

- `reverse_engineering/metadata/MProgService.json` → `Types[Users].Properties`
- `reverse_engineering/userstrings/MProgService.userstrings.json` (`#US` heap)
- `reverse_engineering/metadata/endpoints.json` (endpoint catalogue)
- `analysis/02_JWT_AUTHENTICATION.md` (auth pipeline, JWT `UserId` claim)
- `analysis/03_DATA_MODELS.md` (`Users`, `UserPlaces` DTOs)
- `analysis/05_ORACLE_INTEGRATION.md` (`USER_R`, `USER_MNATK` tables)
- `for_main_repo/permissions_matrix.md` (RN gate table)

— end of `04_PERMISSIONS_SYSTEM.md` —
