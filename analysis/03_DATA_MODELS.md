# 03 — Data Models (DTOs)

> **Status:** ⚪ pending — populated in Phase 5.

## Models inventory (27 known)

| # | Model | Used by (endpoints, expected) | Confidence (from brief) |
|--:|-------|-------------------------------|:-----------------------:|
| 1  | `AccountBalanceInfo`     | `GetAccountBalanceInfo`            | 100% |
| 2  | `Accounts`               | `GetListAccounts`                  | 100% |
| 3  | `AccountsLedger`         | `GetListAccountsLedger`            | 100% |
| 4  | `AuthData`               | `Authenticate`/`Login`             | 100% |
| 5  | `ChangePasswordRespons`  | password endpoint?                 |  80% |
| 6  | `CompanyInfo`            | `GetCompanyInfo`/`GetCompanyData`  | 100% |
| 7  | `Credentials`            | login request                      | 100% |
| 8  | `Currency`               | `GetListCurrency`                  | 100% |
| 9  | `DataComp`               | company data wrapper?              |  70% |
| 10 | `Grops` (sic — "Groups") | grouping reference?                |  60% |
| 11 | `ItemBonds`              | bond endpoints                     | 100% |
| 12 | `ItemReading`            | reading endpoints                  | 100% |
| 13 | `ListData`               | generic list response wrapper      |  80% |
| 14 | `LPlaces`                | location list?                     |  60% |
| 15 | `pGroup`                 | "people group"?                    |  60% |
| 16 | `plocation`              | location DTO                       |  70% |
| 17 | `RepBalanceDetails`      | `GetRepBalanceDetails*`            | 100% |
| 18 | `RepBalanceHeader`       | `GetRepBalanceHeader`              | 100% |
| 19 | `RepBondsHeader`         | `GetRepBondsHeader`                | 100% |
| 20 | `RepBoxMoves`            | report rows                        |  80% |
| 21 | `RepBoxMovesDetals` (sic)| report rows                        |  80% |
| 22 | `RepReading`             | reading reports                    | 100% |
| 23 | `ResultPost`             | generic ack for POSTs              | 100% |
| 24 | `ServiceFault`           | error envelope                     | 100% |
| 25 | `Token`                  | login response                     | 100% |
| 26 | `Users`                  | `GetListUsers` / login result      | 100% |
| 27 | `UserPlaces`             | per-user location list             |  90% |

## Already-known field lists

(Promoted from project brief; will be **verified** against decompiled C# in Phase 5.)

### `Users` — 13 fields
`NOU, NAME_U, NOA, ED, DE, S_K, S_S, REP, SYS, PASS, access_token, version, error_no`

### `ItemBonds` — 19 fields
`type, name, name_s, nmstnd, notes, notes2, notes_box, num, num_s, mden, dain,
balance, mdate, price_trans, cas, currencyid, currencyname, currency, account`

### `ItemReading` — 17 fields
`name, namet, notblh, ind, nomstlm, noadad, num, nog, ks, kh, cas, asts, sk,
mt, kmsn, matm33, rtrdn`

### `Accounts` — 14 fields
`type, name, num, mden, dain, balance, notblh, nomstlm, noadad, nog, tel,
statH, namet, namep`

## Per-model template (to be filled in Phase 5)

```markdown
## <ModelName>

- **Fields (N):**
  | # | C# name | C# type | Inferred Oracle col | NULL? | Notes |
- **Used in endpoints:**
- **Likely Oracle table:** `<NAME>`
- **Source:** `reverse_engineering/decompiled_csharp/MProgService/Models/<File>.cs`
- **Confidence:** xx %
```
