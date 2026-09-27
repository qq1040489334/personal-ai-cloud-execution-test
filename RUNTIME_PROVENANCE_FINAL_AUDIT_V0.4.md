# PERSONAL_AI_RUNTIME_PROVENANCE_FINAL_AUDIT_V0.4_REPORT

- goal: PERSONAL_AI_RUNTIME_PROVENANCE_FINAL_AUDIT_V0.4
- task_id: cf-b3bcb97ef047
- generated_at: 2026-09-27T06:58:01.163134+00:00
- read_only: True
- production_mutated: False
- secrets_exposed: False
- live_endpoint_checked: False
- authoritative_cloudflare_data_captured: False

## Authoritative Cloudflare evidence
- read/write MCP interface available: False
- credential env names present: []
- Cloudflare API network reachable: True (unauthenticated verify http_status=400)
- authoritative Workers versions API read: False (no Cloudflare read/write credential or Cloudflare MCP tool is exposed in this execution environment, so the authoritative Worker versions/deployments API cannot be read; cf-0fe692a1235b recorded the same write surface as unavailable)

## Production deployment / version identity
- service: personal-ai-execution-mcp
- environment: production
- cloudflare_account_id: 78a22a0699aa94a39d8f7bfdbac18249
- declared_production_version: 3e2fed43 (self-declared: worker/PRODUCTION-BASELINE.json)
- cloudflare_deployment_id: None
- cloudflare_version_id: None
- deployment_timestamp: None
- traffic_percentage: None
- identity_status: BLOCKED
- identity_reason: deployment identity is self-declared only (worker/PRODUCTION-BASELINE.json version=3e2fed43); it was not independently confirmed from Cloudflare

## Canonical source vs deployed source
- canonical source: worker/index.js
- canonical git commit (last source commit): 592e7c29af4a5e72e3ec12bb458538629011896b
- canonical sha256: 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (69392 bytes / 1931 lines)
- declared production sha256: 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1
- declared matches canonical HEAD: False
- deployed source sha256: None (available=False)
- deployed matches canonical: None
- relationship: CANNOT_COMPARE
- reason: the actual deployed Worker source could not be fetched from Cloudflare (no authoritative read interface or credential), so no deployed source hash exists to compare against canonical worker/index.js

## Source-to-live-runtime relationship
- relationship_status: UNVERIFIED
- reason: declared production source sha256 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 matches no canonical worker/index.js commit of the repository (4 candidate commits checked); the current canonical source hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (last source commit 592e7c29af4a5e72e3ec12bb458538629011896b); no authoritative Cloudflare deployment/version/deployed-source evidence and no live runtime evidence link the canonical source to the running production Worker, so the Git commit -> source hash -> Cloudflare version/deployment -> live runtime chain is not closed

## Recent runtime changes (live inclusion)
- status-contract: status=BLOCKED canonical_source_includes=True live_inclusion_proven=False live_status=NOT_LIVE_VERIFIED
  - status-contract logic is present in canonical worker/index.js (sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480) but is NOT live-verified: the deployed Worker source hash and Cloudflare version/deployment are unavailable, so its presence in the running production Worker is explicitly not proven
- asset-provenance: status=BLOCKED canonical_source_includes=True live_inclusion_proven=False live_status=NOT_LIVE_VERIFIED
  - asset-provenance logic is present in canonical worker/index.js (sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480) but is NOT live-verified: the deployed Worker source hash and Cloudflare version/deployment are unavailable, so its presence in the running production Worker is explicitly not proven

## MCP surface in canonical source
- tokens present: True (missing=none) live_verified=False

## Candidate source commits
- 592e7c29af4a 2026-09-27T01:10:20Z sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 bytes=69392 lines=1931 on_history=True matches_declared=False tags=[] | cloud agent: gpt task
- 0c3ac20392bf 2026-09-27T00:52:12Z sha256=1fc165aea2b988ff524c95035f4fdb1fe4ede5219958d04a3cccda239b0adcba bytes=60178 lines=1708 on_history=True matches_declared=False tags=[] | cloud agent: gpt task
- 9d60c7bfedca 2026-09-26T10:52:36+08:00 sha256=b001caebf1193b9bab47d519bc516da92df0c1ce1d83ea3db63b1b21fcebf6c9 bytes=54312 lines=1551 on_history=True matches_declared=False tags=['expected-files-v1-20260926'] | feat: support task-scoped expected files
- 6a0c740858a8 2026-09-26T10:19:56+08:00 sha256=ea298b2eebfb0445086aac85ef5c4988e6d508d2df6bfa0ddfc772429b7aca7c bytes=53736 lines=1542 on_history=True matches_declared=False tags=['production-recovered-3e2fed43-20260926'] | chore: recover production execution worker baseline

## Live read-only verification
- performed: False
- reason: the production hostname is not recorded in the repository (only service name and account id are), the workers.dev subdomain is not derivable, and no bearer token is available; probing unverified hostnames is not safe, so bounded live read-only verification is reported not performed rather than fabricated
- NOT_PERFORMED: health endpoint (GET /healthz) -> expect 200 JSON containing {"status":"ok","name":"personal-ai-execution-mcp"}
- NOT_PERFORMED: auth boundary (POST /mcp without Authorization) -> expect 401 with WWW-Authenticate resource_metadata
- NOT_PERFORMED: MCP tools/list schema (POST /mcp (authorized) method=tools/list) -> expect tools include submit_task, get_task_result, mark_reviewed, search_assets
- NOT_PERFORMED: status contract behavior (get_task_result for a known task id) -> expect status derived from workflow/artifact evidence, not self-report
- NOT_PERFORMED: asset provenance read path (search_assets / provenance read) -> expect provenance metadata returned read-only; no mutation

## Deployment intent cf-0fe692a1235b
- deploy_status: BLOCKED
- deployment_attempted: False
- production_mutated: False
- interpreted as: deployment intent only, not proof of production deployment

## Checks
- [BLOCKED] authoritative Cloudflare deployment/version/timestamp captured: not captured: no Cloudflare credential and no Cloudflare read/write MCP tool is available; the Worker versions/deployments API (/accounts/<account>/personal-ai-execution-mcp/versions) could not be read (cf-0fe692a1235b recorded the same write surface as unavailable)
- [BLOCKED] actual deployed Worker source/hash compared to canonical worker/index.js: not compared: deployed source unavailable; canonical source sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (69392 bytes / 1931 lines, commit 592e7c29af4a5e72e3ec12bb458538629011896b); declared production sha256=8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 is only self-declared in worker/PRODUCTION-BASELINE.json and matches no canonical commit
- [BLOCKED] live runtime MCP surface and security boundary verified: not performed: production hostname not recorded and no bearer token available; /healthz, unauthenticated /mcp 401 boundary and authorized tools/list were not probed, so no live runtime claim is made
- [BLOCKED] status-contract and asset-provenance changes proven live: explicitly NOT live-verified: both changes are present in canonical source (sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480) but the deployed source hash and Cloudflare version/deployment are unavailable, so inclusion in the live runtime is unproven
- [BLOCKED] canonical source -> live runtime relationship: [UNVERIFIED] declared production source sha256 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 matches no canonical worker/index.js commit of the repository (4 candidate commits checked); the current canonical source hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (last source commit 592e7c29af4a5e72e3ec12bb458538629011896b); no authoritative Cloudflare deployment/version/deployed-source evidence and no live runtime evidence link the canonical source to the running production Worker, so the Git commit -> source hash -> Cloudflare version/deployment -> live runtime chain is not closed
- [PASS] cf-0fe692a1235b treated as deployment intent only: reports/canonical_deploy_v0.2.json records deploy_status=BLOCKED, deployment_attempted=false, production_mutated=false; it is evidence of deployment intent, not proof of a production deployment
- [PASS] no production mutation: read-only audit: no deploy, upload, secret read, binding change, D1/KV mutation, workflow change or asset mutation performed

## Remaining gap to VERIFIED
- authoritative Cloudflare deployment ID, Worker version ID and deployment timestamp are UNAVAILABLE: no Cloudflare credential (checked CLOUDFLARE_API_TOKEN, CF_API_TOKEN, CLOUDFLARE_API_KEY) and no Cloudflare read/write MCP tool is exposed in this environment
- the actual deployed Worker source could not be fetched, so the deployed source sha256 cannot be compared to canonical worker/index.js sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480
- declared production source sha256 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 (worker/PRODUCTION-BASELINE.json) matches no canonical commit; canonical HEAD hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (last source commit 592e7c29af4a5e72e3ec12bb458538629011896b)
- live runtime verification was not performed: the production hostname is not recorded in-repo and no bearer token is available, so /healthz, the /mcp auth boundary and tools/list remain unchecked
- status-contract and asset-provenance logic are present in canonical source but are explicitly NOT proven live in the running production Worker
- to reach VERIFIED: provide an authoritative Cloudflare read credential/MCP interface, capture deployment id + version id + timestamp + traffic percentage, fetch and hash the deployed Worker source, and run the bounded live read-only checks; only then can the commit -> source hash -> Cloudflare version/deployment -> live runtime chain be closed

## Verdict
DEPLOYED_VERSION=3e2fed43
CLOUDFLARE_DEPLOYMENT_ID=UNAVAILABLE
CLOUDFLARE_VERSION_ID=UNAVAILABLE
DEPLOYMENT_TIMESTAMP=UNAVAILABLE
DEPLOYED_SOURCE_SHA256=UNAVAILABLE
DEPLOYMENT_IDENTITY_STATUS=BLOCKED
RELATIONSHIP_STATUS=UNVERIFIED
CANONICAL_SOURCE_SHA256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480
PRODUCTION_MUTATED=False
SECRETS_EXPOSED=False
OVERALL=BLOCKED
