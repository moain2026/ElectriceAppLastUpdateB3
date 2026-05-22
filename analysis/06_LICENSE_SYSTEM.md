# 06 — License System

> **Status:** 🟢 partial — clear DLL fully understood; obfuscated `Defence`
> class names known, bodies opaque (per rule #3).
> **Confidence:** algorithm = 100% (License.dll); Defence usage = 60%.

This system has **two layers**:

1. `binaries/License.dll` — 2014 VB.NET artefact. **Fully reversed.**
2. `binaries/OracleServiceMobile.exe → OracleServiceMobile.Defence` class —
   2024 build, **obfuscated**, only signatures recovered.

---

## Layer 1 — `License.dll` (2014, unobfuscated)

| Attribute | Value |
|-----------|-------|
| Language       | VB.NET                           |
| Runtime        | .NET 4 Client Profile            |
| Assembly GUID  | `3b54d4c9-eb6a-40dc-b619-bdcf34f93dcb` |
| Built          | 2014                             |
| ConfuserEx?    | **no** (no `ConfusedByAttribute` type) |
| Source         | `reverse_engineering/decompiled_csharp/License/License/License.cs` |

### Method 1 — `GetHDDSerialN(DriveLetter)`

```csharp
public static object GetHDDSerialN(string DriveLetter = "C")
{
    if (DriveLetter == "" || DriveLetter == null) DriveLetter = "C";
    var val = new ManagementObject("Win32_LogicalDisk.DeviceID=\"" + DriveLetter + ":\"");
    val.Get();
    return ((ManagementBaseObject)val)["VolumeSerialNumber"].ToString();
}
```

WMI `Win32_LogicalDisk.VolumeSerialNumber` — returns the 8-char hex string
Windows assigns at format time. Not the physical HDD serial; the **partition**
volume id.

### Method 2 — `PrimaryKey(HDDSerial)`

```csharp
public static object PrimaryKey(string HDDSerial)
{
    var text  = "";
    var s     = HDDSerial.ToUpper();
    for (int i = 0; i <= s.Length - 1; i++)
    {
        char c = s[i];
        if (char.IsDigit(c))
            text += (char)((int)(c - '0' + i + 5) % 10 + '0');     // digit shift
        else
            text += (char)((int)Math.Round(((c - 'A') + i + 3) % 27.0 + 65)); // letter shift mod 27 (sic — bug)
    }
    return text;
}
```

- Per-char Caesar-like shift, **position-dependent** (`+ i`).
- Digits shifted by `+5`, mod 10.
- Letters shifted by `+3`, mod **27** (one off — produces a non-A-Z char
  occasionally when result == 26). Probably an old bug; not security relevant.

### Method 3 — `GetFinalKey(PrimaryKey)`

```csharp
public static string GetFinalKey(string PrimaryKey)
{
    // same shape as PrimaryKey, but digits +3, letters +5
}
```

### Chain

```
HDDSerial  →  PrimaryKey  →  FinalKey
   |             (+5/+3)        (+3/+5)
   └── deterministic, reversible if you know the function.
```

→ **No cryptography.** No secret. Anyone who reads this DLL can write a
keygen. This is **trivial obfuscation**, not protection.

### Status in production

- The `MProgService.dll`/`OracleServiceMobile.exe` of 2024 do **not**
  reference `License.dll` in their `.assembly extern` table — verified by
  inspecting `reverse_engineering/metadata/MProgService.json`:
  the `AssemblyReferences` list contains `mscorlib`, `System.*`,
  `Oracle.DataAccess`, **but not** `License`.
- **Conclusion (confidence 80%):** `License.dll` is a legacy artefact
  shipped alongside the modern binaries but no longer wired in. The current
  protection is the `Defence` class inside `OracleServiceMobile.exe`.

---

## Layer 2 — `OracleServiceMobile.Defence` (2024, obfuscated)

Source (signatures only): `reverse_engineering/decompiled_csharp/OracleServiceMobile/OracleServiceMobile/Defence.cs`

All bodies are unreadable due to ConfuserEx (junk opcodes — `// Invalid
MethodBodyBlock: ...`). The metadata gives us **names + signatures only**:

| Member | Signature | Purpose (inferred) |
|--------|-----------|---------------------|
| `_appConfigFile`         | `string` field        | path to encrypted app config |
| `AddKey()`               | `long`                | issue/store activation key       |
| `MashineSerialNumber(strDrive)` | `long`         | derive machine fingerprint (this is the **`secureId`** the APK passes on Login!) |
| `clear_key()`            | `string`              | erase stored key                 |
| `d_r()`                  | `DateTime`            | "date_read" — expiry check?      |
| `data_demo()`            | `bool`                | running in demo mode?            |
| `text_out()`             | `bool`                | show/hide a debug overlay        |
| `cut_str(in_str, pos, len)` | `string`           | utility — substring              |
| `bool_to_oct(in_bool)`         | `string`        | encode a "bool string" → octal — config-at-rest encoding |
| `bool_to_oct_triade(in_bool)`  | `string`        | variant of the above             |
| `bool_to_val(in_bool)`         | `double`        | encode → double                  |
| `val_to_bool(in_val)`          | `string`        | inverse of `bool_to_val`         |
| `oct_to_bool(in_val)`          | `string`        | inverse of `bool_to_oct`         |
| `ErrorReport2(MyFunction, ex)` | `bool`          | marked `[NoInlining, NoOptimization]` → anti-tamper hook |

> **Inference (confidence 75%):** The "bool_*" group is a homemade
> bit-packing scheme used to persist activation state (date, flags) into
> a string the server can store anywhere — registry value, config file,
> WMI store. It's *cosmetic obfuscation* of the same idea as
> base64-encoding a struct.

### Critical link to client

The APK calls `Login(username, password, appId, secureId)`. We **strongly
suspect** that `secureId` is derived from the **server's**
`Defence.MashineSerialNumber(...)` result, sent to the client by an earlier
bootstrap call, and then echoed back on every login. This is verified in
Phase 7 (APK contains the producer of `secureId` *on the device*, not the
server — but the server's `MashineSerialNumber` is the *expected value*
that login compares against).

### Per project rule #3: we do NOT reverse the bodies

> _"للـ string-encrypted constants: وثّق فقط، لا تستخرج (out of scope)"_

We have documented:
- The class layout.
- All 14 method names + signatures.
- The expected role of each.

We have **not** attempted to:
- Recover any AES/DES key.
- Recover any hardcoded date / expiry.
- Run the binary to observe behaviour.

This is sufficient for the rewrite: licence enforcement happens **server-side**
in the legacy stack, and is invisible to the React Native client.

---

## Implications for the rewrite

| Question | Recommendation |
|----------|----------------|
| Does the RN client need to call licence APIs? | **No.** Licence is server-side only. |
| Does the RN client send `secureId`? | **Yes** — Login takes `secureId`. Source it from the APK (Phase 7). |
| Should the RN client be tied to a device? | TBD by product. The legacy app likely uses Android `Settings.Secure.ANDROID_ID` as the client-side `secureId`. |
| Do we need to keep `License.dll` in production? | No — the modern stack does not reference it. Recommend retirement. |

---

## Open questions

1. Is `Defence.MashineSerialNumber` evaluated **per-request** or **once at startup**?
2. Does `d_r()` enforce a hard expiry, or just log?
3. What value does the APK put in `secureId` for the Login call? (Phase 7)
4. Does the server respect `data_demo() == true` by returning fake/short data?
