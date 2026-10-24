# r5 merged review candidate

Not deployed; no production approval consumed. Supersedes r4 for PR #10.

## Identity and baselines

- Repository main: `3462f65bc10e6b2d3a84f66a07e3a4a1e1e0bec3` (rechecked before submission).
- Previous PR head: `baa2db6c320eb64c50379ee6fdf7113b5b52aefd`.
- Worker SHA-256: `34690cf4f8d1a941ebf3c6839c0695ee3988ba928d578d8a24001dc3a9514467`.
- Workflow SHA-256: `9aaf708983dfd649821aab8d3b1cf2c7d78b64112cc762a26566992bf1f86a38`.
- Production baseline: `c0feaf4a-60bf-413b-b16f-83dbb8c578ce`, last verified deployment `7e59d337-9873-4c0f-a3c8-16a4be67353d`. This is historical evidence, not a fresh production read.
- User-exported production source original SHA-256: `fd0def790c0b1c1ed11a0f132f71b79192da3e354b1a7786bae31a2259a051e8`; normalized SHA-256 `b9b0d64ce6704db8fa21ccb13169bf2af666c611e8316d656ee516a19fb7c502`. Manual editor export corroborated by version screenshot, not API byte attestation. Original export and r4 are retained separately.

## Merge and safety boundaries

Main remains the source baseline: task metadata bounds and lineage, resolveMode, MCP events, and business status contracts remain. Production unique guardedKnowledgePromote and schema snapshot prefix are byte-identical to the normalized export; the safe Knowledge writer is preserved. Public promotion delegates only to this Gate. Legacy approval strings cannot mint or authorize an approval. No schema, credentials, publisher policy, or authoritative store is added.

Candidate review writes required review evidence and expected asset version into the existing schema. FAIL invalidation follows a successful review CAS inside the same transaction; failed CAS rolls back rather than revoking a newer approval. Submission is conditional on DRAFT. Terminal/reserved candidates fail closed; ambiguous prior writes require reconciliation, not automatic duplicate promotion.

Production OAuth task.read remains restricted to its fixed project and two tools. Issued access and refresh tokens retain task_project. Truncated main KV metadata is resolved from the exact full task record before authorization; it is never treated as proof of project identity.

Execution observation uses existing task registration and GitHub GETs only. Workflow adds only run-name identity binding. Discovery is bounded and paginated, checks repository/workflow/task identity and rerun attempt; missing evidence remains unknown. Source timestamps, observed_at, freshness, business outcome and independent acceptance remain separate. Historical completion never implies Agent idleness. Observation never writes KV/D1, registers tasks or emits completion events.

## Test changes and evidence

Synthetic tests only; no real dispatch, production database or approval was used. Real in-memory SQLite executes the production schema and triggers, including counter/approval binding, expiry, single use, wrong valid candidate, review invalidation and claim races. Historical Python/migration tests remain. Replaced only obsolete Worker ISO-expiry/mock-ledger fixtures; safe writer mocks now answer asset_type, lifecycle fixtures provide review evidence, tool discovery expects the additional read tool, and unrelated ACTIVE literals are no longer treated as writer status.

Independent static review found missing OAuth project claims and review-CAS invalidation, both repaired with regressions. It also requested a real second candidate for approval misbinding and a FAIL injection after Gate pre-read but before claim; both are included.

Latest focused run: 80 passed (pytest across observation wrapper, Knowledge golden pipeline, ledger legacy compatibility, and Skill writer). The observation wrapper executes 57 Node boundary cases. Earlier main compatibility run: 233 passed / 2 outdated Skill fixture assertions, subsequently corrected and covered by the passing focused run. Full CI is authoritative for the final repository result; do not treat these local tests as full CI or business acceptance.

## Release remains blocked

This PR is draft and is not deployment authorization. A later reviewed release must bind the new r5 commit and exact module hash, recheck current production/main, and preserve the unique Human Gate, candidate readback and rollback identity. Publisher stays blocked; r4 authorization must not be reused. Both workflow and Worker must be in the release plan, with workflow identity support installed before relying on early-run lookup. Existing runs without that identity may remain unknown or use verified existing mappings. Rollback must restore the exact previous Worker version and workflow commit; no database migration is included.
