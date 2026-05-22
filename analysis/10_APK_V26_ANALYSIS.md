# 10 — APK v26 Analysis

> **Status:** ⚪ pending — populated in Phase 7.
> **Binary:** `binaries/ElectricCollector26.apk` (11 MB).

## Targets

- Package name, applicationId.
- `minSdkVersion`, `targetSdkVersion`, `compileSdkVersion`.
- Permissions (from `AndroidManifest.xml`).
- Activities / Fragments / Services / Receivers.
- Base URL configuration (`strings.xml`, build-config constants).
- `SecureId` algorithm (look for `Defence.java` / `Security.java` /
  `Crypto.java`).
- Hardcoded keys / salts (**document only the first 4 chars** if any).
- SQLite schema (`assets/*.sql`, `DbHelper.java`, `*OpenHelper.java`).
- HTTP layer: LoopJ, Retrofit, Volley, Apache, OkHttp? — and the **exact
  endpoint strings** so we can confirm Phase 3.
- Diff vs v28 (when v28 APK becomes available).

## Plan

1. `apktool d` to recover resources cleanly.
2. `jadx -d apk_decompiled/sources` for readable Java.
3. Sanity-check by grepping for the 27 endpoint names.
4. Produce a *client-side endpoint table* and cross-reference it with the
   *server-side* Phase 3 table — every discrepancy is an open question.
