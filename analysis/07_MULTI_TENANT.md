# 07 — Multi-Tenant Architecture

> **Status:** 🟢 mechanism confirmed · 🟡 wiring details TBD in Phase 7.
> **Confidence:** `appId` as tenant key = **100%** (proven by signatures).
> Connection-string source = 70% (inferred from class names).

---

## TL;DR

**Every** non-meta WCF operation accepts `string appId` as its **last
parameter**. The server uses `appId` as a key into a `Dictionary<int|string,
string>` map of Oracle connection strings, switching the active database per
request.

This means the React-Native client must know **its own `appId`** and pass it
on **every** call. Phase 7 will confirm where the APK obtains `appId`
(login response? hardcoded per-build? config file pulled from server?).

---

## Evidence

| Observation | Source |
|-------------|--------|
| 33 of 33 `IServiceElect` ops carry a `string appId` parameter (only `test`, `GetCompanyData` don't because they take no params; `Login` takes it explicitly). | `analysis/01_WCF_ENDPOINTS.md` table |
| 26 of 27 `IService1` ops carry `appId` (only `Index`, `GetCallerIdentity`, `GetCompanyData`, `GetRepBalanceDetails`, `GetListAccountsLedger`, `GetAccountBalance` are exempt — and most of those are pre-auth or no-arg helpers). | same |
| The `Credentials` DTO itself has `appId` as a property → it travels with the login request. | `reverse_engineering/metadata/MProgService.json` |
| `IdealRegistry` class with 12 methods + `ERegistryPossibleRoots` enum (8 values) lives in `OracleServiceMobile.exe`. | metadata dump |
| `AppConfigHelper` + `AppSetting` (12 properties, 25 methods) live in `OracleServiceMobile.exe`. | metadata dump |

---

## How the server resolves `appId` → connection string

**Hypothesis (confidence 70%):**

1. At startup, `OracleServiceMobile.exe` loads its config from a combination of:
   - The Windows Registry (via `IdealRegistry` — keys under one of
     `ERegistryPossibleRoots`).
   - `OracleServiceMobile.exe.config` (the .NET app-config XML).
   - The encrypted `_appConfigFile` referenced by `Defence`.

2. Config schema looks like:
   ```
   tenant.<appId>.connectionString = "Data Source=...;User Id=...;Password=...;"
   ```
   or a row-array — the parser is `AppConfigHelper.KeyValuePair..ctor`,
   whose body is unfortunately ConfuserEx'd (it's one of the 3 obfuscated
   methods in the host EXE).

3. On each WCF call, `Service1`/`ServiceElect` opens a connection by
   calling `DataBaseHelper.Open(appId)` (or similar — body opaque) which
   does the dictionary lookup.

**Why we believe this:**
- The original brief stated `Dictionary<int, string> ConnetionStrings`
  exists. We can't *see* it (body obfuscated) but the **shape** of the
  classes around it (`AppConfigHelper`, `AppSetting`, `IdealRegistry`)
  matches the standard ".NET Service reads config + registry at startup"
  pattern.
- `appId` is `string` in the WCF surface, but the legacy `Dictionary<int,
  string>` is `int`-keyed. Either:
  - There is a `Convert.ToInt32(appId)` at the boundary, or
  - The dictionary in the modern build is now `<string, string>` (the
    brief was reading older code).

---

## Implications for `app1`

```ts
// Every API call needs appId in the body / query string.
type ApiCallContext = {
  appId: string;     // tenant id; identifies the Oracle database
  jwt:   string;     // session token (contains NOU + permission flags)
  baseUrl: string;   // host + path (e.g. http://10.0.0.5:8080/Service1.svc)
};
```

The Axios layer should:
1. Have `appId` injected on every request (interceptor adds `appId` if missing).
2. Have `appId` baked into the JWT *if* the server also reads it from the
   token (TBD in Phase 4). Sending it twice (in JWT + in param) is
   harmless and probably what the legacy client does.

---

## Open questions

1. Is `appId` numeric-as-string (e.g. `"773035387"` like the company tag),
   or alphanumeric (e.g. `"abbasi_tahseel"`)?
2. Where does the APK *get* `appId`? Hardcoded? From server bootstrap?
3. Is there a single shared `appId` per APK build, or a per-installation one?
4. Does the JWT carry `appId` as a claim, or only the session user id?
5. What happens server-side if `appId` is unknown? `FaultException`?
   Default tenant?

→ Phase 7 (APK reverse) will answer #1, #2, #3 by inspecting the APK's
`strings.xml` and login flow.
→ Phase 4 (JWT) will answer #4.
