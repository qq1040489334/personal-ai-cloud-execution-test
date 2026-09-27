# PERSONAL_AI_RUNTIME_PROVENANCE_FINAL_AUDIT_V0.3_REPORT

- goal: PERSONAL_AI_RUNTIME_PROVENANCE_FINAL_AUDIT_V0.3
- task_id: cf-619649c43aa2
- generated_at: 2026-09-27T01:57:28.378234+00:00
- read_only: True
- production_mutated: False
- secrets_exposed: False
- live_endpoint_checked: False

## Production deployment / version identity
- service: personal-ai-execution-mcp
- environment: production
- production_version: 3e2fed43
- metadata: worker/PRODUCTION-BASELINE.json
- cloudflare_deployment_id: None
- cloudflare_version: None
- deployment_timestamp: None
- deploy_attempted: False
- deploy_link_status: 'INCOMPLETE_BLOCKED'
- identity_status: PARTIAL

## Canonical source vs declared production source
- canonical source: worker/index.js
- canonical HEAD commit: 42a47d9e9d2612ca388177e45e47286479428e0e
- canonical HEAD sha256: 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (69392 bytes / 1931 lines)
- declared production sha256: 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 (55278 bytes / 1543 lines)
- canonical HEAD matches declared: False
- canonical source last commit: 592e7c29af4a5e72e3ec12bb458538629011896b

## Source-to-live-runtime relationship
- relationship_status: UNVERIFIED
- reason: declared production source hash 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 matches no canonical commit of worker/index.js in the repository history; current HEAD source hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480; no Cloudflare deployment/version record exists to link source to the live runtime; the deployed runtime is not traceable to a canonical source commit

## Recent runtime changes (inclusion in deployed runtime)
- status-contract: status=BLOCKED canonical_source_includes=True deployed_inclusion_proven=False source_commits=['0c3ac20392bf']
  - status-contract tokens are present in canonical source (sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480) but the deployed production source hash cannot be tied to a canonical commit, so inclusion in the live runtime is not proven
- asset-provenance: status=BLOCKED canonical_source_includes=True deployed_inclusion_proven=False source_commits=['592e7c29af4a']
  - asset-provenance tokens are present in canonical source (sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480) but the deployed production source hash cannot be tied to a canonical commit, so inclusion in the live runtime is not proven

## Candidate source commits
- 592e7c29af4a 2026-09-27T01:10:20Z sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 bytes=69392 lines=1931 on_history=True matches_declared=False tags=[] | cloud agent: gpt task
- 0c3ac20392bf 2026-09-27T00:52:12Z sha256=1fc165aea2b988ff524c95035f4fdb1fe4ede5219958d04a3cccda239b0adcba bytes=60178 lines=1708 on_history=True matches_declared=False tags=[] | cloud agent: gpt task
- 9d60c7bfedca 2026-09-26T10:52:36+08:00 sha256=b001caebf1193b9bab47d519bc516da92df0c1ce1d83ea3db63b1b21fcebf6c9 bytes=54312 lines=1551 on_history=True matches_declared=False tags=['expected-files-v1-20260926'] | feat: support task-scoped expected files
- 6a0c740858a8 2026-09-26T10:19:56+08:00 sha256=ea298b2eebfb0445086aac85ef5c4988e6d508d2df6bfa0ddfc772429b7aca7c bytes=53736 lines=1542 on_history=True matches_declared=False tags=['production-recovered-3e2fed43-20260926'] | chore: recover production execution worker baseline

## Execution-relevant commits not proven deployed
- dbbbbd13ada2 worker=False workflow=False proven_deployed=False | cloud agent: gpt task
- 592e7c29af4a worker=True workflow=False proven_deployed=False | cloud agent: gpt task
- 0c3ac20392bf worker=True workflow=False proven_deployed=False | cloud agent: gpt task
- 698ac2998c67 worker=False workflow=False proven_deployed=False | cloud agent: gpt task
- ed3ca64977a1 worker=False workflow=True proven_deployed=False | fix: extend agent budget and make cancelled results truthful
- 3263e7d47a60 worker=False workflow=False proven_deployed=False | cloud agent: gpt task
- 1427442526d4 worker=False workflow=False proven_deployed=False | cloud agent: gpt task
- f7218cee6898 worker=False workflow=False proven_deployed=False | cloud agent: gpt task
- d506fd5058e0 worker=False workflow=False proven_deployed=False | cloud agent: gpt task
- 548170eb05df worker=False workflow=False proven_deployed=False | cloud agent: gpt task
- e0f2f2c55b04 worker=False workflow=False proven_deployed=False | bootstrap: support safe task-scoped new files and globs
- 9d60c7bfedca worker=True workflow=False proven_deployed=False | feat: support task-scoped expected files

## Report-only (non-runtime) commits
- 42a47d9e9d26 | cloud agent: gpt task (5 path(s))
- ddf5ca385dff | cloud agent: gpt task (4 path(s))
- 824bd4c41555 | cloud agent: gpt task (1 path(s))
- 39949a75ce5d | cloud agent: gpt task (2 path(s))
- 2058dce16e86 | cloud agent: gpt task (2 path(s))
- 93e64046bef9 | cloud agent: gpt task (1 path(s))
- c7075cb75d65 | cloud agent: gpt task (2 path(s))
- 70a208efca30 | cloud agent: gpt task (1 path(s))

## Live endpoint checks
- performed: False
- reason: no Cloudflare credential or live interface available in the audit environment; a bounded read-only health probe was not possible, so live runtime evidence is not fabricated
- planned: health endpoint (GET /healthz)
- planned: auth boundary (POST /mcp without Authorization)
- planned: MCP tools/list schema (POST /mcp (authorized) method=tools/list)

## Checks
- [PASS] deployment metadata present: deployment baseline present: worker/PRODUCTION-BASELINE.json
- [BLOCKED] production deployment/version identity independently verified: identity only self-declared: service=personal-ai-execution-mcp environment=production version=3e2fed43 (source: worker/PRODUCTION-BASELINE.json); no authoritative live/deployment confirmation available
- [PASS] canonical source present: canonical source present: worker/index.js (sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480, bytes=69392, lines=1931)
- [PASS] canonical commit and exact worker source hash verified: HEAD source worker/index.js sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (69392 bytes / 1931 lines); last source commit 592e7c29af4a5e72e3ec12bb458538629011896b
- [BLOCKED] declared production source hash matches a canonical commit: declared production source hash 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 matches no canonical worker/index.js commit (4 candidate commits checked); current HEAD source hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480
- [BLOCKED] source hash -> Cloudflare deployment/version link: no Cloudflare deployment id/version recorded; the link from the canonical source hash to a live deployment is absent
- [BLOCKED] canonical source -> live runtime relationship: [UNVERIFIED] declared production source hash 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 matches no canonical commit of worker/index.js in the repository history; current HEAD source hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480; no Cloudflare deployment/version record exists to link source to the live runtime; the deployed runtime is not traceable to a canonical source commit
- [BLOCKED] status-contract and asset-provenance runtime changes proven included: status-contract=BLOCKED: status-contract tokens are present in canonical source (sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480) but the deployed production source hash cannot be tied to a canonical commit, so inclusion in the live runtime is not proven; asset-provenance=BLOCKED: asset-provenance tokens are present in canonical source (sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480) but the deployed production source hash cannot be tied to a canonical commit, so inclusion in the live runtime is not proven
- [BLOCKED] execution-relevant commits proven deployed: 12 execution-relevant commit(s) after the recovered baseline are not proven deployed (source presence != deployment)
- [PASS] no production mutation: read-only audit: no deploy, upload, secret change, D1/KV mutation, workflow mutation or asset mutation performed

## Remaining gap to VERIFIED
- production deployment/version identity is only self-declared (worker/PRODUCTION-BASELINE.json version=3e2fed43); no authoritative live-runtime or Cloudflare deployment/version interface confirmed it
- no Cloudflare production deploy credential is available (checked names: CLOUDFLARE_API_TOKEN, CF_API_TOKEN, CLOUDFLARE_API_KEY); the controlled deploy cf-7afde7d95cdb was BLOCKED before any deployment was attempted
- reports/production_deploy_v0.1.json records cloudflare_deployment_id=None, cloudflare_version=None, deployment_timestamp=None, link_status='INCOMPLETE_BLOCKED'
- declared production source sha256 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 matches no canonical worker/index.js commit; current HEAD source hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (last source commit 592e7c29af4a5e72e3ec12bb458538629011896b)
- to reach VERIFIED: deploy the canonical worker source with a Cloudflare credential, record cloudflare_deployment_id/version and deployment_timestamp, and write the deployed worker/index.js sha256 into the production baseline so the commit -> hash -> version -> runtime chain closes
- status-contract and asset-provenance Worker changes are present in canonical source but not proven included in the live runtime because the deployed source hash cannot be tied to a canonical commit

## Verdict
DEPLOYED_VERSION=3e2fed43
CLOUDFLARE_DEPLOYMENT_ID=UNAVAILABLE
CLOUDFLARE_VERSION=UNAVAILABLE
DEPLOYMENT_IDENTITY_STATUS=PARTIAL
RELATIONSHIP_STATUS=UNVERIFIED
CANONICAL_SOURCE_SHA256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480
PRODUCTION_MUTATED=False
SECRETS_EXPOSED=False
OVERALL=BLOCKED
