"""Tests for SUPERVISOR_ACTIVE_PROJECT_CALLER_ENABLEMENT_V0.1.

The already-implemented scoped active-project consumer is now wired into the
existing live Supervisor/advancement caller path. The caller requests
active-project scoped pending results through ``active_project`` or the
``PERSONAL_AI_SUPERVISOR_ACTIVE_PROJECT`` caller config, so the unrelated
historical ``pending_review`` backlog can never be selected while
``excluded_by_lineage`` stays observable. Explicitly unscoped/inactive callers
keep the historical compatibility behavior, exactly one bounded ``next_action``
is returned, and no review state is ever mutated.

The production Worker source (``worker/index.js``) is exercised directly under
Node with a mocked ``TASK_REGISTRY`` KV, proving the caller config enables the
opt-in ``active_project`` scope while the generic unscoped caller is unchanged.
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
    NEXT_ACTION_REVIEW,
    SUPERVISOR_ACTIVE_PROJECT_ENV,
    EventSyncRegistry,
    event_sync,
    list_pending_results,
    supervisor_active_project_enabled,
    supervisor_pending_review_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
NODE = shutil.which("node")

PROJECT_ID = "cloud-assets-activation"
OTHER_PROJECT = "other-project"


def terminal_result(task_id: str, **overrides) -> dict:
    base = {
        "task_id": task_id,
        "status": "success",
        "tests": "3 passed",
        "summary": "caller enablement probe",
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


def seeded(registry: EventSyncRegistry) -> None:
    for i in range(101):
        synced(registry, f"cf-historical-{i:03d}")
    synced(registry, "cf-active", project_id=PROJECT_ID)
    synced(registry, "cf-other", project_id=OTHER_PROJECT)


def active_ids(report: dict) -> list[str]:
    return [item["task_id"] for item in report["pending_review"]]


# -- caller config resolution ------------------------------------------------


def test_supervisor_caller_config_defaults_enabled() -> None:
    # The live caller is enabled when the caller config is absent...
    assert supervisor_active_project_enabled(env={}) is True
    assert supervisor_active_project_enabled(env={SUPERVISOR_ACTIVE_PROJECT_ENV: "1"}) is True
    assert supervisor_active_project_enabled(env={SUPERVISOR_ACTIVE_PROJECT_ENV: "yes"}) is True

    # ...and can be explicitly opted out through the caller config.
    for falsey in ("0", "false", "no", "off", ""):
        assert (
            supervisor_active_project_enabled(env={SUPERVISOR_ACTIVE_PROJECT_ENV: falsey})
            is False
        )


# -- caller selects the active project, never the historical backlog --------


def test_supervisor_caller_requests_active_project_and_excludes_history() -> None:
    registry = EventSyncRegistry()
    seeded(registry)

    report = registry.supervisor_pending_review_report()

    assert active_ids(report) == ["cf-active"]
    assert [item["task_id"] for item in report["recommendations"]] == ["cf-active"]
    assert report["scope"] == {"project_id": PROJECT_ID}
    # 101 historical singletons + 1 unrelated project are excluded, never hidden.
    assert report["excluded_by_lineage"] == 102
    assert report["counts"]["excluded_by_lineage"] == 102
    assert report["next_action"] == {
        "kind": NEXT_ACTION_REVIEW,
        "task_id": "cf-active",
        "recommendation": "PASS",
        "requires_human_review": True,
    }


def test_supervisor_caller_active_project_flag_is_explicit() -> None:
    registry = EventSyncRegistry()
    seeded(registry)

    # active_project=True is equivalent to the default caller scope.
    assert active_ids(registry.supervisor_pending_review_report(active_project=True)) == [
        "cf-active"
    ]

    # active_project=False preserves the historical unscoped compatibility path.
    unscoped = registry.supervisor_pending_review_report(active_project=False)
    assert unscoped["scope"] is None
    assert unscoped["excluded_by_lineage"] == 0
    assert len(unscoped["pending_review"]) == 103


def test_supervisor_caller_config_can_opt_out() -> None:
    registry = EventSyncRegistry()
    seeded(registry)

    report = registry.supervisor_pending_review_report(
        env={SUPERVISOR_ACTIVE_PROJECT_ENV: "0"}
    )
    assert report["scope"] is None
    assert report["excluded_by_lineage"] == 0
    assert len(report["pending_review"]) == 103
    # Exactly one bounded next_action even on the unscoped compatibility path.
    assert report["next_action"]["kind"] == NEXT_ACTION_REVIEW


def test_supervisor_caller_explicit_scope_overrides_caller_config() -> None:
    registry = EventSyncRegistry()
    seeded(registry)

    report = registry.supervisor_pending_review_report(
        OTHER_PROJECT,
        env={SUPERVISOR_ACTIVE_PROJECT_ENV: "0"},
    )
    assert report["scope"] == {"project_id": OTHER_PROJECT}
    assert active_ids(report) == ["cf-other"]
    assert report["excluded_by_lineage"] == 102


def test_supervisor_caller_active_project_is_configurable() -> None:
    registry = EventSyncRegistry()
    seeded(registry)

    report = registry.supervisor_pending_review_report(
        env={ACTIVE_PROJECT_ENV: OTHER_PROJECT}
    )
    assert report["scope"] == {"project_id": OTHER_PROJECT}
    assert active_ids(report) == ["cf-other"]


# -- no review-state mutation and a single bounded next_action --------------


def test_supervisor_caller_does_not_mutate_review_state() -> None:
    registry = EventSyncRegistry()
    seeded(registry)

    before = {task_id: dict(item) for task_id, item in registry._tasks.items()}
    registry.supervisor_pending_review_report()

    assert registry.get_review_events() == []
    for task_id, record in registry._tasks.items():
        assert record["reviewed"] is False
        assert record["review_verdict"] is None
        assert record["review_state"] == before[task_id]["review_state"]
        assert record.get("review_events") == before[task_id].get("review_events")


def test_supervisor_caller_returns_exactly_one_bounded_next_action() -> None:
    registry = EventSyncRegistry()
    synced(registry, "cf-active-a", project_id=PROJECT_ID)
    synced(registry, "cf-active-b", project_id=PROJECT_ID)
    synced(registry, "cf-historical")

    report = registry.supervisor_pending_review_report()

    assert active_ids(report) == ["cf-active-a", "cf-active-b"]
    # The recommendation list may be long, but exactly one bounded action is
    # selected deterministically (the first active-project task in order).
    assert report["next_action"]["task_id"] == "cf-active-a"


def test_module_level_caller_uses_active_project() -> None:
    registry = event_sync.reset_default_registry()
    seeded(registry)

    # The generic unscoped reader is untouched for other callers.
    assert isinstance(list_pending_results(), list)
    assert len(list_pending_results()) == 103

    report = supervisor_pending_review_report()
    assert active_ids(report) == ["cf-active"]
    assert report["excluded_by_lineage"] == 102
    event_sync.reset_default_registry()


# -- Worker source: production caller semantics -----------------------------


WORKER_CALLER_HARNESS = r"""
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
const genericUnscoped = await toolListPendingResults(env, {});
env.PERSONAL_AI_SUPERVISOR_ACTIVE_PROJECT = "1";
const callerConfigured = await toolListPendingResults(env, {});
const callerOptOut = await toolListPendingResults(env, { active_project: false });
const callerExplicit = await toolListPendingResults(env, { active_project: true });
const callerExplicitScope = await toolListPendingResults(env, { scope: { project_id: "other-project" } });
console.log(JSON.stringify({
  genericUnscoped: JSON.parse(genericUnscoped.text),
  callerConfigured: JSON.parse(callerConfigured.text),
  callerOptOut: JSON.parse(callerOptOut.text),
  callerExplicit: JSON.parse(callerExplicit.text),
  callerExplicitScope: JSON.parse(callerExplicitScope.text)
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


def test_worker_source_encodes_caller_config_tokens() -> None:
    source = worker_source()
    for token in (
        "supervisorActiveProjectEnabled",
        "PERSONAL_AI_SUPERVISOR_ACTIVE_PROJECT",
        "activeProjectScope",
        "active_project",
        "excluded_by_lineage",
    ):
        assert token in source, f"worker is missing caller token {token}"


def test_worker_caller_config_enables_scope_and_preserves_unscoped() -> None:
    tasks = [
        make_task("cf-worker-active", project_id=PROJECT_ID),
        make_task("cf-worker-active-child", parent_task_id="cf-worker-active"),
        make_task("cf-worker-historical-a"),
        make_task("cf-worker-historical-b"),
        make_task("cf-worker-other", project_id=OTHER_PROJECT),
    ]
    script = WORKER_CALLER_HARNESS.replace("__TASKS__", json.dumps(tasks))
    report = run_worker_probe(script)

    # The generic caller is unchanged: no supervisor config -> unscoped.
    generic = report["genericUnscoped"]
    assert [item["task_id"] for item in generic["pending_review"]] == [
        "cf-worker-active",
        "cf-worker-active-child",
        "cf-worker-historical-a",
        "cf-worker-historical-b",
        "cf-worker-other",
    ]
    assert "excluded_by_lineage" not in generic

    # The configured live caller requests active-project scope automatically.
    configured = report["callerConfigured"]
    assert [item["task_id"] for item in configured["pending_review"]] == [
        "cf-worker-active",
        "cf-worker-active-child",
    ]
    assert configured["excluded_by_lineage"] == 3
    assert configured["scope"] == {"project_id": PROJECT_ID}

    # Explicit opt-out and explicit opt-in both keep working.
    assert [
        item["task_id"] for item in report["callerOptOut"]["pending_review"]
    ] == [
        "cf-worker-active",
        "cf-worker-active-child",
        "cf-worker-historical-a",
        "cf-worker-historical-b",
        "cf-worker-other",
    ]
    assert report["callerExplicit"]["scope"] == {"project_id": PROJECT_ID}

    # An explicit lineage scope always wins over the caller config.
    assert [
        item["task_id"] for item in report["callerExplicitScope"]["pending_review"]
    ] == ["cf-worker-other"]
