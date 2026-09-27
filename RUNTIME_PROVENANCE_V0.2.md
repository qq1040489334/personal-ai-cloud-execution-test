# PERSONAL_AI_RUNTIME_PROVENANCE_V0.2_REPORT

- goal: PERSONAL_AI_RUNTIME_PROVENANCE_V0.2
- task_id: cf-883c3502ff24
- generated_at: 2026-09-27T01:47:04.735443+00:00
- read_only: True
- production_mutated: False
- live_endpoint_checked: False

## Production runtime / deployment identity
- service: personal-ai-execution-mcp
- environment: production
- production_version: 3e2fed43
- metadata: worker/PRODUCTION-BASELINE.json
- identity_status: VERIFIED
- evidence: in-repo deployment baseline worker/PRODUCTION-BASELINE.json (self-declared; Cloudflare Quick Edit provenance)

## Canonical source vs declared production source
- canonical source: worker/index.js
- canonical HEAD sha256: 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 (69392 bytes / 1931 lines)
- declared production sha256: 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 (55278 bytes / 1543 lines)
- canonical HEAD matches declared: False
- canonical source last commit: 592e7c29af4a5e72e3ec12bb458538629011896b

## Canonical source commit -> deployed runtime relationship
- relationship_status: UNVERIFIED
- reason: declared production source hash 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 matches no canonical commit of worker/index.js in the repository history; current HEAD source hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480; the deployed runtime is not traceable to a canonical source commit
- recovery baseline commit: 6a0c740858a8e28f8132af88a373b9291b6cdd89

### Candidate source commits
- 592e7c29af4a 2026-09-27T01:10:20Z sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480 bytes=69392 lines=1931 on_history=True matches_declared=False tags=[] | cloud agent: gpt task
- 0c3ac20392bf 2026-09-27T00:52:12Z sha256=1fc165aea2b988ff524c95035f4fdb1fe4ede5219958d04a3cccda239b0adcba bytes=60178 lines=1708 on_history=True matches_declared=False tags=[] | cloud agent: gpt task
- 9d60c7bfedca 2026-09-26T10:52:36+08:00 sha256=b001caebf1193b9bab47d519bc516da92df0c1ce1d83ea3db63b1b21fcebf6c9 bytes=54312 lines=1551 on_history=True matches_declared=False tags=['expected-files-v1-20260926'] | feat: support task-scoped expected files
- 6a0c740858a8 2026-09-26T10:19:56+08:00 sha256=ea298b2eebfb0445086aac85ef5c4988e6d508d2df6bfa0ddfc772429b7aca7c bytes=53736 lines=1542 on_history=True matches_declared=False tags=['production-recovered-3e2fed43-20260926'] | chore: recover production execution worker baseline

## Undeployed-or-unproven source commits
- 592e7c29af4a after_baseline=True | cloud agent: gpt task: repository presence alone is not deployment evidence; no deployment record ties this source commit to the declared production version 3e2fed43
- 0c3ac20392bf after_baseline=True | cloud agent: gpt task: repository presence alone is not deployment evidence; no deployment record ties this source commit to the declared production version 3e2fed43
- 9d60c7bfedca after_baseline=True | feat: support task-scoped expected files: repository presence alone is not deployment evidence; no deployment record ties this source commit to the declared production version 3e2fed43
- 6a0c740858a8 after_baseline=False | chore: recover production execution worker baseline: repository presence alone is not deployment evidence; no deployment record ties this source commit to the declared production version 3e2fed43

## Execution-relevant commits not proven deployed
- dbbbbd13ada2 worker=False workflow=False tracked_task_commit=False | cloud agent: gpt task
- 592e7c29af4a worker=True workflow=False tracked_task_commit=True | cloud agent: gpt task
- 824bd4c41555 worker=False workflow=False tracked_task_commit=True | cloud agent: gpt task
- 0c3ac20392bf worker=True workflow=False tracked_task_commit=True | cloud agent: gpt task
- 698ac2998c67 worker=False workflow=False tracked_task_commit=True | cloud agent: gpt task
- 39949a75ce5d worker=False workflow=False tracked_task_commit=True | cloud agent: gpt task
- ed3ca64977a1 worker=False workflow=True tracked_task_commit=True | fix: extend agent budget and make cancelled results truthful
- 3263e7d47a60 worker=False workflow=False tracked_task_commit=False | cloud agent: gpt task
- 1427442526d4 worker=False workflow=False tracked_task_commit=False | cloud agent: gpt task
- f7218cee6898 worker=False workflow=False tracked_task_commit=False | cloud agent: gpt task
- d506fd5058e0 worker=False workflow=False tracked_task_commit=False | cloud agent: gpt task
- 548170eb05df worker=False workflow=False tracked_task_commit=False | cloud agent: gpt task
- e0f2f2c55b04 worker=False workflow=False tracked_task_commit=False | bootstrap: support safe task-scoped new files and globs
- 9d60c7bfedca worker=True workflow=False tracked_task_commit=False | feat: support task-scoped expected files

## Checks
- [PASS] deployment metadata present: deployment baseline present: worker/PRODUCTION-BASELINE.json
- [PASS] deployment identity identified: service=personal-ai-execution-mcp environment=production version=3e2fed43 (source: worker/PRODUCTION-BASELINE.json)
- [PASS] canonical source present: canonical source present: worker/index.js (sha256=6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480, bytes=69392, lines=1931)
- [BLOCKED] declared production source hash matches a canonical commit: declared production source hash 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 matches no canonical worker/index.js commit (4 candidate commits checked); current HEAD source hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480
- [BLOCKED] canonical source -> deployed runtime relationship: [UNVERIFIED] declared production source hash 8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1 matches no canonical commit of worker/index.js in the repository history; current HEAD source hash is 6a2efaa81d6df0d1e5ffd11931d600bba83e4eb1a3c9e06045d35a133b3ae480; the deployed runtime is not traceable to a canonical source commit
- [BLOCKED] execution-relevant commits proven deployed: 14 execution-relevant commit(s) after the recovered baseline are not proven deployed (source presence != deployment)
- [PASS] no production mutation: read-only audit: no deploy, upload, secret change, D1/KV mutation, workflow mutation or asset mutation performed

## Verdict
DEPLOYED_VERSION=3e2fed43
RELATIONSHIP_STATUS=UNVERIFIED
DEPLOYMENT_IDENTITY_STATUS=VERIFIED
PRODUCTION_MUTATED=False
OVERALL=BLOCKED
