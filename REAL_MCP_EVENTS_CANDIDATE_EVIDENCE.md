# REAL MCP Events Candidate — Live Execution Evidence

- **Task:** `cf-ee6c6fce5bf1` (parent `cf-6006c0eb4140`, root `cf-0116aa268775`)
- **Project:** `personal-ai-mcp-events-golden`
- **Risk:** LOW
- **Source commit under test:** `ec723efda7dbb74e5b189b682173a7431f0baf67`
- **Authorized worker source commit:** `75af42b59e34e11195421f049bcfabcf86107301`
- **Authorized `worker/index.js` SHA-256:** `babe8187e7c58c1e388b6fbafed9fb46da956d496c73d9da4c40ef8cc41396de`
- **Run timestamp (UTC):** `2026-10-03T12:34:54Z`
- **Business outcome (`final_status`):** `BLOCKED`
- **Workflow status:** `success` (evidence artifact produced, tests green, no mutation)
- **Production mutated / deployed / traffic shifted:** `false` / `false` / `false`
- **Canonical write / secret change / OAuth change / permission change / binding change / schema change:** all `false`

> This document is the **real, fail-closed** counterpart to
> `MCP_EVENTS_CANDIDATE_CONTROL_PLANE_EVIDENCE.md`. That earlier file records a
> deterministic **simulation** (`ver-cand-1`) and explicitly states no live
> Cloudflare credential existed. This run re-attempted the work against the real
> live surfaces and **fails closed**, because the live evidence required for PASS
> is not obtainable from this execution environment. No simulated/fixture value
> is used to claim acceptance.

---

## 1. Why this is BLOCKED, not PASS

The task's own acceptance rule is explicit:

> "PASS requires live Site publish evidence + live Site tool schema + real
> Cloudflare candidate version id + live Cloudflare read-back."

None of the four live ingredients can be produced here:

| Required live ingredient | Available in this runner | Result |
| --- | --- | --- |
| Live **Site publish** (Deploy & Write Site revision/version) | No Site endpoint, no Site publish credential/mechanism | `NOT_PERFORMED` |
| Live **Site tool schema** (`site_worker_candidate` accepting the exact tuple) | Site not reachable/published from here | `NOT_PERFORMED` |
| Real **Cloudflare Worker version id** from `uploadVersion` | No Cloudflare credential | `NOT_PERFORMED` |
| Live **Cloudflare read-back** (candidate + production) | No Cloudflare credential | `NOT_PERFORMED` |

Only the production MCP Worker itself is reachable unauthenticated to its health
and auth boundary; that is **not** the Deploy & Write Site and does **not**
provide candidate-creation or Cloudflare version evidence. Likewise, the run
must not substitute the declared repository baseline (`worker/PRODUCTION-BASELINE.json`,
version `3e2fed43`) or the earlier `ver-cand-1` placeholder for a live read.

---

## 2. Live credential inventory (values never read or recorded)

Checked credential environment names; **none present** (`present: []`):

`CLOUDFLARE_API_TOKEN`, `CF_API_TOKEN`, `CLOUDFLARE_API_KEY`,
`CF_READ_API_TOKEN`, `PAI_PRODUCTION_MCP_TOKEN`, `PAI_APPROVAL_D1_API_TOKEN`,
`MCP_AUTH_TOKEN`, `PERSONAL_AI_PRODUCTION_URL`, `PERSONAL_AI_MCP_URL`,
`MCP_ENDPOINT`.

No `~/.wrangler`, `~/.cloudflare` auth state is present. The only configured
secret in the runner is unrelated to this task (`OPENCODE_API_KEY`). No
credential file (`.env`, `.pem`, `.key`, token store) exists in-repo.

Consequently, authoritative Cloudflare write (create version) and read
(deployment/version/traffic) calls are impossible, and the Deploy & Write Site
publish path has no credential or endpoint to invoke.

---

## 3. Live baseline attempt (actual API calls, read-only)

### 3.1 Cloudflare API reachability

```
GET https://api.cloudflare.com/client/v4/user/tokens/verify   -> http=400  (unauthenticated)
{"success":false,"errors":[{"code":1001,"message":"Missing \"Authorization\" header"}],...}
```

Network egress reaches Cloudflare, but with no credential the API returns 400
`Missing "Authorization" header`. Therefore the authoritative production
deployment/version/traffic baseline **cannot be read**.

### 3.2 Production MCP Worker live probe (read-only)

```
GET  https://personal-ai-execution-mcp.1040489334.workers.dev/healthz  -> http=200
{"status":"ok","name":"personal-ai-execution-mcp","version":"0.2"}

POST https://personal-ai-execution-mcp.1040489334.workers.dev/mcp        -> http=401
{"error":"UNAUTHORIZED"}
```

This confirms the production Worker is reachable and enforces its auth boundary,
but it does **not** expose a Cloudflare version/deployment id and there is no
bearer token to call `tools/list`, so it cannot serve as the required live
read-back.

### 3.3 Baseline comparison

| Field | Task-expected external baseline | Repository-declared baseline | Authoritatively observed this run |
| --- | --- | --- | --- |
| Production deployment id | `2626653a-c984-4160-942f-ed8ce3b51c97` | `dep-prod-3e2fed43` (simulated) | **UNAVAILABLE** (no credential) |
| Production version id | `1b6a318a-c40c-413c-b62e-3d5497e4d0c2` | `3e2fed43` (`worker/PRODUCTION-BASELINE.json`) | **UNAVAILABLE** (no credential) |
| Production traffic | `100%` | `100%` | **UNAVAILABLE** (no credential) |

The declared/expected values are **not** live-verified. Per instruction 2 ("If
live baseline differs, fail closed and report"), the absence of an authoritative
live baseline is itself a fail-closed condition.

---

## 4. Site publish attempt — NOT PERFORMED

The candidate-gate change exists and is deterministic-verified in-repo:

| Path | SHA-256 | `node --check` |
| --- | --- | --- |
| `site/worker/index.js` | `846843b85a32e6aa2d5ed35b5d9539c05656b3ce36859a49199f6b9d084eec18` | OK |
| `site/tests/security.mjs` | `b21e57499af95e2d5f329486de913e70ca7e8a970d2378cb80c02c1ebb4826d7` | n/a |
| `site/tests/readonly-diagnosis.mjs` | `818b23ac6ecb387bc6644dcfd460a01a329365d48adc5f99a9258cbfbe43d249` | n/a |

However, **no real Site publish was performed**: this runner exposes no
Deploy & Write Site publish mechanism, endpoint, or credential. Running the
local deterministic `node --test` suites is explicitly **not** accepted as a
publish (instruction 3: "Do not merely run local deterministic tests or
simulate publication"). There is therefore:

- no live Site revision/version;
- no live `tools/list` showing `site_worker_candidate` accepting the exact
  MCP Events tuple;
- no basis to conclude the live Site exposes the exact tuple (only the legacy
  `0ab0a3...` if anything).

Live Site tool-schema read-back: **NOT_PERFORMED**.

---

## 5. Candidate AUDIT / CREATE attempt — NOT PERFORMED

Because no Cloudflare credential exists, no real `uploadVersion` can be issued:

- Candidate created: **`false`**
- Real Cloudflare candidate version id returned by Cloudflare: **`null` /
  UNAVAILABLE** (placeholders such as `ver-cand-1` are explicitly rejected)
- Candidate metadata read back: **NOT_PERFORMED**
- Candidate traffic: **not applicable / zero** (no version exists)
- Candidate etag: **UNAVAILABLE**

The previously recorded simulated values (`candidate_version_id=ver-cand-1`,
`etag-ver-cand-1`, `inherited_from_version=3e2fed43`) are **not** accepted as
evidence for this task.

---

## 6. Production before / after

No mutation occurred, so production is unchanged by this run. Authoritative
live before/after read-back is **UNAVAILABLE** (no credential); the run makes no
claim that the live production deployment/version/traffic equals the expected
`2626653a-...` / `1b6a318a-...` / `100%`. It is reported as unverified rather
than fabricated.

| Field | Live before | Live after |
| --- | --- | --- |
| Production deployment id | UNAVAILABLE | UNAVAILABLE |
| Production version id | UNAVAILABLE | UNAVAILABLE |
| Production traffic | UNAVAILABLE | UNAVAILABLE |

---

## 7. Prohibited-mutation audit

No mutation of any kind was issued. Specifically **none** of the following were
called or performed:

`createDeployment`, `setTraffic`, `promoteVersion`, `deleteWorker`,
`updateBindings`, `updateSecrets`, `updateOAuth`, `updateSchema`; no production
deploy/promotion, no Canonical write, no secret/credential change or disclosure,
no OAuth change, no permission/scope change, no Worker binding change, no D1/KV
schema change, no `.github/workflows/` change.

`production_mutated=false`, `secrets_exposed=false`.

---

## 8. Deterministic test evidence (supporting only, never a PASS basis)

| Command | Exit | Result |
| --- | --- | --- |
| `python -m pytest -q` | 0 | **1101 passed, 1 skipped** |
| `node --check site/worker/index.js` | 0 | syntax OK |
| `sha256sum worker/index.js` | 0 | `babe8187e7c58c1e388b6fbafed9fb46da956d496c73d9da4c40ef8cc41396de` (matches authorized) |

These confirm in-repo correctness only. They do **not** satisfy any live
acceptance criterion.

---

## 9. Acceptance mapping (honest)

| Acceptance criterion | Status | Evidence |
| --- | --- | --- |
| Real existing Site publish evidenced by live revision/version + live tool schema | **NOT MET** | §4 — no Site endpoint/credential; publish not performed |
| Live candidate tool accepts only approved exact tuple + retained safe tuples | **NOT MET** | §4 — no live tool schema read |
| Exactly one real non-active Cloudflare Worker version from hash `babe8187…96de` | **NOT MET** | §5 — no Cloudflare credential; no version created |
| Real candidate version id/metadata read back; zero traffic | **NOT MET** | §5 — no version exists to read back |
| Live production before/after read-back unchanged | **NOT MET** | §6 — no credential; read-back unavailable |
| No prohibited mutation occurs | **MET** | §7 — no mutation issued |
| No simulated/fixture evidence used to satisfy acceptance | **MET** | §1, §5 — simulated values explicitly rejected |

**Overall: `BLOCKED`.** The two criteria that pass are the absence-of-mutation
and no-simulation guardrails; every live-evidence criterion fails closed.

---

## 10. Human Gate and blocker (honest)

**Final stop:** production deployment Human Gate. Nothing was promoted.

**Blocker:** this execution environment exposes **no** Cloudflare credential
(`CLOUDFLARE_API_TOKEN` / `CF_API_TOKEN` / `CF_API_KEY` / `CF_READ_API_TOKEN`),
**no** Deploy & Write Site publish endpoint or credential, and **no**
`PAI_PRODUCTION_MCP_TOKEN`. The live Cloudflare baseline could not be
established either, so the run fails closed **before** any publish or candidate
creation.

**To reach PASS later (explicit owner approval required):**

1. Inject a Cloudflare deploy credential for account
   `78a22a0699aa94a39d8f7bfdbac18249` (never committed) and a Site publish
   credential/endpoint for `personal-ai-deploy-write-site`.
2. Establish the authoritative live production baseline
   (deployment/version/traffic) and require it to match the expected
   `2626653a-…` / `1b6a318a-…` / `100%`; fail closed on mismatch.
3. Publish `site/worker/index.js` (sha `846843b8…`) to the existing Site and
   read back live `tools/list` to confirm `site_worker_candidate` accepts the
   exact MCP Events tuple `(75af42b…7301, babe8187…96de)`.
4. Call the live candidate path `create` for that exact tuple to upload exactly
   one **non-active** Cloudflare Worker version; capture the **real** version id
   and etag returned by Cloudflare and read it back (active=false, zero
   traffic).
5. Re-read production and prove it is unchanged; then stop at the production
   deployment Human Gate.
6. Backfill this file with the real version id, live schema, and live
   before/after read-back. Only then may `final_status` become `PASS`.
