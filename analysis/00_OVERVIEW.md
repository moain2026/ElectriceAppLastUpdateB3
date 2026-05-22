# 00 — Executive Overview

> **Status:** 🟡 stub — will be expanded continuously and finalized in Phase 8.
> **Audience:** the AbbasiTahseel React-Native rewrite team (`app1`).
> **Reading time (when complete):** ~10 minutes.

---

## TL;DR

`ElectricCollector` is a field-collection app for an electrical utility. A
technician walks meters, reads them, issues bonds/receipts to customers, and
syncs everything against a central **Oracle DB** through a **self-hosted WCF
service** authenticated by **JWT**.

| Layer | Tech | File |
|-------|------|------|
| Mobile client (current)    | Android (Java, LoopJ/Volley?)        | `binaries/ElectricCollector26.apk` |
| Mobile client (target)     | React Native (rewrite)               | _separate repo `app1`_ |
| Service host               | Windows Service self-hosting WCF     | `binaries/OracleServiceMobile.exe` |
| Business logic             | .NET Framework class library         | `binaries/MProgService.dll` |
| Licensing                  | .NET class library                   | `binaries/License.dll` |
| Auth                       | JWT (jose-jwt)                       | `binaries/jose-jwt.dll` (OSS) |
| Data persistence           | Oracle DB via ODP.NET                | `binaries/Oracle.DataAccess.dll` (vendor) |

---

## Confirmed facts (Phase 1)

- The whole back-end is **one process** (`OracleServiceMobile.exe`) self-hosting WCF.
- The WCF contract is `IService1` exposing **27 operations**.
- **Runtime: .NET Framework 4.x** (confirmed via manifest of MProgService.dll).
- **Oracle client: ODP.NET 1.102.3.0** = Oracle 11g/12c binary (confirmed via
  `.assembly extern Oracle.DataAccess` in IL manifest).
- The .NET assemblies were processed by **ConfuserEx** (or similar). **Empirical proof:**
  `monodis` crashes (SIGSEGV / `g_assert` abort) on all three proprietary
  binaries after dumping only the assembly manifest. See
  [`09_OBFUSCATION_NOTES.md`](./09_OBFUSCATION_NOTES.md). Symbol names of
  internal helpers are expected to be mangled; the public WCF surface is *not*
  mangled (27 method names are visible to callers).
- Multi-tenancy uses a `Dictionary<int, string> ConnetionStrings` (note the
  original typo — `Connetion`).
- 27 DTOs identified (`Accounts`, `ItemBonds`, `ItemReading`, …).
- 7 permission flags on `Users`: `NOA, ED, DE, S_K, S_S, REP, SYS`.

## Open questions (Phase 1)

See `PROGRESS.md → Open questions`.

## Phase-by-phase outcomes (will be filled in)

| Phase | Key deliverable | Status |
|-------|-----------------|:------:|
| 1 | Lab structure + tooling | 🟢 done |
| 2 | C# decompile of 3 priority assemblies | ⚪ |
| 3 | 27 endpoints, OpenAPI, Postman | ⚪ |
| 4 | JWT scheme + interceptor template | ⚪ |
| 5 | 27 models + Oracle DDL + ERD + TS types | ⚪ |
| 6 | Permissions matrix | ⚪ |
| 7 | APK v26 deep dive | ⚪ |
| 8 | `for_main_repo/` packaged + executive summary | ⚪ |
