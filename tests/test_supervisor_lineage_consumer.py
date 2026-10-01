"""Tests for SUPERVISOR_LINEAGE_CONSUMER_WIRING_V0.1.

The optional lineage-scoped ``list_pending_results`` contract is wired into the
existing Supervisor/advancement consumer path so the active Cloud Assets
Activation lineage is selected explicitly instead of the global historical
review backlog.

The consumer resolves the active project from an explicit argument, the
``PERSONAL_AI_ACTIVE_PROJECT_ID`` process override, or the Cloud Assets
Activation default; reads only that lineage; reports the excluded-by-lineage
audit count so filtering stays observable; returns exactly one bounded
``next_action``; and leaves the unscoped call byte-for-byte backward compatible.
No review state is mutated and no deployment occurs.

The production Worker source (``worker/index.js``) is exercised directly under
Node with a mocked ``TASK_REGISTRY`` KV, proving the opt-in ``active_project``
scope and the unchanged unscoped path in production source semantics.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from personal_ai_execution import (
    ACTIVE_PROJECT_ENV,
    DEFAULT_ACTIVE_PROJECT_ID,
    NEXT_ACTION_REVIEW,
    EventSyncRegistry,
    active_project_scope,
    event_sync,
    list_review_recommendations,
    supervisor_pending_review_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
NODE = shutil.which("node")

PROJECT_ID = "cloud-assets-activation"


def terminal_result(task_id: str, **overrides) -> dict:
    base = {
        "task_id": task_id,
        "status": "success",
        "tests": "3 passed",
        "summary": "lineage consumer probe",
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


# -- active-project scope resolution ----------------------------------------


def test_active_project_scope_precedence() -> None:
    # Explicit root wins over an explicit project only when no project is given.
    assert active_project_scope(root_task_id="cf-root") == {"root_task_id": "cf-root"}
    assert active_project_scope("explicit-project") == {"project_id": "explicit-project"}
    assert active_project_scope("explicit-project", "cf-root") == {
        "project_id": "explicit-project"
    }

    # The environment override is reusable configuration, not a hard-coded project.
    assert active_project_scope(env={ACTIVE_PROJECT_ENV: "configured"}) == {
        "project_id": "configured"
    }

    # The Cloud Assets Activation default is only the last resort.
    assert active_project_scope(env={}) == {"project_id": DEFAULT_ACTIVE_PROJECT_ID}
    assert DEFAULT_ACTIVE_PROJECT_ID == PROJECT_ID
    assert active_project_scope("explicit", env={ACTIVE_PROJECT_ENV: "configured"}) == {
        "project_id": "explicit"
    }


# -- scoped consumer selection ----------------------------------------------


def test_consumer_selects_active_project_and_excludes_historical() -> None:
    registry = EventSyncRegistry()
    for i in range(101):
        synced(registry, f"cf-historical-{i:03d}")
    synced(registry, "cf-active", project_id=PROJECT_ID)
    synced(registry, "cf-other-project", project_id="other-project")

    report = registry.supervisor_pending_review_report()

    assert [item["task_id"] for item in report["pending_review"]] == ["cf-active"]
    assert [item["task_id"] for item in report["recommendations"]] == ["cf-active"]
    assert report["scope"] == {"project_id": PROJECT_ID}
    assert report["excluded_by_lineage"] == 102
    assert report["counts"]["excluded_by_lineage"] == 102

    # Exactly one bounded next_action, deterministically the sole selected task.
    assert report["next_action"]["kind"] == NEXT_ACTION_REVIEW
    assert report["next_action"]["task_id"] == "cf-active"
    assert report["next_action"]["recommendation"] == "PASS"
    assert report["next_action"]["requires_human_review"] is True


def test_consumer_exclusion_is_auditable_and_non_destructive() -> None:
    registry = EventSyncRegistry()
    for i in range(5):
        synced(registry, f"cf-historical-{i}")

    registry.supervisor_pending_review_report()

    # The historical backlog is excluded from selection but never mutated.
    assert registry.get_review_events() == []
    assert [item["task_id"] for item in registry.list_pending_results()] == [
        "cf-historical-0",
        "cf-historical-1",
        "cf-historical-2",
        "cf-historical-3",
        "cf-historical-4",
    ]


def test_consumer_scope_is_configurable_via_env() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-default-active", project_id=PROJECT_ID)
    synced(registry, "cf-custom-active", project_id="custom-project")

    default_report = registry.supervisor_pending_review_report(env={})
    assert [item["task_id"] for item in default_report["pending_review"]] == [
        "cf-default-active"
    ]

    custom_report = registry.supervisor_pending_review_report(
        env={ACTIVE_PROJECT_ENV: "custom-project"}
    )
    assert [item["task_id"] for item in custom_report["pending_review"]] == [
        "cf-custom-active"
    ]
    assert custom_report["scope"] == {"project_id": "custom-project"}


def test_consumer_explicit_scope_overrides_env() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-env-active", project_id="configured")
    synced(registry, "cf-explicit-active", project_id="explicit")

    report = registry.supervisor_pending_review_report(
        "explicit",
        env={ACTIVE_PROJECT_ENV: "configured"},
    )
    assert [item["task_id"] for item in report["pending_review"]] == [
        "cf-explicit-active"
    ]


def test_unknown_parent_fails_closed_and_is_excluded() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-active", project_id=PROJECT_ID)
    registry.submit_task(
        "cf-orphan",
        goal="legacy orphan",
        status="success",
        parent_task_id="cf-ghost-parent",
    )
    registry._tasks["cf-orphan"].update(
        {"normalized_status": "PASS", "terminal": True, "result_available": True}
    )

    report = registry.supervisor_pending_review_report()
    assert [item["task_id"] for item in report["pending_review"]] == ["cf-active"]
    assert report["excluded_by_lineage"] == 1


# -- review recommendations consumer ----------------------------------------


def test_scoped_review_recommendations_report_excludes_historical() -> None:
    registry = EventSyncRegistry()
    for i in range(101):
        synced(registry, f"cf-historical-{i:03d}")
    synced(registry, "cf-active", project_id=PROJECT_ID)

    report = registry.list_review_recommendations({"project_id": PROJECT_ID})

    assert isinstance(report, dict)
    assert [item["task_id"] for item in report["recommendations"]] == ["cf-active"]
    assert [item["task_id"] for item in report["pending"]] == ["cf-active"]
    assert report["excluded_by_lineage"] == 101
    assert report["scope"] == {"project_id": PROJECT_ID}


def test_unscoped_review_recommendations_backward_compatible() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-part-a", project_id=PROJECT_ID)
    synced(registry, "cf-part-b")
    synced(registry, "cf-part-c", project_id="other")

    unscoped = registry.list_review_recommendations()
    assert isinstance(unscoped, list)
    assert [item["task_id"] for item in unscoped] == [
        "cf-part-a",
        "cf-part-b",
        "cf-part-c",
    ]


# -- advancement: the selected child stays in the active lineage -------------


def test_approved_child_stays_in_active_project_lineage() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-parent", project_id=PROJECT_ID)

    calls: list[dict] = []
    result = registry.mark_reviewed(
        "cf-parent",
        "PASS",
        "ship the child",
        approved_next_task={
            "goal": "child",
            "instructions": ["do it"],
            "acceptance": ["done"],
            "expected_files": ["worker/index.js"],
        },
        dispatcher=lambda contract: (calls.append(dict(contract)) or {"accepted": True}),
    )

    assert result["child_dispatch"]["dispatched"] is True
    child = calls[0]
    assert child["project_id"] == PROJECT_ID
    assert child["root_task_id"] == "cf-parent"
    assert child["parent_task_id"] == "cf-parent"

    registry.submit_task(
        child["task_id"],
        goal="child",
        status="success",
        normalized_status="PASS",
        terminal=True,
        result_available=True,
        **{
            k: child[k]
            for k in ("project_id", "root_task_id", "parent_task_id")
            if k in child
        },
    )
    registry._tasks[child["task_id"]].update(
        {"terminal": True, "result_available": True, "requires_review": True}
    )
    report = registry.supervisor_pending_review_report()
    assert [item["task_id"] for item in report["pending_review"]] == [child["task_id"]]


def test_supervisor_next_action_absent_for_empty_project() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-historical")
    report = registry.supervisor_pending_review_report()
    assert report["pending_review"] == []
    assert report["next_action"] is None


# -- module-level consumer --------------------------------------------------


def test_module_level_consumer_uses_active_project() -> None:
    registry = event_sync.reset_default_registry()
    synced(registry, "cf-module-historical")
    synced(registry, "cf-module-active", project_id=PROJECT_ID)

    unscoped = list_review_recommendations()
    assert isinstance(unscoped, list)
    assert len(unscoped) == 2

    report = supervisor_pending_review_report()
    assert [item["task_id"] for item in report["pending_review"]] == [
        "cf-module-active"
    ]
    assert report["excluded_by_lineage"] == 1
    event_sync.reset_default_registry()


# -- Worker source: production consumer semantics ---------------------------


WORKER_CONSUMER_HARNESS = r"""
const kv = new Map();
function seedTask(task) { kv.set("task:" + task.task_id, JSON.stringify(task)); }
const env = {
  GITHUB_REPO: "owner/repo",
  GITHUB_TOKEN: "test-token",
  PERSONAL_AI_ACTIVE_PROJECT_ID: "cloud-assets-activation",
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
const active = await toolListPendingResults(env, { active_project: true });
const explicit = await toolListPendingResults(env, { active_project: true, scope: { project_id: "other-project" } });
const unscoped = await toolListPendingResults(env, {});
env.PERSONAL_AI_ACTIVE_PROJECT_ID = "other-project";
const reconfigured = await toolListPendingResults(env, { active_project: true });
console.log(JSON.stringify({
  active: JSON.parse(active.text),
  explicit: JSON.parse(explicit.text),
  unscoped: JSON.parse(unscoped.text),
  reconfigured: JSON.parse(reconfigured.text)
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


def test_worker_source_encodes_consumer_tokens() -> None:
    source = worker_source()
    for token in (
        "activeProjectScope",
        "PERSONAL_AI_ACTIVE_PROJECT_ID",
        "cloud-assets-activation",
        "active_project",
        "excluded_by_lineage",
    ):
        assert token in source, f"worker is missing consumer token {token}"


def test_worker_active_project_scope_and_unscoped_unchanged() -> None:
    tasks = [
        make_task("cf-worker-active", project_id=PROJECT_ID),
        make_task("cf-worker-active-child", parent_task_id="cf-worker-active"),
        make_task("cf-worker-historical-a"),
        make_task("cf-worker-historical-b"),
        make_task("cf-worker-other", project_id="other-project"),
    ]
    script = WORKER_CONSUMER_HARNESS.replace("__TASKS__", json.dumps(tasks))
    report = run_worker_probe(script)

    active = report["active"]
    assert [item["task_id"] for item in active["pending_review"]] == [
        "cf-worker-active",
        "cf-worker-active-child",
    ]
    assert active["excluded_by_lineage"] == 3
    assert active["scope"] == {"project_id": PROJECT_ID}

    explicit = report["explicit"]
    assert [item["task_id"] for item in explicit["pending_review"]] == [
        "cf-worker-other"
    ]

    reconfigured = report["reconfigured"]
    assert [item["task_id"] for item in reconfigured["pending_review"]] == [
        "cf-worker-other"
    ]

    unscoped = report["unscoped"]
    assert [item["task_id"] for item in unscoped["pending_review"]] == [
        "cf-worker-active",
        "cf-worker-active-child",
        "cf-worker-historical-a",
        "cf-worker-historical-b",
        "cf-worker-other",
    ]
    assert "excluded_by_lineage" not in unscoped
