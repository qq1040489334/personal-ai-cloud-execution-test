# PERSONAL_AI_CANONICAL_WORKER_CONTROLLED_PRODUCTION_DEPLOY_V0.1_REPORT

- goal: PERSONAL_AI_CANONICAL_WORKER_CONTROLLED_PRODUCTION_DEPLOY_V0.1
- task_id: cf-7afde7d95cdb
- generated_at: 2026-09-27T01:47:04.502092+00:00
- verdict: BLOCKED
- deployment_attempted: False
- production_mutated: False
- secrets_exposed: False

## Authorization
- stated: True
- source: task contract cf-7afde7d95cdb (parent ChatGPT conversation)
- independently_verified: False

## Preflight
- canonical HEAD: dbbbbd13ada2e257a028aee4f9bdffee14a1ad5a
- canonical source: worker/index.js sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (69392 bytes / 1931 lines)
- last source commit: 592e7c29af4a5e72e3ec12bb458538629011896b
- baseline version: 3e2fed43 sha256=8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1
- canonical matches baseline: False
- bindings: {'ASSET_DB': '45d6f18a-3a34-4ccd-8337-c00a775cd7a2', 'TASK_REGISTRY': '60f6203f262d44378abd0accfa7fef46'}
- secret names (values never read): ['GITHUB_TOKEN', 'MCP_AUTH_TOKEN', 'OAUTH_SIGNING_KEY', 'OWNER_PASSWORD']

## Migration
- path: worker/migrations/0001_asset_provenance_v0_2.sql sha256=c5417eee980b00425775d20d0541b5795094314ef8e75c361a45027019b98fab
- additive: True idempotent: True
- destructive statements: none
- required by worker source: False
- applied: False
- apply method: npx wrangler d1 execute ASSET_DB --remote --file=worker/migrations/0001_asset_provenance_v0_2.sql

## Credential gate
- deploy token env names checked: ['CLOUDFLARE_API_TOKEN', 'CF_API_TOKEN', 'CLOUDFLARE_API_KEY']
- deploy token present: False
- account id available: True
- values recorded: False

## Provenance chain (Git commit -> source hash -> Cloudflare -> runtime)
- git_commit: dbbbbd13ada2e257a028aee4f9bdffee14a1ad5a
- source_sha256: 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480
- cloudflare_deployment_id: None
- cloudflare_version: None
- deployment_timestamp: None
- link_status: INCOMPLETE_BLOCKED

## Gates
- [PASS] human authorization recorded in task contract: task contract cf-7afde7d95cdb states production authorization is granted in the parent conversation; recorded here, not independently verifiable from the repository (authorization is not a credential)
- [PASS] canonical source present: canonical worker source present: worker/index.js
- [PASS] canonical source identified and hashed: source_sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 bytes=69392 lines=1931 last_source_commit=592e7c29af4a5e72e3ec12bb458538629011896b (preflight HEAD recorded in preflight.canonical_head_commit)
- [BLOCKED] canonical source matches declared production baseline: declared baseline source hash 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 does not match canonical HEAD source hash 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480; deploying would supersede the Quick Edit baseline and must be paired with a new provenance record (not a hard failure, but it requires a live deploy)
- [PASS] worker bindings present: bindings: ASSET_DB=45d6f18a-3a34-4ccd-8337-c00a775cd7a2, TASK_REGISTRY=60f6203f262d44378abd0accfa7fef46
- [PASS] required secret names identified (values not read): secret names referenced by the worker source: GITHUB_TOKEN, MCP_AUTH_TOKEN, OAUTH_SIGNING_KEY, OWNER_PASSWORD; values were never read or recorded
- [PASS] asset provenance migration is additive and non-destructive: worker/migrations/0001_asset_provenance_v0_2.sql sha256=c5417eee980b00425775d20d0541b5795094314ef8e75c361a45027019b98fab uses CREATE TABLE/INDEX IF NOT EXISTS and contains no destructive statements (found: none)
- [PASS] required additive migration: the current worker source does not reference the new provenance tables, so no migration is required for the deployed execution/asset-read contract; the additive migration is safe to apply via the canonical wrangler D1 mechanism
- [BLOCKED] Cloudflare deploy credential available: no deploy credential in environment (checked names: CLOUDFLARE_API_TOKEN, CF_API_TOKEN, CLOUDFLARE_API_KEY); `npx wrangler whoami` reports 'You are not authenticated. Please run `wrangler login`.' -> fail closed before deploy
- [PASS] Cloudflare account identified: account id 78a22a0699aa94a39d8f7bfdbac18249 from worker/PRODUCTION-BASELINE.json
- [BLOCKED] wrangler non-interactive deploy possible: wrangler non-interactive deploy can proceed only with a deploy token; blocked here
- [PASS] no production mutation performed: preflight only: no deploy, upload, secret rotation, D1/KV write or workflow mutation was performed
- [PASS] no secret value exposed in evidence: only non-secret environment variable names and in-repo identifiers were inspected; no secret value was read or written

## Verdict
VERDICT=BLOCKED
DEPLOYMENT_ATTEMPTED=False
PRODUCTION_MUTATED=False
SECRETS_EXPOSED=False
OVERALL=BLOCKED
