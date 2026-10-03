# MCP Events Golden — Production Release Plan (V0.1)

- **Task:** `cf-7b631b36bfe4` / `MCP_EVENTS_GOLDEN_PREP_V0.1` / project `mcp-events-golden`
- **Mode:** `LOCAL_SIMULATION_PREP` — audit + prepare only. **No production mutation.**
- **Status:** PREP PASS. Live end-to-end wake remains **UNKNOWN** and is **not claimed**.
- **Evidence:** `outputs/mcp_events_prep_evidence.json`
- **Official spec:** https://developers.openai.com/plugins/build/mcp-events (`.md` route)
- **Protocol required:** MCP 2.0 / `2026-07-28`

---

## 1. Baseline (facts, with discrepancies)

| Item | Value |
| --- | --- |
| Repository | `qq1040489334/personal-ai-cloud-execution-test` |
| Worker service | `personal-ai-execution-mcp` |
| Current HEAD | `6e0050ea5c14b0c87315f4f4635b5e25b9095b39` |
| Worker source | `worker/index.js` |
| Worker source sha256 | `2559370db404e837a0bf0185f3194146c49697e465156581e7480237a41cac22` |
| Worker source bytes / lines | 124,259 / 3,079 |
| Task-declared authorized source commit | `0ab0a3e4e6539fb0d99173e10dbb1351730058e0` |
| Worker sha256 at that commit | `2559370d…1cac22` (identical to HEAD) |
| Task-declared production version | `1b6a318a-c40c-413c-b62e-3d5497e4d0c2` |
| Repo `worker/PRODUCTION-BASELINE.json` version | `3e2fed43` (source 55,278 bytes / 1,543 lines) |

**Discrepancy (must be resolved at Human Gate):** the task-declared production
version `1b6a318a-…` and source `0ab0a3e4` match `outputs/webauthn-golden-evidence.json`
(a Cloudflare **Pages** WebAuthn closure artifact), not the MCP **Worker** baseline
(`3e2fed43`, 55,278 bytes). This sandbox has **no Cloudflare credentials**, so the live
production Worker version is `UNKNOWN`. Per instruction, current HEAD is **not** assumed
equal to deployed source. The one thing that is verified: `worker/index.js` at HEAD is
**byte-identical** (sha256) to the declared authorized source commit `0ab0a3e4`.

---

## 2. Current-source reuse audit

Reuse the existing Worker; create nothing new.

| Reused | Location |
| --- | --- |
| Single `POST /mcp` MCP endpoint + OAuth auth | `worker/index.js` `fetch()` (~line 3065) |
| JSON-RPC dispatch | `handleMcp()` switch (`worker/index.js:2989`) |
| `TASK_REGISTRY` KV binding | `worker/wrangler.toml` id `60f6203f262d44378abd0accfa7fef46` |
| Evidence read-back | existing `get_task_result` tool (`worker/index.js:2741`, call site `:3007`) |
| HMAC-SHA256 helpers | `hmacKey` / `signPayload` (`worker/index.js:575–608`) |

**Not created:** second server, task DB, router, or event-bus repo.
**Not restored:** PersonOS / Curator / Inbox.

Current state: protocol `2025-06-18`; 11 tools; **no** `server/discover`, **no** `events` capability, **no** `events/*` methods. The change is strictly additive so all 11 existing tools keep working.

---

## 3. Narrow scope

- One event only: `personal_ai.golden.completed`.
- `inputSchema`: `{ golden_id: string, task_id: string }` (both required, no extras).
- `payloadSchema`: `{ golden_id: string, task_id: string, status: string }` (no extras).
- `data` carries **IDs and status only**. Full evidence is read through the existing
  `get_task_result(task_id)`.
- Real task completions are **not** wired in this prep.

Subscription operational state lives under the existing KV namespace prefix
`events-subscription::<sub_id>` — **operational state only**, no production KV/D1 writes during PREP.

---

## 4. Proposed patch (REVIEWABLE, NOT APPLIED)

> Applying this patch requires a Human Gate with an expanded allowlist. It is not
> applied in the PREP commit; the only committed files are the two `outputs/` artifacts.

### 4.1 Insert near `PROTOCOL_VERSION` (`worker/index.js:528`)

```js
var EVENTS_PROTOCOL_VERSION = "2026-07-28";
var EVENTS_KV_PREFIX = "events-subscription::";
var MAX_EVENT_BYTES = 256 * 1024;
var DEFAULT_EVENT_TTL_MS = 7 * 24 * 60 * 60 * 1000;
var MIN_EVENT_TTL_MS = 60 * 1000;
var EVENTS = [{
  name: "personal_ai.golden.completed",
  description: "Narrowly filtered harmless golden test event; read full evidence via get_task_result.",
  delivery: ["webhook"],
  inputSchema: {
    type: "object",
    properties: { golden_id: { type: "string" }, task_id: { type: "string" } },
    required: ["golden_id", "task_id"],
    additionalProperties: false
  },
  payloadSchema: {
    type: "object",
    properties: { golden_id: { type: "string" }, task_id: { type: "string" }, status: { type: "string" } },
    required: ["golden_id", "task_id", "status"],
    additionalProperties: false
  }
}];
var EVENT_NAMES = new Set(EVENTS.map((e) => e.name));

function canonicalJson(value) {
  if (Array.isArray(value)) return "[" + value.map(canonicalJson).join(",") + "]";
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + canonicalJson(value[k])).join(",") + "}";
  }
  return JSON.stringify(value);
}
function validateSigningSecret(secret) {
  if (typeof secret !== "string" || !secret.startsWith("whsec_")) return null;
  try {
    const raw = Uint8Array.from(atob(secret.slice(6).replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
    if (raw.length < 24 || raw.length > 64) return null;
    return raw;
  } catch { return null; }
}
async function standardWebhookSignature(secret, msgId, timestamp, body) {
  const key = await crypto.subtle.importKey("raw", validateSigningSecret(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const signed = new TextEncoder().encode(`${msgId}.${timestamp}.${body}`);
  const sig = await crypto.subtle.sign("HMAC", key, signed);
  return "v1," + bytesToB64url(new Uint8Array(sig));
}
function subscriptionId(principal, url, name, args) {
  return "sub_" + sha256Hex(`${principal}.${url}.${name}.${canonicalJson(args)}`).slice(0, 32);
}
```

(`sha256Hex`, if absent, is a small `crypto.subtle.digest` wrapper. `bytesToB64url`
already exists at `worker/index.js:559`.)

### 4.2 Callback safety — used by verification *and* delivery

```js
async function assertCallbackUrl(url) {
  const u = new URL(url);
  if (u.protocol !== "https:") throw { reason: "insecure_scheme" };
  if (u.username || u.password) throw { reason: "userinfo_not_allowed" };
  // DNS resolution + public-address check is performed by the injectable
  // webhookFetch, which MUST use redirect:"error" and connect to the resolved
  // validated address while preserving the hostname for TLS verification.
  return u;
}
```

All outbound fetches use a single `webhookFetch` wrapper enforcing:
`redirect:"error"`, `AbortSignal.timeout(10_000)`, resolved-address validation
(block loopback / private / link-local / reserved / multicast / unspecified / CGNAT).

### 4.3 Subscription handlers (add cases to `handleMcp`)

```js
case "server/discover":
  return ok({ resultType: "complete", supportedVersions: [EVENTS_PROTOCOL_VERSION],
              capabilities: { tools: {}, events: {} } });
case "events/list":
  return ok({ events: EVENTS, nextCursor: null, truncated: false });
case "events/subscribe": {
  if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
  return handleEventsSubscribe(env, auth, params, ok, fail);   // verify callback, store KV, return id/refreshBefore
}
case "events/unsubscribe": {
  if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
  return handleEventsUnsubscribe(env, auth, params, ok, fail); // account-scoped, idempotent, returns {}
}
```

`initialize` / `tools/list` / `tools/call` are **unchanged**, preserving all existing clients and tools.

### 4.4 Delivery

`sendEvent(subscription, event, webhookFetch)`:
- `body = JSON.stringify(event)`, reject `Buffer.byteLength(body) > 262144`;
- headers `Content-Type`, `webhook-id: event.eventId`, `webhook-timestamp`,
  `webhook-signature` (Standard Webhooks over the **exact** body bytes),
  `X-MCP-Subscription-Id`;
- one event per request; 2xx = ack; bounded exponential backoff; fresh
  timestamp/signature each attempt; preserve `eventId`; **no retry on 410/413**.

---

## 5. Local deterministic verification (LOCAL_SIMULATION — no live claim)

| Command | Exit | Result |
| --- | --- | --- |
| `python -m pytest -q /tmp/opencode/test_mcp_events_sim.py` | 0 | **24 passed** in 0.03s |
| `python -m pytest -q` (repo) | 0 | **1077 passed, 1 skipped** in 35.09s |
| `node --check worker/index.js` | 0 | syntax OK |

Golden sequence proven locally: subscribe → signed callback verification
(2xx + constant-time challenge echo) → signed webhook delivery → fixture
read-back via `get_task_result` → idempotent unsubscribe.

Negative/security matrix (all pass): wrong signature; tampered body; replay
outside tolerance; bad secret shape; unauthorized subscribe/unsubscribe;
cross-account unsubscribe; duplicate subscribe; duplicate delivery; filter
mismatch; refresh + secret rotation; expired subscription; restart persistence;
`ttlMs:null` finite expiry; blocked callback destinations; failed verification;
bounded retries + stop on 410/413; 256 KiB bound; no secret in evidence;
existing tools unchanged.

**No network I/O. No production writes. No live subscription. The ephemeral local
test signing secret is generated in `/tmp` and excluded from all repository artifacts
(only a non-reversible fingerprint is reported).**

---

## 6. Build / artifact

There is **no build step**: `worker/wrangler.toml` (`main = "index.js"`) deploys the
prebuilt `worker/index.js` bundle directly, so the deploy artifact hash equals the
source hash.

- Baseline source/build hash: `2559370db404e837a0bf0185f3194146c49697e465156581e7480237a41cac22`
- Proposed patched build hash: **must be recomputed at Human Gate** after the patch is
  applied (`sha256sum worker/index.js`) and recorded here before any deploy.

---

## 7. Changed-file allowlist (this PREP commit)

```
outputs/mcp_events_prep_evidence.json
outputs/mcp_events_release_plan.md
```

- No deletions. No `.github/workflows/`, secret, `.env`, `.pem`, `.key` paths touched.
- No OAuth changes, no secret changes, no Canonical writes, no external messages.
- `scripts/scope_guard.py` expected: `PASS: all changes within allowlist`.
- `scripts/secret_guard.py` expected: `PASS: no secret value and no api-key-like string`.

---

## 8. Rollback target

- Documented repo target: Cloudflare version **`3e2fed43`** (`worker/PRODUCTION-BASELINE.json`).
- **Caveat:** live verification of this target from the sandbox is `UNKNOWN_NO_CREDENTIALS`,
  and the repo baseline conflicts with the task-declared version `1b6a318a` (see §1).
  Human Gate must confirm the actual live Worker version and record a known-good rollback
  version id before deploy.

---

## 9. Human Gate scope (exact, future action — not done here)

1. Approve an expanded changed-file allowlist including `worker/index.js` (and tests).
2. Apply the patch on an isolated branch; run `node --check`, the 24-case local
   event simulation, and the full `pytest` suite (1077+).
3. Review the KV signing-secret storage decision (DEP-2) and the protocol 2026-07-28
   negotiation (DEP-4).
4. With Cloudflare credentials, confirm the live production version and set a verified
   rollback version id.
5. Deploy to staging/non-production version first; then production with explicit approval.
6. Run exactly one **LIVE** wake test with ChatGPT Work chat (real subscribe →
   verification → delivery) and record the observed event id/status. Until this runs,
   end-to-end wake is **UNKNOWN**.

**Out of scope for PREP (prohibited):** deploy / upload / publish, OAuth or secret
changes, Canonical writes, external messages, live subscriptions, production KV/D1 writes.

---

## 10. Blockers / dependencies

| ID | Severity | Summary |
| --- | --- | --- |
| DEP-1 | non-blocking | Code cannot be committed under the PREP allowlist; delivered as a reviewable proposed patch. |
| DEP-2 | Human Gate | Signing secrets in existing TASK_REGISTRY KV (no new binding needed) need security review. |
| DEP-3 | UNKNOWN | Live production version unverifiable without credentials; baseline conflict (§1). |
| DEP-4 | protocol | Additive MCP 2.0 `server/discover` handshake needs compatibility review. |
