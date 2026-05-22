# 02 — JWT Authentication System

> **Status:** ⚪ pending — populated in Phase 4.

## Classes of interest

The following types are expected (names from the project brief — confirmation
in Phase 2's decompile):

- `AuthTokenService`             — creates & signs tokens at login.
- `DatabaseTokenBuilder`         — builds the claim set from DB user row.
- `DatabaseTokenValidator`       — validates incoming tokens against the DB.
- `TokenValidationBehaviorExtension` — registers the inspector in WCF config.
- `TokenValidationInspector`     — the actual WCF `IDispatchMessageInspector`.

## To be answered in Phase 4

- [ ] Algorithm: **HS256 vs RS256 vs HS512**? (look at `jose-jwt`'s API call)
- [ ] Signing key: hardcoded? from config? from DB? — **document first 4 chars only**.
- [ ] Claim set: `sub`, `exp`, `iat`, custom (`nou`, `noa`, …)?
- [ ] Token TTL.
- [ ] Header name expected by `TokenValidationInspector`: `Authorization: Bearer …`?
- [ ] Refresh strategy (if any).
- [ ] What happens on 401 — fault contract or HTTP code?

## Deliverable

- This document, fully populated with citations.
- `for_main_repo/jwt_interceptor.ts` — Axios interceptor template that mimics
  the original client's behaviour.
