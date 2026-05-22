# 08 — Error Handling

> **Status:** ⚪ pending — populated in Phase 3.

## Hypothesis

- The model `ServiceFault` (one of the 27 DTOs) is the **WCF FaultContract**
  envelope. Likely fields: `ErrorNumber`, `ErrorMessage`, `Details`.
- The `Users` model contains `error_no` — suggesting that some endpoints
  return a "success" object with an error number rather than a HTTP fault.
- Mixed style: business errors in body (`error_no != 0`), infra errors as
  HTTP 4xx/5xx + FaultContract.

## To verify in Phase 3

- [ ] For each endpoint: what does *failure* look like on the wire?
- [ ] List of `error_no` codes encountered in the decompile.
- [ ] Whether exceptions bubble out of `IService1` methods at all, or are
      caught and translated.

## Implications for the rewrite

Axios interceptor must handle **both**:

1. HTTP-level failures (status ≥ 400).
2. `result.error_no !== 0` business failures in 200-OK responses.
