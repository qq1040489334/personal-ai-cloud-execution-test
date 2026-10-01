"""PERSONAL_AI_DECISION_INGESTION_CONTRACT_V0.1 regression tests.

The read-only DECISION normalization contract maps the decision evidence the
platform already produces into one canonical DECISION record shape:

* the human review verdict (``review_verdict`` / ``verdict``);
* the exactly-once dispatch-marker outcome
  (``review_dispatch.dispatch_state`` / ``task_dispatch_markers.dispatch_state``);
* the ASSET_PROVENANCE_V0.2 promotion decision
  (``promotion.decision`` / ``promotion_decision``);
* the explicit user choice and user outcome.

The contract is fail-closed: a record missing any required component is
``INCOMPLETE``, is never ``VERIFIED``, and reports the exact missing fields.
The alias table reuses the existing vocabulary rather than inventing a second
one, which is asserted here against the provenance and Worker sources.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from personal_ai_execution import decision_contract
from personal_ai_execution.decision_contract import (
    DECISION_CONTRACT_VERSION,
    DECISION_FIELD_ALIASES,
    DECISION_FIELDS,
    DECISION_MATRIX,
    DECISION_STATUSES,
    DISPATCH_OUTCOMES,
    OPTIONAL_DECISION_FIELDS,
    REQUIRED_DECISION_FIELDS,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
    build_decision,
    decision_matrix,
    normalize_decision,
)
from personal_ai_execution.provenance_contract import (
    PROVENANCE_FIELD_ALIASES,
)
from personal_ai_execution.status_contract import REVIEW_VERDICTS

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
MIGRATION_PATH = REPO_ROOT / "worker" / "migrations" / "0002_dispatch_idempotency.sql"


def complete_record() -> dict:
    """A complete DECISION input using the existing nested record shapes."""
    return {
        "task_id": "cf-decision-parent",
        "review_verdict": "PASS",
        "review_dispatch": {
            "parent_task_id": "cf-decision-parent",
            "child_task_id": "cf-decision-child",
            "dispatch_state": "DISPATCHED",
            "dispatch_status": "accepted",
            "reason": "DISPATCHED",
        },
        "promotion": {
            "decision": "PROMOTE",
            "event_id": "promote-42",
            "decided_at": "2026-09-02T00:00:00+00:00",
        },
        "user_choice": "approve_and_continue",
        "user_outcome": "accepted",
        "decided_at": "2026-09-02T00:00:00+00:00",
    }


# -- importability and vocabulary -------------------------------------------


def test_module_and_function_are_importable() -> None:
    assert callable(decision_contract.normalize_decision)
    assert DECISION_CONTRACT_VERSION == "PERSONAL_AI_DECISION_INGESTION_V0.1"
    assert set(DECISION_STATUSES) == {STATUS_VERIFIED, STATUS_INCOMPLETE}
    assert set(REQUIRED_DECISION_FIELDS).issubset(set(DECISION_FIELDS))
    assert set(OPTIONAL_DECISION_FIELDS).issubset(set(DECISION_FIELDS))


def test_required_fields_match_fail_closed_spec() -> None:
    assert REQUIRED_DECISION_FIELDS == (
        "review_verdict",
        "dispatch_outcome",
        "promotion_decision",
        "user_choice",
        "user_outcome",
    )


def test_dispatch_outcomes_reuse_advancement_vocabulary() -> None:
    assert DISPATCH_OUTCOMES == ("PENDING", "DISPATCHED", "FAILED")


# -- complete records --------------------------------------------------------


def test_complete_decision_is_verified() -> None:
    result = normalize_decision(complete_record())

    assert result["status"] == STATUS_VERIFIED
    assert result["complete"] is True
    assert result["verified"] is True
    assert result["missing"] == []
    assert result["invalid"] == []
    assert result["record"]["review_verdict"] == "PASS"
    assert result["record"]["dispatch_outcome"] == "DISPATCHED"
    assert result["record"]["promotion_decision"] == "PROMOTE"
    assert result["record"]["user_choice"] == "approve_and_continue"
    assert result["record"]["user_outcome"] == "accepted"


def test_build_decision_round_trips_to_verified() -> None:
    built = build_decision(
        task_id="cf-built",
        review_verdict="PASS",
        dispatch_outcome="DISPATCHED",
        promotion_decision="PROMOTE",
        user_choice="approve",
        user_outcome="accepted",
        promotion_event="promote-1",
    )
    result = normalize_decision(built)

    assert result["verified"] is True
    assert result["record"]["decision_id"] == "cf-built"
    assert result["record"]["promotion_event"] == "promote-1"


# -- incomplete / fail-closed ------------------------------------------------


@pytest.mark.parametrize("field", REQUIRED_DECISION_FIELDS)
def test_each_missing_required_field_is_incomplete_and_never_verified(
    field: str,
) -> None:
    record = complete_record()
    if field in ("review_verdict", "user_choice", "user_outcome"):
        del record[field]
    elif field == "dispatch_outcome":
        del record["review_dispatch"]
    elif field == "promotion_decision":
        record["promotion"] = {"event_id": "promote-42"}

    result = normalize_decision(record)

    assert result["status"] == STATUS_INCOMPLETE
    assert result["complete"] is False
    assert result["verified"] is False
    assert field in result["missing"]


def test_choice_missing_reports_user_choice() -> None:
    record = complete_record()
    del record["user_choice"]

    result = normalize_decision(record)

    assert result["verified"] is False
    assert result["missing"] == ["user_choice"]


def test_outcome_missing_reports_user_outcome() -> None:
    record = complete_record()
    del record["user_outcome"]

    result = normalize_decision(record)

    assert result["verified"] is False
    assert result["missing"] == ["user_outcome"]


def test_missing_list_is_exact_and_ordered() -> None:
    record = {
        "task_id": "cf-x",
        "review_verdict": "PASS",
        "review_dispatch": {"dispatch_state": "DISPATCHED"},
        # promotion_decision, user_choice and user_outcome absent
    }

    result = normalize_decision(record)

    assert result["missing"] == [
        "promotion_decision",
        "user_choice",
        "user_outcome",
    ]


def test_blank_strings_are_not_meaningful() -> None:
    record = complete_record()
    record["user_choice"] = "   "

    result = normalize_decision(record)

    assert result["verified"] is False
    assert "user_choice" in result["missing"]


def test_unrecognized_verdict_is_not_verified() -> None:
    record = complete_record()
    record["review_verdict"] = "MAYBE"

    result = normalize_decision(record)

    assert result["complete"] is False
    assert result["verified"] is False
    assert "review_verdict" in result["invalid"]


def test_unrecognized_dispatch_outcome_is_not_verified() -> None:
    record = complete_record()
    record["review_dispatch"]["dispatch_state"] = "DROPPED"

    result = normalize_decision(record)

    assert result["complete"] is False
    assert result["verified"] is False
    assert "dispatch_outcome" in result["invalid"]


def test_empty_input_is_incomplete() -> None:
    result = normalize_decision(None)

    assert result["status"] == STATUS_INCOMPLETE
    assert result["verified"] is False
    assert set(result["missing"]) == set(REQUIRED_DECISION_FIELDS)


def test_normalize_does_not_mutate_input() -> None:
    record = complete_record()
    snapshot = {
        "task_id": record["task_id"],
        "review_verdict": record["review_verdict"],
        "dispatch": dict(record["review_dispatch"]),
        "promotion": dict(record["promotion"]),
    }

    normalize_decision(record)

    assert record["task_id"] == snapshot["task_id"]
    assert record["review_verdict"] == snapshot["review_verdict"]
    assert record["review_dispatch"] == snapshot["dispatch"]
    assert record["promotion"] == snapshot["promotion"]


# -- alias table reuses existing vocabulary ---------------------------------


def test_review_verdict_aliases_reuse_existing_field() -> None:
    aliases = DECISION_FIELD_ALIASES["review_verdict"]
    assert "review_verdict" in aliases
    assert "verdict" in aliases


def test_dispatch_outcome_aliases_reuse_existing_markers() -> None:
    aliases = DECISION_FIELD_ALIASES["dispatch_outcome"]
    assert "review_dispatch.dispatch_state" in aliases
    assert "task_dispatch_marker.dispatch_state" in aliases


def test_promotion_aliases_reuse_provenance_vocabulary() -> None:
    decision_aliases = set(DECISION_FIELD_ALIASES["promotion_decision"])
    event_aliases = set(DECISION_FIELD_ALIASES["promotion_event"])

    assert set(PROVENANCE_FIELD_ALIASES["promotion_decision"]).issubset(
        decision_aliases
    )
    assert set(PROVENANCE_FIELD_ALIASES["promotion_event"]).issubset(event_aliases)


def test_flat_legacy_aliases_resolve() -> None:
    record = {
        "task_id": "cf-flat",
        "verdict": "FAIL",
        "dispatch_state": "FAILED",
        "promotion_decision": "REJECT",
        "user_choice": "hold",
        "user_outcome": "rejected",
    }

    result = normalize_decision(record)

    assert result["verified"] is True
    assert result["record"]["review_verdict"] == "FAIL"
    assert result["record"]["dispatch_outcome"] == "FAILED"


# -- reuse of the real production records -----------------------------------


def test_registry_review_record_normalizes() -> None:
    from personal_ai_execution.event_sync import EventSyncRegistry

    parent = "cf-decision-integration"
    registry = EventSyncRegistry()
    registry.sync_terminal_result(
        parent,
        {
            "task_id": parent,
            "status": "success",
            "tests": "3 passed",
            "summary": "decision contract integration",
            "commit": "deadbeef",
            "changed_files": ["src/personal_ai_execution/decision_contract.py"],
        },
        "success",
        artifact_present=True,
        commit_present=True,
    )

    def dispatcher(child):
        return {"accepted": True, "dispatch_status": "accepted"}

    reviewed = registry.mark_reviewed(
        parent,
        "PASS",
        "approved",
        approved_next_task={
            "goal": "child",
            "instructions": ["do it"],
            "acceptance": ["done"],
            "expected_files": ["hello.py"],
        },
        dispatcher=dispatcher,
    )

    decision_input = {
        "task_id": reviewed["task_id"],
        "review_verdict": reviewed["review_verdict"],
        "review_dispatch": reviewed["review_dispatch"],
        "promotion": {"decision": "PROMOTE", "event_id": "promote-9"},
        "user_choice": "approve",
        "user_outcome": "accepted",
    }

    result = normalize_decision(decision_input)

    assert result["verified"] is True
    assert result["record"]["review_verdict"] == "PASS"
    assert result["record"]["dispatch_outcome"] == "DISPATCHED"


def test_worker_and_advancement_markers_exist() -> None:
    worker = WORKER_PATH.read_text(encoding="utf-8")
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "task_dispatch_markers" in worker
    assert "dispatch_state" in worker
    assert "review_verdict" in worker
    assert "dispatch_state" in migration
    assert "review_verdict" in migration


# -- documented matrix -------------------------------------------------------


def test_matrix_documents_every_fail_closed_case() -> None:
    matrix = decision_matrix()
    scenarios = {row["scenario"] for row in matrix}

    assert matrix[0]["status"] == STATUS_VERIFIED
    assert matrix[0]["verified"] is True
    assert any("verdict" in row["required_fields"] for row in matrix[1:])
    assert DECISION_MATRIX is not matrix
    assert len(REVIEW_VERDICTS) == 3
    assert "user choice never captured" in scenarios
    assert "user outcome never captured" in scenarios


def test_doc_exists_and_documents_alias_mapping() -> None:
    doc = REPO_ROOT / "DECISION_INGESTION_CONTRACT_V0.1.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    for token in (
        "review_verdict",
        "task_dispatch_markers",
        "promotion.decision",
        "user_choice",
        "user_outcome",
        "PERSONAL_AI_DECISION_INGESTION_CONTRACT_V0.1",
    ):
        assert token in text
    assert re.search(r"INCOMPLETE", text)
