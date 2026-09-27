-- PERSONAL_AI_AUTONOMOUS_ADVANCEMENT_DISPATCH_IDEMPOTENCY_V0.1
-- Atomic exactly-once marker for the PASS-review -> pre-authorized child
-- dispatch edge. One row exists per reviewed parent task that was allowed to
-- dispatch a child, so a replay / idempotent mark_reviewed can never create a
-- second child.
--
-- Additive only. No existing table, column or row is dropped or rewritten, so
-- the existing ASSET_DB audit history is preserved. This migration is
-- idempotent and non-destructive.
--
-- ---------------------------------------------------------------------------
-- Deploy provenance record
-- goal            : PERSONAL_AI_AUTONOMOUS_ADVANCEMENT_PRODUCTION_DEPLOY_GOLDEN_V0.1
-- task_id         : cf-936b81da5f0d
-- baseline_commit : 0d50b9dd6f1f28bbe2a77324c82406eb1c848ca5
-- PRODUCTION_DEPLOY_STATUS : BLOCKED (fail-closed; no production mutation)
-- CLOUDFLARE_VERSION_ID    : UNAVAILABLE
-- CLOUDFLARE_DEPLOYMENT_ID : UNAVAILABLE
-- D1_MIGRATION_RESULT      : NOT_APPLIED_REMOTE -- no Cloudflare deploy
--                            credential is present in the execution
--                            environment, so no remote D1/Worker write was
--                            attempted; the additive DDL below was verified
--                            in-repo only.
--
-- Verified in-repo for this patch:
--   * task_dispatch_markers table creation (CREATE TABLE IF NOT EXISTS)
--   * idx_task_dispatch_markers_parent, UNIQUE on (parent_task_id)
--   * idx_task_dispatch_markers_child on (child_task_id)
--   * idx_task_dispatch_markers_state on (dispatch_state)
--
-- Golden parent_task_id -> child_task_id dispatch, exactly-once replay and
-- fail-closed FAIL / BLOCKED / missing-child behavior are exercised by
-- tests/test_autonomous_advancement.py (the "tested patch" this task deploys).
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS task_dispatch_markers (
  dispatch_key TEXT PRIMARY KEY,
  parent_task_id TEXT NOT NULL,
  review_verdict TEXT NOT NULL,
  review_timestamp TEXT,
  review_note TEXT,
  child_task_id TEXT NOT NULL,
  dispatch_state TEXT NOT NULL,
  dispatch_status TEXT,
  github_http_status INTEGER,
  github_request_id TEXT,
  dispatched_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_task_dispatch_markers_parent
  ON task_dispatch_markers (parent_task_id);

CREATE INDEX IF NOT EXISTS idx_task_dispatch_markers_child
  ON task_dispatch_markers (child_task_id);

CREATE INDEX IF NOT EXISTS idx_task_dispatch_markers_state
  ON task_dispatch_markers (dispatch_state);
