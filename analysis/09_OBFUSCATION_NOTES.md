# 09 — Obfuscation Notes

> **Status:** ⚪ pending — populated continuously starting Phase 2.

## Observed obfuscator

`ConfuserEx` (or a fork). Evidence: the `ConfusedByAttribute` we expect to
see at the assembly level once `monodis --output` or `ilspycmd` exposes
custom attributes. The tool emits:

- mangled internal type names (e.g. unicode soup, control chars).
- string encryption (constants wrapped in a decoder method).
- control-flow flattening (state machines for methods that should be linear).
- anti-tamper checks.

## Bypass strategy

1. **De-obfuscate first.** Try `de4dot` (https://github.com/de4dot/de4dot)
   on a copy of each protected DLL:
   ```
   de4dot binaries/MProgService.dll  -o binaries/MProgService.cleaned.dll
   ```
2. Run `ilspycmd` on the cleaned DLL.
3. If `de4dot` can't fully clean it (very common with newer ConfuserEx
   forks), do **two-pass**: dump cleaned IL, manually rebuild method
   signatures from `monodis` output.
4. For string-encrypted constants, locate the decoder method, invoke it
   offline via `mono` or `dotnet` for each call-site (out of scope here —
   document for later if needed).

## Tooling status (Phase 1)

| Tool | Installed | Path |
|------|:---------:|------|
| `monodis`  | ✅ | system `/usr/bin/monodis` (mono-utils) |
| `ilspycmd` | ✅ | `~/.dotnet/tools/ilspycmd` (v8.2.0.7535, runtime net6.0) |
| `de4dot`   | ⚠️ source-only | `tools/bin/de4dot/de4dot-master/` (we got source from `de4dot/de4dot` master; **no compiled binary yet**) |

> **de4dot status:** the original `de4dot/de4dot` GitHub project has no
> published releases anymore (404 on the older release URL). The
> community fork `dnSpyEx/de4dot` is the current home but doesn't host a
> stable zip either. For Phase 2 we will therefore **start without de-obf**
> and only build de4dot from source if obfuscation actually blocks us.
> A `dotnet build` of `tools/bin/de4dot/de4dot-master/de4dot.sln` is the
> fallback recipe.

## Per-binary status

| Binary | monodis (Phase 1 smoke) | de4dot result | ilspycmd result | manual work needed |
|--------|-------------------------|---------------|-----------------|--------------------|
| `MProgService.dll`        | ❌ SEGFAULT after 95 lines (manifest only)  | ⚪ | ⚪ | likely |
| `OracleServiceMobile.exe` | ❌ SEGFAULT after 102 lines (manifest only) | ⚪ | ⚪ | likely |
| `License.dll`             | ❌ ABORT after 278 lines (manifest only)    | ⚪ | ⚪ | likely |

> **Phase-1 finding (confidence: 95%):** all three proprietary assemblies
> crash `monodis` after dumping only the **assembly manifest**.
> This is **strong empirical evidence of ConfuserEx-style metadata
> tampering** — confused metadata tables (TypeRef / MemberRef / TypeSpec /
> Method table corruption) are the classic monodis crashers.
>
> Implication: **ilspycmd will likely also struggle**. Phase 2 must:
>
> 1. Try ilspycmd first (it's much more tolerant than monodis).
> 2. If ilspycmd produces unreadable identifiers, build de4dot from source
>    and try again.
> 3. If de4dot can't clean it, fall back to **PE-level metadata reading**
>    via Python `pefile` + manual `dnlib` (or `Mono.Cecil`) walking.

## Manifest-only findings (Phase 1)

The few hundred lines that monodis *did* write before crashing are still
informative — they reveal external assembly references and target framework:

```il
.assembly extern mscorlib            { .ver 4:0:0:0 }   // .NET Framework 4.x
.assembly extern Oracle.DataAccess   { .ver 1:102:3:0 } // ODP.NET (Oracle 12c era)
.assembly extern System.Data         { .ver 4:0:0:0 }
.assembly extern System.ServiceModel { .ver 4:0:0:0 }   // WCF runtime
```

→ Target runtime: **.NET Framework 4.x** (likely 4.5 or 4.6.x).
→ Oracle client: **ODP.NET 1.102.3.0** = **Oracle 11g/12c** binary.
→ WCF confirmed.
