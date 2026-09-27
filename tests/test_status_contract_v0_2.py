"""PERSONAL_AI_STATUS_CONTRACT_V0.2 regression tests.

One authoritative task-status contract must hold across GitHub workflow truth,
Python normalization, Worker responses, EVENT_SYNC and the Task Registry:

* the workflow conclusion is the execution terminal truth;
* success / failure / cancelled cannot disagree with ``get_task_result``;
* the Task Registry is written back to a terminal state instead of staying
  stale as ``submitted``;
* execution status and review verdict are separate concepts;
* historical reconciliation is fail-closed for ambiguous records.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from personal_ai_execution import (
    BLOCKED,
    EXECUTION_STATUSES,
    FAIL,
    PASS,
    PENDING,
    REVIEW_VERDICTS,
    TERMINAL_STATUSES,
    WORKFLOW_CONCLUSION_TO_STATUS,
    EventSyncRegistry,
    canonical_conclusion_status,
    is_terminal_status,
    normalize_lifecycle_status,
    normalize_result,
    separate_review_fields,
    status_contract,
    status_matrix,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"

NODE = shutil.which("node")


# --- Python contract -------------------------------------------------------


def test_conclusion_mapping_is_fail_closed() -> None:
    for conclusion, expected in WORKFLOW_CONCLUSION_TO_STATUS.items():
        assert canonical_conclusion_status(conclusion) == expected
        assert canonical_conclusion_status(conclusion.upper()) == expected
    assert canonical_conclusion_status(None) == BLOCKED
    assert canonical_conclusion_status("") == BLOCKED
    assert canonical_conclusion_status("unrecognized") == BLOCKED


def test_execution_status_vocabulary_is_canonical() -> None:
    assert tuple(EXECUTION_STATUSES) == (PENDING, PASS, FAIL, BLOCKED)
    assert frozenset(TERMINAL_STATUSES) == frozenset({PASS, FAIL, BLOCKED})
    assert is_terminal_status(PASS) is True
    assert is_terminal_status("pAsS") is True
    assert is_terminal_status(PENDING) is False
    # Review verdicts are the same tokens but a separate concept.
    assert tuple(REVIEW_VERDICTS) == (PASS, FAIL, BLOCKED)


@pytest.mark.parametrize(
    "advisory",
    ["submitted", "pending", "queued", "in_progress", "running", "unknown"],
)
def test_advisory_lifecycle_never_success(advisory: str) -> None:
    assert normalize_lifecycle_status(advisory) == PENDING
    assert normalize_lifecycle_status(advisory) != PASS


def test_conclusion_overrides_advisory_status() -> None:
    assert normalize_lifecycle_status("submitted", conclusion="cancelled") == BLOCKED
    assert normalize_lifecycle_status("submitted", conclusion="success") == PASS


def test_status_matrix_is_consistent() -> None:
    matrix = status_matrix()
    assert matrix is not status_contract.STATUS_MATRIX
    for row in matrix:
        assert row["execution_status"] in EXECUTION_STATUSES
        assert row["terminal"] is is_terminal_status(row["execution_status"])
        assert row["review_verdict_separate"] is True
    assert any(row["workflow_conclusion"] is None for row in matrix)


# --- Registry write-back / separation --------------------------------------


def test_get_task_result_writes_back_terminal_state() -> None:
    registry = EventSyncRegistry()
    registry.submit_task("cf-writeback", goal="write-back", status="submitted")
    record = registry._tasks["cf-writeback"]
    record["execution_result_json"] = {"status": "success", "tests": "1 passed"}
    record["workflow_conclusion"] = "cancelled"

    payload = registry.get_task_result("cf-writeback")

    assert payload["status"] == BLOCKED
    assert payload["execution_status"] == BLOCKED
    assert payload["workflow_conclusion"] == "cancelled"
    assert payload["terminal"] is True
    # The registry is no longer stale as submitted.
    assert record["normalized_status"] == BLOCKED
    assert record["terminal"] is True
    pending = registry.list_pending_results()
    assert [item["task_id"] for item in pending] == ["cf-writeback"]
    assert pending[0]["status"] == BLOCKED


def test_get_task_result_is_pending_without_conclusion() -> None:
    registry = EventSyncRegistry()
    registry.submit_task("cf-no-conclusion", status="submitted")
    registry._tasks["cf-no-conclusion"]["execution_result_json"] = {
        "status": "success",
    }

    payload = registry.get_task_result("cf-no-conclusion")

    assert payload["status"] == PENDING
    assert payload["terminal"] is False
    assert payload["conclusion_authoritative"] is False
    assert registry._tasks["cf-no-conclusion"]["terminal"] is False
    assert registry.list_pending_results() == []


def test_execution_status_and_review_verdict_stay_separate() -> None:
    registry = EventSyncRegistry()
    registry.sync_terminal_result(
        "cf-separate", {"status": "success", "tests": "1 passed"}, "failure"
    )

    before = registry.get_task_result("cf-separate")
    assert before["status"] == FAIL
    assert before["review_verdict"] is None

    registry.mark_reviewed("cf-separate", PASS, "human override")
    after = registry.get_task_result("cf-separate")

    # The human verdict never rewrites the machine execution status.
    assert after["status"] == FAIL
    assert after["execution_status"] == FAIL
    assert after["review_verdict"] == PASS
    fields = separate_review_fields(registry._tasks["cf-separate"])
    assert fields["execution_status"] == FAIL
    assert fields["review_verdict"] == PASS


# --- Worker-facing semantics ----------------------------------------------


def worker_source() -> str:
    return WORKER_PATH.read_text(encoding="utf-8")


def test_worker_source_encodes_the_canonical_contract() -> None:
    source = worker_source()
    for token in (
        "EXECUTION_STATUS_PENDING",
        "EXECUTION_STATUS_PASS",
        "EXECUTION_STATUS_FAIL",
        "EXECUTION_STATUS_BLOCKED",
        "WORKFLOW_CONCLUSION_STATUS",
        "TERMINAL_EXECUTION_STATUSES",
        "normalized_status",
        "execution_status",
        "review_verdict",
        "persistTerminalExecution",
    ):
        assert token in source, f"worker is missing contract token {token}"
    # The canonical vocabulary must literally match Python.
    for status in EXECUTION_STATUSES:
        assert f'"{status}"' in source
    for conclusion in WORKFLOW_CONCLUSION_TO_STATUS:
        assert re.search(rf"\b{conclusion}:", source), conclusion


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


def test_worker_contract_matches_python_exactly() -> None:
    report = run_worker_probe(
        """
console.log(JSON.stringify({
  execution_statuses: EXECUTION_STATUSES,
  terminal: TERMINAL_EXECUTION_STATUSES,
  review_verdicts: REVIEW_VERDICTS_CANONICAL,
  conclusion_map: WORKFLOW_CONCLUSION_STATUS,
}));
"""
    )
    assert report["execution_statuses"] == list(EXECUTION_STATUSES)
    assert set(report["terminal"]) == set(TERMINAL_STATUSES)
    assert report["review_verdicts"] == list(REVIEW_VERDICTS)
    assert report["conclusion_map"] == dict(WORKFLOW_CONCLUSION_TO_STATUS)


@pytest.mark.parametrize(
    ("raw_status", "run_conclusion", "run_status", "expected"),
    [
        ("success", "success", "completed", PASS),
        ("success", "failure", "completed", FAIL),
        ("success", "cancelled", "completed", BLOCKED),
        ("success", "timed_out", "completed", BLOCKED),
        ("failure", "success", "completed", FAIL),
        ("success", "success", "in_progress", PENDING),
        ("success", "mystery", "completed", BLOCKED),
    ],
)
def test_worker_verified_status_agrees_with_python(
    raw_status: str, run_conclusion: str, run_status: str, expected: str
) -> None:
    report = run_worker_probe(
        f"""
const result = verifiedResultStatus(
  {json.dumps(raw_status)},
  {{ status: {json.dumps(run_status)}, conclusion: {json.dumps(run_conclusion)} }}
);
console.log(JSON.stringify({{ result }}));
"""
    )
    assert report["result"] == expected
    if run_status != "completed":
        assert report["result"] == PENDING
        return
    # The Worker must agree with the Python normalization for the same inputs.
    authoritative = normalize_result({"status": raw_status}, run_conclusion)
    assert report["result"] == authoritative["status"]


def test_worker_mark_reviewed_gate_and_separation() -> None:
    report = run_worker_probe(
        """
const store = new Map();
const env = {
  TASK_REGISTRY: {
    async get(key) { const v = store.get(key); return v === undefined ? null : JSON.parse(v); },
    async put(key, value) { store.set(key, value); },
    async list() { return { keys: [...store.keys()].map((name) => ({ name, metadata: JSON.parse(store.get(name)) })) }; }
  }
};
store.set("task:cf-1", JSON.stringify({
  task_id: "cf-1", status: "PENDING", normalized_status: "PENDING",
  terminal: false, result_available: false
}));
const denied = await toolMarkReviewed(env, { task_id: "cf-1", verdict: "PASS" });

store.set("task:cf-2", JSON.stringify({
  task_id: "cf-2", status: "FAIL", normalized_status: "FAIL",
  terminal: true, result_available: true
}));
const accepted = await toolMarkReviewed(env, { task_id: "cf-2", verdict: "PASS" });
const stored = JSON.parse(store.get("task:cf-2"));

const persisted = { };
await persistTerminalExecution(env, "cf-3", {
  status: "BLOCKED", normalized_status: "BLOCKED", terminal: true,
  result_available: true, workflow_conclusion: "cancelled"
});
const written = JSON.parse(store.get("task:cf-3"));

console.log(JSON.stringify({
  denied: denied.isError,
  accepted: accepted.isError,
  review_verdict: stored.review_verdict,
  execution_status: stored.status,
  persisted_status: written.normalized_status,
  persisted_terminal: written.terminal,
}));
"""
    )
    assert report["denied"] is True
    assert report["accepted"] is False
    assert report["review_verdict"] == "PASS"
    # The verdict does not overwrite the execution status.
    assert report["execution_status"] == "FAIL"
    assert report["persisted_status"] == "BLOCKED"
    assert report["persisted_terminal"] is True
