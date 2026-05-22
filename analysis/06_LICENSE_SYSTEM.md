# 06 — License System

> **Status:** ⚪ pending — populated in Phases 2-3.
> **Binary:** `binaries/License.dll` (15 KB — smallest of the .NET binaries).

## Questions to answer

- [ ] Activation strategy: hardware-ID? machine-name? customer number?
- [ ] Expiry: fixed date? counter? signed expiry blob?
- [ ] Where is the licence file expected on disk?
- [ ] Is the licence consulted **on every WCF call**, **once at startup**, or **per session**?
- [ ] What happens on licence failure — exception? quiet read-only mode?
- [ ] Are there any **hardcoded backdoor keys**? (Must be **flagged immediately**, not committed.)

## Risk notes (for the rewrite)

If the licence file is tied to a machine ID, the rewrite has two paths:

1. **Keep server side enforcement** — the React Native client never sees the licence, the WCF/REST shim does.
2. **Drop the licence layer** — if the rewrite is owned by the same customer
   and they no longer need anti-piracy.

Decision goes to the product owner. The RE document only describes the
mechanism — it does **not** advise.
