# 05 — Oracle Integration

> **Status:** ⚪ pending — populated in Phase 5.

## What we expect to find

- All access goes through **`Oracle.DataAccess.Client`** (ODP.NET).
- `MProgService.dll` likely contains a thin DAL (Data Access Layer):
  parametrised `OracleCommand`s, `OracleParameter` arrays, mapping back to
  the DTOs in `analysis/03_DATA_MODELS.md`.
- Connection strings are **per-tenant**, held in `Dictionary<int, string>
  ConnetionStrings`. The tenant id likely arrives via a JWT claim or a query
  parameter.

## Plan

1. Locate the helper that opens connections — likely `OpenConn(int tenantId)`
   or similar.
2. For every WCF method, capture the exact SQL string built (with `:bind`
   variable names).
3. Build `schemas/inferred_oracle_schema.sql` by union-ing all column names
   per implied table.
4. Detect indexes implied by `WHERE` clauses and unique constraints implied
   by `INSERT … SELECT … FROM dual WHERE NOT EXISTS …` patterns.
5. Document `ROWNUM` / pagination idioms.
6. Document any PL/SQL `PROCEDURE` / `FUNCTION` call (`CommandType.StoredProcedure`).
