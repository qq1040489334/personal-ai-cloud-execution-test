# PERSONAL_AI_ASSET_PROVENANCE_V0.2

Canonical Cloud Asset provenance: one documented contract that links every
canonical asset version to its origin, version, hash, verification evidence,
promotion event and supersession lineage -- queryable and auditable end to end
without weakening any existing governance gate.

- Task id: `cf-f50188360f3c`
- Risk level: `LOW`
- Canonical Python module: `src/personal_ai_execution/provenance_contract.py`
- Worker read path: `worker/index.js` (`evaluateAssetProvenance`, `get_asset`,
  `search_assets`)
- Additive schema: `worker/migrations/0001_asset_provenance_v0_2.sql`

## 1. Canonical provenance contract

A provenance record is stored on the canonical asset version
(`asset_versions.provenance`, with the separate `asset_versions.verification`
column accepted as a fallback). The contract fields are:

| Field | Meaning | Required |
| --- | --- | --- |
| `source_identity` | stable identity of the origin (e.g. `wechat:conversation:42`) | yes |
| `source_location` | where the source lives (URI); local paths are redacted on read | yes |
| `source_version` | version/revision of the source record | yes |
| `content_version` | version of the source content that was captured | yes |
| `canonical_version` | the `asset_versions.version` this provenance belongs to | yes |
| `content_hash` | hash of the canonicalized content that was promoted | yes |
| `source_content_hash` | hash of the source content as captured | no |
| `verification_evidence` | how the asset was checked and the recorded evidence | yes |
| `promotion_decision` | explicit promotion decision (e.g. `PROMOTE`) | yes |
| `promotion_event` | append-only promotion event id | yes |
| `captured_at` | when the source was captured | yes |
| `promoted_at` | when the asset was promoted | yes |
| `supersedes` | version(s)/asset(s) this version replaces | where applicable |
| `superseded_by` | version/asset that replaces this version | where applicable |

Aliases let historical records (flat or nested, with legacy names such as
`source_id`, `source_uri`, `hash`, `decision`, `promotion_event_id`) be read
without inventing any metadata. The Python and Worker alias tables are asserted
identical by a regression test.

## 2. Fail-closed verification

`evaluate_provenance` / `evaluateAssetProvenance` return an explicit
`provenance_completeness` object (`status`, `complete`, `verified`, `missing`,
`fields`, `hash_checked`, `hash_match`, `lineage`, `reason`). The decision matrix:

| Scenario | Required fields | Hash | Status | Verified |
| --- | --- | --- | --- | --- |
| complete provenance, content hash agrees | all present | match | `VERIFIED` | yes |
| historical record missing verification evidence | `verification_evidence` absent | n/a | `INCOMPLETE` | no |
| content hash disagrees with verification evidence | all present | mismatch | `HASH_MISMATCH` | no |
| promotion decision/event never recorded | `promotion_decision`/`promotion_event` absent | n/a | `INCOMPLETE` | no |
| supersession lineage recorded | all present | match | `VERIFIED` | yes |

Rules:

- A record missing any required field is `INCOMPLETE`, **never** verified, and
  reports the exact missing field list.
- A record whose `content_hash` disagrees with the recorded verification
  evidence (or whose verification explicitly reports `content_hash_matches:
  false`) is `HASH_MISMATCH` and is **never** verified.
- `verification_evidence` must be explicit; a lone `content_hash_matches` flag is
  not treated as evidence.
- No verification evidence is ever fabricated for a historical asset: only the
  fields actually present are echoed back.
- Hash comparison is fail-closed across `content_hash`, the asset row
  `assets.content_hash`, and the recorded expected hash.

## 3. Queryable through the existing read path

No parallel source of truth is introduced. Provenance is exposed through the
existing canonical asset interfaces:

| Surface | Provenance behaviour |
| --- | --- |
| `get_asset` | returns the full `provenance`, the separate `verification`, and `provenance_completeness`; adds `provenance_status`, `provenance_verified`, and `historical_provenance_incomplete`. |
| `search_assets` | joins the current `asset_versions` row and returns `provenance_status`, `provenance_complete`, `provenance_verified`, `provenance_missing`, the resolved `provenance` fields, and `provenance_lineage`. |

`historical_provenance_incomplete` is `true` exactly when the provenance is
structurally incomplete, making the distinction between "never recorded" and
"recorded but failing integrity" explicit and queryable.

## 4. Additive schema (no history deleted)

`worker/migrations/0001_asset_provenance_v0_2.sql` is additive and idempotent:

- `asset_provenance_events` -- append-only capture / verification / promotion
  evidence keyed by `(asset_id, version)`;
- `asset_supersessions` -- supersession lineage between asset versions.

No existing table, column or row is dropped or rewritten, so the existing
`assets` / `asset_versions` audit history (SUBMIT/PROMOTE records) is preserved.

## 5. No weakening of gates 1-5

- `.github/workflows/` is untouched.
- `scripts/task_contract.py` (Gate 1), `scripts/plan_gate.py` (Gate 1b),
  `scripts/scope_guard.py` (Gate 2) and `scripts/secret_guard.py` (Gate 3) are
  untouched.
- Provider authentication, scope, expected-files and secret-leak gates are
  unchanged.
- Provenance verification is a **new, separate** concept; it never becomes an
  execution status and never changes the `WORKFLOW_CONCLUSION_TO_STATUS`
  fail-closed mapping.

## 6. Tests and evidence

Focused suite: `tests/test_asset_provenance_v0_2.py` (38 tests) covering:

- contract vocabulary and the documented provenance matrix;
- complete provenance verified;
- every required field missing -> `INCOMPLETE` and never verified;
- missing promotion linkage;
- hash mismatch (declared and explicit `content_hash_matches: false`);
- hash prefix/case normalization;
- legacy flat aliases and separate verification column;
- historical incomplete records explicitly reported, no fabricated metadata;
- supersession lineage preservation;
- Worker/Python alias-table and evaluation parity;
- Worker `get_asset` / `search_assets` provenance status for complete and
  historical records;
- migration is additive (no `DROP`/`DELETE`).

Full regression suite:

```
442 passed in 56.79s
```

Command: `python -m pytest -q`

## 7. Changed files

- `src/personal_ai_execution/provenance_contract.py` (new)
- `src/personal_ai_execution/__init__.py`
- `worker/index.js`
- `worker/migrations/0001_asset_provenance_v0_2.sql` (new)
- `tests/test_asset_provenance_v0_2.py` (new)
- `ASSET_PROVENANCE_CONTRACT_V0.2.md` (new)

## Verdict: PASS

Cloud Asset canonical provenance is now complete, queryable and auditable
end to end: complete assets expose linked source/version/hash/verification/
promotion/supersession evidence through the existing `get_asset` and
`search_assets` paths, and incomplete or hash-mismatched historical records are
explicitly represented and never silently treated as verified.
