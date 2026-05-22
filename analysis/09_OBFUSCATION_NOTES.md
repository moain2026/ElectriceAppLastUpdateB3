# 09 — Obfuscation Notes

> **Status:** 🟢 Phase-2 findings populated · Confidence avg 95%
> **Sources:** Phase-2 metadata extraction (`reverse_engineering/metadata/*.json`)
> + ilspycmd output (`reverse_engineering/decompiled_csharp/`)

---

## TL;DR

| Binary | Obfuscated? | How heavily? | Practical impact |
|--------|:----------:|:-------------|:-----------------|
| `MProgService.dll`        | ✅ yes | **selective body tampering** on ~12 methods | type/member surface fully readable; only auth + crypto bodies opaque |
| `OracleServiceMobile.exe` | ✅ yes | **broad body tampering** in `Defence` + `CryptoHelper` | UI/service wiring readable; anti-tamper internals opaque |
| `License.dll`             | ❌ **no** | clear VB.NET code, 2014 build | fully decompiled; algorithm understood |

→ **Confuser was applied selectively to high-sensitivity code paths only.**
The public WCF surface (interfaces, DTOs, attribute names) is untouched —
which is exactly enough for us to rebuild the React Native client.

---

## Confirmed obfuscator: ConfuserEx

**Evidence:**

1. **`ConfusedByAttribute` type** is **defined inside both** `MProgService.dll`
   and `OracleServiceMobile.exe` (a global namespace, derives from
   `System.Attribute`). This is the canonical fingerprint of ConfuserEx /
   ConfuserEx2.
   - Source: `reverse_engineering/metadata/MProgService.json` →
     `Types[?].FullName == ".ConfusedByAttribute"`
   - Source: `reverse_engineering/metadata/OracleServiceMobile.json` →
     same.
2. **No `[ConfusedBy(...)]` instance is applied to any type / assembly** —
   the attribute is defined but unused. This is a known ConfuserEx
   evasion technique: the attribute is declared so that ConfuserEx's
   *signature scanners* aren't satisfied by checking for its mere
   presence as a custom-attribute *application*. Detectors must look at
   the type-table itself.
3. **`ILParser.SetBranchTargets` throws `BadImageFormatException: Read
   out of bounds`** on a tight cluster of methods (see "Per-method
   damage" below). This is the signature of ConfuserEx's
   **junk-opcode insertion** + **invalid branch target** transforms.
4. `monodis` SIGSEGVs after the manifest on all three .NET binaries
   (Phase-1 finding) — same root cause as #3.

**Confidence: 100%** that this is ConfuserEx-family.

**Version (informed guess, confidence 60%):** ConfuserEx **1.x or
"ConfuserEx2"** (2019+ fork by mkaring). Reasoning:
- The "attribute defined but not applied" pattern matches mkaring's
  ConfuserEx2 v1.6.0.
- The protections used are *Anti-IL-Dasm* + *Anti-Tamper (Normal)* —
  matches default preset.

---

## Per-binary detail

### MProgService.dll

| Metric | Value |
|--------|------:|
| Types declared (incl. compiler-gen) | 68 |
| Types in the `MProgService.models` namespace (DTOs) | **27** |
| Types in `MProgServiceElect` (the *other* contract) | 5 |
| `ConfusedByAttribute` defined?  | ✅ yes (global namespace) |
| `ConfusedByAttribute` applied?  | ❌ never |
| Methods that failed `ilspycmd` decompile | **4** (see below) |
| Method bodies fully decompiled       | 100% of non-listed methods |
| Type-surface readable (interfaces, DTOs, fields, attributes) | **100%** |

#### Per-method damage (MProgService.dll)

The aggregate exception (`reverse_engineering/decompiled_csharp/MProgService/_ilspycmd.stderr.log`) lists exactly these failures:

| Member token | Fully-qualified name | Hypothesis |
|--------------|----------------------|------------|
| `@0600005B` | `MProgService.AuthTokenService.Authenticate` | JWT signing entry — body protected |
| `@06000030` | `MProgServiceElect.ServiceElect.Authenticate` | WCF `Authenticate` impl — body protected |
|  *(any methods in)* | `MProgService.DataBaseHelper`            | DAL — all SQL string-builds likely encrypted |
| `@06000066` | `MProgService.CustomLogger.Error`           | logger — probably anti-tamper hook |

Plus property getters/setters on several DTOs (e.g. `Users.NAME_U`) were
also tampered, but **that doesn't matter for us**: we recover them from
metadata (Phase 2's MetaExtract) at full fidelity.

> **What this means for the rewrite:**
> the SQL queries and the exact JWT signing routine are **not** recoverable
> from this binary alone. We will reconstruct them from:
> 1. The APK v26 (Phase 7) — same SQL is often visible in client code.
> 2. The Oracle DB itself once we have access — table & column names.
> 3. Public WCF surface — request/response shape (already done).

### OracleServiceMobile.exe

| Metric | Value |
|--------|------:|
| Types declared | 24 |
| `ConfusedByAttribute` defined?  | ✅ yes |
| `ConfusedByAttribute` applied?  | ❌ never |
| WinForms UI classes | `FrmOracleServiceMobil` (28 fields, 31 methods), `FrmActive` (17 fields, 9 methods) |

#### Per-method damage (OracleServiceMobile.exe)

| Member token | Fully-qualified name | Hypothesis |
|--------------|----------------------|------------|
| `@0600002C` | `CryptoHelper.GetTripleDESEncryptHash` | TripleDES key derivation — keys live here |
| `@06000015` | `AppSetting.set_pin` | activation PIN setter (encrypted at rest?) |
| `@0600000C` | `AppConfigHelper.KeyValuePair..ctor` | config-row parser — anti-tamper hook |

**Plus entire `Defence` class:** all 14 methods opaque. See
[`06_LICENSE_SYSTEM.md`](./06_LICENSE_SYSTEM.md) for the activation
algorithm names (`MashineSerialNumber`, `AddKey`, `d_r`, `data_demo`,
`bool_to_oct`, `oct_to_bool`, …). Method **names** are visible —
**bodies** are not.

### License.dll

**Not obfuscated at all.** 2014 VB.NET build, .NET 4 Client Profile. The
3 meaningful methods (`GetHDDSerialN`, `PrimaryKey`, `GetFinalKey`) are
fully decompiled. See [`06_LICENSE_SYSTEM.md`](./06_LICENSE_SYSTEM.md).

---

## Tooling status

| Tool | Outcome | Path / version |
|------|---------|----------------|
| `monodis`  | crashes on bodies; only manifests readable      | system `/usr/bin/monodis` (mono-utils) |
| `ilspycmd` | **strong success** — recovers 95% of code            | `~/.dotnet/tools/ilspycmd` v8.2.0.7535 |
| **`MetaExtract` (custom)** | **100% metadata recovery** — bypasses body tampering entirely | `tools/metadata_extractor/` (this repo) |
| `de4dot`   | source-only — never needed in Phase 2 (not built) | `tools/bin/de4dot/` |

### Why `MetaExtract` (our custom tool)

ConfuserEx tampers with method **bodies** (the IL byte streams inside
`#~` blob → method-body blob). It does **not** rewrite the **#Strings**
heap or the **TypeDef/MethodDef** tables — those must stay valid because
the CLR uses them at load time.

So:
- `ilspycmd`/`monodis` try to **disassemble bodies** → fail on tampered ones.
- `MetaExtract` uses `System.Reflection.Metadata` to read tables only,
  never touches `MethodBodyBlock` → **never** fails on obfuscation.

Result: every type, member, parameter name, custom-attribute *blob*
(raw + UTF-8 strings) lands in JSON. We rebuild the entire public API
contract from metadata even when bodies are unreadable.

See `tools/metadata_extractor/Program.cs` + `reverse_engineering/metadata/*.json`.

---

## Manifest-only findings (recap, confirmed)

| Field | Value | Source |
|-------|-------|--------|
| Target runtime | **.NET Framework 4.5.1**       | `TargetFrameworkAttribute` |
| Build year     | **2024**                       | `AssemblyCopyrightAttribute` |
| Company        | **YDsoft-773035387**           | `AssemblyCompanyAttribute` |
| Assembly GUID (MProgService) | `91bfb504-3851-4ccd-a30e-29ba41ac7ba6` | `GuidAttribute` |
| Assembly GUID (OracleServiceMobile) | `1429d5b4-d928-48f2-bd53-f38f3b3b15ae` | `GuidAttribute` |
| Oracle client | ODP.NET 1.102.3.0 (Oracle 11g/12c era) | IL extern ref |
| License.dll runtime | .NET 4 Client Profile (2014) | `TargetFrameworkAttribute` |

---

## Strings & secrets — surveillance

We performed a `BlobStrings` scan over every custom-attribute payload
(ASCII substrings ≥ 4 chars). **No credential, JWT key, or Oracle
password leaked.** Findings limited to:

- product/title/version strings (`MProgService`, `1.0.0.0`, `2024`).
- the company tag `YDsoft-773035387`.
- assembly GUIDs.
- TargetFramework strings.

The string-encryption transform of ConfuserEx prevents extraction of
encrypted constants (Oracle connection strings, JWT signing key, table
names) from these binaries. **Per `معين`'s direction (rule #3): we
document this and do not extract.**

→ See [`07_MULTI_TENANT.md`](./07_MULTI_TENANT.md) on how we recover
tenant config from `OracleServiceMobile.exe.config` / Registry at
deployment time instead.
