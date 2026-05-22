# 🎁 for_main_repo/

> **Status:** ⚪ scaffold only (Phase 1). Real artefacts land here in Phases 3-8.

This folder is the **ONLY** thing the AbbasiTahseel React-Native team
(`app1` repo) needs to look at. Everything else in this repository is
*evidence* and *reasoning* — this folder is the *answer*.

## Planned contents

| File | Filled in | Description |
|------|:---------:|-------------|
| `endpoints.ts`          | Phase 3 | `const ENDPOINTS = {...}` + per-endpoint request/response types. |
| `jwt_interceptor.ts`    | Phase 4 | Axios interceptor template (drop into `app1/src/api/`). |
| `permissions_matrix.md` | Phase 6 | Plain-English matrix for product/QA. |
| `bond_dto.ts`           | Phase 5 | `ItemBonds` interface + Zod schema. |
| `reading_dto.ts`        | Phase 5 | `ItemReading` interface + Zod schema. |
| `user_dto.ts`           | Phase 5 | `Users` interface + Zod schema. |

## Copy guide (for the `app1` engineer)

When this folder is complete, copy as follows:

```
for_main_repo/endpoints.ts          →  app1/src/api/endpoints.ts
for_main_repo/jwt_interceptor.ts    →  app1/src/api/jwt.ts
for_main_repo/permissions_matrix.md →  app1/docs/permissions.md
for_main_repo/*_dto.ts              →  app1/src/types/
```

> Always re-export types from a single barrel `app1/src/types/index.ts` —
> do not import from this folder at runtime; copy and adapt.
