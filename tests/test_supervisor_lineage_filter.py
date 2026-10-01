"""Tests for SUPERVISOR_LINEAGE_FILTER_IMPL_V0.1.

Optional ``project_id`` / ``root_task_id`` / ``parent_task_id`` lineage metadata
on the canonical Task Registry plus an optional ``scope`` on
``list_pending_results`` lets a Supervisor select exactly one active
project/root lineage. The unscoped call is byte-for-byte the historical behavior,
historical records without lineage fail closed into singleton lineages, child
tasks deterministically inherit lineage, and unknown/cyclic parent chains never
cross-associate projects.

The production Worker source (``worker/index.js``) is exercised directly under
Node with a mocked ``TASK_REGISTRY`` KV so the scoped listing is verified in
production source semantics.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from personal_ai_execution import EventSyncRegistry
from personal_ai_execution import event_sync
from personal_ai_execution.event_sync import (
    LINEAGE_KIND_PROJECT,
    LINEAGE_KIND_ROOT,
    lineage_in_scope,
    resolve_lineage,
)
from personal_ai_execution.advancement import dispatch_approved_child

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
NODE = shutil.which("node")

PROJECT_ID = "cloud-assets-activation"


def terminal_result(task_id: str, **overrides) -> dict:
    base = {
        "task_id": task_id,
        "status": "success",
        "tests": "3 passed",
        "summary": "lineage probe",
        "commit": "cafebabe",
        "changed_files": ["worker/index.js"],
    }
    base.update(overrides)
    return base


def synced(registry: EventSyncRegistry, task_id: str, **lineage) -> dict:
    result = terminal_result(task_id, **lineage)
    return registry.sync_terminal_result(
        task_id,
        result,
        "success",
        artifact_present=True,
        commit_present=True,
    )


def pending_ids(registry: EventSyncRegistry, scope=None):
    result = registry.list_pending_results(scope)
    if isinstance(result, dict):
        return [item["task_id"] for item in result["pending"]]
    return [item["task_id"] for item in result]


# -- resolver ---------------------------------------------------------------


def test_lineage_resolver_self_roots_history() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-historical-singleton")
    index = registry._tasks

    kind, key = resolve_lineage(registry._tasks["cf-historical-singleton"], index)
    assert (kind, key) == (LINEAGE_KIND_ROOT, "cf-historical-singleton")

    # A historical singleton is never captured by a current project scope.
    assert not lineage_in_scope(
        registry._tasks["cf-historical-singleton"],
        {"project_id": PROJECT_ID},
        index,
    )


def test_project_and_root_records_resolve_to_their_declared_lineage() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-project", project_id=PROJECT_ID)
    synced(registry, "cf-root", root_task_id="cf-root-anchor")

    assert resolve_lineage(registry._tasks["cf-project"], registry._tasks) == (
        LINEAGE_KIND_PROJECT,
        PROJECT_ID,
    )
    assert resolve_lineage(registry._tasks["cf-root"], registry._tasks) == (
        LINEAGE_KIND_ROOT,
        "cf-root-anchor",
    )


# -- child inheritance ------------------------------------------------------


def test_child_inherits_project_lineage() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-project-parent", project_id=PROJECT_ID)

    calls: list[dict] = []

    def dispatcher(contract):
        calls.append(dict(contract))
        return {"accepted": True}

    result = registry.mark_reviewed(
        "cf-project-parent",
        "PASS",
        "ship the child",
        approved_next_task={
            "goal": "child",
            "instructions": ["do it"],
            "acceptance": ["done"],
            "expected_files": ["worker/index.js"],
        },
        dispatcher=dispatcher,
    )

    assert result["child_dispatch"]["dispatched"] is True
    assert len(calls) == 1
    child = calls[0]
    assert child["parent_task_id"] == "cf-project-parent"
    assert child["project_id"] == PROJECT_ID
    assert child["root_task_id"] == "cf-project-parent"

    # The child joins the parent's project lineage when registered.
    registry.submit_task(child["task_id"], goal="child", **{
        k: child[k]
        for k in ("project_id", "root_task_id", "parent_task_id")
        if k in child
    })
    assert resolve_lineage(registry._tasks[child["task_id"]], registry._tasks) == (
        LINEAGE_KIND_PROJECT,
        PROJECT_ID,
    )


def test_child_inherits_root_lineage_from_unlineaged_parent() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-bare-parent")
    calls: list[dict] = []
    dispatch_approved_child(
        registry._tasks["cf-bare-parent"],
        "cf-bare-parent",
        "PASS",
        {
            "goal": "child",
            "instructions": ["do it"],
            "acceptance": ["done"],
        },
        lambda contract: (calls.append(dict(contract)) or {"accepted": True}),
    )
    child = calls[0]
    assert child["root_task_id"] == "cf-bare-parent"
    assert child["parent_task_id"] == "cf-bare-parent"
    assert resolve_lineage(registry._tasks["cf-bare-parent"], registry._tasks) == (
        LINEAGE_KIND_ROOT,
        "cf-bare-parent",
    )


# -- scoped selection -------------------------------------------------------


def test_scoped_list_excludes_historical_backlog() -> None:
    registry = EventSyncRegistry()
    for i in range(101):
        synced(registry, f"cf-historical-{i:03d}")
    synced(registry, "cf-active", project_id=PROJECT_ID)

    report = registry.list_pending_results({"project_id": PROJECT_ID})

    assert isinstance(report, dict)
    assert [item["task_id"] for item in report["pending"]] == ["cf-active"]
    assert report["pending_review"] == report["pending"]
    assert report["scope"] == {"project_id": PROJECT_ID}
    assert report["excluded_by_lineage"] == 101
    assert report["counts"]["excluded_by_lineage"] == 101


def test_scoped_list_is_deterministic_and_selects_children() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-active-parent", project_id=PROJECT_ID)
    synced(registry, "cf-other", project_id="other-project")
    synced(registry, "cf-active-child", parent_task_id="cf-active-parent")

    report = registry.list_pending_results({"project_id": PROJECT_ID})
    assert [item["task_id"] for item in report["pending"]] == [
        "cf-active-child",
        "cf-active-parent",
    ]
    assert report["excluded_by_lineage"] == 1


def test_unscoped_list_is_backward_compatible() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-part-a", project_id=PROJECT_ID)
    synced(registry, "cf-part-b")
    synced(registry, "cf-part-c", project_id="other")

    unscoped = registry.list_pending_results()
    assert isinstance(unscoped, list)
    assert [item["task_id"] for item in unscoped] == [
        "cf-part-a",
        "cf-part-b",
        "cf-part-c",
    ]

    empty_scope = registry.list_pending_results({})
    assert isinstance(empty_scope, list)
    assert pending_ids(registry, {}) == ["cf-part-a", "cf-part-b", "cf-part-c"]


def test_module_level_scoped_wrapper() -> None:
    registry = event_sync.reset_default_registry()
    synced(registry, "cf-module-historical")
    synced(registry, "cf-module-active", project_id=PROJECT_ID)

    assert event_sync.list_pending_results() != []
    report = event_sync.list_pending_results({"project_id": PROJECT_ID})
    assert [item["task_id"] for item in report["pending"]] == ["cf-module-active"]
    assert report["excluded_by_lineage"] == 1
    event_sync.reset_default_registry()


# -- fail-closed parent walking --------------------------------------------


def test_unknown_parent_fails_closed_to_singleton() -> None:
    registry = EventSyncRegistry()
    registry.submit_task(
        "cf-orphan",
        goal="legacy child with no known parent",
        status="in_progress",
        parent_task_id="cf-ghost-parent",
    )
    kind, key = resolve_lineage(registry._tasks["cf-orphan"], registry._tasks)
    assert (kind, key) == (LINEAGE_KIND_ROOT, "cf-orphan")
    assert not lineage_in_scope(
        registry._tasks["cf-orphan"], {"project_id": PROJECT_ID}, registry._tasks
    )


def test_cyclic_parent_fails_closed_to_singleton() -> None:
    registry = EventSyncRegistry()
    registry.submit_task("cf-cycle-a", goal="a", status="in_progress", parent_task_id="cf-cycle-b")
    registry.submit_task("cf-cycle-b", goal="b", status="in_progress", parent_task_id="cf-cycle-a")

    assert resolve_lineage(registry._tasks["cf-cycle-a"], registry._tasks) == (
        LINEAGE_KIND_ROOT,
        "cf-cycle-a",
    )
    assert resolve_lineage(registry._tasks["cf-cycle-b"], registry._tasks) == (
        LINEAGE_KIND_ROOT,
        "cf-cycle-b",
    )


def test_deep_parent_chain_is_bounded() -> None:
    registry = EventSyncRegistry()
    # A self-referential chain must terminate without looping.
    registry.submit_task("cf-loop", goal="loop", status="in_progress", parent_task_id="cf-loop")
    assert resolve_lineage(registry._tasks["cf-loop"], registry._tasks) == (
        LINEAGE_KIND_ROOT,
        "cf-loop",
    )


# -- Worker source: production semantics ------------------------------------


WORKER_LIST_HARNESS = r"""
const kv = new Map();
function seedTask(task) { kv.set("task:" + task.task_id, JSON.stringify(task)); }
const env = {
  GITHUB_REPO: "owner/repo",
  GITHUB_TOKEN: "test-token",
  TASK_REGISTRY: {
    get: async function(key, type) {
      const raw = kv.has(key) ? kv.get(key) : null;
      if (raw == null) return null;
      return type === "json" ? JSON.parse(raw) : raw;
    },
    put: async function(key, value) { kv.set(key, value); },
    list: async function() {
      return { keys: Array.from(kv.entries()).map(function(entry) {
        return { name: entry[0], metadata: JSON.parse(entry[1]) };
      }) };
    }
  }
};
globalThis.fetch = async function() { throw new Error("unexpected fetch during scoped listing"); };
const TASKS = __TASKS__;
for (const task of TASKS) seedTask(task);
const scoped = await toolListPendingResults(env, { scope: { project_id: "cloud-assets-activation" } });
const unscoped = await toolListPendingResults(env, {});
console.log(JSON.stringify({
  scoped: JSON.parse(scoped.text),
  unscoped: JSON.parse(unscoped.text)
}));
"""


def worker_source() -> str:
    return WORKER_PATH.read_text(encoding="utf-8")


def run_worker_probe(script: str) -> dict:
    if NODE is None:
        pytest.skip("node is not available to execute the worker bundle")
    source = re.sub(r"export\s*\{[^}]*\};?\s*$", "", worker_source())
    probe = source + "\n" + script
    out = subprocess.run(
        [NODE, "--input-type=module", "-e", probe],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def make_task(task_id: str, **overrides) -> dict:
    base = {
        "task_id": task_id,
        "status": "PASS",
        "normalized_status": "PASS",
        "execution_status": "PASS",
        "terminal": True,
        "result_available": True,
        "workflow_verified": True,
        "reviewed": False,
        "review_verdict": None,
        "created_at": "2026-09-27T00:00:00.000Z",
        "updated_at": "2026-09-27T00:00:00.000Z",
    }
    base.update(overrides)
    return base


def test_worker_source_encodes_lineage_filter_tokens() -> None:
    source = worker_source()
    for token in (
        "resolveLineage",
        "lineageInScope",
        "normalizeLineageScope",
        "excluded_by_lineage",
        "root_task_id",
        "project_id",
        "parent_task_id",
    ):
        assert token in source, f"worker is missing lineage token {token}"


def test_worker_scoped_list_filters_and_unscoped_is_unchanged() -> None:
    tasks = [
        make_task("cf-worker-active", project_id=PROJECT_ID),
        make_task("cf-worker-active-child", parent_task_id="cf-worker-active"),
        make_task("cf-worker-historical-a"),
        make_task("cf-worker-historical-b"),
        make_task("cf-worker-other", project_id="other-project"),
    ]
    script = WORKER_LIST_HARNESS.replace("__TASKS__", json.dumps(tasks))
    report = run_worker_probe(script)

    scoped = report["scoped"]
    assert [item["task_id"] for item in scoped["pending"]] == [
        "cf-worker-active",
        "cf-worker-active-child",
    ]
    assert scoped["excluded_by_lineage"] == 3
    assert scoped["scope"] == {"project_id": PROJECT_ID}

    unscoped = report["unscoped"]
    assert [item["task_id"] for item in unscoped["pending"]] == [
        "cf-worker-active",
        "cf-worker-active-child",
        "cf-worker-historical-a",
        "cf-worker-historical-b",
        "cf-worker-other",
    ]
    assert "excluded_by_lineage" not in unscoped
