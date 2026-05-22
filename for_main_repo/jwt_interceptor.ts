/**
 * jwt_interceptor.ts — Axios interceptor template for ElectricCollector28 (RN port).
 *
 * Drop this file into the same folder as `endpoints.ts` (e.g. `app1/src/api/`)
 * and call `installJwtInterceptors(axiosInstance, opts)` once at startup.
 *
 * What this implements (matches the server's wire contract — see
 * `analysis/02_JWT_AUTHENTICATION.md`):
 *
 *  - For every request whose `EndpointDescriptor.auth === true`, attach
 *    `Authorization: Bearer <token>` (note: prefix has a trailing space —
 *    the server's parse is `headerValue.Substring(7)`, so a missing space
 *    is rejected).
 *  - For the 7 public ops (Authenticate / Login / test / GetCallerIdentity
 *    / Index / legacy Login / legacy Authenticate — see
 *    `01_WCF_ENDPOINTS.md → Public endpoints rationale`), skip the header
 *    entirely.
 *  - On HTTP 401, clear the in-memory token and re-call `/Login` exactly
 *    once with the cached credentials, then retry the original request.
 *    Bail out on the second failure (no infinite loop).
 *  - The JWT is treated as **opaque**. We do not decode it client-side;
 *    the algorithm and the absence of an `exp` claim are both unresolved
 *    in the binary (jose-jwt enum constant, server-side TTL only — see
 *    Phase-4 doc §3.1 / §3.2 / §6.3).
 *
 * Why we don't use `axios.defaults.headers.common.Authorization`:
 *  the 7 public ops MUST NOT carry a Bearer header (the server's
 *  TokenValidationInspector still runs for them but treats the missing
 *  header as "anonymous"; sending a malformed or expired Bearer can
 *  trigger a 401 even on a public op).
 *
 * Compiles clean under TypeScript 5 `--strict`. No runtime deps beyond
 * `axios@^1`.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import type {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from 'axios';
import {
  ENDPOINTS,
  type EndpointDescriptor,
  type EndpointKey,
} from './endpoints';

// ---------------------------------------------------------------------------
// Public surface
// ---------------------------------------------------------------------------

/**
 * What the host app (the RN screen layer) must provide to wire the
 * interceptor. None of these are React-Native-specific so this file can
 * be unit-tested in plain Node.
 */
export interface JwtInterceptorOptions {
  /**
   * Returns the current bearer token, or `null` if the user is not yet
   * signed in. Synchronous reads keep the request hot-path simple; if
   * your storage is async (e.g. AsyncStorage), keep an in-memory mirror
   * and hydrate it at app start.
   */
  readonly getToken: () => string | null;

  /**
   * Persists a new token (e.g. after a successful `/Login`) and updates
   * the in-memory mirror. May be sync or async.
   */
  readonly setToken: (token: string | null) => void | Promise<void>;

  /**
   * Re-authenticates with cached credentials and returns the new token.
   * Throws on hard failure (bad credentials, network down, …). The
   * interceptor will call this at most once per request lifetime.
   */
  readonly reauth: () => Promise<string>;

  /**
   * Optional hook fired when the second 401 lands — the host app can
   * use this to kick the user out to the login screen.
   */
  readonly onUnrecoverable?: (originalUrl: string) => void;
}

/**
 * Public endpoint paths (canonical, without `baseUrl`).
 *
 * MIRRORED from `tools/generate_artifacts.py → PUBLIC_OPS` (Phase 3).
 * If you ever flip an endpoint's `auth` flag in the generated
 * `endpoints.ts`, the request interceptor below picks it up
 * automatically; this `Set` is only used by the legacy-shaped error
 * recovery in `handleResponseError` (which inspects the response URL,
 * not the endpoint descriptor).
 */
export const PUBLIC_PATHS: ReadonlySet<string> = new Set<string>([
  '/Authenticate',
  '/Login',
  '/test',
  '/GetCallerIdentity',
  '/',                  // Index (modern surface)
  '/Login.legacy',      // synthetic — see endpoints.ts for the legacy renaming
  '/Authenticate.legacy',
]);

/**
 * Wires both interceptors onto the given Axios instance and returns
 * an `uninstall` handle (useful for hot-reload in dev).
 */
export function installJwtInterceptors(
  client: AxiosInstance,
  opts: JwtInterceptorOptions,
): () => void {
  const reqId = client.interceptors.request.use(buildRequestInterceptor(opts));
  const resId = client.interceptors.response.use(
    (r) => r,
    buildResponseInterceptor(client, opts),
  );
  return () => {
    client.interceptors.request.eject(reqId);
    client.interceptors.response.eject(resId);
  };
}

// ---------------------------------------------------------------------------
// Request interceptor — attach `Authorization: Bearer <token>` when needed
// ---------------------------------------------------------------------------

/**
 * Augment a request config with a per-request `endpoint` hint so the
 * interceptor can decide whether to attach the bearer header without
 * doing path matching at the network layer. Callers should set this
 * via the `endpoint` field of `EndpointAwareRequest` below.
 */
export interface EndpointAwareRequest extends AxiosRequestConfig {
  /**
   * The `EndpointKey` from `ENDPOINTS` — REQUIRED for any call that
   * goes through this interceptor. We use this rather than path matching
   * because the modern and legacy surfaces share several URL prefixes.
   */
  readonly endpoint: EndpointKey;
}

function buildRequestInterceptor(
  opts: JwtInterceptorOptions,
): (cfg: InternalAxiosRequestConfig) => InternalAxiosRequestConfig {
  return (cfg) => {
    const key = (cfg as InternalAxiosRequestConfig & { endpoint?: EndpointKey })
      .endpoint;

    if (!key) {
      // Defensive: a call slipped through without using our typed wrapper.
      // We don't throw — the request may legitimately bypass the helper
      // (health check, ad-hoc debug fetch) — but we also don't attach a
      // header we cannot prove is needed.
      return cfg;
    }

    const desc: EndpointDescriptor = ENDPOINTS[key];

    // Some endpoints carry the token in the URI itself (the legacy
    // surface's `/Op/{appId}/{token}/{secureId}` shape). Those still
    // have `auth: true` so we still attach the Authorization header —
    // the server checks both. See Phase-3 doc §4.2.
    if (!desc.auth) {
      return cfg; // public op — never attach
    }

    const token = opts.getToken();
    if (!token) {
      // Don't throw — let the call proceed and let the 401 path handle
      // re-auth. Throwing here would mask whatever the caller's own
      // error semantics are.
      return cfg;
    }

    cfg.headers = cfg.headers ?? {};
    // CRITICAL: the prefix has a trailing space — the server's parse
    // is `headerValue.Substring(7)` which only works if the format
    // is exactly `"Bearer "<token>` (see Phase-4 doc §3.3).
    (cfg.headers as Record<string, string>).Authorization = `Bearer ${token}`;
    return cfg;
  };
}

// ---------------------------------------------------------------------------
// Response interceptor — handle 401 with one retry
// ---------------------------------------------------------------------------

interface RetryableConfig extends InternalAxiosRequestConfig {
  /** Set to `true` on the retry pass so we never loop forever. */
  _retried?: boolean;
  endpoint?: EndpointKey;
}

function buildResponseInterceptor(
  client: AxiosInstance,
  opts: JwtInterceptorOptions,
) {
  return async (error: unknown): Promise<AxiosResponse> => {
    // Be defensive about the error shape — Axios v1 surfaces `error.response`.
    const err = error as {
      response?: { status?: number; config?: RetryableConfig };
      config?: RetryableConfig;
      message?: string;
    };

    const status = err.response?.status;
    const cfg = (err.response?.config ?? err.config) as
      | RetryableConfig
      | undefined;

    if (status !== 401 || !cfg) {
      throw error; // anything other than 401 is a host-app concern
    }
    if (cfg._retried) {
      opts.onUnrecoverable?.(cfg.url ?? '');
      throw error; // we already tried once — give up
    }
    if (cfg.endpoint && ENDPOINTS[cfg.endpoint].auth === false) {
      // A 401 on a public op means the server failed for some other
      // reason (a deployed bug, perhaps). Don't try to re-auth.
      throw error;
    }

    cfg._retried = true;
    try {
      const fresh = await opts.reauth();
      await opts.setToken(fresh);
      cfg.headers = cfg.headers ?? {};
      (cfg.headers as Record<string, string>).Authorization = `Bearer ${fresh}`;
      return await client.request(cfg);
    } catch (reauthFail) {
      await opts.setToken(null);
      opts.onUnrecoverable?.(cfg.url ?? '');
      throw reauthFail;
    }
  };
}

// ---------------------------------------------------------------------------
// Convenience wrapper — type-safe `client.request({ endpoint: '...', ... })`
// ---------------------------------------------------------------------------

/**
 * Wraps `axios.request` with a typed `endpoint` field. Prefer this
 * over raw axios calls so the request interceptor can find the
 * `EndpointDescriptor` without resorting to path matching.
 *
 * @example
 *   const res = await call(api, {
 *     endpoint: 'getUserAccounts',
 *     method: 'POST',
 *     url: ENDPOINTS.getUserAccounts.path,
 *     data: { userId: 42 },
 *   });
 */
export function call<T = unknown>(
  client: AxiosInstance,
  cfg: EndpointAwareRequest,
): Promise<AxiosResponse<T>> {
  return client.request<T>(cfg as AxiosRequestConfig);
}
