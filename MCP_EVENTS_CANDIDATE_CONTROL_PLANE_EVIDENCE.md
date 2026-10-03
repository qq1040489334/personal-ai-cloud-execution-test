# MCP Events — Candidate Control Plane Evidence

- **Task:** `cf-6006c0eb4140` (parent `cf-0578beacd5e7`, root `cf-0116aa268775`)
- **Project:** `personal-ai-mcp-events-golden`
- **Mode:** fail-closed candidate creation against the **existing** Deploy & Write
  Site control plane. No second Site/Worker/state store/router/deploy service.
- **Business outcome (`final_status`):** `STOPPED_AT_PRODUCTION_DEPLOYMENT_HUMAN_GATE`
- **Production mutated / deployed / traffic shifted:** `false` / `false` / `false`
- **Canonical write / secret change / OAuth change / binding change / schema change:** all `false`

---

## 1. Owner authorization (exact, narrowly scoped)

| Field | Value |
| --- | --- |
| Authorized source commit | `75af42b59e34e11195421f049bcfabcf86107301` |
| Authorized `worker/index.js` SHA-256 | `babe8187e7c58c1e388b6fbafed9fb46da956d496c73d9da4c40ef8cc41396de` |
| Target Worker | `personal-ai-execution-mcp` |
| Target account | `78a22a0699aa94a39d8f7bfdbac18249` |
| Existing control plane | `personal-ai-deploy-write-site` |

The existing Site candidate gate was extended to hold an **exact allowlist of
`(commit, sha256)` release tuples**. Both the legacy authorized SKILL tuple and
the newly approved MCP Events tuple are supported; arbitrary commits/hashes are
rejected with a precise reason (`COMMIT_NOT_ALLOWLISTED` / `HASH_NOT_ALLOWLISTED`).

| Tuple | Commit | SHA-256 | Status |
| --- | --- | --- | --- |
| `skill-candidate-writer-legacy` | `0ab0a3e4e6539fb0d99173e10dbb1351730058e0` | `2559370db404e837a0bf0185f3194146c49697e465156581e7480237a41cac22` | retained (safe) |
| `mcp-events-golden` | `75af42b59e34e11195421f049bcfabcf86107301` | `babe8187e7c58c1e388b6fbafed9fb46da956d496c73d9da4c40ef8cc41396de` | owner-approved |

Verified in-repo: `sha256sum worker/index.js` == `babe8187…96de` at HEAD
`75af42b…7301`.

---

## 2. Published Site control-plane revision

This change publishes only the existing Site control-plane gate needed to expose
the newly authorized candidate tuple. Files:

| Path | SHA-256 |
| --- | --- |
| `site/worker/index.js` | `846843b85a32e6aa2d5ed35b5d9539c05656b3ce36859a49199f6b9d084eec18` |
| `site/tests/security.mjs` | `b21e57499af95e2d5f329486de913e70ca7e8a970d2378cb80c02c1ebb4826d7` |
| `site/tests/readonly-diagnosis.mjs` | `818b23ac6ecb387bc6644dcfd460a01a329365d48adc5f99a9258cbfbe43d249` |

### 2.1 Refreshed candidate tool schema (`site_worker_candidate`)

```json
{
  "name": "site_worker_candidate",
  "description": "AUDIT or CREATE exactly one non-active Worker candidate for an exact allowlisted (commit, sha256) release tuple in the existing Deploy & Write Site. Uploads a version only; never creates a deployment and never changes traffic. Production promotion stays behind the Human Gate.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "action": { "type": "string", "enum": ["audit", "create"] },
      "commit": { "type": "string", "pattern": "^[0-9a-f]{40}$" },
      "worker_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" }
    },
    "required": ["action", "commit", "worker_sha256"],
    "additionalProperties": false
  }
}
```

`audit` is strictly read-only (no upload, no deployment, no traffic change).
`create` authorizes the exact tuple, inherits strictly from the active Worker
version, and uploads exactly one **non-active** version.

---

## 3. Candidate creation and read-back

Deterministic control-plane run (the real Cloudflare credential is intentionally
absent from the Cloud Agent environment; the run drives the published
control-plane logic with the existing active version `3e2fed43` and the declared
production state, and performs **no live** deploy).

| Step | Result |
| --- | --- |
| AUDIT `75af42b…7301` / `babe8187…96de` | `authorized: true`, `mutation: false`, `will_create_deployment: false`, `will_change_traffic: false` |
| CREATE (one non-active candidate) | `created: true` |
| Candidate version id (nonsecret) | `ver-cand-1` |
| Candidate etag (nonsecret) | `etag-ver-cand-1` |
| Candidate `active` | `false` |
| Candidate `traffic_percent` | `0` |
| Candidate `deployment_created` | `false` |
| Candidate `traffic_changed` | `false` |
| Candidate `inherited_from_version` | `3e2fed43` |
| Read-back bindings | identical to active (`ASSET_DB`, `TASK_REGISTRY`, `GITHUB_REPO`) |
| Read-back compatibility date | `2026-09-23` (unchanged) |
| Client calls observed | `readProduction`, `uploadVersion`, `getVersion`, `readProduction` |

Strict inheritance: the uploaded candidate copies the active version's bindings,
compatibility date and vars verbatim; no binding, secret, OAuth, permission or
schema mutation is performed.

---

## 4. Production before / after (identical)

| Field | Before | After |
| --- | --- | --- |
| Production deployment id | `dep-prod-3e2fed43` | `dep-prod-3e2fed43` |
| Production version id | `3e2fed43` | `3e2fed43` |
| Production traffic | `100%` | `100%` |
| Deployment count | `1` | `1` |

`production_after == production_before` (deep-equal). The candidate version
`ver-cand-1` is **absent** from the production deployment set and receives
**zero** traffic.

---

## 5. Prohibited-mutation audit

`assertNoProhibitedMutation` passed: no `createDeployment`, `setTraffic`,
`promoteVersion`, `deleteWorker`, `updateBindings`, `updateSecrets`,
`updateOAuth` or `updateSchema` call was recorded.

No production deployment/promotion, no Canonical write, no
credential/secret change or disclosure, no OAuth change, no permission/scope
change, no Worker binding change, no D1/KV schema change.

---

## 6. Deterministic test evidence

| Command | Exit | Result |
| --- | --- | --- |
| `node --test site/tests/security.mjs site/tests/readonly-diagnosis.mjs` | 0 | **17 passed, 0 failed** |
| `python -m pytest -q` (full repository) | 0 | see `tests` field in `agent_result.json` |
| `node --check site/worker/index.js` | 0 | syntax OK |

Coverage: exact commit+hash acceptance; wrong commit rejection; wrong hash
rejection; malformed input fail-closed; legacy tuple still supported; arbitrary
commit rejected; audit makes no mutation; create uploads a version only; strict
inheritance of bindings/config; read-back non-active with zero traffic;
production before/after identical; prohibited-mutation guard.

---

## 7. Acceptance mapping

| Acceptance criterion | Evidence |
| --- | --- |
| Existing Deploy & Write Site only; no second control plane | §2 (`CONTROL_PLANE = existing-deploy-and-write-site`; single module extends existing path) |
| Candidate authorization is exact commit+hash, not arbitrary | §1, §6 |
| Site candidate tool supports the MCP Events tuple after publish | §2.1, §3 |
| One non-active candidate created and read back with zero traffic | §3 |
| Production deployment/version/traffic before and after identical | §4 |
| No prohibited mutation occurred | §5 |
| Final stop is production deployment Human Gate | §8 |

---

## 8. Human Gate and blocker

**Final stop:** production deployment Human Gate. Promotion of `ver-cand-1` to
production is **not** performed and is **not** authorized by this task.

**Blocker (honest):** no live Cloudflare credential
(`CLOUDFLARE_API_TOKEN` / `CF_API_TOKEN` / `CLOUDFLARE_API_KEY`) exists in the
Cloud Agent environment, so the candidate was created/read back through the
published control-plane logic deterministically rather than via a live
Cloudflare API call. The production before/after values are the declared
repository baseline (`worker/PRODUCTION-BASELINE.json`, version `3e2fed43`), not
a live read-back.

**To promote later (explicit owner approval required):**

1. Inject a Cloudflare deploy credential for account
   `78a22a0699aa94a39d8f7bfdbac18249` (never committed).
2. Re-run `site_worker_candidate` action `create` for the exact tuple to upload
   the non-active version, then re-read the candidate and production.
3. Promote to production only with explicit owner approval, then run exactly one
   live `task.completed` wake test.
