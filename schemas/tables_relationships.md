# Tables ↔ DTOs ↔ endpoints relationship map

> Phase 5 deliverable. Cross-references the inferred Oracle schema
> (`inferred_oracle_schema.sql`), the DTO catalogue
> (`analysis/03_DATA_MODELS.md`), and the WCF endpoint table
> (`analysis/01_WCF_ENDPOINTS.md`).

## DTO → Oracle table

| DTO | Hinted table | Confidence | Source signal |
|---|---|:--:|---|
| `AccountBalanceInfo` | — | n/a | aggregate over data_acc/DATA_D — not a row |
| `Accounts` | `data_acc` | 100% | SQL template at #US +0x1011 names this table |
| `AccountsLedger` | `DATA_D` | 100% | SQL template at #US +0x3c6c names this table |
| `ChangePasswordRespons` | — | n/a | response envelope (Success/Message) |
| `RepBoxMovesDetals` | `SNDK_A` | 100% | SQL template at #US +0x2063 names this table |
| `RepBoxMoves` | `SNDK_A` | 100% | SQL template at #US +0x2063 names this table |
| `ServiceFault` | — | n/a | error envelope |
| `UserPlaces` | `USER_MNATK` | 100% | SQL template at #US +0x14cf/+0x1578 names this table |
| `RepReading` | — | n/a | report aggregate over data_H |
| `LPlaces` | — | n/a | report aggregate (USER_MNATK ⨝ Mkb2) |
| `pGroup` | `GRP` | 100% | SQL template at #US +0x1405 names this table |
| `plocation` | `Mkb2` | 100% | SQL template at #US +0x1578 names this table |
| `Grops` | `GRP` | 100% | SQL template at #US +0x1405 names this table |
| `ListData` | — | n/a | generic envelope |
| `AuthData` | — | n/a | request DTO {username, password} — USER_R columns are NAME_U/PASS |
| `CompanyInfo` | `titl` | 80% | SQL template at #US +0x1323 names titl; DTO match by column count |
| `Credentials` | — | n/a | request DTO {User, Password, appId} |
| `Currency` | `amlh` | 100% | SQL template at #US +0x4d5e names this table |
| `ItemReading` | `DATA_M` | 85% | SQL template at #US +0x1dca names DATA_M; DTO match by column names |
| `ItemBonds` | `DATA_D` | 100% | SQL template at #US +0x3c6c names this table |
| `RepBalanceDetails` | — | n/a | report aggregate over DATA_D |
| `RepBalanceHeader` | — | n/a | report aggregate (header summary over DATA_D) |
| `RepBondsHeader` | — | n/a | report aggregate (header summary over DATA_D) |
| `DataComp` | — | n/a | company-wrapper response |
| `ResultPost` | — | n/a | POST ack envelope (status/note) |
| `Token` | — | n/a | in-memory only — token row is in a separate auth table per §3.4 |
| `Users` | `USER_R` | 100% | SQL template at #US +0x4c7a/+0x4cf8 names this table |

## DTO ↔ endpoint usage

> For each DTO, which WCF operations emit/consume it. Source:
> `reverse_engineering/metadata/endpoints.json` (Phase 3).

| DTO | Returned by | Accepted as body |
|---|---|---|
| `AccountBalanceInfo` | — | — |
| `Accounts` | — | — |
| `AccountsLedger` | — | — |
| `ChangePasswordRespons` | — | — |
| `RepBoxMovesDetals` | — | — |
| `RepBoxMoves` | — | — |
| `ServiceFault` | — | — |
| `UserPlaces` | — | — |
| `RepReading` | — | — |
| `LPlaces` | — | — |
| `pGroup` | — | — |
| `plocation` | — | — |
| `Grops` | — | — |
| `ListData` | — | — |
| `AuthData` | — | — |
| `CompanyInfo` | — | — |
| `Credentials` | — | — |
| `Currency` | — | — |
| `ItemReading` | — | — |
| `ItemBonds` | — | — |
| `RepBalanceDetails` | — | — |
| `RepBalanceHeader` | — | — |
| `RepBondsHeader` | — | — |
| `DataComp` | — | — |
| `ResultPost` | — | — |
| `Token` | — | — |
| `Users` | — | — |
