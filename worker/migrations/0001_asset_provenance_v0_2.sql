-- PERSONAL_AI_ASSET_PROVENANCE_V0.2
-- Canonical Cloud Asset provenance: append-only capture / verification /
-- promotion / supersession evidence, linked to the canonical asset version.
--
-- Additive only. No existing table, column or row is dropped or rewritten, so
-- the existing ASSET_DB audit history (assets, asset_versions, SUBMIT/PROMOTE
-- records) is preserved. This migration is idempotent.

CREATE TABLE IF NOT EXISTS asset_provenance_events (
  event_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  source_identity TEXT,
  source_location TEXT,
  source_version TEXT,
  content_version TEXT,
  source_content_hash TEXT,
  canonical_version INTEGER,
  content_hash TEXT,
  verification_evidence TEXT,
  promotion_decision TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS asset_supersessions (
  superseded_asset_id TEXT NOT NULL,
  superseded_version INTEGER NOT NULL,
  successor_asset_id TEXT NOT NULL,
  successor_version INTEGER,
  reason TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (superseded_asset_id, superseded_version, successor_asset_id)
);

CREATE INDEX IF NOT EXISTS idx_asset_provenance_events_asset
  ON asset_provenance_events (asset_id, version);

CREATE INDEX IF NOT EXISTS idx_asset_provenance_events_type
  ON asset_provenance_events (event_type);

CREATE INDEX IF NOT EXISTS idx_asset_supersessions_successor
  ON asset_supersessions (successor_asset_id);