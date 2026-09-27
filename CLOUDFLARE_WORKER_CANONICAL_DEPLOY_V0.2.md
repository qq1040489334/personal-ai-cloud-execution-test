# CLOUDFLARE_WORKER_CANONICAL_DEPLOY_V0.2_REPORT

- goal: CLOUDFLARE_WORKER_CANONICAL_DEPLOY_V0.2
- task_id: cf-0fe692a1235b
- generated_at: 2026-09-27T06:30:33.926852+00:00
- deploy_status: BLOCKED
- deployment_attempted: False
- production_mutated: False
- secrets_exposed: False

## Canonical source
- git_commit: cbcdbe306e0aa300d2c36a99bd0cefe4d6631ef6
- source_file: worker/index.js
- source_sha256: 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480
- source_bytes: 69392 lines: 1931
- module_worker: True
- last_source_commit: 592e7c29af4a5e72e3ec12bb458538629011896b
- baseline version: 3e2fed43 sha256=8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1

## Module-Worker upload
- format: module
- main_module: index.js
- module content-type: application/javascript+module
- bindings: [{'type': 'd1', 'name': 'ASSET_DB', 'id': '45d6f18a-3a34-4ccd-8337-c00a775cd7a2'}, {'type': 'kv_namespace', 'name': 'TASK_REGISTRY', 'namespace_id': '60f6203f262d44378abd0accfa7fef46'}, {'type': 'plain_text', 'name': 'GITHUB_REPO', 'text': 'qq1040489334/personal-ai-cloud-execution-test'}]
- preserved secret bindings: ['GITHUB_TOKEN', 'MCP_AUTH_TOKEN', 'OAUTH_SIGNING_KEY', 'OWNER_PASSWORD']
- keep_bindings: ['secret_text']

## Versions API plan (version-first, no content-endpoint retry)
- strategy: versions_api
- create version: POST /accounts/78a22a0699aa94a39d8f7bfdbac18249/workers/scripts/personal-ai-execution-mcp/versions
- create deployment: POST /accounts/78a22a0699aa94a39d8f7bfdbac18249/workers/scripts/personal-ai-execution-mcp/deployments

## Credential gate
- deploy token env names checked: ['CLOUDFLARE_API_TOKEN', 'CF_API_TOKEN', 'CLOUDFLARE_API_KEY']
- deploy token present: False
- account id available: True
- values recorded: False

## Cloudflare version / deployment identity
- version_id: None
- deployment_id: None
- deployment_timestamp: None

## Runtime provenance relationship
- git_commit: cbcdbe306e0aa300d2c36a99bd0cefe4d6631ef6
- source_sha256: 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480
- cloudflare_version_id: None
- cloudflare_deployment_id: None
- relationship_status: BLOCKED
- relationship_reason: git commit and exact source sha256 are recorded, but no Cloudflare version id / deployment id exists because the write surface is unavailable; the runtime link stays BLOCKED until a real deploy backfills cloudflare.version_id / cloudflare.deployment_id

## Gates
- [PASS] canonical source present: canonical worker source present: worker/index.js
- [PASS] canonical git commit and source hash recorded: git_commit=cbcdbe306e0aa300d2c36a99bd0cefe4d6631ef6 source_sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 bytes=69392 lines=1931 last_source_commit=592e7c29af4a5e72e3ec12bb458538629011896b
- [PASS] module worker syntax (export default fetch): worker/index.js is a Module Worker exporting a default fetch handler; upload uses main_module=index.js
- [PASS] module upload metadata uses main_module=index.js: metadata.main_module=index.js content_type for the module part is application/javascript+module (multipart/form-data)
- [PASS] union of preserved binding/secret names matches production set: preserved: ASSET_DB, GITHUB_REPO, GITHUB_TOKEN, MCP_AUTH_TOKEN, OAUTH_SIGNING_KEY, OWNER_PASSWORD, TASK_REGISTRY; secret bindings preserved via keep_bindings=['secret_text']; values never read
- [PASS] required secret names identified (values not read): secret names referenced by the worker source: GITHUB_TOKEN, MCP_AUTH_TOKEN, OAUTH_SIGNING_KEY, OWNER_PASSWORD; values were never read or recorded
- [PASS] versions API selected over legacy content endpoint: deploy strategy=versions_api; create version via POST /accounts/78a22a0699aa94a39d8f7bfdbac18249/workers/scripts/personal-ai-execution-mcp/versions then create deployment via POST /accounts/78a22a0699aa94a39d8f7bfdbac18249/workers/scripts/personal-ai-execution-mcp/deployments
- [BLOCKED] Cloudflare write credential available: no Cloudflare write credential in environment (checked names: CLOUDFLARE_API_TOKEN, CF_API_TOKEN, CLOUDFLARE_API_KEY); the Cloudflare Asset Deploy Write MCP / versions API is not reachable from this execution environment -> fail closed before any upload
- [PASS] Cloudflare account identified: account id 78a22a0699aa94a39d8f7bfdbac18249 from worker/PRODUCTION-BASELINE.json
- [PASS] production identity preserved (no unrelated resource mutation): no secret rotation, no binding rename/removal, no KV/D1 deletion, no OAuth or auth-logic change; resource ids are read-only in evidence
- [PASS] no secret value exposed in evidence: only non-secret environment variable names and in-repo identifiers were inspected; credentials.values_recorded=False

## Verdict
DEPLOY_STATUS=BLOCKED
VERDICT=BLOCKED
PRODUCTION_MUTATED=False
SECRETS_EXPOSED=False
RELATIONSHIP_STATUS=BLOCKED
CANONICAL_SOURCE_SHA256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480
CLOUDFLARE_VERSION_ID=UNAVAILABLE
CLOUDFLARE_DEPLOYMENT_ID=UNAVAILABLE
OVERALL=BLOCKED
