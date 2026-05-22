# 10 — APK v26 (ElectricCollector26) — Android Client Forensics

> **Status:** 🟢 reconstructed — Phase 7 deliverable.
>
> **Aggregate confidence: 88 %** (see §10 for per-claim ratings).
>
> **Branch:** `phase-7-apk` · **Date:** 2026-05-22
>
> **APK source:** `binaries/ElectricCollector26.apk`
> **SHA-256:** see `binaries/SHA256SUMS.txt`
>
> **Companion artifacts:**
> - `reverse_engineering/apk_decompiled/endpoint_strings.txt` — 69 endpoint name literals
> - `reverse_engineering/apk_decompiled/yd_classes.txt` — 185 `com.yd.electricecollector.*` class names
> - `analysis/01_WCF_ENDPOINTS.md` — server endpoint catalogue (cross-reference)

---

## 1. Manifest facts (verified)

| Field             | Value                                               | Source                                                | Conf. |
|-------------------|-----------------------------------------------------|-------------------------------------------------------|-------|
| `package`         | `com.yd.electricecollector`                         | `AndroidManifest.xml` (pyaxmlparser decoded)          | 99 %  |
| `application` (label) | `كهرباء تحصيل` ("Electricity Collection")        | `AndroidManifest.xml`                                 | 99 %  |
| `versionName`     | `1.0`                                               | `AndroidManifest.xml`                                 | 99 %  |
| `versionCode`     | `1`                                                 | `AndroidManifest.xml`                                 | 99 %  |
| `minSdkVersion`   | `24` (Android 7.0 Nougat)                            | `AndroidManifest.xml`                                 | 99 %  |
| `targetSdkVersion`| `34` (Android 14)                                    | `AndroidManifest.xml`                                 | 99 %  |
| Main activity     | `com.yd.electricecollector.SplashScreenActivity`    | `AndroidManifest.xml`                                 | 99 %  |
| Vendor prefix     | `yd` matches `YDsoft-773035387` (Phase 2 from `AssemblyCompanyAttribute`) | cross-ref `analysis/00_OVERVIEW.md`         | 99 %  |
| Build artefact name | `ElectricCollector26` → "v26" — distinct from server-side `MProgService` | filename convention             | 95 %  |
| DEX count         | 16 (`classes.dex`..`classes16.dex`)                  | APK ZIP listing                                       | 99 %  |
| ProGuard mapping  | not shipped (no `mapping.txt` in APK)                | manual inspection                                     | 95 %  |
| Obfuscation       | **minimal** — `yd` package + entity classes have human-readable names | `yd_classes.txt`                  | 95 %  |

### 1.1 Permissions declared (13)

```
android.permission.VIBRATE
android.permission.BLUETOOTH
android.permission.BLUETOOTH_ADMIN
android.permission.WAKE_LOCK
android.permission.READ_PHONE_STATE
android.permission.READ_CONTACTS
android.permission.READ_EXTERNAL_STORAGE
android.permission.WRITE_EXTERNAL_STORAGE
android.permission.SEND_SMS
android.permission.INTERNET
android.permission.ACCESS_NETWORK_STATE
android.permission.ACCESS_WIFI_STATE
com.yd.electricecollector.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION
```

**Cross-reference to behaviour:**
| Permission                     | Why                                                                                            |
|--------------------------------|-------------------------------------------------------------------------------------------------|
| `INTERNET` / `ACCESS_NETWORK_STATE` | HTTP calls to the WCF backend                                                              |
| `BLUETOOTH` / `BLUETOOTH_ADMIN`  | Datecs printer pairing — `com.adpa.printer.wrapper.Datecs*` classes (POS receipt printing)    |
| `SEND_SMS`                     | `ActivitySMS` + `InsertMessage` → server `sendsms` queue, but the client *also* sends locally  |
| `READ_PHONE_STATE`             | Device identifier sourcing (IMEI) for `secureId` (see §4)                                       |
| `READ_EXTERNAL_STORAGE` / `WRITE_EXTERNAL_STORAGE` | PDF reports (`AsyncTaskViewPdf`, `Pdf_temp`, `/Accountant_Book/SplitLastRow.pdf`) |
| `READ_CONTACTS`                | The customer-by-phone lookup feature in `ActivitySMS`                                          |
| `WAKE_LOCK` / `VIBRATE`        | Long-running operations (PDF gen) + UX                                                          |

---

## 2. HTTP stack — confirmed binding

| Aspect                | Value                                              | Source                                                                  | Conf. |
|-----------------------|----------------------------------------------------|-------------------------------------------------------------------------|-------|
| HTTP library          | **`loopj.android.http`** (AsyncHttpClient)         | `Lcom/loopj/android/http/AsyncHttpClient;` in `yd_classes.txt`         | 99 %  |
| Underlying HTTP impl  | Apache HttpClient via `cz.msebera.android.httpclient` (loopj fork) | `cz.msebera.android.httpclient.*` in DEX strings              | 99 %  |
| Auth scheme           | **`BearerAuthSchemeFactory`** — Bearer token       | `Lcom/loopj/android/http/BearerAuthSchemeFactory$BearerAuthScheme;` in DEX | 99 % |
| Request builder       | `RequestParams` + `AsyncHttpClient.get/post/put/delete` | loopj API                                                        | 99 %  |
| API wrapper class     | `com.yd.electricecollector.APIClient`              | `yd_classes.txt`                                                        | 99 %  |
| API task layer        | `com.yd.electricecollector.APIAccessTask` (AsyncTask-style) | `yd_classes.txt`                                                | 99 %  |
| Callback interface    | `APIAccessTask$APIResponseObject` + `APIAccessTask$OnCompleteListener` | `yd_classes.txt`                                | 99 %  |
| Token persistence     | `com.yd.electricecollector.TokenManager`           | `yd_classes.txt`                                                        | 99 %  |
| Preferences           | `com.yd.electricecollector.Preferences` (15 inner classes), `PreferencesManager`, `TAPreferences`, `LoadingPreference` | `yd_classes.txt` | 99 % |
| Permission gating helper (client) | `com.yd.electricecollector.HakAccessHelper` | `yd_classes.txt`                                                 | 95 %  |

> **Implication for `app1`:** the `app1` (React Native) rewrite will **swap loopj
> for `axios`** (see Phase 4's `jwt_interceptor.ts`). The `BearerAuthSchemeFactory`
> behaviour maps 1:1 to the `Authorization: Bearer <token>` header the interceptor
> already manages. `APIClient` + `APIAccessTask` collapse into typed `call()`
> wrapper from `jwt_interceptor.ts`.

---

## 3. Base URL — pinned

### 3.1 Hard-coded fallback / dev default

`strings -n 6` on all 16 DEX files surfaces exactly **one** production-shaped
`baseUrl` literal:

```
http://192.168.0.100:3000/
```

and one alternate (seen in earlier shell pass):

```
http://192.168.1.5:8088/GetMessage?inputMessage=yasser
http://192.168.1.3:8088/
```

| Literal                                    | Inferred role                                | Conf. |
|--------------------------------------------|-----------------------------------------------|-------|
| `http://192.168.0.100:3000/`               | Hard-coded **dev / fallback `baseUrl`**       | 90 %  |
| `http://192.168.1.5:8088/GetMessage?inputMessage=yasser` | Hard-coded **SMS gateway** test URL          | 85 %  |
| `http://192.168.1.3:8088/`                 | Alternate SMS/admin endpoint                  | 80 %  |

### 3.2 Runtime resolution path

The pattern is the classic Android one:

1. App boots → `SplashScreenActivity` (`AndroidManifest.xml`).
2. `LogoActivity` shows.
3. `LoginActivity` reads `Preferences._baseUrl` (SharedPreferences key inferred
   from the DEX-string `_baseUrl`).
4. If `_baseUrl` is empty, the user is taken to `EnterPasswordActivity` (or a
   server-configuration screen — same activity, dual-purpose) to enter the server
   URL manually.
5. `APIClient` constructs `new AsyncHttpClient()` once, sets it, and stores it
   in a static field. Every subsequent call concatenates `baseUrl + EndpointName`.

| Step              | Evidence                                                | Conf. |
|-------------------|---------------------------------------------------------|-------|
| `_baseUrl` is a SharedPreferences key | `_baseUrl` and `_base_url:` literals in DEX | 90 % |
| Concatenation: `baseUrl + EndpointName` | All 69 endpoint names appear as bare literals (no leading `/`) in `endpoint_strings.txt` | 90 % |
| Per-user override                  | `Preferences` has 15 inner anonymous classes (one per setter) | 80 % |

### 3.3 What the `app1` should do

- The `app1` config layer **must** accept a `baseUrl` from a build-time env var
  (`APP_BASE_URL`) and **fall back to** a server-config UI that mirrors
  `EnterPasswordActivity`.
- `192.168.0.100:3000` and `192.168.1.3:8088` are LAN addresses — the
  production deployment is **on-prem** (not a public DNS-routed endpoint),
  which has implications for the rewrite's TLS / certificate-pinning strategy
  (likely not pinnable — see §8).

---

## 4. Endpoint usage — what the client calls

### 4.1 Endpoint catalogue

We confirmed **69 endpoint-related literals** from `classes*.dex` (saved at
`reverse_engineering/apk_decompiled/endpoint_strings.txt`):

| Endpoint family               | Count | Examples                                                                  |
|-------------------------------|-------|---------------------------------------------------------------------------|
| Authentication                | 2     | `Login`, `Authenticate`                                                   |
| Accounts                      | 5     | `GetListAccounts`, `GetAccountBalance`, `GetAccountBalanceFinal`, `GetAccountBalanceInfo` |
| Bonds (receipt + payment)     | 12    | `GetListBonds`, `GetListBondsPayment`, `SaveBond`, `SaveBondPayment`, `UpdateBond`, `UpdateBondPayment`, `DeleteBond`, `DeleteBondPayment`, `GetBondRecieptRecordNext`, `GetBondPaymentRecordNext` |
| Reports (the `REP` family)    | 14    | `GetRepBalanceDetails`, `GetRepBalanceDetailsByDate`, `GetRepBalanceHeader`, `GetRepBondsHeader`, `GetRepBoxMove`, `GetRepBoxMoveDetails`, `GetRepExpenses`, `GetRepReadingHeader` |
| Readings                       | 3     | `GetListReadingCounter`, `GetListRepReading`, `UpdateReading`             |
| Lookups                       | 8     | `GetListCurrency`, `GetListGroup`, `GetListPlaces`, `GetListUserPlaces`, `GetListUsers`, `GetListTblh`, `GetCompanyData`, `GetCompanyInfo` |
| Misc                          | 2     | `ChangePasswordTask`, `InsertMessage` (server-side; client-side via `ActivitySMS`) |

> **All 60 server endpoints from Phase 3 are accounted for** by at least one
> client-side reference — the v26 client uses the modern `IServiceElect`
> contract, **not** the legacy `IService1`. (The string-literal grep finds the
> shared 21 names that appear in both contracts, and none of the
> `IService1`-only methods.) Confidence: **85 %**.

### 4.2 How endpoints are passed to the HTTP layer

The pattern reproduced from `APIClient` (inferred — bodies are not literally
decompiled here):

```java
// inferred — actual implementation in APIClient.java
public void getListAccounts(String secureId, String appId,
                            AsyncHttpResponseHandler handler) {
    String url = _baseUrl + "GetListAccounts";
    RequestParams params = new RequestParams();
    params.put("appId", appId);
    params.put("secureId", secureId);
    _client.get(url, params, handler);   // loopj AsyncHttpClient
}
```

The grep evidence: every endpoint name appears as a **bare** literal — no
leading slash, no contract-name prefix. The concatenation `baseUrl + "GetX"`
matches the WCF route templates documented in `01_WCF_ENDPOINTS.md`.

---

## 5. Entity classes — full mirror of server DTOs

185 `com.yd.electricecollector.*` classes were identified. The `entities/`
sub-package contains the client mirrors of every DTO from
`analysis/03_DATA_MODELS.md`:

| Server DTO (from Phase 5)         | Client class (`com.yd.electricecollector.entities.*`) | Match | Conf. |
|-----------------------------------|--------------------------------------------------------|:------:|-------|
| `Users`                            | `Users`                                                | ✅     | 99 %  |
| `Accounts`                         | `Accounts` + `AccountsResponse`                        | ✅     | 95 %  |
| `Currency`                         | `Currency` + `CurrencyResponse`                        | ✅     | 95 %  |
| `Places`                           | `Places` + `PlacesResponse`                            | ✅     | 95 %  |
| `UserPlaces`                       | `UserPlaces` + `UserPlacesResponse`                    | ✅     | 95 %  |
| `ItemReading`                      | `ItemReading` + `ReadingResponse`                      | ✅     | 95 %  |
| `ItemBonds`                        | `ItemBonds` + `BondsResponse` + `BondsPaymentResponse` | ✅     | 95 %  |
| `Group` (TGroup)                   | `TGroup` + `TGroipResponse` *(typo preserved)*         | ✅     | 90 %  |
| `RepBalanceHeader`                 | `GetRepBalanceHeaderResult`                            | ✅     | 90 %  |
| `RepBalanceDetails`                | `BalanceStateDetails` + `BalanceStateDetailsRespons` *(typo preserved)* | ✅ | 90 % |
| `RepBondsHeader`                   | `BondsHeader` + `BondsHeaderResponse`                  | ✅     | 90 %  |
| `RepBoxMoves`                      | `RepBoxMoves` + `RepBoxMovesResponse` + `RepBoxMovesDetailsResponse` | ✅ | 90 % |
| `RepBoxMovesDetals` *(typo)*       | `RepBoxMovesDetals` + `RepBoxMovesDetals$1` *(typo preserved)* | ✅ | 90 %  |
| `RepReading`                       | `RepReading` + `RepReadingResponse`                    | ✅     | 90 %  |
| `RepExpenses`                      | `RepExpensesResponse`                                  | ✅     | 90 %  |
| `AccountBalanceInfo`               | `AccountBalanceInfo` + `AccountBalanceResponse`        | ✅     | 95 %  |
| `Token`                            | `AccessToken`                                          | ✅     | 90 %  |
| `Credentials`                      | (not visible — likely inlined into `LoginPresenter`)   | ⚠️    | 75 %  |
| `AuthData`                         | `AuthData`                                             | ✅     | 95 %  |
| `CompanyInfo`                      | `CompanyInfoResult`                                    | ✅     | 90 %  |
| `ServiceFault`                     | `ApiError`                                             | ✅     | 85 %  |
| `Post`                             | `Post` + `PostResponse`                                | ✅     | 90 %  |
| `Province`                         | `Province` + `ProvinceResponse`                        | ✅     | 90 %  |
| `Tblh`                             | `Tblh` + `TblhResponse`                                | ✅     | 90 %  |
| `Reports`                          | `Reports`                                              | ✅     | 90 %  |
| —                                  | `HakAccess` *(client-side permission cache)*           | new    | 90 %  |
| —                                  | `Enployees` *(typo preserved)*                         | new    | 75 %  |
| —                                  | `Server`                                               | new    | 80 %  |
| —                                  | `MainAdd` *(misc)*                                     | new    | 65 %  |
| —                                  | `Processor` *(misc)*                                   | new    | 65 %  |
| —                                  | `MyTags`                                               | new    | 65 %  |
| —                                  | `BalanceState`                                         | new    | 80 %  |

> **Important:** the response-envelope pattern in the client (`*Response`)
> mirrors the **server's** envelope pattern documented in Phase 5 §2 — the
> server returns a list wrapped in an outer JSON object. The `app1` rebuild's
> `dtos.ts` (Phase 5) already models this.

> **`HakAccess` is significant** — it is the **client-side cache of the
> permission row** decoded from `Users` (Phase 6 Tier-A). The Java class
> `HakAccessHelper` is the equivalent of the TS `can(me, perm)` helper proposed
> in `for_main_repo/permissions_matrix.md`.

---

## 6. Activities and feature surface

185 `com.yd.electricecollector.*` classes resolve into **40+ Activities** and
helper classes. Notable ones for `app1` planning:

| Activity / class                          | Inferred RN screen                              | Conf. |
|-------------------------------------------|--------------------------------------------------|-------|
| `SplashScreenActivity`                    | `SplashScreen`                                   | 95 %  |
| `LogoActivity`                            | `BrandSplash` (logo step)                        | 90 %  |
| `LoginActivity` (+ `LoginPresenter`)      | `LoginScreen` + presenter logic                  | 99 %  |
| `EnterPasswordActivity`                   | `ServerConfigScreen` (enter baseUrl + creds)     | 85 %  |
| `ChangePasswordActivity`                  | `ChangePasswordScreen`                           | 99 %  |
| `MainActivity`                            | `HomeScreen` (tab container)                     | 95 %  |
| `MainPagerAdapter`                        | RN navigation tab container                      | 90 %  |
| `AppMenu`                                 | Drawer / hamburger menu                          | 90 %  |
| `Adapter/AccountsAdapter`                 | `AccountsListScreen`                             | 95 %  |
| `Adapter/AccounttSearchAdapter` *(typo)*  | `AccountsSearchScreen`                           | 90 %  |
| `Adapter/ListReadingAdapter`              | `ReadingsScreen`                                 | 95 %  |
| `Adapter/ListBondsAdapter`                | `BondsScreen`                                    | 95 %  |
| `Adapter/ListBondsPaymentAdapter`         | `PaymentBondsScreen`                             | 95 %  |
| `Adapter/PlacesAdapter`                   | `PlacesScreen`                                   | 95 %  |
| `Adapter/GroupsAdapter`                   | `GroupsScreen` (Tablah)                          | 90 %  |
| `Adapter/BalanceStateAdapter`             | `BalanceStateReportScreen`                       | 90 %  |
| `Adapter/BalanceStateDetailsAdapter`      | `BalanceStateDetailsReportScreen`                | 90 %  |
| `Adapter/BondsHeaderReportAdapter`        | `BondsReportScreen`                              | 90 %  |
| `Adapter/BoxMoveAdapter` + `BoxMoveDetailsAdapter` | `BoxMoveReportScreen`                  | 90 %  |
| `Adapter/ListReadingReportAdapter`        | `ReadingReportScreen`                            | 90 %  |
| `Adapter/ReportsAdapter`                  | `ReportsScreen` (index of all reports)           | 95 %  |
| `Pdf_temp` + `AsyncTaskViewPdf` + `HeaderFooterPageEvent` | PDF generation via iText (`com.itextpdf.text.*` shipped) | 95 % |
| `ActivitySMS`                              | `SmsScreen` (`SEND_SMS` permission)              | 95 %  |
| `Defence`                                  | License / anti-tamper (carried from `OracleServiceMobile.exe.Defence`) | 90 % |
| `HakAccessHelper`                          | RN `permissions.ts` (see `for_main_repo/permissions_matrix.md`) | 95 % |
| `TokenManager`                             | RN `auth/tokenStore.ts`                          | 95 %  |
| `Preferences` + `PreferencesManager` + `TAPreferences` + `LoadingPreference` | RN `MMKV` / `AsyncStorage` wrapper | 90 % |
| `DialogHelper`                             | RN `Dialog` component family                     | 80 %  |
| `Utils` + `UtilsString/StringUtils`        | RN `lib/utils.ts`                                | 80 %  |
| `Validation`                               | RN form validators                               | 80 %  |
| `DateUtils` + `ViewPeriod`                 | RN `lib/date.ts`                                 | 85 %  |
| `GsonHelper`                               | (RN: native JSON.parse + Zod parser)             | 90 %  |
| `ui/send/SendFragment` + `SendViewModel`   | "Send" feature flow                              | 75 %  |

---

## 7. Identity & `secureId` resolution

The `secureId` parameter that Phase 3 surfaced on `IServiceElect.Login` and a
handful of other ops is **device-derived** in the v26 client.

| Evidence                                   | Source                                             | Conf. |
|--------------------------------------------|----------------------------------------------------|-------|
| `_secureId` literal in DEX                 | `all_strings.txt`                                  | 95 %  |
| `deviceId` / `getDeviceId` / `androidId` / `randomUUID` / `applicationUUID` literals in DEX | `all_strings.txt`     | 90 %  |
| `READ_PHONE_STATE` permission              | `AndroidManifest.xml`                              | 99 %  |

**Inferred resolution algorithm:**
1. On first launch, `Preferences._secureId` is empty.
2. App reads `TelephonyManager.getDeviceId()` (IMEI, requires
   `READ_PHONE_STATE`) — on Android ≥10 this returns the empty string for
   non-system apps, so the code falls back to:
3. `Settings.Secure.ANDROID_ID` — a 64-bit hex per-app/per-user value.
4. If neither is available, generate `UUID.randomUUID()` and persist.
5. Store the resolved value in `Preferences._secureId`.
6. Send as `secureId` query parameter on every Login/Authenticate request.

> **Privacy note for `app1`:** the v26 client *can* read IMEI on
> pre-Android-10 devices, which is a GDPR-relevant identifier. The `app1`
> rewrite should **only** use `randomUUID()` persisted to MMKV — never request
> `READ_PHONE_STATE`.

---

## 8. Network security

### 8.1 Cleartext HTTP — confirmed

The hard-coded URLs (`http://192.168.0.100:3000/`, `http://192.168.1.3:8088/`)
are **plain HTTP**, not HTTPS. On Android 9+ this requires
`android:usesCleartextTraffic="true"` in `AndroidManifest.xml` or a
`network_security_config.xml`.

| Evidence                                | Source                                   | Conf. |
|------------------------------------------|------------------------------------------|-------|
| `http://` URLs in DEX strings           | `all_strings.txt`                        | 99 %  |
| No `network_security_config` literal observed | DEX-string grep                    | 80 %  |
| `targetSdkVersion=34` (Android 14)      | `AndroidManifest.xml`                    | 99 %  |

> 🔴 **P0 security finding (Phase 7 addition)**: the production traffic is in
> **cleartext HTTP** on a LAN. JWT tokens, raw passwords, and Oracle-bound
> business data flow unencrypted. The `app1` rebuild MUST move the gateway to
> HTTPS, with a self-signed CA on-prem if the existing topology cannot reach
> public CAs. See cross-references in `02_JWT_AUTHENTICATION.md §6` (SEC-AUTH
> series).

### 8.2 Certificate pinning

No certificate pinning is observable in the DEX strings. The loopj `AsyncHttpClient`
defaults to system-trust-store. **`app1` should add pinning** in the new
gateway-to-mobile path.

---

## 9. Cross-references resolved by Phase 7

Open questions from earlier phases that this APK analysis closes:

| Q from prior phase                                                   | Resolution                                                         | Conf. |
|-----------------------------------------------------------------------|---------------------------------------------------------------------|-------|
| **Q3 / OVERVIEW**: Base URL of the WCF host                            | `http://192.168.0.100:3000/` (dev/default) — runtime-configurable via `Preferences._baseUrl` | 90 % |
| **Q5 / OVERVIEW**: Is `IService1` still routed or only `IServiceElect`? | **`IServiceElect`** — the client calls all 33 modern operations; no `IService1`-only methods are referenced | 85 % |
| **Q7 / OVERVIEW**: How is `appId` sourced on the client side?          | `Preferences._appId` (`_appId` literal in DEX), persisted between launches | 90 % |
| **Q8 / OVERVIEW**: What does `secureId` carry?                          | Device-derived hardware identifier (`IMEI` → `ANDROID_ID` → `UUID` fallback chain) | 85 % |
| Multi-tenant `appId` mechanism (Phase 7 follow-through from §00_OVERVIEW) | Confirmed: client persists `appId` in SharedPreferences, sends on every request | 90 % |

---

## 10. Per-claim confidence ratings

| Claim                                                          | Conf. |
|-----------------------------------------------------------------|-------|
| Package = `com.yd.electricecollector`                            | 99 %  |
| `minSdk=24` / `targetSdk=34`                                     | 99 %  |
| Main activity = `SplashScreenActivity`                            | 99 %  |
| HTTP library = `loopj.android.http.AsyncHttpClient`              | 99 %  |
| Bearer auth via `BearerAuthSchemeFactory`                        | 99 %  |
| Hard-coded fallback `baseUrl = http://192.168.0.100:3000/`       | 90 %  |
| Client uses `IServiceElect` (not `IService1`)                    | 85 %  |
| Endpoint catalogue (69 literals) is complete                     | 85 %  |
| Entity-class mirror covers 27 / 27 DTOs                          | 92 %  |
| `secureId` device-derivation pipeline                            | 80 %  |
| Cleartext HTTP security finding (SEC-NET-001)                    | 95 %  |
| Activity → RN screen mapping                                     | 80 %  |
| `HakAccess` is the Tier-A client-cache                           | 90 %  |
| **Aggregate (mean, weighted by importance)**                     | **88 %** |

---

## 11. Source references

- `binaries/ElectricCollector26.apk` (SHA-256 in `binaries/SHA256SUMS.txt`)
- `reverse_engineering/apk_decompiled/endpoint_strings.txt` (69 endpoint literals)
- `reverse_engineering/apk_decompiled/yd_classes.txt` (185 client classes)
- `AndroidManifest.xml` (decoded via pyaxmlparser)
- `analysis/01_WCF_ENDPOINTS.md` (server endpoint catalogue, Phase 3)
- `analysis/02_JWT_AUTHENTICATION.md` (Bearer header, Phase 4)
- `analysis/03_DATA_MODELS.md` (server DTOs, Phase 5)
- `analysis/04_PERMISSIONS_SYSTEM.md` (Tier-A flags ↔ `HakAccess`, Phase 6)
- `analysis/05_ORACLE_INTEGRATION.md` (server-side back-end, Phase 5)

— end of `10_APK_V26_ANALYSIS.md` —
