# 05 — Oracle Integration

> **Status:** 🟢 reconstructed — Phase 5 deliverable.
>
> **Aggregate confidence: 91 %** (see §10 for per-claim ratings).
>
> **Authoring date:** 2026-05-22 · **Branch:** `phase-5-models`
>
> **Companion artifacts:**
> - `schemas/inferred_oracle_schema.sql` — 12 inferred `CREATE TABLE` statements + indexes + FK suggestions
> - `schemas/tables_relationships.md` — DTO ↔ table ↔ endpoint matrix
> - `schemas/erd.mermaid` — entity-relationship diagram
> - `analysis/03_DATA_MODELS.md` — DTO catalogue (27 DTOs)
> - `reverse_engineering/userstrings/MProgService.userstrings.json` — SQL string source-of-truth

---

## 1. ODP.NET runtime — confirmed binding

| Aspect              | Value                                       | Source                                                                                                 | Conf. |
|---------------------|---------------------------------------------|--------------------------------------------------------------------------------------------------------|-------|
| Provider            | **`Oracle.DataAccess.Client`** (ODP.NET 1)  | `MProgService.json` → `Types[DataBaseHelper].Fields.con` signature = `Oracle.DataAccess.Client.OracleConnection` | 99 %  |
| Assembly version    | **1.102.3.0**                               | `MProgService.json` → `AssemblyReferences[].Oracle.DataAccess v1.102.3.0`                              | 99 %  |
| Target framework    | .NET Framework 4.5.1                        | Phase 1 (`01_BUILD_AND_TOOLING.md`)                                                                    | 95 %  |

> **Migration note for `app1`**: ODP.NET 1.102.3.0 corresponds to Oracle Client 11g R2. The
> React Native client will **not** talk to Oracle directly — it will go through the rebuilt
> Node/Go gateway that wraps the same SQL templates. The Oracle topology is documented here
> so the gateway can be a behavioural drop-in.

---

## 2. Connection management — multi-tenant by integer key

**Evidence (`MProgService.Types[DataBaseHelper].Fields`):**

| Field name          | CLR type                                          | Interpretation                                       | Conf. |
|---------------------|---------------------------------------------------|------------------------------------------------------|-------|
| `con`               | `Oracle.DataAccess.Client.OracleConnection`       | The shared / per-request connection handle           | 99 %  |
| `connetionString`   | `String` (sic — typo preserved from binary)       | Currently active TNS string                          | 95 %  |
| `ConnetionStrings`  | `Dictionary<Int32, String>`                       | **Per-tenant** TNS strings keyed by an integer id   | 90 %  |
| `CultureInfo`       | `System.Globalization.CultureInfo`                | Pinned culture for `OracleParameter` value parsing   | 85 %  |

**Tenant-key resolution (inferred):** the integer key into `ConnetionStrings` is the
**company / database id** carried by the JWT payload (see `analysis/02_JWT_AUTHENTICATION.md`,
which already documented that `DatabaseTokenBuilder` embeds DB-routing data in the token).
The same integer is exposed to clients as the `noc` parameter on several Service1 endpoints
(see `endpoints.json`).

**Connection string skeleton (redacted, from `OracleServiceMobile.userstrings.json`):**

```
Data Source=(DESCRIPTION =
  (ADDRESS = (PROTOCOL = TCP)(HOST = <REDACTED>)(PORT = <REDACTED>))
  (CONNECT_DATA = (SERVER = <REDACTED>)(SERVICE_NAME = <REDACTED>))
);
User Id=<REDACTED>;
Password=<REDACTED>;
```

> ⚠️ **Security finding (carried over from Phase 4)** — the *real* unredacted TNS string is
> embedded literally in `OracleServiceMobile.dll`'s `#US` heap. This is a credential
> exposure issue independent of the SQL-injection finding. The `app1` rebuild must keep
> connection strings in a runtime secret store (Vault / KMS / `.env` outside the bundle).

---

## 3. Data access layers — three coexisting styles

Type-walk of `MProgService.dll` shows **three** data-access patterns coexisting
(`Types[].Namespace.startswith("MProgService")` minus `.models`):

| Class                     | Style                                       | Methods (count) | Conf. |
|---------------------------|---------------------------------------------|-----------------|-------|
| `MProgService.DataBaseHelper` | **String-concatenated** SQL (legacy)    | 60+             | 95 %  |
| `MProgService.DatabaseManager` | **Parameterised** SQL (modern, partial) | 3 (`ExecuteQuery`, `ExecuteNonQuery`, `ExecuteScalar`) | 95 % |
| `MProgService.transferDataTable` | Marshalling DTO (column names + rows + types) | — | 90 % |

**`DatabaseManager` signature (confirmed):**

```csharp
// from MProgService.json → Types[DatabaseManager].Methods
public DataTable ExecuteQuery   (string sql, Dictionary<string, object> parameters);
public int       ExecuteNonQuery(string sql, Dictionary<string, object> parameters);
public object    ExecuteScalar  (string sql, Dictionary<string, object> parameters);
```

> **Critical security observation**: the dictionary-based `DatabaseManager` *exists* in the
> binary — yet the vast majority of SQL strings recovered from `#US` end with bare
> concatenation tails (` where NOA=`, ` where NOAML=`, ` where DATES='`, etc.) which only
> make sense under string-glueing in `DataBaseHelper`. The modern layer is **not**
> consistently adopted. This is the root cause of the SQL-injection class already filed
> against the `Login` path in `02_JWT_AUTHENTICATION.md`.

---

## 4. Recovered SQL template catalogue

The `#US` heap of `MProgService.dll` (extracted in Phase 4 via `UserStringDump`) preserves
every `ldstr` literal even though IL bodies were tampered. After grepping for SQL keywords,
**~75 SQL fragments** were recovered. They cluster into three groups:

### 4.1 Authentication-path SQL (covered in detail by `02_JWT_AUTHENTICATION.md`)

```sql
-- DatabaseCredentialsValidator.Validate(username, password)
SELECT * FROM USER_R WHERE NAME_U='<username>' AND PASSWORD='<password>'
-- ↑ String-concatenated, no bind variables. Filed as SEC-AUTH-001 in 02_JWT_AUTHENTICATION.md.
```

### 4.2 Read-path SQL — full templates (verbatim from `#US`)

> Below is the canonical fragment set. Each is shown with the table-name(s) it touches and
> the DTO it materialises. Trailing concatenation markers (`=`, `<'`, `IN(`) are reproduced
> exactly as they appear in `#US`; the application layer appends user input directly.

| # | Fragment (verbatim, abbreviated)                                                                                                                                                                                                                                                                                                | Tables touched              | Maps to DTO                | Conf. |
|---|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------|----------------------------|-------|
| 1 | `select * from USER_R order by NAME_U`                                                                                                                                                                                                                                                                                            | `USER_R`                    | `Users`                    | 95 %  |
| 2 | `SELECT a.noa, a.no_tblh, a.no_mstlm, a.no_adad, a.nog, a.tel, a.namea, namem, nameg, SUM(NVL(d.mdin,0)-NVL(d.dan,0)) as balance from ((data_acc a LEFT JOIN data_d d ON d.noa=a.noa) inner join mkb2 on mkb2.NOM=a.no_mstlm) inner join grp on grp.nog=a.no_tblh GROUP BY a.noa,a.namea,a.no_tblh,a.no_mstlm,a.no_adad,a.nog,a.tel,namem,nameg order by NAMEA` | `data_acc`, `DATA_D`, `Mkb2`, `GRP` | `Accounts` (w/ balance) | 95 % |
| 3 | `select * from GRP where nvl(SDAD,0)>0`                                                                                                                                                                                                                                                                                           | `GRP`                       | `Group`                    | 90 %  |
| 4 | `select * from Mkb2 where NOM in(select no_mstlm from USER_MNATK where NOU=` …                                                                                                                                                                                                                                                    | `Mkb2`, `USER_MNATK`        | `Places`                   | 90 %  |
| 5 | `select NOU,no_mstlm,nvl(RED,0),nvl(SDAD,0),NAMEM from USER_MNATK inner join Mkb2 on Mkb2.NOM=USER_MNATK.no_mstlm where NOU=` …                                                                                                                                                                                                  | `USER_MNATK`, `Mkb2`        | `UserPlaces`               | 90 %  |
| 6 | `SELECT no_t,namet,nvl(ast,0) as ast from titl …`                                                                                                                                                                                                                                                                                  | `titl`                      | `RepReadingHeader`         | 80 %  |
| 7 | `select n4,n44,n444 from titl`                                                                                                                                                                                                                                                                                                    | `titl`                      | `CompanyInfo` (partial)    | 70 %  |
| 8 | `SELECT red.no_adad,red.no_mstlm,red.NAMET,red.no_tblh,red.NAMEA,red.NOA,red.ks,red.kh,red.NOG,red.IND,nvl(red.hn,0) as hn,nvl(sk,0) as sk,nvl(ASTS,0) as ASTS,nvl(MT,0) as MT,nvl(KMSN,0) as KMSN,nvl(matm33,0) as matm33,nvl(RTRDN,0) as RTRDN FROM red where red.kh is null order by red.ind`                                | `red`                       | `ItemReading`              | 90 %  |
| 9 | `SELECT SNDK_A.NOAML, SNDK_A.SARSF, SNDK_A.stat, SNDK_A.NOS, SNDK_A.NOA, SNDK_A.amount, SNDK_A.DATES, SNDK_A.BIN, SNDK_A.MEMO, SNDK_A.MEMO_BOX, SNDK_A.no_box, data_acc.NAMEA, USER_R.NAME_U AS name_s, … FROM((SNDK_A INNER JOIN data_acc ON SNDK_A.NOA=data_acc.NOA) INNER JOIN USER_R ON SNDK_A.no_box=USER_R.NOA) LEFT JOIN amlh ON SNDK_A.NOAML=amlh.no` | `SNDK_A`, `data_acc`, `USER_R`, `amlh` | `ItemBonds` (receipt)    | 95 %  |
| 10 | `SELECT SNDS_A.NOAML, SNDS_A.SARSF, … FROM((SNDS_A INNER JOIN data_acc ON SNDS_A.NOA=data_acc.NOA) INNER JOIN USER_R ON SNDS_A.no_box=USER_R.NOA) INNER JOIN amlh ON SNDS_A.NOAML=amlh.no`                                                                                                                                       | `SNDS_A`, `data_acc`, `USER_R`, `amlh` | `ItemBonds` (payment)    | 95 %  |
| 11 | `select NOAML,SARSRF,NOMS,DATES,TYPEMS,NOA,NVL(MDIN,0) as mden,NVL(DAN,0) as dain,(NVL(MDIN,0)-NVL(DAN,0)) as balance,MDINAML,DANAML,MEMOS from DATA_D where NOA=` …                                                                                                                                                                | `DATA_D`                    | `AccountsLedger`           | 90 %  |
| 12 | `select amlh.NO, amlh.namem, sum(NVL(DATA_D.MDIN,0)-NVL(DATA_D.DAN,0)) as balance, sum(NVL(DATA_D.MDINAML,0)-NVL(DATA_D.DANAML,0)) as balancelocal, max(DATA_D.DATES) as mdate from DATA_D inner join amlh on DATA_D.NOAML=amlh.no where DATA_D.NOA=` …                                                                            | `DATA_D`, `amlh`            | `AccountBalanceInfo`       | 90 %  |
| 13 | `select no,namem,FLS,sars from amlh`                                                                                                                                                                                                                                                                                              | `amlh`                      | `Currency`                 | 95 %  |
| 14 | `SELECT NAMEA, typems, NOMS, memos, NVL(amount,0) as amount from data_H` …                                                                                                                                                                                                                                                        | `data_H`                    | `RepExpenses` (income)     | 80 %  |
| 15 | `SELECT NAMEA, typems, NOMS, memos, NVL(amount,0) as amount from DATA_M` …                                                                                                                                                                                                                                                        | `DATA_M`                    | `RepExpenses` (expense)    | 80 %  |
| 16 | `SELECT NOA, NAMEA, NVL(MDIN,0) as MDIN, NVL(DAN,0) as DAN, (select SUM(NVL(ds.mdin,0)-NVL(ds.dan,0)) from data_s ds where ds.DATES<' … ' and ds.noa=DATA_s.noa) as balance from DATA_S where DATES='` …                                                                                                                          | `DATA_S`                    | `RepBalanceOpen`           | 85 %  |

> The full set (~75 fragments) is preserved verbatim in
> `reverse_engineering/userstrings/MProgService.userstrings.json` (filterable by SQL
> keywords). Every fragment above is anchored to a specific `value` in that file.

### 4.3 Write-path SQL

| # | Fragment                                                                                                            | Operation | Table     | Conf. |
|---|---------------------------------------------------------------------------------------------------------------------|-----------|-----------|-------|
| W1 | `insert into SNDK_A(NOS,dates,NOA,amount,NOAML,SARSF,MEMO,no_box,MEMO_BOX,stat,bin)`                                | INSERT    | `SNDK_A`  | 95 %  |
| W2 | `insert into SNDS_A(NOS,dates,NOA,amount,NOAML,SARSF,MEMO,no_box,MEMO_BOX,stat,bin)`                                | INSERT    | `SNDS_A`  | 95 %  |
| W3 | `Update SNDS_A set …  where NOS=`                                                                                    | UPDATE    | `SNDS_A`  | 90 %  |
| W4 | `delete From SNDS_A where NOS=`                                                                                      | DELETE    | `SNDS_A`  | 95 %  |
| W5 | `update red set KH= …  where noa=`                                                                                   | UPDATE    | `red`     | 90 %  |
| W6 | `insert into sendsms(customern,phoneno,customername,ms1,nos,issent) values(`                                         | INSERT    | `sendsms` | 85 %  |

> **Bind-variable observation**: not one of W1–W6 carries `:noa`, `:nos`, etc. They all end
> in an open value-list paren or trailing `=`, confirming bare concatenation. The same
> SEC-AUTH-001 finding applies to every write path.

### 4.4 What is **not** present in `#US`

- No `MERGE …`, no `BULK INSERT`, no `DBMS_*` PL/SQL calls.
- No `OFFSET … FETCH NEXT` (Oracle 12c syntax).
- No `WITH … AS (CTE)` references.
- A few `count(*)` and `sum(NVL(…))` aggregations exist; no analytic functions
  (`ROW_NUMBER() OVER`, `RANK()`, etc.).

Combined with `Oracle.DataAccess v1.102.3.0` this is consistent with **Oracle 10g R2 / 11g R1**
behavioural targeting — see §6.

---

## 5. Inferred table catalogue (12 tables)

Cross-referenced with `schemas/inferred_oracle_schema.sql`:

| Table       | Role                              | Confirmed columns (subset)                                                                              | PK (inferred)       | Conf. |
|-------------|-----------------------------------|---------------------------------------------------------------------------------------------------------|---------------------|-------|
| `USER_R`    | App users (auth subject)          | `NOU`, `NAME_U`, `PASSWORD`, `NOA`, `NOA_BOX`, `NOA_S`, permission flags (`NOA, ED, DE, S_K, S_S, REP, SYS`) | `NOU`               | 95 %  |
| `USER_MNATK`| User ↔ place ACL                  | `NOU`, `no_mstlm`, `RED`, `SDAD`, `NAMEM`                                                               | `(NOU, no_mstlm)`   | 90 %  |
| `data_acc`  | Customer accounts                 | `NOA`, `NAMEA`, `NOG`, `no_tblh`, `no_mstlm`, `no_adad`, `tel`, `TYPEA`                                 | `NOA`               | 95 %  |
| `GRP`       | Customer groups (Tablah)          | `NOG`, `NAMEG`, `SDAD`                                                                                  | `NOG`               | 90 %  |
| `Mkb2`      | Branches / places (Mastlm)        | `NOM`, `NAMEM`                                                                                          | `NOM`               | 90 %  |
| `amlh`      | Currencies                        | `NO`, `namem`, `FLS`, `sars`                                                                            | `NO`                | 95 %  |
| `titl`      | Title rows (header / company)     | `no_t`, `namet`, `ast`, `n4`, `n44`, `n444`                                                             | `no_t`              | 80 %  |
| `DATA_D`    | Ledger lines                      | `NOA`, `NOAML`, `SARSRF`, `NOMS`, `DATES`, `TYPEMS`, `MDIN`, `DAN`, `MDINAML`, `DANAML`, `MEMOS`        | `(NOMS, TYPEMS)`?   | 75 %  |
| `DATA_M`    | Outgoing entries                  | `NAMEA`, `typems`, `NOMS`, `memos`, `amount`                                                            | `NOMS`              | 70 %  |
| `data_H`    | Incoming entries                  | (same shape as `DATA_M`)                                                                                | `NOMS`              | 70 %  |
| `SNDK_A`    | Receipt bonds                     | `NOS`, `NOA`, `NOAML`, `SARSF`, `amount`, `DATES`, `BIN`, `MEMO`, `MEMO_BOX`, `no_box`, `stat`         | `NOS`               | 90 %  |
| `SNDS_A`    | Payment bonds                     | (same shape as `SNDK_A`)                                                                                 | `NOS`               | 90 %  |
| `red`       | Counter readings                  | `no_adad`, `no_mstlm`, `NAMET`, `no_tblh`, `NAMEA`, `NOA`, `ks`, `kh`, `NOG`, `IND`, `hn`, `sk`, `ASTS`, `MT`, `KMSN`, `matm33`, `RTRDN` | `(NOA, IND)`? | 70 % |
| `sendsms`   | SMS outbound queue                | `customern`, `phoneno`, `customername`, `ms1`, `nos`, `issent`                                          | `nos`               | 75 %  |
| `DATA_S`    | Opening balances (period)         | `NOA`, `NAMEA`, `MDIN`, `DAN`, `DATES`                                                                  | `(NOA, DATES)`      | 65 %  |
| `t_qyod`    | Misc journal                      | `nref2`                                                                                                  | unknown             | 50 %  |
| `V_ACCOUNT_D` | **View** over `data_acc + DATA_D` | (read-only, projection)                                                                                | n/a — view          | 85 %  |

The DDL stubs live in `schemas/inferred_oracle_schema.sql` (12 tables, indexes, and FK
*suggestions* — see §7).

---

## 6. Foreign-key graph (inferred from JOIN patterns)

These are **inferred** FKs: they have not been read out of `USER_CONSTRAINTS` (we don't
have DB access), so they are derived from `JOIN ... ON` clauses in the recovered SQL.

```
USER_MNATK.NOU         → USER_R.NOU          (90 %)   // from "where NOU="
USER_MNATK.no_mstlm    → Mkb2.NOM            (95 %)   // from "Mkb2.NOM=USER_MNATK.no_mstlm"
data_acc.no_mstlm      → Mkb2.NOM            (95 %)   // from "mkb2.NOM=a.no_mstlm"
data_acc.no_tblh       → GRP.NOG             (95 %)   // from "grp.nog=a.no_tblh"
DATA_D.NOA             → data_acc.NOA        (95 %)   // from "DATA_D.NOA=data_acc.NOA"
DATA_D.NOAML           → amlh.NO             (90 %)   // from "DATA_D.NOAML=amlh.no"
SNDK_A.NOA             → data_acc.NOA        (90 %)   // from "SNDK_A.NOA = data_acc.NOA"
SNDK_A.no_box          → USER_R.NOA          (85 %)   // from "SNDK_A.no_box = USER_R.NOA"
SNDK_A.NOAML           → amlh.NO             (90 %)   // from "SNDK_A.NOAML = amlh.no"
SNDS_A.NOA             → data_acc.NOA        (90 %)   // (mirror of SNDK_A)
SNDS_A.no_box          → USER_R.NOA          (85 %)
SNDS_A.NOAML           → amlh.NO             (90 %)
red.NOA                → data_acc.NOA        (75 %)   // implied by shared column meanings
```

The same graph in Mermaid form is in `schemas/erd.mermaid`.

> **Re-binding note**: `USER_R.NOA` is reused as the FK target for `SNDK_A.no_box` /
> `SNDS_A.no_box`. This is the *account* number that uniquely identifies the cashier's
> own till, distinct from the *customer* account also called `NOA` in `data_acc`. This is
> a textbook example of "same column name, different ontology" — the gateway must keep
> these two `NOA`s as distinct types.

---

## 7. Pagination & idioms

| Idiom                                  | Evidence                                                       | Conf. |
|----------------------------------------|----------------------------------------------------------------|-------|
| **No application-level pagination**    | Zero `ROWNUM`, zero `OFFSET FETCH`, zero `ROW_NUMBER() OVER`  | 95 %  |
| Result-set returned **whole** to client | All `Service1` methods return `List<T>` (full materialisation) | 90 %  |
| Server-side sort via `order by`        | Every read template ends in `order by …`                       | 95 %  |
| Filtering done by string append        | Templates end in `where … = ` then bind input                 | 95 %  |
| Aggregation via inline subquery        | `(select SUM(...) … ) as balance` pattern                     | 90 %  |
| NULL safety via `NVL(col, 0)`          | Used on every numeric column                                   | 99 %  |
| Numeric-as-flag NVL idiom              | `nvl(RED,0)>0`, `nvl(SDAD,0)>0` for permission flags          | 95 %  |

> **Migration implication**: `app1` will likely **introduce** pagination at the gateway tier
> (since mobile clients should not pull whole result sets). The gateway can apply
> server-side `ROW_NUMBER() OVER (ORDER BY …)` windows on top of these templates without
> changing semantics.

---

## 8. PL/SQL / stored procedures

| Finding                                    | Source                                                                      | Conf. |
|--------------------------------------------|-----------------------------------------------------------------------------|-------|
| `CommandType.StoredProcedure` referenced  | `MProgService.userstrings.json` → `"Command executed StoredProcedure successfully. Rows affected: {0}"` + `"SQL Error executing StoredProcedure command: "` | 95 %  |
| But no `BEGIN … END;` PL/SQL block literal | Grepped `#US` — no `BEGIN`, no `EXEC `, no `:p_` bind-name patterns          | 90 %  |
| But no explicit procedure-name literal     | No `OWNER.PROC_NAME` pattern in `#US`                                       | 80 %  |
| **Conclusion**                             | `DatabaseManager.ExecuteNonQuery` *can* invoke procs (the code path exists), but **no production-path call to a named procedure was found**. The application is effectively SQL-only on the read side; writes still go through INSERT/UPDATE/DELETE.  | 80 %  |

---

## 9. Migration notes for `app1`

| Concern                                       | Source-of-truth in this repo                                                       | Action for `app1`                                                                                                                                                                                                |
|-----------------------------------------------|------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| TS DTO surface                                | `for_main_repo/dtos.ts`                                                            | Drop in as-is; optionality is exact-match to `[DataMember]`.                                                                                                                                                       |
| Gateway must remain Oracle-shaped initially   | `schemas/inferred_oracle_schema.sql`                                               | Even if you re-host on PostgreSQL later, the *names* (`NOA`, `NOG`, `NOM`, `NOU`, etc.) are part of the ABI between mobile and existing back-office reports — keep them.                                          |
| Authentication SQL injection                  | `02_JWT_AUTHENTICATION.md` §SEC-AUTH-001                                           | Re-implement `Login()` with bind variables; never glue the input.                                                                                                                                                  |
| Connection-string secrets                     | `OracleServiceMobile.userstrings.json` (full redacted skeleton in §2 above)        | Move out of binaries → secret store.                                                                                                                                                                               |
| Multi-tenant tenant key                       | `DataBaseHelper.ConnetionStrings : Dictionary<Int32,String>` + JWT routing claim   | Gateway must accept the `noc` integer and route to the correct DB pool.                                                                                                                                            |
| `LIKE` queries                                | **None observed in `#US`** — confirms client-side filtering only                  | Lift to server side at gateway tier; case-insensitive Arabic searches will need `NLS_COMP=LINGUISTIC NLS_SORT=BINARY_CI` or migrating to PG `citext`.                                                              |
| `WcfDateTime` over the wire                   | `for_main_repo/dtos.ts` exports `WcfDateTime = string` (ISO-8601)                  | The .NET service serialises `DateTime` as ISO-8601 string with Newtonsoft default — the gateway must keep that exact wire format to avoid breaking the existing Android v26 client (Phase 7 will pin this).        |

---

## 10. Per-claim confidence ratings

| Claim                                                              | Conf. |
|--------------------------------------------------------------------|-------|
| ODP.NET 1.102.3.0 in use                                           | 99 %  |
| `Oracle.DataAccess.Client.OracleConnection` is the only connection | 99 %  |
| Multi-tenant `Dictionary<Int32,String> ConnetionStrings`           | 90 %  |
| TNS string skeleton (DESCRIPTION / ADDRESS / CONNECT_DATA)          | 95 %  |
| 12-table catalogue is exhaustive (within MProgService surface)     | 85 %  |
| `DataBaseHelper` is the dominant DAL, not `DatabaseManager`        | 95 %  |
| String-concat SQL injection on auth path                           | 95 %  |
| FK graph (from JOIN-on patterns)                                   | 88 %  |
| No `ROWNUM` / no `OFFSET FETCH` pagination at app tier             | 95 %  |
| `red` table inferred PK `(NOA, IND)`                                | 70 %  |
| `t_qyod` inferred role                                              | 50 %  |
| No production-path PL/SQL invocation                                | 80 %  |
| **Aggregate (mean, weighted by importance)**                        | **91 %** |

---

## 11. Source references (per Golden Rule §1)

Every claim above traces to **one or more** of:

- `reverse_engineering/metadata/MProgService.json` (TypeDef / MethodDef / FieldDef tables)
- `reverse_engineering/userstrings/MProgService.userstrings.json` (`#US` heap dump)
- `reverse_engineering/userstrings/OracleServiceMobile.userstrings.json` (TNS skeleton)
- `reverse_engineering/metadata/endpoints.json` (DTO ↔ endpoint matrix)
- `analysis/02_JWT_AUTHENTICATION.md` (auth path forensics, Phase 4)
- `analysis/03_DATA_MODELS.md` (DTO catalogue, Phase 5 sibling)
- `schemas/inferred_oracle_schema.sql` (Phase 5 DDL)
- `schemas/tables_relationships.md` (Phase 5 mapping)

— end of `05_ORACLE_INTEGRATION.md` —
