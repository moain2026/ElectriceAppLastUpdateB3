# 04 — Permissions System

> **Status:** ⚪ pending — populated in Phase 6.

## Known permission flags (from project brief)

| Flag | Hypothesised meaning | Hypothesised type |
|------|----------------------|-------------------|
| `NOU` | "Number Of User"  — primary user id | int |
| `NAME_U` | username (display) | string |
| `NOA` | "Number Of Allowed (accounts)"?  | int / bool |
| `ED`  | **E**dit permission | 0/1 bool |
| `DE`  | **DE**lete permission | 0/1 bool |
| `S_K` | **S**ave **K**ara'a (reading) | 0/1 bool |
| `S_S` | **S**ave **S**anad (bond) | 0/1 bool |
| `REP` | **REP**orts access | 0/1 bool |
| `SYS` | **SYS**tem admin | 0/1 bool |

Phase 6 will produce a **matrix** mapping each flag → exact method/endpoint
where it is enforced, with the verbatim IL/C# check.

## Investigation plan (Phase 6)

1. Grep the C# decompile for the symbol of each flag.
2. For every hit, capture: method name → check pattern → action on failure.
3. Cross-reference with the endpoints table from Phase 3.
4. Document **both** server-side enforcement and any client-side hint
   (e.g. fields returned to disable buttons).
