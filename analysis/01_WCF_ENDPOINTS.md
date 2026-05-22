# 01 — WCF Endpoints (IService1)

> **Status:** ⚪ pending — populated in Phase 3.
> **Source of truth:** `reverse_engineering/decompiled_csharp/MProgService/` after Phase 2.

## Known endpoint list (27)

> Names confirmed by previous analysis (see project brief). Routes, HTTP verbs,
> parameters, SQL, and confidence scores will be filled in per-method during
> Phase 3.

| # | Operation | HTTP (TBD) | Auth | Category |
|--:|-----------|:---------:|:----:|----------|
| 1  | `Index`                       | GET? | none | meta |
| 2  | `GetCallerIdentity`           | GET? | JWT | diagnostics |
| 3  | `Authenticate`                | POST?| none | auth |
| 4  | `Login`                       | POST | none | auth |
| 5  | `UserAuth`                    | POST?| none | auth |
| 6  | `GetListAccounts`             | GET  | JWT  | accounts |
| 7  | `GetListCurrency`             | GET  | JWT  | reference |
| 8  | `GetListUsers`                | GET  | JWT (`SYS`) | admin |
| 9  | `GetListAccountsLedger`       | GET  | JWT  | accounts |
| 10 | `GetAccountBalanceInfo`       | GET  | JWT  | accounts |
| 11 | `GetAccountBalance`           | GET  | JWT  | accounts |
| 12 | `GetRepBalanceDetails`        | GET  | JWT (`REP`) | reports |
| 13 | `GetRepBalanceDetailsByDate`  | GET  | JWT (`REP`) | reports |
| 14 | `GetRepBalanceHeader`         | GET  | JWT (`REP`) | reports |
| 15 | `GetRepBondsHeader`           | GET  | JWT (`REP`) | reports |
| 16 | `GetListBonds`                | GET  | JWT  | bonds |
| 17 | `GetBondRecieptRcordNext`     | GET  | JWT  | bonds |
| 18 | `SaveBond`                    | POST | JWT (`S_S`) | bonds |
| 19 | `UpdateBond`                  | POST | JWT (`ED`)  | bonds |
| 20 | `DeleteBond`                  | POST | JWT (`DE`)  | bonds |
| 21 | `GetBondPaymentRecordNext`    | GET  | JWT  | bond-payments |
| 22 | `GetListBondsPayment`         | GET  | JWT  | bond-payments |
| 23 | `SaveBondPayment`             | POST | JWT (`S_S`) | bond-payments |
| 24 | `UpdateBondPayment`           | POST | JWT (`ED`)  | bond-payments |
| 25 | `DeleteBondPayment`           | POST | JWT (`DE`)  | bond-payments |
| 26 | `GetCompanyInfo`              | GET  | JWT  | company |
| 27 | `GetCompanyData`              | GET  | JWT  | company |

> _Auth column reflects an **educated guess** based on naming conventions; it
> is to be **verified** against `WebInvoke` attributes and method bodies in
> Phase 3._

---

## Template (one section per endpoint — to be filled in Phase 3)

```markdown
## <OperationName>

- **HTTP Method:** GET | POST
- **Route / UriTemplate:** `/...`
- **Auth required:** Yes / No  (which permission flag?)
- **Request body / query params:**
  | Name | Type | Required | Description |
- **Returns:** `<DTO>` (link to model in `analysis/03_DATA_MODELS.md`)
- **SQL extracted (if any):** ```sql\n...\n```
- **Source:** `reverse_engineering/decompiled_csharp/MProgService/ServiceElect.cs:Lxx`
- **Confidence:** xx %
- **Notes / edge cases:**
```
