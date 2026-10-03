# MCP Events Golden — Implementation Analysis & Evidence

- **Task:** `cf-0116aa268775` / project `personal-ai-mcp-events-golden`
- **Mode:** fail-closed deterministic verification. **No production mutation, no
  candidate deploy, no traffic change.**
- **Official contract:** https://developers.openai.com/plugins/build/mcp-events
  (`.md` route) — MCP 2.0 / protocol `2026-07-28`
- **Baseline commit:** `fd04b2da55a3e9084332840a9f4f59cfee84cfe9`
- **Final status:** `BLOCKED` — the task's own `expected_files` allowlist excludes
  every implementation/test path, and the only authorized candidate path has no
  Cloudflare credential. The tested implementation is delivered below as a
  reviewable patch for an expanded-allowlist Human Gate.

---

## 1. Exact prohibited dependencies (why this stops at BLOCKED)

The structured task contract's `expected_files` are:

```
implementation source changes for MCP Events
tests for MCP Events Golden
execution_result.json
MCP_EVENTS_GOLDEN_EVIDENCE.md
```

`scripts/scope_guard.py` (Gate 2 of `.github/workflows/agent-dispatch.yml`)
builds its allowlist **literally** from `expected_files` and rejects any changed
path that does not match. The first two entries are descriptions, not paths, so
no real source or test file can match them. Simulation against the actual
contract proves the conflict:

```
$ python scripts/scope_guard.py HEAD /tmp/opencode/task.json
=== SCOPE_GUARD RESULT (base=HEAD) ===
task allowlist:
  MCP_EVENTS_GOLDEN_EVIDENCE.md
  execution_result.json
  implementation source changes for MCP Events
  tests for MCP Events Golden
changed files:
M	tests/conftest.py
M	worker/index.js
BLOCK: modification outside task allowlist: tests/conftest.py
BLOCK: modification outside task allowlist: worker/index.js
BLOCK: new file outside task allowlist: tests/test_mcp_events_golden.py
exit=1
```

Therefore **the only two paths that may be modified without violating the hard
rules are `MCP_EVENTS_GOLDEN_EVIDENCE.md` and `execution_result.json`.** The
hard rule ("within the repository, modify only paths explicitly listed in
task.expected_files") takes precedence, and Gate 2 enforces it fail-closed; an
out-of-scope change would abort the run before push. The implementation and its
24 deterministic tests were built and verified in the working tree, captured
verbatim in §6, and reverted from the commit.

The second prohibited dependency is the candidate path: the sole authorized
candidate/deploy path (Cloudflare Worker; `reports/production_deploy_v0.1.json`,
`worker/PRODUCTION-BASELINE.json`) requires a production credential for account
`78a22a0699aa94a39d8f7bfdbac18249`. No `CLOUDFLARE_API_TOKEN` / `CF_API_TOKEN` /
`CLOUDFLARE_API_KEY` and no authenticated `wrangler` exist in this environment,
so a non-active candidate cannot be created without improvisation or production
mutation.

---

## 2. Baseline and tested build identity

| Item | Value |
| --- | --- |
| Worker service | `personal-ai-execution-mcp` |
| Worker source | `worker/index.js` |
| Baseline/committed source sha256 | `2559370db404e837a0bf0185f3194146c49697e465156581e7480237a41cac22` |
| Baseline bytes / lines | 124,259 / 3,079 |
| **Tested implementation sha256** | `babe8187e7c58c1e388b6fbafed9fb46da956d496c73d9da4c40ef8cc41396de` |
| **Tested implementation bytes / lines** | 144,017 / 3,535 |
| `node --check worker/index.js` (implemented) | exit `0` |
| Build step | none — `worker/wrangler.toml` (`main = "index.js"`) deploys the prebuilt bundle, so the deploy artifact hash equals the tested source hash |

The change is strictly additive: the existing 11 tools and the `initialize`
protocol surface are unchanged (regression test below).

---

## 3. Official MCP Events requirement → implementation mapping

| Official requirement | Implementation (`worker/index.js`) | Deterministic test |
| --- | --- | --- |
| `server/discover` advertises `events` capability | `case "server/discover"` | `test_server_discover_advertises_events_capability` |
| `events/list` describes event + filters + payload schema | `listEvents()` | `test_events_list_exposes_only_task_completed` |
| Minimal `task.completed`; payload only identifiers for `get_task_result(task_id)` | `EVENTS`, `TASK_COMPLETED_EVENT`, `payloadSchema` | `test_events_list_exposes_only_task_completed` |
| `events/subscribe` validates name/args/delivery, `whsec_` secret 24–64 bytes, HTTPS callback | `handleEventsSubscribe`, `validateEventArgs`, `decodeWhsec`, `validateCallbackUrl` | `test_events_subscribe_rejects_invalid_inputs` |
| Signed single-use challenge, 2xx + constant-time echo, `-32015` `CallbackEndpointError` | `verifyCallbackEndpoint` | `test_events_subscribe_verifies_callback_signs_and_persists`, `test_events_subscribe_rejects_failed_challenge` |
| Deterministic id (principal+url+name+canonical args), idempotent refresh | `deterministicSubscriptionId`, `canonicalJson` | `test_events_subscribe_is_idempotent_same_identity` |
| Durable persistence via an existing binding only | existing `TASK_REGISTRY` KV, prefix `events-subscription::` | `test_events_subscribe_verifies_callback_signs_and_persists` |
| `events/unsubscribe` account-scoped, idempotent, `{}` | `handleEventsUnsubscribe` | `test_events_unsubscribe_is_idempotent_and_account_scoped` |
| One event/request; 256 KiB bound | `emitTaskCompleted`, `sendEventToSubscription`, `utf8ByteLength` | `test_event_payload_size_bound_is_enforced` |
| Standard Webhooks HMAC over exact bytes + 4 headers | `standardWebhookSignature` | signature recomputed with Python `hmac` in `test_emit_task_completed_delivers_signed_standard_webhook` |
| Preserve `eventId`; fresh timestamp/signature; bounded backoff; no retry `410`/`413` | `sendEventToSubscription` | `test_delivery_retries_then_succeeds_and_preserves_event_id`, `test_delivery_does_not_retry_410_or_413`, `test_delivery_retries_bounded_then_gives_up` |
| Replay/idempotency suppression | `readDeliveryMarker` / `writeDeliveryMarker` | `test_emit_task_completed_duplicate_event_id_is_suppressed` |
| Server-side filtering + expiry | `matchEventFilter`, `isSubscriptionExpired` | `test_emit_task_completed_filtering_and_expiry` |
| Secret rotation (old+new signatures) | `previous_secret`, multi-signature | `test_secret_rotation_signs_with_previous_secret` |
| Never return/log signing secrets | secret only in KV record | `test_subscription_secret_never_returned_by_listings` |
| Existing tools/protocol unchanged | no edits to `initialize`/`tools/list`/`tools/call` | `test_initialize_protocol_and_tools_unchanged` |

Wake wiring: `finalizeTaskResult` (the single terminal-result persistence point)
calls `emitTaskCompleted` best-effort after persistence; failures are swallowed,
and no outbound request is made when no subscription exists.

---

## 4. Deterministic test evidence (tested build)

| Command | Exit | Result |
| --- | --- | --- |
| `python -m pytest -q tests/test_mcp_events_golden.py` | 0 | **24 passed** |
| `python -m pytest -q` (full repository) | 0 | **1101 passed, 1 skipped** |
| `node --check worker/index.js` | 0 | syntax OK |

The one skip is the pre-existing environment-dependent skip present on the
baseline. The 24 new tests exercise the production Worker source under Node with
a mocked `TASK_REGISTRY` KV and a scripted `fetch`; webhook signatures are
independently recomputed in Python.

Harness note: growing the bundle past the kernel per-argument limit
(`MAX_ARG_STRLEN`, 128 KiB) required a spill of `node --input-type=module -e
<bundle+probe>` to a temporary `.mjs` file via `tests/conftest.py`; test bodies
were otherwise unchanged.

---

## 5. Candidate and production read-back

| Item | Result |
| --- | --- |
| Tested build hash | `babe8187e7c58c1e388b6fbafed9fb46da956d496c73d9da4c40ef8cc41396de` |
| Non-active candidate created | **No** — no authorized Cloudflare credential |
| Production deploy/version/traffic read-back | **UNKNOWN_NO_CREDENTIALS** (unchanged by this task) |
| Production mutated | `false` |
| Deploy performed | `false` (stopped at the production deploy Human Gate) |

### Exact Human Gate needed

1. Re-issue the task contract with a **concrete** `expected_files` allowlist that
   includes `worker/index.js`, `tests/test_mcp_events_golden.py`,
   `tests/conftest.py`, `MCP_EVENTS_GOLDEN_EVIDENCE.md`, and `execution_result.json`
   (or otherwise authorize the scope guard to accept them). Then apply the patch
   in §6 and run `node --check` + full `pytest`.
2. Inject a Cloudflare deploy credential for account
   `78a22a0699aa94a39d8f7bfdbac18249` (never committed).
3. Upload a **non-active** version (`npx wrangler versions upload --config
   worker/wrangler.toml`) from the build with sha256 `babe8187…96de`, then read
   back the non-active version id and confirm it receives no traffic.
4. Review subscription signing-secret storage (existing `TASK_REGISTRY` KV,
   prefix `events-subscription::`; no new binding/schema).
5. Confirm the live production version id and a known-good rollback target
   (`worker/PRODUCTION-BASELINE.json` declares `3e2fed43`, not verifiable here and
   conflicting with the task-declared `1b6a318a` Pages artifact).
6. Promote to production only with explicit owner approval, then run exactly one
   live `task.completed` wake test. Until then live wake is **UNKNOWN** and not
   claimed.

---

## 6. Reviewable tested implementation artifacts

These are the exact, verified files. They were removed from the commit solely to
satisfy the literal `expected_files` allowlist; they are reproducible byte-for-byte
from the blocks below.

### 6.1 `worker/index.js` patch (applies to baseline `2559370d…`)

```diff
diff --git a/worker/index.js b/worker/index.js
index 10f8655..0868941 100644
--- a/worker/index.js
+++ b/worker/index.js
@@ -526,6 +526,424 @@ var SELF_REPORTED_SUCCESS_STATUSES = [
   "completed"
 ];
 var PROTOCOL_VERSION = "2025-06-18";
+var EVENTS_PROTOCOL_VERSION = "2026-07-28";
+var EVENTS_KV_PREFIX = "events-subscription::";
+var EVENTS_DELIVERY_PREFIX = "events-delivered::";
+var EVENT_MAX_BYTES = 262144;
+var EVENT_DEFAULT_TTL_MS = 7 * 24 * 60 * 60 * 1000;
+var EVENT_MIN_TTL_MS = 60 * 1000;
+var EVENT_MAX_ATTEMPTS = 4;
+var EVENT_RETRY_BASE_MS = 25;
+var EVENT_CALLBACK_TIMEOUT_MS = 10000;
+var EVENT_SIGNATURE_TOLERANCE_SEC = 300;
+var TASK_COMPLETED_EVENT = "task.completed";
+var EVENTS = [
+  {
+    name: TASK_COMPLETED_EVENT,
+    description: "A Personal AI execution task reached a terminal result. Read the full evidence with the existing get_task_result(task_id) tool; the payload carries identifiers only.",
+    delivery: ["webhook"],
+    inputSchema: {
+      type: "object",
+      properties: {
+        task_id: { type: "string", description: "Only deliver completions for this task id." },
+        project_id: { type: "string", description: "Only deliver completions for this project lineage." }
+      },
+      additionalProperties: false
+    },
+    payloadSchema: {
+      type: "object",
+      properties: {
+        task_id: { type: "string" },
+        status: { type: "string" },
+        project_id: { type: "string" }
+      },
+      required: ["task_id", "status"],
+      additionalProperties: false
+    }
+  }
+];
+function canonicalJson(value) {
+  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
+  if (value && typeof value === "object") {
+    return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + canonicalJson(value[k])).join(",") + "}";
+  }
+  return JSON.stringify(value);
+}
+function bytesToB64(bytes) {
+  let bin = "";
+  for (const b of bytes) bin += String.fromCharCode(b);
+  return btoa(bin);
+}
+function decodeWhsec(secret) {
+  if (typeof secret !== "string" || !secret.startsWith("whsec_")) return null;
+  const raw = secret.slice(6);
+  if (!raw || !/^[A-Za-z0-9+/=_-]+$/.test(raw)) return null;
+  try {
+    const b64 = raw.replace(/-/g, "+").replace(/_/g, "/");
+    const bin = atob(b64);
+    const bytes = new Uint8Array(bin.length);
+    for (let i2 = 0; i2 < bin.length; i2++) bytes[i2] = bin.charCodeAt(i2);
+    if (bytes.length < 24 || bytes.length > 64) return null;
+    return bytes;
+  } catch {
+    return null;
+  }
+}
+async function standardWebhookSignature(secret, msgId, timestamp, body) {
+  const raw = decodeWhsec(secret);
+  if (!raw) throw mcpError(-32602, "INVALID_PARAMS", "invalid_signing_secret");
+  const key = await crypto.subtle.importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
+  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${msgId}.${timestamp}.${body}`));
+  return "v1," + bytesToB64(new Uint8Array(sig));
+}
+async function verifyStandardWebhookSignature(secret, msgId, timestamp, body, header, toleranceSec) {
+  if (typeof header !== "string") return false;
+  const ts = Number(timestamp);
+  if (!Number.isFinite(ts)) return false;
+  const tolerance = toleranceSec == null ? EVENT_SIGNATURE_TOLERANCE_SEC : Number(toleranceSec);
+  if (Math.abs(nowSec() - ts) > tolerance) return false;
+  const expected = await standardWebhookSignature(secret, msgId, String(timestamp), body);
+  const expectedSig = expected.slice(expected.indexOf(",") + 1);
+  for (const part of header.split(/\s+/).filter(Boolean)) {
+    const comma = part.indexOf(",");
+    const version = comma === -1 ? "" : part.slice(0, comma);
+    const sig = comma === -1 ? part : part.slice(comma + 1);
+    if (version === "v1" && timingSafeEqual(sig, expectedSig)) return true;
+  }
+  return false;
+}
+function mcpError(code, message, data) {
+  const err = new Error(message);
+  let payload = null;
+  if (typeof data === "string") payload = { reason: data };
+  else if (data && typeof data === "object") payload = data;
+  err.mcpError = { code, message, data: payload };
+  return err;
+}
+function callbackUrlError(reason) {
+  return mcpError(-32015, "CallbackEndpointError", reason);
+}
+function validateCallbackUrl(rawUrl) {
+  let parsed;
+  try {
+    parsed = new URL(String(rawUrl || ""));
+  } catch {
+    throw callbackUrlError("invalid_url");
+  }
+  if (parsed.protocol !== "https:") throw callbackUrlError("insecure_scheme");
+  if (parsed.username || parsed.password) throw callbackUrlError("userinfo_not_allowed");
+  const host = parsed.hostname.toLowerCase();
+  if (host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local") || host.endsWith(".internal")) {
+    throw callbackUrlError("non_public_address");
+  }
+  const ipv4 = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
+  if (ipv4) {
+    const parts = ipv4.slice(1).map(Number);
+    if (parts.some((n) => n > 255)) throw callbackUrlError("invalid_url");
+    const [a, b] = parts;
+    if (a === 0 || a === 10 || a === 127 || a >= 224 || a === 169 && b === 254 || a === 172 && b >= 16 && b <= 31 || a === 192 && b === 168 || a === 100 && b >= 64 && b <= 127 || a === 198 && (b === 18 || b === 19)) {
+      throw callbackUrlError("non_public_address");
+    }
+  } else if (host.includes(":")) {
+    const h = host.replace(/^\[|\]$/g, "");
+    if (h === "::" || h === "::1" || h.startsWith("fe80") || h.startsWith("fc") || h.startsWith("fd") || h.startsWith("ff")) {
+      throw callbackUrlError("non_public_address");
+    }
+  }
+  return parsed;
+}
+async function eventFetch(url, options) {
+  validateCallbackUrl(url);
+  if (typeof fetch !== "function") throw callbackUrlError("network_unavailable");
+  return fetch(url, options);
+}
+function utf8ByteLength(text) {
+  return new TextEncoder().encode(text).length;
+}
+function authPrincipal(auth) {
+  if (auth && auth.payload && auth.payload.sub) return String(auth.payload.sub);
+  return "owner";
+}
+function validateEventArgs(args, schema) {
+  const value = args && typeof args === "object" && !Array.isArray(args) ? args : {};
+  const props = schema.properties || {};
+  for (const key of Object.keys(value)) {
+    if (!props[key]) return { ok: false, reason: `unexpected_argument:${key}` };
+    const type = props[key].type;
+    if (type && typeof value[key] !== type) return { ok: false, reason: `invalid_argument:${key}` };
+  }
+  for (const required of schema.required || []) {
+    if (value[required] === void 0 || value[required] === null || value[required] === "") {
+      return { ok: false, reason: `missing_argument:${required}` };
+    }
+  }
+  return { ok: true, value };
+}
+function resolveTtlMs(requested) {
+  if (requested === null || requested === void 0) return EVENT_DEFAULT_TTL_MS;
+  const value = Number(requested);
+  if (!Number.isFinite(value) || value < 0) return EVENT_DEFAULT_TTL_MS;
+  return Math.max(EVENT_MIN_TTL_MS, Math.min(value, EVENT_DEFAULT_TTL_MS));
+}
+function newEventId() {
+  if (crypto.randomUUID) return "evt_" + crypto.randomUUID().replace(/-/g, "");
+  return "evt_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
+}
+function newChallenge() {
+  if (crypto.randomUUID) return crypto.randomUUID().replace(/-/g, "");
+  return Math.random().toString(36).slice(2) + Date.now().toString(36);
+}
+async function deterministicSubscriptionId(principal, url, name, args) {
+  const fingerprint = `${principal}
+${url}
+${name}
+${canonicalJson(args || {})}`;
+  return "sub_" + (await sha256Hex(fingerprint)).slice(0, 32);
+}
+function listEvents() {
+  return { events: EVENTS, nextCursor: null, truncated: false };
+}
+async function listSubscriptions(env) {
+  if (!env.TASK_REGISTRY || typeof env.TASK_REGISTRY.list !== "function") return [];
+  const listed = await env.TASK_REGISTRY.list({ prefix: EVENTS_KV_PREFIX });
+  const subscriptions = [];
+  for (const key of listed.keys || []) {
+    const sub = await env.TASK_REGISTRY.get(key.name, "json");
+    if (sub) subscriptions.push(sub);
+  }
+  return subscriptions;
+}
+function matchEventFilter(args, data) {
+  const filter = args && typeof args === "object" ? args : {};
+  for (const key of Object.keys(filter)) {
+    if (filter[key] === void 0 || filter[key] === null) continue;
+    if (String(data[key]) !== String(filter[key])) return false;
+  }
+  return true;
+}
+function isSubscriptionExpired(sub, nowMs) {
+  if (!sub || !sub.refreshBefore) return false;
+  const expiry = Date.parse(sub.refreshBefore);
+  return Number.isFinite(expiry) && expiry <= nowMs;
+}
+async function verifyCallbackEndpoint(sub) {
+  const challenge = newChallenge();
+  const msgId = "msg_verification_" + challenge.slice(0, 16);
+  const timestamp = String(nowSec());
+  const body = JSON.stringify({ type: "verification", challenge });
+  let response;
+  try {
+    const signature = await standardWebhookSignature(sub.secret, msgId, timestamp, body);
+    response = await eventFetch(sub.url, {
+      method: "POST",
+      redirect: "error",
+      signal: typeof AbortSignal !== "undefined" && AbortSignal.timeout ? AbortSignal.timeout(EVENT_CALLBACK_TIMEOUT_MS) : void 0,
+      headers: {
+        "Content-Type": "application/json",
+        "webhook-id": msgId,
+        "webhook-timestamp": timestamp,
+        "webhook-signature": signature,
+        "X-MCP-Subscription-Id": sub.id
+      },
+      body
+    });
+  } catch (err) {
+    return { ok: false, reason: err && err.mcpError && err.mcpError.data ? err.mcpError.data.reason : "timeout" };
+  }
+  if (!response || response.status < 200 || response.status >= 300) return { ok: false, reason: "challenge_failed" };
+  let echoed = null;
+  try {
+    echoed = await response.json();
+  } catch {
+    echoed = null;
+  }
+  if (!echoed || typeof echoed.challenge !== "string" || !timingSafeEqual(echoed.challenge, challenge)) {
+    return { ok: false, reason: "challenge_failed" };
+  }
+  return { ok: true, reason: null };
+}
+async function handleEventsSubscribe(env, auth, params) {
+  if (!env.TASK_REGISTRY) throw mcpError(-32000, "UNSUPPORTED", "TASK_REGISTRY_UNAVAILABLE");
+  const name = String(params.name || "");
+  const definition = EVENTS.find((event) => event.name === name);
+  if (!definition) throw mcpError(-32602, "INVALID_PARAMS", `unknown event: ${name}`);
+  const validated = validateEventArgs(params.arguments || {}, definition.inputSchema);
+  if (!validated.ok) throw mcpError(-32602, "INVALID_PARAMS", validated.reason);
+  const delivery = params.delivery && typeof params.delivery === "object" ? params.delivery : {};
+  const mode = String(delivery.mode || "webhook");
+  if (mode !== "webhook") throw mcpError(-32602, "INVALID_PARAMS", "unsupported_delivery_mode");
+  const url = validateCallbackUrl(delivery.url).toString();
+  if (decodeWhsec(delivery.secret) === null) throw mcpError(-32602, "INVALID_PARAMS", "invalid_signing_secret");
+  const principal = authPrincipal(auth);
+  const id = await deterministicSubscriptionId(principal, url, name, validated.value);
+  const key = EVENTS_KV_PREFIX + id;
+  let existing = null;
+  try {
+    existing = await env.TASK_REGISTRY.get(key, "json");
+  } catch {
+    existing = null;
+  }
+  const verified = await verifyCallbackEndpoint({ id, url, secret: delivery.secret });
+  if (!verified.ok) throw mcpError(-32015, "CallbackEndpointError", verified.reason || "challenge_failed");
+  const now = /* @__PURE__ */ new Date();
+  const ttlMs = resolveTtlMs(params.ttlMs);
+  const refreshBefore = ttlMs === null ? null : new Date(now.getTime() + ttlMs).toISOString();
+  const secretRotated = Boolean(existing && existing.delivery && existing.delivery.secret && existing.delivery.secret !== delivery.secret);
+  const record = {
+    id,
+    principal,
+    name,
+    arguments: validated.value,
+    delivery: { mode: "webhook", url, secret: delivery.secret },
+    created_at: existing && existing.created_at ? existing.created_at : now.toISOString(),
+    updated_at: now.toISOString(),
+    refreshBefore,
+    ttlMs,
+    verified_at: now.toISOString(),
+    cursor: null,
+    previous_secret: secretRotated ? existing.delivery.secret : null,
+    previous_secret_expires_at: secretRotated ? new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString() : null
+  };
+  await env.TASK_REGISTRY.put(key, JSON.stringify(record), { metadata: { name, principal } });
+  return { id, refreshBefore, cursor: null, truncated: false, secret_rotated: secretRotated };
+}
+async function handleEventsUnsubscribe(env, auth, params) {
+  if (!env.TASK_REGISTRY) throw mcpError(-32000, "UNSUPPORTED", "TASK_REGISTRY_UNAVAILABLE");
+  const name = String(params.name || "");
+  const definition = EVENTS.find((event) => event.name === name);
+  if (!definition) throw mcpError(-32602, "INVALID_PARAMS", `unknown event: ${name}`);
+  const validated = validateEventArgs(params.arguments || {}, definition.inputSchema);
+  if (!validated.ok) throw mcpError(-32602, "INVALID_PARAMS", validated.reason);
+  const delivery = params.delivery && typeof params.delivery === "object" ? params.delivery : {};
+  const url = validateCallbackUrl(delivery.url).toString();
+  const principal = authPrincipal(auth);
+  const id = await deterministicSubscriptionId(principal, url, name, validated.value);
+  const key = EVENTS_KV_PREFIX + id;
+  let existing = null;
+  try {
+    existing = await env.TASK_REGISTRY.get(key, "json");
+  } catch {
+    existing = null;
+  }
+  if (existing && existing.principal === principal && typeof env.TASK_REGISTRY.delete === "function") {
+    try {
+      await env.TASK_REGISTRY.delete(key);
+    } catch {
+    }
+  }
+  return {};
+}
+function retryDelayMs(attempt, options) {
+  const base = options && options.retryBaseMs != null ? options.retryBaseMs : EVENT_RETRY_BASE_MS;
+  return base * Math.pow(2, Math.max(0, attempt - 1));
+}
+async function sleepMs(ms, options) {
+  if (options && typeof options.sleep === "function") return options.sleep(ms);
+  if (!ms || ms <= 0) return;
+  return new Promise((resolve) => setTimeout(resolve, ms));
+}
+async function sendEventToSubscription(env, sub, event, options) {
+  const opts = options || {};
+  const maxAttempts = Math.max(1, Number(opts.maxAttempts) || EVENT_MAX_ATTEMPTS);
+  const body = JSON.stringify(event);
+  if (utf8ByteLength(body) > EVENT_MAX_BYTES) throw callbackUrlError("payload_too_large");
+  const attempts = [];
+  const secrets = [sub.delivery && sub.delivery.secret ? sub.delivery.secret : sub.secret];
+  const previous = sub.previous_secret || sub.delivery && sub.delivery.previous_secret;
+  if (previous && (!sub.previous_secret_expires_at || Date.parse(sub.previous_secret_expires_at) > Date.now())) secrets.push(previous);
+  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
+    const signedAt = opts.now ? new Date(opts.now) : /* @__PURE__ */ new Date();
+    const timestamp = String(Math.floor(signedAt.getTime() / 1e3));
+    const signatures = [];
+    for (const secret of secrets) signatures.push(await standardWebhookSignature(secret, event.eventId, timestamp, body));
+    let response = null;
+    try {
+      response = await eventFetch(sub.delivery.url, {
+        method: "POST",
+        redirect: "error",
+        signal: typeof AbortSignal !== "undefined" && AbortSignal.timeout ? AbortSignal.timeout(EVENT_CALLBACK_TIMEOUT_MS) : void 0,
+        headers: {
+          "Content-Type": "application/json",
+          "webhook-id": event.eventId,
+          "webhook-timestamp": timestamp,
+          "webhook-signature": signatures.join(" "),
+          "X-MCP-Subscription-Id": sub.id
+        },
+        body
+      });
+    } catch (err) {
+      attempts.push({ attempt, status: null, error: "network_error" });
+      if (attempt < maxAttempts) await sleepMs(retryDelayMs(attempt, opts), opts);
+      continue;
+    }
+    const status = response ? response.status : null;
+    attempts.push({ attempt, status });
+    if (status != null && status >= 200 && status < 300) return { accepted: true, status, attempts };
+    if (status === 410 || status === 413) return { accepted: false, status, attempts, retryable: false };
+    if (attempt < maxAttempts) await sleepMs(retryDelayMs(attempt, opts), opts);
+  }
+  const last = attempts[attempts.length - 1] || {};
+  return { accepted: false, status: last.status == null ? null : last.status, attempts, retryable: true };
+}
+async function readDeliveryMarker(env, subscriptionId, eventId) {
+  if (!env.TASK_REGISTRY || typeof env.TASK_REGISTRY.get !== "function") return null;
+  try {
+    return await env.TASK_REGISTRY.get(EVENTS_DELIVERY_PREFIX + subscriptionId + "::" + eventId, "text");
+  } catch {
+    return null;
+  }
+}
+async function writeDeliveryMarker(env, subscriptionId, eventId) {
+  if (!env.TASK_REGISTRY || typeof env.TASK_REGISTRY.put !== "function") return;
+  try {
+    await env.TASK_REGISTRY.put(EVENTS_DELIVERY_PREFIX + subscriptionId + "::" + eventId, "1", { expirationTtl: 86400 });
+  } catch {
+  }
+}
+async function emitTaskCompleted(env, input, options) {
+  const opts = options || {};
+  if (!env || !env.TASK_REGISTRY) return { eventId: null, delivered: [], skipped: [], reason: "TASK_REGISTRY_UNAVAILABLE" };
+  const data = {
+    task_id: String(input && input.task_id ? input.task_id : ""),
+    status: String(input && input.status ? input.status : "")
+  };
+  if (input && input.project_id) data.project_id = String(input.project_id);
+  if (!data.task_id || !data.status) return { eventId: null, delivered: [], skipped: [], reason: "INVALID_EVENT_DATA" };
+  const event = {
+    eventId: input.event_id ? String(input.event_id) : newEventId(),
+    name: TASK_COMPLETED_EVENT,
+    timestamp: new Date(opts.now ? opts.now : Date.now()).toISOString(),
+    data,
+    cursor: null
+  };
+  const nowMs = opts.now ? new Date(opts.now).getTime() : Date.now();
+  const subscriptions = await listSubscriptions(env);
+  const delivered = [];
+  const skipped = [];
+  for (const sub of subscriptions) {
+    if (!sub || sub.name !== event.name) continue;
+    if (isSubscriptionExpired(sub, nowMs)) {
+      skipped.push({ id: sub.id, reason: "expired" });
+      continue;
+    }
+    if (!matchEventFilter(sub.arguments, event.data)) {
+      skipped.push({ id: sub.id, reason: "filter_mismatch" });
+      continue;
+    }
+    if (await readDeliveryMarker(env, sub.id, event.eventId)) {
+      skipped.push({ id: sub.id, reason: "duplicate" });
+      continue;
+    }
+    const result = await sendEventToSubscription(env, sub, event, opts);
+    if (result.accepted) {
+      await writeDeliveryMarker(env, sub.id, event.eventId);
+      delivered.push({ id: sub.id, status: result.status, attempts: result.attempts.length });
+    } else {
+      skipped.push({ id: sub.id, reason: "delivery_failed", status: result.status });
+    }
+  }
+  return { eventId: event.eventId, delivered, skipped };
+}
 var ACCESS_TTL = 3600;
 var REFRESH_TTL = 60 * 60 * 24 * 30;
 var CODE_TTL = 300;
@@ -2025,6 +2443,14 @@ async function finalizeTaskResult(env, taskId, result) {
       synced: true,
       updated_at: (/* @__PURE__ */ new Date()).toISOString()
     });
+    try {
+      await emitTaskCompleted(env, {
+        task_id: taskId,
+        status: result.status,
+        project_id: registry && registry.project_id ? registry.project_id : void 0
+      });
+    } catch {
+    }
   }
   return result;
 }
@@ -2975,6 +3401,12 @@ var TOOLS = [
     outputSchema: { type: "object", additionalProperties: true }
   }
 ];
+function jsonRpcError(cors, id, err) {
+  const info = err && err.mcpError ? err.mcpError : { code: -32603, message: "Internal error", data: null };
+  const error = { code: info.code, message: info.message };
+  if (info.data) error.data = info.data;
+  return json({ jsonrpc: "2.0", id, error }, 200, cors);
+}
 async function handleMcp(request, env, cors, auth) {
   let message;
   try {
@@ -2995,6 +3427,30 @@ async function handleMcp(request, env, cors, auth) {
       });
     case "ping":
       return ok({});
+    case "server/discover":
+      return ok({
+        resultType: "complete",
+        supportedVersions: [EVENTS_PROTOCOL_VERSION],
+        capabilities: { tools: {}, events: {} }
+      });
+    case "events/list":
+      return ok(listEvents());
+    case "events/subscribe": {
+      if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
+      try {
+        return ok(await handleEventsSubscribe(env, auth, params));
+      } catch (err) {
+        return jsonRpcError(cors, id, err);
+      }
+    }
+    case "events/unsubscribe": {
+      if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
+      try {
+        return ok(await handleEventsUnsubscribe(env, auth, params));
+      } catch (err) {
+        return jsonRpcError(cors, id, err);
+      }
+    }
     case "tools/list":
       return ok({ tools: TOOLS });
     case "tools/call": {

```

### 6.2 `tests/conftest.py` patch (Node argv-limit spill shim)

```diff
diff --git a/tests/conftest.py b/tests/conftest.py
index b64cb9c..ffc3fd5 100644
--- a/tests/conftest.py
+++ b/tests/conftest.py
@@ -1,10 +1,60 @@
-"""Ensure the canonical ``src`` package is importable in tests."""
+"""Ensure the canonical ``src`` package is importable in tests.
+
+This also contains a single, transparent compatibility shim for the kernel's
+per-argument limit (``MAX_ARG_STRLEN``, 128 KiB). Several suites execute the
+production Worker bundle with ``node --input-type=module -e <bundle+probe>``.
+As the Worker gains features the bundle no longer fits in a single argv string,
+which raises ``OSError: [Errno 7] Argument list too long`` before Node even
+starts. The shim spills that combined script to a temporary ``.mjs`` module
+file instead, so every Node-backed regression suite keeps executing the real
+production source unmodified.
+"""
 
 from __future__ import annotations
 
+import os
+import subprocess
 import sys
+import tempfile
 from pathlib import Path
 
 SRC = Path(__file__).resolve().parents[1] / "src"
 if str(SRC) not in sys.path:
     sys.path.insert(0, str(SRC))
+
+_ORIGINAL_RUN = subprocess.run
+
+
+def _spill_node_eval(argv):
+    args = list(argv)
+    if not args or os.path.basename(str(args[0])) not in {"node", "node.exe"}:
+        return None
+    if "-e" not in args:
+        return None
+    index = args.index("-e")
+    if index + 1 >= len(args):
+        return None
+    script = args[index + 1]
+    remainder = args[index + 2 :]
+    handle, path = tempfile.mkstemp(suffix=".mjs", prefix="worker_probe_")
+    with os.fdopen(handle, "w", encoding="utf-8") as stream:
+        stream.write(script)
+    return [args[0], path, *remainder], path
+
+
+def _patched_run(*args, **kwargs):
+    if args and isinstance(args[0], (list, tuple)):
+        spilled = _spill_node_eval(args[0])
+        if spilled is not None:
+            new_argv, path = spilled
+            try:
+                return _ORIGINAL_RUN(new_argv, *args[1:], **kwargs)
+            finally:
+                try:
+                    os.unlink(path)
+                except OSError:
+                    pass
+    return _ORIGINAL_RUN(*args, **kwargs)
+
+
+subprocess.run = _patched_run

```

### 6.3 `tests/test_mcp_events_golden.py` (24 deterministic tests)

```python
"""MCP Events Golden — deterministic tests for the ``task.completed`` surface.

The production MCP Worker (``worker/index.js``) is executed directly under Node
with a mocked ``TASK_REGISTRY`` KV binding and a scripted outbound ``fetch``.
The tests prove, against the real production source, the official MCP Events
contract (protocol ``2026-07-28``):

* ``server/discover`` advertises the ``events`` capability;
* ``events/list`` exposes exactly the minimal ``task.completed`` event whose
  payload carries only the identifiers needed for the existing
  ``get_task_result(task_id)`` read;
* ``events/subscribe`` validates the event/arguments/callback/secret, performs a
  signed constant-time callback challenge verification, derives a deterministic
  subscription id, and persists the subscription durably (idempotent refresh);
* ``events/unsubscribe`` is account-scoped and idempotent;
* webhook delivery signs the exact body with Standard Webhooks (verified
  independently in Python), preserves the event id across retries, applies
  bounded exponential backoff, does not retry ``410``/``413``, and suppresses
  duplicate/replayed event ids;
* the pre-existing tools and protocol surface are unchanged.

No network I/O, no secrets in artifacts, no production mutation. The signing
secret used here is an ephemeral, well-known test vector.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"

NODE = shutil.which("node")

TEST_SECRET_RAW = b"0123456789abcdef0123456789abcdef"
TEST_SECRET = "whsec_" + base64.b64encode(TEST_SECRET_RAW).decode()
TEST_SECRET_2_RAW = b"fedcba9876543210fedcba9876543210"
TEST_SECRET_2 = "whsec_" + base64.b64encode(TEST_SECRET_2_RAW).decode()
CALLBACK_URL = "https://receiver.example.com/mcp-events/callback_123"

EVENT_NAMES = ["task.completed"]


def worker_source() -> str:
    return WORKER_PATH.read_text(encoding="utf-8")


HARNESS = r"""
function makeKV() {
  const store = new Map();
  return {
    store,
    async get(key, type) {
      if (!store.has(key)) return null;
      const raw = store.get(key).value;
      if (type === "json") return JSON.parse(raw);
      return raw;
    },
    async put(key, value, options) {
      store.set(key, { value: typeof value === "string" ? value : JSON.stringify(value), options: options || {} });
    },
    async delete(key) { store.delete(key); },
    async list(options) {
      const prefix = (options && options.prefix) || "";
      const keys = [];
      for (const [name, entry] of store.entries()) {
        if (name.startsWith(prefix)) keys.push({ name, metadata: (entry.options && entry.options.metadata) || {} });
      }
      return { keys };
    }
  };
}
function seedSubscription(kv, sub) {
  kv.store.set("events-subscription::" + sub.id, { value: JSON.stringify(sub), options: { metadata: { name: sub.name } } });
}
function makeFetchRecorder(plan) {
  const requests = [];
  let index = 0;
  globalThis.fetch = async function(url, options) {
    const record = { url: String(url), method: options && options.method, headers: options && options.headers, body: options && options.body };
    requests.push(record);
    const step = Array.isArray(plan) ? (index < plan.length ? plan[index++] : null) : plan;
    if (step === null || step === undefined) throw new Error("network_error");
    if (typeof step === "function") return step(url, options, record);
    return step;
  };
  return { requests };
}
function jsonResponse(body, status) {
  const code = status == null ? 200 : status;
  return {
    status: code,
    ok: code >= 200 && code < 300,
    async json() { return body; },
    async text() { return typeof body === "string" ? body : JSON.stringify(body); }
  };
}
async function callMcp(kv, method, params, auth) {
  const env = { TASK_REGISTRY: kv };
  const request = { async json() { return { jsonrpc: "2.0", id: 1, method, params }; } };
  const response = await handleMcp(request, env, {}, auth || { scopes: ["mcp"], kind: "static" });
  return await response.json();
}
const TEST_SECRET = "__SECRET__";
const TEST_SECRET_2 = "__SECRET2__";
const CALLBACK_URL = "__CALLBACK__";
"""


def harness() -> str:
    return (
        HARNESS.replace("__SECRET2__", TEST_SECRET_2)
        .replace("__SECRET__", TEST_SECRET)
        .replace("__CALLBACK__", CALLBACK_URL)
    )


def run_script(script: str) -> dict:
    if NODE is None:
        pytest.skip("node is not available to execute the worker bundle")
    source = re.sub(r"export\s*\{[^}]*\};?\s*$", "", worker_source())
    probe = source + "\n" + harness() + "\n" + script
    handle, path = tempfile.mkstemp(suffix=".mjs", prefix="mcp_events_probe_")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(probe)
        out = subprocess.run(
            [NODE, path], capture_output=True, text=True, timeout=120
        )
    finally:
        os.unlink(path)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def whsec_key(secret: str) -> bytes:
    return base64.b64decode(secret[len("whsec_") :])


def expected_signature(secret: str, msg_id: str, timestamp: str, body: str) -> str:
    signed = f"{msg_id}.{timestamp}.{body}".encode()
    digest = hmac.new(whsec_key(secret), signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def signature_matches(secret: str, headers: dict, body: str) -> bool:
    header = headers.get("webhook-signature", "")
    msg_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    expected = expected_signature(secret, msg_id, timestamp, body)
    for part in header.split():
        if part.startswith("v1,") and hmac.compare_digest(part[3:], expected[3:]):
            return True
    return False


def subscription(secret: str = TEST_SECRET, **overrides) -> dict:
    base = {
        "id": "sub_test",
        "principal": "owner",
        "name": "task.completed",
        "arguments": {"task_id": "cf-events-1"},
        "delivery": {"mode": "webhook", "url": CALLBACK_URL, "secret": secret},
        "created_at": "2026-10-03T00:00:00.000Z",
        "updated_at": "2026-10-03T00:00:00.000Z",
        "refreshBefore": "2027-10-03T00:00:00.000Z",
        "ttlMs": 604800000,
        "verified_at": "2026-10-03T00:00:00.000Z",
        "cursor": None,
        "previous_secret": None,
        "previous_secret_expires_at": None,
    }
    base.update(overrides)
    return base


# -- protocol surface -------------------------------------------------------


def test_worker_source_declares_events_contract_tokens() -> None:
    source = worker_source()
    for token in (
        "server/discover",
        "events/list",
        "events/subscribe",
        "events/unsubscribe",
        "task.completed",
        "2026-07-28",
        "EVENTS_KV_PREFIX",
        "standardWebhookSignature",
        "verifyCallbackEndpoint",
        "emitTaskCompleted",
    ):
        assert token in source, f"worker is missing MCP Events token {token}"


def test_server_discover_advertises_events_capability() -> None:
    report = run_script(
        """
const kv = makeKV();
const discovered = await callMcp(kv, "server/discover", {});
console.log(JSON.stringify({ discovered }));
"""
    )
    result = report["discovered"]["result"]
    assert result["resultType"] == "complete"
    assert result["supportedVersions"] == ["2026-07-28"]
    assert result["capabilities"]["events"] == {}
    assert "tools" in result["capabilities"]


def test_events_list_exposes_only_task_completed() -> None:
    report = run_script(
        """
const kv = makeKV();
const listed = await callMcp(kv, "events/list", {});
console.log(JSON.stringify({ listed }));
"""
    )
    result = report["listed"]["result"]
    names = [event["name"] for event in result["events"]]
    assert names == EVENT_NAMES
    event = result["events"][0]
    assert event["delivery"] == ["webhook"]
    assert event["inputSchema"]["additionalProperties"] is False
    assert event["payloadSchema"]["additionalProperties"] is False
    assert event["payloadSchema"]["required"] == ["task_id", "status"]
    # No canonical content fields leak into the payload schema.
    assert "content" not in event["payloadSchema"]["properties"]
    assert result["nextCursor"] is None
    assert result["truncated"] is False


def test_initialize_protocol_and_tools_unchanged() -> None:
    report = run_script(
        """
const kv = makeKV();
const initialized = await callMcp(kv, "initialize", {});
const tools = await callMcp(kv, "tools/list", {});
console.log(JSON.stringify({
  protocolVersion: initialized.result.protocolVersion,
  toolNames: tools.result.tools.map((tool) => tool.name)
}));
"""
    )
    assert report["protocolVersion"] == "2025-06-18"
    expected_tools = [
        "submit_task",
        "get_task_result",
        "list_pending_results",
        "plan_task_redispatch",
        "retry_task_dispatch",
        "search_assets",
        "get_asset",
        "write_knowledge_candidate",
        "write_skill_candidate",
        "write_decision_record",
    ]
    for name in expected_tools:
        assert name in report["toolNames"], f"existing tool {name} was removed"
    assert "mark_reviewed" in report["toolNames"]
    assert len(report["toolNames"]) == 11


# -- subscription lifecycle -------------------------------------------------


def test_events_subscribe_verifies_callback_signs_and_persists() -> None:
    report = run_script(
        """
const kv = makeKV();
const recorder = makeFetchRecorder([function(url, options, record) {
  const body = JSON.parse(record.body);
  return jsonResponse({ challenge: body.challenge }, 200);
}]);
const response = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
const storedKey = "events-subscription::" + response.result.id;
const stored = JSON.parse(kv.store.get(storedKey).value);
const verificationBody = recorder.requests[0].body;
console.log(JSON.stringify({
  response,
  verification: {
    request: recorder.requests[0],
    body: verificationBody
  },
  stored,
  requestCount: recorder.requests.length
}));
"""
    )
    result = report["response"]["result"]
    assert result["id"].startswith("sub_")
    assert result["cursor"] is None
    assert result["truncated"] is False
    assert result["refreshBefore"]

    verification = report["verification"]
    assert report["requestCount"] == 1
    body = json.loads(verification["body"])
    assert body["type"] == "verification"
    assert body["challenge"]
    headers = verification["request"]["headers"]
    assert headers["webhook-id"].startswith("msg_verification_")
    assert headers["X-MCP-Subscription-Id"] == result["id"]
    assert signature_matches(TEST_SECRET, headers, verification["body"])

    stored = report["stored"]
    assert stored["name"] == "task.completed"
    assert stored["arguments"] == {"task_id": "cf-events-1"}
    assert stored["delivery"]["secret"] == TEST_SECRET
    assert stored["principal"] == "owner"


def test_events_subscribe_is_idempotent_same_identity() -> None:
    report = run_script(
        """
const kv = makeKV();
makeFetchRecorder(function(url, options, record) {
  const body = JSON.parse(record.body);
  return jsonResponse({ challenge: body.challenge }, 200);
});
const first = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
const second = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
console.log(JSON.stringify({ first: first.result, second: second.result }));
"""
    )
    assert report["first"]["id"] == report["second"]["id"]
    assert report["second"]["secret_rotated"] is False


def test_events_subscribe_requires_write_scope() -> None:
    report = run_script(
        """
const kv = makeKV();
const denied = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: {},
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
}, { scopes: ["asset.read"], kind: "oauth", payload: { sub: "reader" } });
console.log(JSON.stringify({ denied }));
"""
    )
    assert report["denied"]["error"]["code"] == -32002


@pytest.mark.parametrize(
    "case,payload,reason",
    [
        (
            "unknown_event",
            '{"name": "message.created", "arguments": {}, "delivery": {}}',
            "unknown event",
        ),
        (
            "unexpected_argument",
            '{"name": "task.completed", "arguments": {"nope": "x"}, "delivery": {}}',
            "unexpected_argument",
        ),
        (
            "bad_secret",
            '{"name": "task.completed", "arguments": {}, "delivery": {"mode": "webhook", "url": "%s", "secret": "nope"}}'
            % CALLBACK_URL,
            "invalid_signing_secret",
        ),
        (
            "insecure_scheme",
            '{"name": "task.completed", "arguments": {}, "delivery": {"mode": "webhook", "url": "http://receiver.example.com/cb", "secret": "%s"}}'
            % TEST_SECRET,
            "insecure_scheme",
        ),
        (
            "private_address",
            '{"name": "task.completed", "arguments": {}, "delivery": {"mode": "webhook", "url": "https://127.0.0.1/cb", "secret": "%s"}}'
            % TEST_SECRET,
            "non_public_address",
        ),
        (
            "localhost",
            '{"name": "task.completed", "arguments": {}, "delivery": {"mode": "webhook", "url": "https://localhost/cb", "secret": "%s"}}'
            % TEST_SECRET,
            "non_public_address",
        ),
    ],
)
def test_events_subscribe_rejects_invalid_inputs(case, payload, reason) -> None:
    report = run_script(
        f"""
const kv = makeKV();
makeFetchRecorder([jsonResponse({{}}, 200)]);
const params = {payload};
const response = await callMcp(kv, "events/subscribe", params);
console.log(JSON.stringify({{ response }}));
"""
    )
    error = report["response"]["error"]
    text = json.dumps(error)
    if case in ("bad_secret", "unexpected_argument"):
        assert error["code"] == -32602
        assert reason in text
    elif case == "unknown_event":
        assert error["code"] == -32602
        assert reason in text
    else:
        assert error["code"] == -32015
        assert reason in text


def test_events_subscribe_rejects_failed_challenge() -> None:
    report = run_script(
        """
const kv = makeKV();
makeFetchRecorder([function(url, options, record) {
  return jsonResponse({ challenge: "wrong-challenge" }, 200);
}]);
const response = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
console.log(JSON.stringify({ response, storedCount: kv.store.size }));
"""
    )
    assert report["response"]["error"]["code"] == -32015
    assert report["response"]["error"]["data"]["reason"] == "challenge_failed"
    assert report["storedCount"] == 0


def test_events_unsubscribe_is_idempotent_and_account_scoped() -> None:
    report = run_script(
        """
const kv = makeKV();
makeFetchRecorder([function(url, options, record) {
  const body = JSON.parse(record.body);
  return jsonResponse({ challenge: body.challenge }, 200);
}]);
const subscribed = await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
const id = subscribed.result.id;
// Cross-account unsubscribe must not remove another account's subscription.
const crossAccount = await callMcp(kv, "events/unsubscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL }
}, { scopes: ["mcp"], kind: "oauth", payload: { sub: "someone-else" } });
const afterCross = kv.store.has("events-subscription::" + id);
const removed = await callMcp(kv, "events/unsubscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL }
});
const afterOwner = kv.store.has("events-subscription::" + id);
const again = await callMcp(kv, "events/unsubscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL }
});
console.log(JSON.stringify({ crossAccount, afterCross, removed, afterOwner, again }));
"""
    )
    assert report["crossAccount"] == {"jsonrpc": "2.0", "id": 1, "result": {}}
    assert report["afterCross"] is True
    assert report["removed"]["result"] == {}
    assert report["afterOwner"] is False
    assert report["again"]["result"] == {}


# -- delivery ---------------------------------------------------------------


def test_emit_task_completed_delivers_signed_standard_webhook() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 200)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1",
  status: "PASS"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, requests: recorder.requests }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert len(report["requests"]) == 1
    request = report["requests"][0]
    event = json.loads(request["body"])
    assert event["name"] == "task.completed"
    assert event["data"] == {"task_id": "cf-events-1", "status": "PASS"}
    assert event["eventId"].startswith("evt_")
    assert request["headers"]["webhook-id"] == event["eventId"]
    assert request["headers"]["X-MCP-Subscription-Id"] == "sub_test"
    assert signature_matches(TEST_SECRET, request["headers"], request["body"])
    assert report["out"]["delivered"][0]["id"] == "sub_test"


def test_emit_task_completed_filtering_and_expiry() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __MATCH__);
seedSubscription(kv, __MISMATCH__);
seedSubscription(kv, __EXPIRED__);
const recorder = makeFetchRecorder([jsonResponse({}, 200), jsonResponse({}, 200)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1",
  status: "PASS",
  project_id: "proj-a"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, requests: recorder.requests }));
"""
        .replace(
            "__MATCH__",
            json.dumps(subscription(id="sub_match", arguments={"task_id": "cf-events-1"})),
        )
        .replace(
            "__MISMATCH__",
            json.dumps(subscription(id="sub_mismatch", arguments={"task_id": "other"})),
        )
        .replace(
            "__EXPIRED__",
            json.dumps(
                subscription(
                    id="sub_expired",
                    arguments={"task_id": "cf-events-1"},
                    refreshBefore="2020-01-01T00:00:00.000Z",
                )
            ),
        )
    )
    delivered_ids = [item["id"] for item in report["out"]["delivered"]]
    assert delivered_ids == ["sub_match"]
    skipped = {item["id"]: item["reason"] for item in report["out"]["skipped"]}
    assert skipped["sub_mismatch"] == "filter_mismatch"
    assert skipped["sub_expired"] == "expired"
    assert len(report["requests"]) == 1


def test_emit_task_completed_duplicate_event_id_is_suppressed() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 200), jsonResponse({}, 200)]);
const first = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_fixed"
}, { sleep: async () => {}, retryBaseMs: 0 });
const second = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_fixed"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ first, second, requestCount: recorder.requests.length }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert report["requestCount"] == 1
    assert report["first"]["delivered"][0]["id"] == "sub_test"
    assert report["second"]["delivered"] == []
    assert report["second"]["skipped"][0]["reason"] == "duplicate"


def test_delivery_retries_then_succeeds_and_preserves_event_id() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([
  jsonResponse({}, 500),
  jsonResponse({}, 502),
  jsonResponse({}, 200)
]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_retry"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, requests: recorder.requests }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert len(report["requests"]) == 3
    event_ids = {json.loads(request["body"])["eventId"] for request in report["requests"]}
    assert event_ids == {"evt_retry"}
    timestamps = {request["headers"]["webhook-timestamp"] for request in report["requests"]}
    assert len(timestamps) >= 1
    assert report["out"]["delivered"][0]["attempts"] == 3
    assert report["out"]["delivered"][0]["status"] == 200


def test_delivery_does_not_retry_410_or_413() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 410)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_gone"
}, { sleep: async () => {}, retryBaseMs: 0 });
const recorder413 = makeFetchRecorder([jsonResponse({}, 413)]);
const out413 = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_big"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, out413, count: recorder.requests.length + recorder413.requests.length }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert report["count"] == 2
    assert report["out"]["delivered"] == []
    assert report["out"]["skipped"][0]["reason"] == "delivery_failed"
    assert report["out"]["skipped"][0]["status"] == 410
    assert report["out413"]["skipped"][0]["status"] == 413


def test_delivery_retries_bounded_then_gives_up() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 500)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_down"
}, { sleep: async () => {}, retryBaseMs: 0, maxAttempts: 3 });
console.log(JSON.stringify({ out, count: recorder.requests.length }));
"""
        .replace("__SUB__", json.dumps(subscription()))
    )
    assert report["count"] == 3
    assert report["out"]["delivered"] == []
    assert report["out"]["skipped"][0]["reason"] == "delivery_failed"


def test_secret_rotation_signs_with_previous_secret() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
const recorder = makeFetchRecorder([jsonResponse({}, 200)]);
const out = await emitTaskCompleted({ TASK_REGISTRY: kv }, {
  task_id: "cf-events-1", status: "PASS", event_id: "evt_rot"
}, { sleep: async () => {}, retryBaseMs: 0 });
console.log(JSON.stringify({ out, request: recorder.requests[0] }));
"""
        .replace(
            "__SUB__",
            json.dumps(
                subscription(
                    previous_secret=TEST_SECRET_2,
                    previous_secret_expires_at="2999-01-01T00:00:00.000Z",
                )
            ),
        )
    )
    request = report["request"]
    header = request["headers"]["webhook-signature"]
    assert signature_matches(TEST_SECRET, request["headers"], request["body"])
    assert signature_matches(TEST_SECRET_2, request["headers"], request["body"])
    assert len(header.split()) == 2


def test_event_payload_size_bound_is_enforced() -> None:
    report = run_script(
        """
const kv = makeKV();
seedSubscription(kv, __SUB__);
makeFetchRecorder([jsonResponse({}, 200)]);
let error = null;
try {
  await emitTaskCompleted({ TASK_REGISTRY: kv }, {
    task_id: "x".repeat(300000), status: "PASS"
  }, { sleep: async () => {}, retryBaseMs: 0 });
} catch (err) {
  error = err.mcpError || { message: err.message };
}
console.log(JSON.stringify({ error }));
"""
        .replace("__SUB__", json.dumps(subscription(arguments={})))
    )
    assert report["error"]["code"] == -32015
    assert report["error"]["data"]["reason"] == "payload_too_large"


def test_subscription_secret_never_returned_by_listings() -> None:
    report = run_script(
        """
const kv = makeKV();
makeFetchRecorder([function(url, options, record) {
  const body = JSON.parse(record.body);
  return jsonResponse({ challenge: body.challenge }, 200);
}]);
await callMcp(kv, "events/subscribe", {
  name: "task.completed",
  arguments: { task_id: "cf-events-1" },
  delivery: { mode: "webhook", url: CALLBACK_URL, secret: TEST_SECRET }
});
const listed = await callMcp(kv, "events/list", {});
console.log(JSON.stringify({ listed, listText: JSON.stringify(listed) }));
"""
    )
    assert TEST_SECRET not in report["listText"]
    assert report["listed"]["result"]["events"][0]["name"] == "task.completed"

```

---

## 7. Changed-files allowlist (this commit)

```
MCP_EVENTS_GOLDEN_EVIDENCE.md   # analysis + tested implementation artifacts
```

`execution_result.json` is produced by the workflow into `${RUNNER_TEMP}` and
uploaded as the `execution_result-<task_id>` artifact by
`scripts/build_execution_result.py` (sourced from
`/home/runner/work/_temp/agent_result.json`). It is intentionally **not
committed at the repository root**: `hello.py::_read_execution_result` reads
`REPO_ROOT/execution_result.json`, so a root file with this task's id breaks 11
baseline `test_hello.py` golden tests (verified: root file present => 11 failed;
absent => 1077 passed, 1 skipped). The structured result is preserved in the
workflow artifact and in `agent_result.json`.

- No deletions of repository files. No `.github/workflows/`, secret, `.env`,
  `.pem`, `.key` paths.
- No Canonical writes, OAuth changes, secret changes, permission/scope changes,
  binding changes, or schema changes.
- `scripts/scope_guard.py`: `PASS` (only the allowlisted path).
- `scripts/secret_guard.py`: `PASS` (no secret value / api-key-like string).
