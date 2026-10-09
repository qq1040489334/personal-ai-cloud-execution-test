-- PERSONAL_AI_KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_V1
-- (task KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_V1 / cf-00bcf790b680)
--
-- Additive migration for the independent Knowledge candidate golden pipeline:
--
--   1. knowledge_candidates  -- independent candidate staging. Distinct from the
--      Golden ``assets`` / ``asset_versions`` tables. A candidate NEVER writes
--      Canonical storage; it only records the raw input, its canonical content
--      hash, the review state and the lifecycle status so a later authorised
--      promotion can be gated and read back.
--
--   2. approval_ledger_operations -- the trusted operation registry. It declares
--      which operations the single approval authority
--      (``personal_ai_approval_ledger``) supports and which canonical writer each
--      operation is allowed to reach. Knowledge promotion is registered as
--      ``KNOWLEDGE_PROMOTION`` and reuses the SAME ledger as ``decision_write``
--      and ``knowledge_write`` -- there is no second approval authority.
--
--   3. personal_ai_approval_ledger -- the one durable, single-use, operation
--      bound approval ledger. A Knowledge promotion approval must bind
--      candidate_id / candidate_version / content_hash / review_result /
--      approved_by / expires_at / operation. Consumption is a conditional
--      compare-and-swap (``... WHERE approval_id = ? AND consumed = 0``) so at
--      most one concurrent consumer can win. ``invalidated`` / ``invalidated_at``
--      record a FAIL-revoked stale approval permanently (revocation is additive:
--      the row is never deleted), and both the gate read and the consume CAS
--      exclude invalidated rows so a revoked approval can never be replayed.
--
-- Additive only and idempotent (CREATE TABLE/INDEX IF NOT EXISTS + INSERT OR
-- IGNORE). It never alters or drops ``assets``, ``asset_versions`` or any
-- existing Knowledge row, and it introduces no write path that bypasses the
-- candidate gate. No production D1 is touched by this file; it is committed for
-- a later, separately authorised production migration.

CREATE TABLE IF NOT EXISTS knowledge_candidates (
  candidate_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  title TEXT,
  status TEXT NOT NULL,
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  provenance TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  review_state TEXT NOT NULL DEFAULT 'NOT_REVIEWED',
  review_result TEXT,
  reviewed_by TEXT,
  reviewed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_knowledge_candidates_status
  ON knowledge_candidates (status);

CREATE INDEX IF NOT EXISTS idx_knowledge_candidates_asset
  ON knowledge_candidates (asset_id);

CREATE TABLE IF NOT EXISTS approval_ledger_operations (
  operation TEXT PRIMARY KEY,
  asset_type TEXT NOT NULL,
  canonical_writer TEXT NOT NULL,
  single_use INTEGER NOT NULL DEFAULT 1,
  replay_guard INTEGER NOT NULL DEFAULT 1
);

INSERT OR IGNORE INTO approval_ledger_operations
  (operation, asset_type, canonical_writer, single_use, replay_guard)
VALUES
  ('decision_write', 'DECISION', 'writeDecisionRecord', 1, 1),
  ('knowledge_write', 'KNOWLEDGE', 'writeKnowledgeCandidate', 1, 1),
  ('KNOWLEDGE_PROMOTION', 'KNOWLEDGE', 'writeKnowledgeCandidate', 1, 1);

CREATE TABLE IF NOT EXISTS personal_ai_approval_ledger (
  approval_id TEXT PRIMARY KEY,
  operation TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  candidate_id TEXT,
  candidate_version INTEGER,
  content_hash TEXT,
  review_result TEXT,
  approved_by TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'REGISTERED',
  consumed INTEGER NOT NULL DEFAULT 0,
  consume_count INTEGER NOT NULL DEFAULT 0,
  invalidated INTEGER NOT NULL DEFAULT 0,
  invalidated_at TEXT,
  created_at TEXT NOT NULL,
  consumed_at TEXT,
  FOREIGN KEY (operation) REFERENCES approval_ledger_operations (operation)
);

CREATE INDEX IF NOT EXISTS idx_approval_ledger_binding
  ON personal_ai_approval_ledger
    (operation, candidate_id, candidate_version, content_hash);

CREATE INDEX IF NOT EXISTS idx_approval_ledger_state
  ON personal_ai_approval_ledger (operation, consumed, invalidated);
