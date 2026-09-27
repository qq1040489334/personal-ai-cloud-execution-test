"""PERSONAL_AI_ASSET_PROVENANCE_V0.2 regression tests.

The Cloud Asset canonical provenance contract links every canonical asset
version to its source identity/location, source/content version, canonical
version, content hash, verification evidence, promotion decision/event,
timestamps and supersession lineage.

The contract is fail-closed:

* a complete, hash-consistent record is ``VERIFIED``;
* a record missing any required field is ``INCOMPLETE`` and is never verified;
* a record whose content hash disagrees with its verification evidence is
  ``HASH_MISMATCH`` and is never verified;
* historical incomplete records are explicitly represented (with the exact
  missing field list) and are never silently treated as verified.

The Python contract and the deployed Worker read path (``get_asset`` /
``search_assets``) implement the same field/alias tables and evaluation.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from personal_ai_execution import (
    PROVENANCE_CONTRACT_VERSION,
    PROVENANCE_FIELD_ALIASES,
    PROVENANCE_FIELDS,
    PROVENANCE_STATUSES,
    REQUIRED_PROVENANCE_FIELDS,
    STATUS_HASH_MISMATCH,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
    build_provenance,
    evaluate_provenance,
    provenance_matrix,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
MIGRATION_PATH = REPO_ROOT / "worker" / "migrations" / "0001_asset_provenance_v0_2.sql"

NODE = shutil.which("node")


def base_provenance() -> dict:
    return {
        "source": {
            "identity": "wechat:conversation:42",
            "location": "cloud://inbox/wechat/42",
        },
        "source_version": "src-2026-09-01",
        "content_version": "content-v3",
        "source_content_hash": "sha256:111111",
        "canonical_version": 7,
        "content_hash": "sha256:abc123",
        "verification": {
            "method": "recompute_content_hash",
            "evidence": {"checked_by": "gate2", "recomputed": "abc123"},
            "verified_at": "2026-09-02T00:00:00+00:00",
            "expected_content_hash": "sha256:abc123",
            "content_hash_matches": True,
        },
        "promotion": {
            "decision": "PROMOTE",
            "event_id": "promote-7",
            "decided_at": "2026-09-02T00:00:00+00:00",
            "actor": "owner",
        },
        "captured_at": "2026-09-01T00:00:00+00:00",
        "promoted_at": "2026-09-02T00:00:00+00:00",
        "supersedes": ["6"],
        "superseded_by": None,
    }


# --- Contract vocabulary ---------------------------------------------------


def test_contract_vocabulary_is_canonical() -> None:
    assert PROVENANCE_CONTRACT_VERSION == "PERSONAL_AI_ASSET_PROVENANCE_V0.2"
    assert tuple(PROVENANCE_STATUSES) == (
        STATUS_VERIFIED,
        STATUS_INCOMPLETE,
        STATUS_HASH_MISMATCH,
    )
    assert set(REQUIRED_PROVENANCE_FIELDS) <= set(PROVENANCE_FIELDS)
    for field in (
        "source_identity",
        "source_location",
        "source_version",
        "content_version",
        "canonical_version",
        "content_hash",
        "verification_evidence",
        "promotion_decision",
        "promotion_event",
        "captured_at",
        "promoted_at",
    ):
        assert field in REQUIRED_PROVENANCE_FIELDS
        assert PROVENANCE_FIELD_ALIASES[field]


def test_provenance_matrix_is_consistent() -> None:
    from personal_ai_execution import provenance_contract

    rows = provenance_matrix()
    assert rows is not provenance_contract.PROVENANCE_MATRIX
    assert rows == tuple(dict(row) for row in provenance_contract.PROVENANCE_MATRIX)
    for row in rows:
        assert row["status"] in PROVENANCE_STATUSES
        assert row["verified"] is False or row["complete"] is True
        if row["status"] == STATUS_VERIFIED:
            assert row["complete"] is True and row["verified"] is True
        else:
            assert row["verified"] is False
    assert any(row["status"] == STATUS_HASH_MISMATCH for row in rows)
    assert any(row["status"] == STATUS_INCOMPLETE for row in rows)


# --- Complete provenance ---------------------------------------------------


def test_complete_provenance_is_verified() -> None:
    provenance = build_provenance(
        source_identity="wechat:conversation:42",
        source_location="cloud://inbox/wechat/42",
        source_version="src-1",
        content_version="content-1",
        canonical_version=7,
        content_hash="sha256:abc123",
        source_content_hash="sha256:111111",
        verification_evidence={"method": "recompute_content_hash"},
        promotion_decision="PROMOTE",
        promotion_event="promote-7",
        captured_at="2026-09-01T00:00:00+00:00",
        promoted_at="2026-09-02T00:00:00+00:00",
        supersedes=["6"],
    )

    report = evaluate_provenance(provenance, content_hash="sha256:abc123")

    assert report["status"] == STATUS_VERIFIED
    assert report["complete"] is True
    assert report["verified"] is True
    assert report["missing"] == []
    assert report["hash_checked"] is True
    assert report["hash_match"] is True
    assert report["fields"]["promotion_event"] == "promote-7"
    assert report["fields"]["canonical_version"] == 7
    assert report["lineage"]["supersedes"] == ["6"]


def test_complete_provenance_with_expected_hash_in_verification_only() -> None:
    report = evaluate_provenance(base_provenance())
    assert report["status"] == STATUS_VERIFIED
    assert report["verified"] is True
    assert report["hash_match"] is True


# --- Fail-closed incompleteness -------------------------------------------


def remove_path(mapping: dict, path: str) -> None:
    parts = path.split(".")
    current: object = mapping
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict):
        current.pop(parts[-1], None)


@pytest.mark.parametrize("removed", REQUIRED_PROVENANCE_FIELDS)
def test_missing_required_field_is_incomplete_and_never_verified(removed: str) -> None:
    provenance = json.loads(json.dumps(base_provenance()))
    for alias in PROVENANCE_FIELD_ALIASES[removed]:
        remove_path(provenance, alias)

    report = evaluate_provenance(provenance, content_hash="sha256:abc123")

    assert report["status"] == STATUS_INCOMPLETE
    assert report["complete"] is False
    # Incomplete provenance is never silently treated as verified.
    assert report["verified"] is False
    assert removed in report["missing"]


def test_missing_verification_evidence_is_incomplete() -> None:
    provenance = base_provenance()
    provenance["verification"] = {"method": "recompute_content_hash"}

    report = evaluate_provenance(provenance, content_hash="sha256:abc123")

    assert report["status"] == STATUS_INCOMPLETE
    assert report["verified"] is False
    assert "verification_evidence" in report["missing"]


def test_missing_promotion_linkage_is_incomplete() -> None:
    provenance = base_provenance()
    provenance["promotion"] = {"decision": "PROMOTE"}

    report = evaluate_provenance(provenance, content_hash="sha256:abc123")

    assert report["status"] == STATUS_INCOMPLETE
    assert report["verified"] is False
    assert "promotion_event" in report["missing"]


# --- Hash integrity --------------------------------------------------------


def test_hash_mismatch_fails_closed() -> None:
    provenance = base_provenance()
    provenance["content_hash"] = "sha256:deadbeef"

    report = evaluate_provenance(provenance, content_hash="sha256:abc123")

    assert report["status"] == STATUS_HASH_MISMATCH
    assert report["verified"] is False
    assert report["hash_checked"] is True
    assert report["hash_match"] is False
    # Structurally complete but explicitly not verified.
    assert report["complete"] is True


def test_explicit_verification_hash_mismatch_fails_closed() -> None:
    provenance = base_provenance()
    provenance["verification"]["content_hash_matches"] = False

    report = evaluate_provenance(provenance)

    assert report["status"] == STATUS_HASH_MISMATCH
    assert report["verified"] is False


def test_hash_prefix_and_case_are_normalized() -> None:
    provenance = base_provenance()
    provenance["content_hash"] = "ABC123"

    report = evaluate_provenance(provenance, content_hash="sha256:abc123")

    assert report["status"] == STATUS_VERIFIED


# --- Historical / legacy records ------------------------------------------


def test_legacy_flat_provenance_aliases_resolve() -> None:
    legacy = {
        "source_id": "legacy-src",
        "source_uri": "cloud://legacy",
        "source_version": "v1",
        "content_version": "cv1",
        "version": 3,
        "hash": "sha256:aaa",
        "evidence": {"method": "manual_attestation"},
        "decision": "PROMOTE",
        "promotion_event_id": "evt-legacy",
        "source_timestamp": "2026-01-01T00:00:00+00:00",
        "promotion": {"timestamp": "2026-01-02T00:00:00+00:00"},
        "supersedes": ["2"],
    }

    report = evaluate_provenance(legacy, content_hash="sha256:aaa")

    assert report["status"] == STATUS_VERIFIED
    assert report["verified"] is True
    assert report["fields"]["source_identity"] == "legacy-src"
    assert report["fields"]["canonical_version"] == 3
    assert report["lineage"]["supersedes"] == ["2"]


def test_historical_incomplete_record_is_explicit_and_not_verified() -> None:
    historical = {"content_hash": "sha256:abc123", "source_id": "old-import"}

    report = evaluate_provenance(historical, content_hash="sha256:abc123", canonical_version=1)

    assert report["status"] == STATUS_INCOMPLETE
    assert report["complete"] is False
    assert report["verified"] is False
    assert "verification_evidence" in report["missing"]
    assert "promotion_decision" in report["missing"]
    assert "promotion_event" in report["missing"]
    # No metadata was fabricated: only the historical fields are echoed back.
    assert report["fields"]["source_identity"] == "old-import"
    assert report["fields"]["promotion_event"] is None


def test_empty_or_missing_provenance_is_incomplete() -> None:
    for empty in (None, {}, "not-a-mapping"):
        report = evaluate_provenance(empty, content_hash="sha256:abc123")
        assert report["status"] == STATUS_INCOMPLETE
        assert report["verified"] is False
        assert set(REQUIRED_PROVENANCE_FIELDS) <= set(report["missing"])


def test_separate_verification_column_links_evidence() -> None:
    provenance = base_provenance()
    provenance.pop("verification")

    report = evaluate_provenance(
        provenance,
        content_hash="sha256:abc123",
        verification={
            "evidence": {"method": "recompute_content_hash"},
            "expected_content_hash": "sha256:abc123",
        },
    )

    assert report["status"] == STATUS_VERIFIED
    assert report["verified"] is True


def test_supersession_lineage_is_preserved_where_applicable() -> None:
    provenance = base_provenance()
    provenance["supersedes"] = ["5", "6"]
    provenance["superseded_by"] = 8

    report = evaluate_provenance(provenance, content_hash="sha256:abc123")

    assert report["lineage"] == {"supersedes": ["5", "6"], "superseded_by": 8}


# --- Worker parity ---------------------------------------------------------


def worker_source() -> str:
    return WORKER_PATH.read_text(encoding="utf-8")


def test_worker_source_encodes_provenance_contract() -> None:
    source = worker_source()
    for token in (
        "PERSONAL_AI_ASSET_PROVENANCE_V0.2",
        "evaluateAssetProvenance",
        "PROVENANCE_FIELD_ALIASES",
        "REQUIRED_PROVENANCE_FIELDS",
        "provenance_completeness",
        "historical_provenance_incomplete",
        "promotion_event",
        "verification_evidence",
    ):
        assert token in source, f"worker is missing provenance token {token}"


def run_worker_probe(script: str) -> dict:
    if NODE is None:
        pytest.skip("node is not available to execute the worker bundle")
    source = worker_source()
    source = re.sub(r"export\s*\{[^}]*\};?\s*$", "", source)
    probe = source + "\n" + script
    out = subprocess.run(
        [NODE, "--input-type=module", "-e", probe],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_worker_provenance_tables_match_python_exactly() -> None:
    report = run_worker_probe(
        """
console.log(JSON.stringify({
  contract: ASSET_PROVENANCE_CONTRACT,
  statuses: [PROVENANCE_STATUS_VERIFIED, PROVENANCE_STATUS_INCOMPLETE, PROVENANCE_STATUS_HASH_MISMATCH],
  fields: PROVENANCE_FIELDS,
  required: REQUIRED_PROVENANCE_FIELDS,
  aliases: PROVENANCE_FIELD_ALIASES,
}));
"""
    )
    assert report["contract"] == PROVENANCE_CONTRACT_VERSION
    assert report["statuses"] == list(PROVENANCE_STATUSES)
    assert report["fields"] == list(PROVENANCE_FIELDS)
    assert report["required"] == list(REQUIRED_PROVENANCE_FIELDS)
    assert report["aliases"] == {
        field: list(aliases) for field, aliases in PROVENANCE_FIELD_ALIASES.items()
    }


PROVENANCE_CASES = {
    "complete": (base_provenance(), "sha256:abc123", None),
    "incomplete": (
        {"source": "old-import", "content_hash": "sha256:abc123"},
        "sha256:abc123",
        None,
    ),
    "hash_mismatch": (
        {**base_provenance(), "content_hash": "sha256:deadbeef"},
        "sha256:abc123",
        None,
    ),
    "explicit_mismatch": (
        {
            **base_provenance(),
            "verification": {**base_provenance()["verification"], "content_hash_matches": False},
        },
        None,
        None,
    ),
    "separate_verification": (
        {key: value for key, value in base_provenance().items() if key != "verification"},
        "sha256:abc123",
        {"evidence": {"method": "recompute_content_hash"}, "expected_content_hash": "sha256:abc123"},
    ),
    "lineage": (
        {**base_provenance(), "supersedes": ["5", "6"], "superseded_by": 8},
        "sha256:abc123",
        None,
    ),
}


@pytest.mark.parametrize("case", sorted(PROVENANCE_CASES))
def test_worker_provenance_evaluation_agrees_with_python(case: str) -> None:
    provenance, content_hash, verification = PROVENANCE_CASES[case]

    report = run_worker_probe(
        f"""
const report = evaluateAssetProvenance(
  {json.dumps(provenance)},
  {{ content_hash: {json.dumps(content_hash)}, verification: {json.dumps(verification)}, canonical_version: 1 }}
);
console.log(JSON.stringify(report));
"""
    )
    expected = evaluate_provenance(
        provenance,
        content_hash=content_hash,
        verification=verification,
        canonical_version=1,
    )

    for key in ("status", "complete", "verified", "missing", "hash_checked", "hash_match", "lineage"):
        assert report[key] == expected[key], f"{case}: {key} disagrees with Python"


def test_worker_get_asset_reports_incomplete_historical_provenance() -> None:
    row = {
        "asset_id": "asset-legacy",
        "asset_type": "KNOWLEDGE",
        "schema_version": "v0.1",
        "title": "legacy import",
        "status": "ACTIVE",
        "current_version": 1,
        "content_hash": "sha256:abc123",
        "updated_at": "2026-01-01T00:00:00Z",
        "content": json.dumps({"text": "legacy"}),
        "provenance": json.dumps({"source": "old-import", "content_hash": "sha256:abc123"}),
        "verification": None,
    }
    probe = (
        "const row = __ROW__;\n"
        "const env = { ASSET_DB: { prepare: function() { return { bind: function() {"
        " return { first: async function() { return row; } }; } }; } } };\n"
        "const outcome = await toolGetAsset(env, { asset_id: __ASSET_ID__ });\n"
        "console.log(JSON.stringify(outcome.structuredContent));\n"
    )
    report = run_worker_probe(
        probe.replace("__ROW__", json.dumps(row)).replace(
            "__ASSET_ID__", json.dumps("asset-legacy")
        )
    )

    assert report["asset_id"] == "asset-legacy"
    assert report["provenance_status"] == STATUS_INCOMPLETE
    assert report["provenance_verified"] is False
    assert report["historical_provenance_incomplete"] is True
    completeness = report["provenance_completeness"]
    assert completeness["complete"] is False
    assert completeness["verified"] is False
    assert "promotion_event" in completeness["missing"]
    # No fabricated evidence for the historical record.
    assert report["verification"] is None
    assert report["provenance"]["source"] == "old-import"
    assert report["provenance"].get("promotion_event") is None


def test_worker_get_asset_returns_verified_complete_provenance() -> None:
    provenance = base_provenance()
    row = {
        "asset_id": "asset-complete",
        "asset_type": "KNOWLEDGE",
        "schema_version": "wechat-conversation-snapshot-v0.1",
        "title": "complete",
        "status": "ACTIVE",
        "current_version": 7,
        "content_hash": "sha256:abc123",
        "updated_at": "2026-09-02T00:00:00Z",
        "content": json.dumps({"text": "complete"}),
        "provenance": json.dumps(provenance),
        "verification": json.dumps(provenance["verification"]),
    }
    probe = (
        "const row = __ROW__;\n"
        "const env = { ASSET_DB: { prepare: function() { return { bind: function() {"
        " return { first: async function() { return row; } }; } }; } } };\n"
        "const outcome = await toolGetAsset(env, { asset_id: __ASSET_ID__ });\n"
        "console.log(JSON.stringify(outcome.structuredContent));\n"
    )
    report = run_worker_probe(
        probe.replace("__ROW__", json.dumps(row)).replace(
            "__ASSET_ID__", json.dumps("asset-complete")
        )
    )

    assert report["provenance_status"] == STATUS_VERIFIED
    assert report["provenance_verified"] is True
    assert report["historical_provenance_incomplete"] is False
    completeness = report["provenance_completeness"]
    assert completeness["complete"] is True
    assert completeness["missing"] == []
    assert completeness["fields"]["promotion_event"] == "promote-7"
    assert completeness["lineage"]["supersedes"] == ["6"]
    # The existing read path still returns provenance and canonical content.
    assert report["provenance"]["promotion"]["event_id"] == "promote-7"
    assert report["content"] == {"text": "complete"}


def test_worker_search_assets_exposes_provenance_status() -> None:
    provenance = base_provenance()
    rows = [
        {
            "asset_id": "asset-complete",
            "asset_type": "KNOWLEDGE",
            "schema_version": "v0.1",
            "title": "complete",
            "status": "ACTIVE",
            "current_version": 7,
            "content_hash": "sha256:abc123",
            "updated_at": "2026-09-02T00:00:00Z",
            "content": json.dumps({"text": "complete"}),
            "provenance": json.dumps(provenance),
            "verification": json.dumps(provenance["verification"]),
        },
        {
            "asset_id": "asset-legacy",
            "asset_type": "KNOWLEDGE",
            "schema_version": "v0.1",
            "title": "legacy",
            "status": "ACTIVE",
            "current_version": 1,
            "content_hash": "sha256:abc123",
            "updated_at": "2026-01-01T00:00:00Z",
            "content": json.dumps({"text": "legacy"}),
            "provenance": json.dumps({"source": "old-import"}),
            "verification": None,
        },
    ]
    probe = (
        "const rows = __ROWS__;\n"
        "const env = { ASSET_DB: { prepare: function() { return { bind: function() {"
        " return { all: async function() { return { results: rows }; } }; } }; } } };\n"
        "const outcome = await toolSearchAssets(env, { limit: 10 });\n"
        "console.log(JSON.stringify(outcome.structuredContent));\n"
    )
    report = run_worker_probe(probe.replace("__ROWS__", json.dumps(rows)))

    assets = {asset["asset_id"]: asset for asset in report["assets"]}
    assert assets["asset-complete"]["provenance_status"] == STATUS_VERIFIED
    assert assets["asset-complete"]["provenance_verified"] is True
    assert assets["asset-complete"]["provenance"]["promotion_event"] == "promote-7"
    assert assets["asset-legacy"]["provenance_status"] == STATUS_INCOMPLETE
    assert assets["asset-legacy"]["provenance_verified"] is False
    assert assets["asset-legacy"]["provenance_complete"] is False
    assert "verification_evidence" in assets["asset-legacy"]["provenance_missing"]


# --- Migration / no weakening ---------------------------------------------


def test_migration_is_additive_and_creates_provenance_tables() -> None:
    assert MIGRATION_PATH.is_file()
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "asset_provenance_events" in sql
    assert "asset_supersessions" in sql
    assert "CREATE TABLE IF NOT EXISTS" in sql
    assert "CREATE INDEX IF NOT EXISTS" in sql
    upper = sql.upper()
    for destructive in ("DROP TABLE", "DROP COLUMN", "DELETE FROM", "TRUNCATE"):
        assert destructive not in upper


def test_provenance_never_weakens_status_gates() -> None:
    from personal_ai_execution import (
        WORKFLOW_CONCLUSION_TO_STATUS,
        canonical_conclusion_status,
    )

    # Gate-relevant fail-closed behaviour is untouched by the provenance work.
    assert canonical_conclusion_status(None) == "BLOCKED"
    assert canonical_conclusion_status("unrecognized") == "BLOCKED"
    assert WORKFLOW_CONCLUSION_TO_STATUS["success"] == "PASS"
    assert WORKFLOW_CONCLUSION_TO_STATUS["cancelled"] == "BLOCKED"
    # Provenance verification is not an execution status.
    assert STATUS_VERIFIED not in WORKFLOW_CONCLUSION_TO_STATUS.values()