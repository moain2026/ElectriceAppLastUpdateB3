# 07 — Multi-Tenant Architecture

> **Status:** ⚪ pending — populated in Phase 3.

## What we know

- The service exposes a `Dictionary<int, string> ConnetionStrings` (note the
  typo — `Connetion`, not `Connection`).
- The key is `int` → likely a **company id** or **tenant id**.
- The value is a full Oracle connection string.

## Open questions

- [ ] Is the tenant id supplied:
  - via a JWT claim (e.g. `tenant`)?
  - via a HTTP header (e.g. `X-Company-Id`)?
  - via a URI segment?
  - via a request body field?
- [ ] How are new tenants provisioned — config file? DB row? environment variable?
- [ ] What is the fallback when the id is missing or unknown?
- [ ] Is `Dictionary` **thread-safe** in this codebase, or is it wrapped in a lock?

## Implications for the rewrite

The React Native client must know how to express *"I belong to tenant N"*.
Whatever channel the legacy app uses must be preserved or explicitly migrated.
