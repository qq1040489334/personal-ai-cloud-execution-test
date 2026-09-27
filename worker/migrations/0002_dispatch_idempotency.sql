-- PERSONAL_AI_AUTONOMOUS_ADVANCEMENT_DISPATCH_IDEMPOTENCY_V0.1
-- Atomic exactly-once marker for the PASS-review -> pre-authorized child
-- dispatch edge. One row exists per reviewed parent task that was allowed to
-- dispatch a child, so a replay / idempotent mark_reviewed can never create a
-- second child.
--
-- Additive only. No existing table, column or row is dropped or rewritten, so
-- the existing ASSET_DB audit history is preserved. This migration is
-- idempotent and non-destructive.

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
