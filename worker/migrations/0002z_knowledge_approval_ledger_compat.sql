-- 0002z_knowledge_approval_ledger_compat.sql
-- KNOWLEDGE_LEDGER_PRODUCTION_COMPAT_REPAIR_V0.2 (OFFLINE, NOT APPLIED)
-- Committed by KNOWLEDGE_LEDGER_COMPAT_CODE_INTEGRATION_V0.3R1
-- (task cf-b92be4c2cc0a / root cf-44b8447f89a1).
--
-- Routing: this file sorts AFTER 0002_dispatch_idempotency.sql and BEFORE
-- 0003_knowledge_candidate_golden_pipeline.sql under the in-order D1 runner,
-- so the pre-existing production ledger is reshaped to the union schema BEFORE
-- 0003's CREATE TABLE IF NOT EXISTS (a no-op) and its two indexes run. No
-- migration history is rewritten and no failed migration is silently skipped.
--
-- PRE-CONDITION (fail-closed, enforced by the runner BEFORE this file):
--   shape(personal_ai_approval_ledger) == LEGACY, i.e. exactly
--   (approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
--    created_at, expires_at, consumed_at) with the UNWIDENED operation CHECK
--   IN ('deploy_worker_version','write_decision_record').
--   UNION  -> runner skips (idempotent).
--   DRIFT / absent -> runner HALTS (no partial mutation).
--
-- Guarantees:
--   * legacy columns/order/type/constraints unchanged; INTEGER epoch timing is
--     NEVER converted to TEXT;
--   * old CHECK is widened by ADDITION of new operation names only;
--   * the legacy WebAuthn single-use CAS on `consumed_at` remains authoritative;
--   * every existing row is copied byte-for-byte; the pre-state is retained as
--     personal_ai_approval_ledger__legacy_backup for byte-for-byte rollback;
--   * exactly one approval ledger / one mint authority (the Site) is preserved.

-- 1. Ensure the trusted operation registry exists and contains ALL operations
--    (legacy + repo) before the FK-bound rebuild, so no existing row is orphaned.
CREATE TABLE IF NOT EXISTS approval_ledger_operations (
  operation        TEXT PRIMARY KEY,
  asset_type       TEXT NOT NULL,
  canonical_writer TEXT NOT NULL,
  single_use       INTEGER NOT NULL DEFAULT 1,
  replay_guard     INTEGER NOT NULL DEFAULT 1
);

INSERT OR IGNORE INTO approval_ledger_operations
  (operation, asset_type, canonical_writer, single_use, replay_guard) VALUES
  ('deploy_worker_version', 'DEPLOY',    'deployWorkerVersion',     1, 1),
  ('write_decision_record', 'DECISION',  'writeDecisionRecord',     1, 1),
  ('decision_write',        'DECISION',  'writeDecisionRecord',     1, 1),
  ('knowledge_write',       'KNOWLEDGE', 'writeKnowledgeCandidate', 1, 1),
  ('KNOWLEDGE_PROMOTION',   'KNOWLEDGE', 'writeKnowledgeCandidate', 1, 1);

-- 2. Union table: legacy columns verbatim + nullable Worker columns.
CREATE TABLE personal_ai_approval_ledger__v2 (
  approval_id          TEXT PRIMARY KEY,
  requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64),
  operation            TEXT NOT NULL CHECK (operation IN (
      'deploy_worker_version','write_decision_record',
      'decision_write','knowledge_write','KNOWLEDGE_PROMOTION')),
  exact_target         TEXT,
  payload_sha256       TEXT,
  created_at           INTEGER,
  expires_at           INTEGER,
  consumed_at          INTEGER,
  asset_type           TEXT,
  candidate_id         TEXT,
  candidate_version    INTEGER,
  content_hash         TEXT,
  review_result        TEXT,
  approved_by          TEXT,
  state                TEXT NOT NULL DEFAULT 'REGISTERED',
  consumed             INTEGER NOT NULL DEFAULT 0,
  consume_count        INTEGER NOT NULL DEFAULT 0,
  invalidated          INTEGER NOT NULL DEFAULT 0,
  invalidated_at       TEXT,
  FOREIGN KEY (operation) REFERENCES approval_ledger_operations (operation)
) STRICT;

-- 3. Copy every legacy row without loss. `consumed` mirrors legacy consumed_at.
INSERT INTO personal_ai_approval_ledger__v2
  (approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
   created_at, expires_at, consumed_at,
   asset_type, candidate_id, candidate_version, content_hash, review_result,
   approved_by, state, consumed, consume_count, invalidated, invalidated_at)
SELECT approval_id, requesting_user_hash, operation, exact_target, payload_sha256,
       created_at, expires_at, consumed_at,
       NULL, NULL, NULL, NULL, NULL,
       NULL,
       CASE WHEN consumed_at IS NULL THEN 'REGISTERED' ELSE 'CONSUMED' END,
       CASE WHEN consumed_at IS NULL THEN 0 ELSE 1 END,
       0, 0, NULL
FROM personal_ai_approval_ledger;

-- 4. Swap, retaining the pre-state for rollback, then create 0003's indexes.
ALTER TABLE personal_ai_approval_ledger RENAME TO personal_ai_approval_ledger__legacy_backup;
ALTER TABLE personal_ai_approval_ledger__v2 RENAME TO personal_ai_approval_ledger;

CREATE INDEX IF NOT EXISTS idx_approval_ledger_binding
  ON personal_ai_approval_ledger (operation, candidate_id, candidate_version, content_hash);
CREATE INDEX IF NOT EXISTS idx_approval_ledger_state
  ON personal_ai_approval_ledger (operation, consumed, invalidated);
