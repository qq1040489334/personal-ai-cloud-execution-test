"""Tests for PERSONAL_AI_AUTONOMOUS_ADVANCEMENT_V0.2.

The only new production edge is: an authoritative terminal validated ``PASS``
review with an *explicit* ``approved_next_task`` dispatches exactly one child
task. The Worker and the registry never invent next work. Every other path
(FAIL / BLOCKED / non-terminal / missing result / invalid child / replay)
dispatches nothing or is exactly-once idempotent.

The production Worker source (``worker/index.js``) is exercised directly under
Node with a mocked ``ASSET_DB`` D1, ``TASK_REGISTRY`` KV and ``fetch`` so the
exactly-once child dispatch is verified in production source semantics.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from personal_ai_execution import (
    APPROVED_NEXT_TASK_FIELD,
    BLOCKED,
    DISPATCH_REASON_ALREADY,
    DISPATCH_REASON_DISPATCHED,
    DISPATCH_REASON_INVALID,
    DISPATCH_REASON_NO_CHILD,
    DISPATCH_REASON_UNAVAILABLE,
    DISPATCH_REASON_VERDICT,
    DISPATCH_STATE_DISPATCHED,
    FAIL,
    PASS,
    EventSyncRegistry,
    normalize_approved_next_task,
    reset_default_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
MIGRATION_PATH = (
    REPO_ROOT / "worker" / "migrations" / "0002_dispatch_idempotency.sql"
)

NODE = shutil.which("node")

PARENT_TASK_ID = "cf-advancement-parent"

OMIT = object()


def execution_result(task_id: str = PARENT_TASK_ID, **overrides) -> dict:
    base = {
        "task_id": task_id,
        "status": "success",
        "tests": "5 passed in 1.20s",
        "summary": "autonomous advancement probe",
        "commit": "cafebabe",
        "changed_files": ["src/personal_ai_execution/advancement.py"],
    }
    base.update(overrides)
    return base


def synced(conclusion: str = "success", task_id: str = PARENT_TASK_ID) -> EventSyncRegistry:
    registry = EventSyncRegistry()
    registry.sync_terminal_result(
        task_id,
        execution_result(task_id),
        conclusion,
        artifact_present=True,
        commit_present=True,
    )
    return registry


def approved_child() -> dict:
    return {
        "goal": "child task",
        "instructions": ["do the next thing"],
        "acceptance": ["next thing done"],
        "expected_files": ["hello.py"],
    }


class Recorder:
    def __init__(self, accepted: bool = True) -> None:
        self.calls: list[dict] = []
        self.accepted = accepted

    def __call__(self, contract):
        self.calls.append(dict(contract))
        return {
            "accepted": self.accepted,
            "dispatch_status": "accepted" if self.accepted else "github_rejected",
        }


# -- Python registry: happy path + exactly-once -----------------------------


def test_pass_with_valid_approved_next_task_dispatches_once() -> None:
    registry = synced()
    recorder = Recorder()

    result = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "approved", approved_next_task=approved_child(), dispatcher=recorder
    )

    assert result["reviewed"] is True
    assert result["review_verdict"] == PASS
    assert result["idempotent"] is False
    assert len(recorder.calls) == 1
    child = recorder.calls[0]
    assert child["goal"] == "child task"
    assert child["instructions"] == ["do the next thing"]
    assert child["acceptance"] == ["next thing done"]
    assert child["expected_files"] == ["hello.py"]
    assert child["parent_task_id"] == PARENT_TASK_ID

    dispatch = result["child_dispatch"]
    assert dispatch["dispatched"] is True
    assert dispatch["reason"] == DISPATCH_REASON_DISPATCHED
    assert dispatch["child_task_id"] == child["task_id"]
    assert dispatch["parent_task_id"] == PARENT_TASK_ID

    marker = registry._tasks[PARENT_TASK_ID]["review_dispatch"]
    assert marker["parent_task_id"] == PARENT_TASK_ID
    assert marker["child_task_id"] == child["task_id"]
    assert marker["dispatch_state"] == DISPATCH_STATE_DISPATCHED
    assert marker["review_verdict"] == PASS
    assert marker["review_timestamp"]
    assert marker["dispatched_at"]
    trail = registry._tasks[PARENT_TASK_ID]["review_dispatches"]
    assert len(trail) == 1


def test_replay_is_exactly_once_and_never_creates_a_second_child() -> None:
    registry = synced()
    recorder = Recorder()

    first = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "approved", approved_next_task=approved_child(), dispatcher=recorder
    )
    second = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "approved", approved_next_task=approved_child(), dispatcher=recorder
    )

    assert first["child_dispatch"]["dispatched"] is True
    assert second["idempotent"] is True
    assert second["child_dispatch"]["idempotent"] is True
    assert second["child_dispatch"]["reason"] == DISPATCH_REASON_ALREADY
    assert second["child_dispatch"]["child_task_id"] == first["child_dispatch"]["child_task_id"]
    assert len(recorder.calls) == 1


def test_no_approved_next_task_is_backward_compatible() -> None:
    registry = synced()
    recorder = Recorder()

    result = registry.mark_reviewed(PARENT_TASK_ID, PASS, "no child here")

    assert result["reviewed"] is True
    assert result["review_verdict"] == PASS
    assert recorder.calls == []
    assert result["child_dispatch"]["dispatched"] is False
    assert result["child_dispatch"]["reason"] == DISPATCH_REASON_NO_CHILD
    assert registry._tasks[PARENT_TASK_ID]["review_dispatch"] is None


def test_explicit_null_approved_next_task_dispatches_nothing() -> None:
    registry = synced()
    recorder = Recorder()

    result = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "null", approved_next_task=None, dispatcher=recorder
    )

    assert recorder.calls == []
    assert result["child_dispatch"]["reason"] == DISPATCH_REASON_NO_CHILD


@pytest.mark.parametrize("verdict", [FAIL, BLOCKED])
def test_fail_and_blocked_dispatch_nothing(verdict: str) -> None:
    registry = synced()
    recorder = Recorder()

    result = registry.mark_reviewed(
        PARENT_TASK_ID, verdict, "no", approved_next_task=approved_child(), dispatcher=recorder
    )

    assert recorder.calls == []
    assert result["child_dispatch"]["dispatched"] is False
    assert result["child_dispatch"]["reason"] == DISPATCH_REASON_VERDICT
    assert registry._tasks[PARENT_TASK_ID]["review_dispatch"] is None


@pytest.mark.parametrize(
    "bad_child",
    [
        {},
        {"goal": "", "instructions": ["x"], "acceptance": ["y"]},
        {"goal": "g", "instructions": [], "acceptance": ["y"]},
        {"goal": "g", "instructions": ["x"], "acceptance": []},
        {"goal": "g", "instructions": "not-a-list", "acceptance": ["y"]},
        {"goal": "g", "instructions": ["x"], "acceptance": ["y"], "expected_files": "/etc/passwd"},
        {"goal": "g", "instructions": ["x"], "acceptance": ["y"], "expected_files": [".github/workflows/agent.yml"]},
        ["not", "a", "mapping"],
    ],
)
def test_invalid_approved_next_task_fails_closed(bad_child) -> None:
    registry = synced()
    recorder = Recorder()

    result = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "bad child", approved_next_task=bad_child, dispatcher=recorder
    )

    assert recorder.calls == []
    assert result["child_dispatch"]["dispatched"] is False
    assert result["child_dispatch"]["reason"] == DISPATCH_REASON_INVALID
    assert registry._tasks[PARENT_TASK_ID]["review_dispatch"] is None


def test_non_terminal_task_dispatches_nothing() -> None:
    registry = EventSyncRegistry()
    registry.submit_task(PARENT_TASK_ID, goal="in flight", status="in_progress")
    recorder = Recorder()

    with pytest.raises(ValueError):
        registry.mark_reviewed(
            PARENT_TASK_ID, PASS, "early", approved_next_task=approved_child(), dispatcher=recorder
        )

    assert recorder.calls == []


def test_missing_dispatcher_fails_closed_then_dispatches_once() -> None:
    registry = synced()
    recorder = Recorder()

    blocked = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "no gateway", approved_next_task=approved_child()
    )

    assert recorder.calls == []
    assert blocked["child_dispatch"]["dispatched"] is False
    assert blocked["child_dispatch"]["reason"] == DISPATCH_REASON_UNAVAILABLE
    assert registry._tasks[PARENT_TASK_ID]["review_dispatch"] is None

    # A later call that has a gateway may still dispatch exactly once.
    dispatched = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "gateway now", approved_next_task=approved_child(), dispatcher=recorder
    )
    assert dispatched["child_dispatch"]["dispatched"] is True
    assert len(recorder.calls) == 1
    assert registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "replay", approved_next_task=approved_child(), dispatcher=recorder
    )["child_dispatch"]["reason"] == DISPATCH_REASON_ALREADY
    assert len(recorder.calls) == 1


def test_dispatcher_failure_is_at_most_once() -> None:
    registry = synced()
    recorder = Recorder(accepted=False)

    failed = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "rejected", approved_next_task=approved_child(), dispatcher=recorder
    )

    assert failed["child_dispatch"]["dispatched"] is False
    assert failed["child_dispatch"]["dispatch_state"] == "FAILED"
    assert len(recorder.calls) == 1

    # A replay must not retry a dispatch that was already attempted.
    replay = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "rejected", approved_next_task=approved_child(), dispatcher=recorder
    )
    assert replay["child_dispatch"]["idempotent"] is True
    assert len(recorder.calls) == 1


def test_dispatcher_exception_fails_closed() -> None:
    registry = synced()

    def boom(_contract):
        raise RuntimeError("network down")

    result = registry.mark_reviewed(
        PARENT_TASK_ID, PASS, "boom", approved_next_task=approved_child(), dispatcher=boom
    )

    assert result["child_dispatch"]["dispatched"] is False
    assert result["child_dispatch"]["dispatch_state"] == "FAILED"
    assert registry._tasks[PARENT_TASK_ID]["review_dispatch"]["error"].startswith("RuntimeError")


def test_normalizer_rejects_forbidden_and_unsafe_paths() -> None:
    contract, errors = normalize_approved_next_task(approved_child())
    assert errors == []
    assert contract is not None
    assert contract["expected_files"] == ["hello.py"]

    _contract, errors = normalize_approved_next_task(
        {"goal": "g", "instructions": ["x"], "acceptance": ["y"], "expected_files": ["../escape.py"]}
    )
    assert errors and "unsafe" in errors[0]

    _contract, errors = normalize_approved_next_task(
        {"goal": "g", "instructions": ["x"], "acceptance": ["y"], "expected_files": ["a/.env"]}
    )
    assert errors and "forbidden" in errors[0]


def test_module_level_default_registry_dispatch() -> None:
    reset_default_registry()
    from personal_ai_execution import event_sync, mark_reviewed

    event_sync.sync_terminal_result(PARENT_TASK_ID, execution_result(), "success")
    recorder = Recorder()
    reviewed = mark_reviewed(
        PARENT_TASK_ID, PASS, "module flow", approved_next_task=approved_child(), dispatcher=recorder
    )
    assert reviewed["child_dispatch"]["dispatched"] is True
    assert len(recorder.calls) == 1


def test_approved_next_task_field_name_is_stable() -> None:
    assert APPROVED_NEXT_TASK_FIELD == "approved_next_task"


# -- Worker source: production semantics ------------------------------------

WORKER_DISPATCH_HARNESS = r"""
const markerRows = new Map();
function makeD1() {
  return {
    prepare: function(sql) {
      return {
        bind: function(...args) {
          return {
            run: async function() {
              if (sql.indexOf("INSERT OR IGNORE INTO task_dispatch_markers") === 0) {
                const key = args[0];
                if (markerRows.has(key)) return { success: true, meta: { changes: 0 } };
                markerRows.set(key, {
                  dispatch_key: args[0], parent_task_id: args[1], review_verdict: args[2],
                  review_timestamp: args[3], review_note: args[4], child_task_id: args[5],
                  dispatch_state: args[6], dispatch_status: null, github_http_status: null,
                  github_request_id: null, dispatched_at: null, created_at: args[7], updated_at: args[8]
                });
                return { success: true, meta: { changes: 1 } };
              }
              if (sql.indexOf("UPDATE task_dispatch_markers") === 0) {
                const row = markerRows.get(args[6]);
                if (row) {
                  row.dispatch_state = args[0]; row.dispatch_status = args[1];
                  row.github_http_status = args[2]; row.github_request_id = args[3];
                  row.dispatched_at = args[4]; row.updated_at = args[5];
                  return { success: true, meta: { changes: 1 } };
                }
                return { success: true, meta: { changes: 0 } };
              }
              return { success: true, meta: { changes: 0 } };
            },
            first: async function() {
              if (sql.indexOf("FROM task_dispatch_markers") !== -1) {
                return markerRows.get(args[0]) || null;
              }
              return null;
            },
            all: async function() { return { results: [] }; }
          };
        }
      };
    }
  };
}
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
    list: async function() { return { keys: [] }; }
  }
};
__ASSET_DB__
const dispatchCalls = [];
globalThis.fetch = async function(url, options) {
  let parsed = null;
  try { parsed = options && options.body ? JSON.parse(options.body) : null; } catch (e) { parsed = null; }
  dispatchCalls.push({ url: String(url), body: parsed });
  return {
    ok: __FETCH_OK__,
    status: __FETCH_STATUS__,
    headers: { get: function() { return "req-1"; } },
    text: async function() { return ""; }
  };
};
const TASK_ID = __TASK_ID__;
seedTask(__TASK_JSON__);
const args = __ARGS_JS__;
const results = [];
for (let i = 0; i < __TIMES__; i++) {
  results.push(await toolMarkReviewed(env, args));
}
console.log(JSON.stringify({
  results: results,
  dispatchCalls: dispatchCalls,
  markerRows: Array.from(markerRows.values())
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


def worker_dispatch_probe(
    *,
    verdict: str = "PASS",
    approved=OMIT,
    times: int = 2,
    asset_db: bool = True,
    fetch_ok: bool = True,
    fetch_status: int = 204,
) -> dict:
    task = {
        "task_id": PARENT_TASK_ID,
        "normalized_status": "PASS",
        "status": "PASS",
        "execution_status": "PASS",
        "terminal": True,
        "result_available": True,
        "reviewed": False,
        "review_verdict": None,
        "updated_at": "2026-09-27T00:00:00.000Z",
    }
    if approved is OMIT:
        args_js = '{ task_id: TASK_ID, verdict: %s, note: "n" }' % json.dumps(verdict)
    else:
        args_js = (
            '{ task_id: TASK_ID, verdict: %s, note: "n", approved_next_task: %s }'
            % (json.dumps(verdict), json.dumps(approved))
        )
    script = WORKER_DISPATCH_HARNESS
    script = script.replace(
        "__ASSET_DB__", "env.ASSET_DB = makeD1();" if asset_db else ""
    )
    script = script.replace("__FETCH_OK__", "true" if fetch_ok else "false")
    script = script.replace("__FETCH_STATUS__", str(fetch_status))
    script = script.replace("__TASK_ID__", json.dumps(task["task_id"]))
    script = script.replace("__TASK_JSON__", json.dumps(task))
    script = script.replace("__ARGS_JS__", args_js)
    script = script.replace("__TIMES__", str(times))
    return run_worker_probe(script)


def structured(entry: dict) -> dict:
    return entry.get("structuredContent", json.loads(entry["text"]))


def test_worker_source_encodes_the_dispatch_edge() -> None:
    source = worker_source()
    for token in (
        "approved_next_task",
        "task_dispatch_markers",
        "dispatchApprovedChild",
        "dispatchMarkerKey",
        "claimDispatchMarker",
        "finalizeDispatchMarker",
        "INSERT OR IGNORE INTO task_dispatch_markers",
        "DISPATCHED",
        "ALREADY_DISPATCHED",
        "INVALID_APPROVED_NEXT_TASK",
        "DISPATCH_MARKER_UNAVAILABLE",
        "child_dispatch",
    ):
        assert token in source, f"worker is missing advancement token {token}"


def test_worker_pass_review_dispatches_exactly_one_real_child() -> None:
    report = worker_dispatch_probe(approved=approved_child(), times=2)

    first = structured(report["results"][0])
    second = structured(report["results"][1])

    assert first["reviewed"] is True
    assert first["child_dispatch"]["dispatched"] is True
    child_task_id = first["child_dispatch"]["child_task_id"]
    assert child_task_id

    # Exactly one real repository_dispatch request reached GitHub.
    assert len(report["dispatchCalls"]) == 1
    call = report["dispatchCalls"][0]
    assert call["url"].endswith("/repos/owner/repo/dispatches")
    assert call["body"]["event_type"] == "gpt_task"
    child = call["body"]["client_payload"]["task"]
    assert child["task_id"] == child_task_id
    assert child["goal"] == "child task"
    assert child["instructions"] == ["do the next thing"]
    assert child["acceptance"] == ["next thing done"]

    # Replay is idempotent and creates no second child.
    assert second["idempotent"] is True
    assert second["child_dispatch"]["idempotent"] is True
    assert second["child_dispatch"]["reason"] == "ALREADY_DISPATCHED"
    assert second["child_dispatch"]["child_task_id"] == child_task_id
    assert len(report["dispatchCalls"]) == 1
    assert len(report["markerRows"]) == 1


def test_worker_without_approved_next_task_dispatches_nothing() -> None:
    report = worker_dispatch_probe(approved=OMIT, times=2)

    assert report["dispatchCalls"] == []
    assert report["markerRows"] == []
    for entry in report["results"]:
        result = structured(entry)
        assert result["reviewed"] is True
        assert result["child_dispatch"]["dispatched"] is False
        assert result["child_dispatch"]["reason"] == "NO_APPROVED_NEXT_TASK"


@pytest.mark.parametrize("verdict", ["FAIL", "BLOCKED"])
def test_worker_fail_and_blocked_dispatch_nothing(verdict: str) -> None:
    report = worker_dispatch_probe(verdict=verdict, approved=approved_child(), times=1)

    assert report["dispatchCalls"] == []
    assert report["markerRows"] == []
    result = structured(report["results"][0])
    assert result["child_dispatch"]["dispatched"] is False
    assert result["child_dispatch"]["reason"] == "VERDICT_NOT_PASS"


@pytest.mark.parametrize(
    "bad_child",
    [
        {"goal": "", "instructions": ["x"], "acceptance": ["y"]},
        {"goal": "g", "instructions": [], "acceptance": ["y"]},
        {"goal": "g", "instructions": ["x"], "acceptance": ["y"], "expected_files": [".github/workflows/x.yml"]},
    ],
)
def test_worker_invalid_child_fails_closed(bad_child: dict) -> None:
    report = worker_dispatch_probe(approved=bad_child, times=1)

    assert report["dispatchCalls"] == []
    assert report["markerRows"] == []
    result = structured(report["results"][0])
    assert result["child_dispatch"]["dispatched"] is False
    assert result["child_dispatch"]["reason"] == "INVALID_APPROVED_NEXT_TASK"


def test_worker_without_dispatch_marker_store_fails_closed() -> None:
    report = worker_dispatch_probe(approved=approved_child(), times=1, asset_db=False)

    assert report["dispatchCalls"] == []
    result = structured(report["results"][0])
    assert result["child_dispatch"]["dispatched"] is False
    assert result["child_dispatch"]["reason"] == "DISPATCH_MARKER_UNAVAILABLE"


def test_worker_github_rejection_never_retries_on_replay() -> None:
    report = worker_dispatch_probe(
        approved=approved_child(), times=2, fetch_ok=False, fetch_status=422
    )

    # Only the first call reaches GitHub; the claim marker makes replay a no-op.
    assert len(report["dispatchCalls"]) == 1
    first = structured(report["results"][0])
    second = structured(report["results"][1])
    assert first["child_dispatch"]["dispatched"] is False
    assert first["child_dispatch"]["dispatch_state"] == "FAILED"
    assert second["child_dispatch"]["idempotent"] is True
    assert second["child_dispatch"]["reason"] == "ALREADY_DISPATCHED"
    assert len(report["markerRows"]) == 1
    assert report["markerRows"][0]["dispatch_state"] == "FAILED"


def test_dispatch_marker_migration_is_additive_and_non_destructive() -> None:
    assert MIGRATION_PATH.is_file()
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "task_dispatch_markers" in sql
    assert "CREATE TABLE IF NOT EXISTS" in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS" in sql
    assert "parent_task_id" in sql
    assert "child_task_id" in sql
    assert "dispatch_state" in sql
    upper = sql.upper()
    for destructive in ("DROP TABLE", "DROP COLUMN", "DELETE FROM", "TRUNCATE"):
        assert destructive not in upper


# -- Worker source: bounded KV metadata for long review notes ----------------
#
# Cloudflare KV caps the serialized ``metadata`` object at 1024 UTF-8 bytes.
# ``saveTask`` used to spill the whole registry entry (including ``review_note``
# and ``review_event.note``) into that metadata, so a single real long note was
# duplicated and blew the limit. These probes exercise the *production* source
# with a KV mock that measures the exact serialized metadata and records a
# violation whenever the 1024-byte bound is exceeded.

LONG_ENGLISH_NOTE = "review " + (
    "the reviewer confirmed the full evidence chain and signed off. " * 16
)
LONG_CHINESE_NOTE = "审查备注：" + (
    "这是一段用于验证元数据边界的完整中文长备注内容。" * 24
)

MAX_METADATA_BYTES = 1024


def utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def metadata_task(task_id: str = PARENT_TASK_ID, **overrides) -> dict:
    base = {
        "task_id": task_id,
        "status": "PASS",
        "normalized_status": "PASS",
        "execution_status": "PASS",
        "terminal": True,
        "result_available": True,
        "workflow_verified": True,
        "workflow_conclusion": "success",
        "reviewed": False,
        "review_verdict": None,
        "title": "long-note metadata bounds probe",
        "project_id": "cloud-assets-activation",
        "root_task_id": task_id,
        "dispatch_state": "CONFIRMED",
        "dispatch_attempt": 1,
        "dispatch_accepted_at": "2026-09-27T00:00:00.000Z",
        "created_at": "2026-09-27T00:00:00.000Z",
        "updated_at": "2026-09-27T00:00:00.000Z",
    }
    base.update(overrides)
    return base


WORKER_METADATA_HARNESS = r"""
const markerRows = new Map();
function makeD1() {
  return {
    prepare: function(sql) {
      return {
        bind: function(...args) {
          return {
            run: async function() {
              if (sql.indexOf("INSERT OR IGNORE INTO task_dispatch_markers") === 0) {
                const key = args[0];
                if (markerRows.has(key)) return { success: true, meta: { changes: 0 } };
                markerRows.set(key, {
                  dispatch_key: args[0], parent_task_id: args[1], review_verdict: args[2],
                  review_timestamp: args[3], review_note: args[4], child_task_id: args[5],
                  dispatch_state: args[6], dispatch_status: null, github_http_status: null,
                  github_request_id: null, dispatched_at: null, created_at: args[7], updated_at: args[8]
                });
                return { success: true, meta: { changes: 1 } };
              }
              if (sql.indexOf("UPDATE task_dispatch_markers") === 0) {
                const row = markerRows.get(args[6]);
                if (row) {
                  row.dispatch_state = args[0]; row.dispatch_status = args[1];
                  row.github_http_status = args[2]; row.github_request_id = args[3];
                  row.dispatched_at = args[4]; row.updated_at = args[5];
                  return { success: true, meta: { changes: 1 } };
                }
                return { success: true, meta: { changes: 0 } };
              }
              return { success: true, meta: { changes: 0 } };
            },
            first: async function() {
              if (sql.indexOf("FROM task_dispatch_markers") !== -1) {
                return markerRows.get(args[0]) || null;
              }
              return null;
            },
            all: async function() { return { results: [] }; }
          };
        }
      };
    }
  };
}
const kv = new Map();
const metaStore = new Map();
const putLog = [];
const violations = [];
const MAX_METADATA_BYTES = 1024;
function utf8Len(text) { return new TextEncoder().encode(text).length; }
function projectMetadata(record) {
  const meta = {};
  for (const key of Object.keys(record)) {
    if (key === "task_id" || key === "dispatch_contract" || key === "dispatch_events") continue;
    meta[key] = record[key];
  }
  return meta;
}
function seedTask(task) {
  kv.set("task:" + task.task_id, JSON.stringify(task));
  metaStore.set("task:" + task.task_id, projectMetadata(task));
}
const env = {
  GITHUB_REPO: "owner/repo",
  GITHUB_TOKEN: "test-token",
  ASSET_DB: makeD1(),
  TASK_REGISTRY: {
    get: async function(key, type) {
      const raw = kv.has(key) ? kv.get(key) : null;
      if (raw == null) return null;
      return type === "json" ? JSON.parse(raw) : raw;
    },
    put: async function(key, value, opts) {
      const metadata = opts && opts.metadata ? opts.metadata : {};
      const bytes = utf8Len(JSON.stringify(metadata));
      if (bytes > MAX_METADATA_BYTES) violations.push({ key: key, bytes: bytes });
      putLog.push({ key: key, value: JSON.parse(value), metadata: metadata, metadata_bytes: bytes });
      kv.set(key, value);
      metaStore.set(key, metadata);
    },
    list: async function() {
      return { keys: Array.from(kv.keys()).map(function(name) {
        return { name: name, metadata: metaStore.get(name) || {} };
      }) };
    }
  }
};
const dispatchCalls = [];
globalThis.fetch = async function(url, options) {
  const u = String(url);
  if (u.indexOf("/actions/artifacts") !== -1) {
    return {
      ok: true, status: 200,
      headers: { get: function() { return null; } },
      json: async function() { return { artifacts: [] }; },
      text: async function() { return ""; }
    };
  }
  let parsed = null;
  try { parsed = options && options.body ? JSON.parse(options.body) : null; } catch (e) { parsed = null; }
  dispatchCalls.push({ url: u, body: parsed });
  return {
    ok: true, status: 204,
    headers: { get: function() { return "req-1"; } },
    text: async function() { return ""; }
  };
};
const TASK_ID = __TASK_ID__;
seedTask(__TASK_JSON__);
const args = __ARGS_JS__;
const results = [];
for (let i = 0; i < __TIMES__; i++) results.push(await toolMarkReviewed(env, args));
const putsAfterReviews = putLog.length;
const stored = JSON.parse(kv.get("task:" + TASK_ID));
const listing = JSON.parse((await toolListPendingResults(env, {})).text);
console.log(JSON.stringify({
  results: results,
  dispatchCalls: dispatchCalls,
  violations: violations,
  putLog: putLog,
  putsAfterReviews: putsAfterReviews,
  metadata: metaStore.get("task:" + TASK_ID),
  stored: stored,
  listing: listing
}));
"""


def run_worker_metadata_probe(
    *,
    note: str,
    verdict: str = "PASS",
    approved=OMIT,
    times: int = 1,
    task: dict | None = None,
) -> dict:
    task = task if task is not None else metadata_task()
    if approved is OMIT:
        args_js = '{ task_id: TASK_ID, verdict: %s, note: %s }' % (
            json.dumps(verdict),
            json.dumps(note),
        )
    else:
        args_js = (
            '{ task_id: TASK_ID, verdict: %s, note: %s, approved_next_task: %s }'
            % (json.dumps(verdict), json.dumps(note), json.dumps(approved))
        )
    script = WORKER_METADATA_HARNESS
    script = script.replace("__TASK_ID__", json.dumps(task["task_id"]))
    script = script.replace("__TASK_JSON__", json.dumps(task))
    script = script.replace("__ARGS_JS__", args_js)
    script = script.replace("__TIMES__", str(times))
    return run_worker_probe(script)


@pytest.mark.parametrize("note", [LONG_ENGLISH_NOTE, LONG_CHINESE_NOTE])
def test_worker_long_review_note_metadata_stays_within_kv_limit(note: str) -> None:
    # A real long note is many hundreds of bytes; the historic defect duplicated
    # it into metadata and immediately exceeded the 1024-byte KV bound.
    assert utf8_len(note) > 611

    report = run_worker_metadata_probe(note=note, times=1)

    assert report["violations"] == [], report["violations"]
    assert report["putLog"], "review must persist the registry record"
    for put in report["putLog"]:
        assert put["metadata_bytes"] <= MAX_METADATA_BYTES
        # The unbounded review payload stays in the JSON value, not metadata.
        assert "review_note" not in put["metadata"]
        assert "review_event" not in put["metadata"]

    # Full original content is preserved in the value and reads back identically.
    stored = report["stored"]
    assert stored["review_note"] == note
    assert stored["review_event"]["note"] == note

    # Listing/lineage/liveness/review fields the consumers rely on survive.
    metadata = report["metadata"]
    assert metadata["reviewed"] is True
    assert metadata["review_verdict"] == "PASS"
    assert metadata["review_note_present"] is True
    assert metadata["review_event_present"] is True
    assert metadata["status"] == "PASS"
    assert metadata["normalized_status"] == "PASS"
    assert metadata["execution_status"] == "PASS"
    assert metadata["terminal"] is True
    assert metadata["result_available"] is True
    assert metadata["project_id"] == "cloud-assets-activation"
    assert metadata["root_task_id"] == PARENT_TASK_ID
    assert metadata["dispatch_state"] == "CONFIRMED"
    assert metadata["dispatch_attempt"] == 1
    assert metadata["created_at"] and metadata["updated_at"]

    # Listing still enumerates the task (now reviewed, so not pending-review).
    assert report["listing"]["counts"]["total"] == 1


@pytest.mark.parametrize("verdict", ["PASS", "FAIL", "BLOCKED"])
def test_worker_long_review_note_bounds_all_verdicts(verdict: str) -> None:
    report = run_worker_metadata_probe(note=LONG_ENGLISH_NOTE, verdict=verdict, times=1)

    assert report["violations"] == []
    assert report["metadata"]["review_verdict"] == verdict
    assert report["stored"]["review_event"]["verdict"] == verdict
    assert report["stored"]["review_note"] == LONG_ENGLISH_NOTE
    for put in report["putLog"]:
        assert put["metadata_bytes"] <= MAX_METADATA_BYTES


def test_worker_long_review_note_replay_is_idempotent_and_bounded() -> None:
    report = run_worker_metadata_probe(note=LONG_CHINESE_NOTE, times=2)

    first = structured(report["results"][0])
    second = structured(report["results"][1])
    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert first["review_verdict"] == "PASS"
    assert second["review_verdict"] == "PASS"
    assert report["violations"] == []
    # A replay without an approved child never rewrites the registry record.
    assert report["putsAfterReviews"] == 1
    for put in report["putLog"]:
        assert put["metadata_bytes"] <= MAX_METADATA_BYTES


def test_worker_long_review_note_without_approved_next_task_dispatches_nothing() -> None:
    report = run_worker_metadata_probe(note=LONG_ENGLISH_NOTE, times=1)

    assert report["dispatchCalls"] == []
    result = structured(report["results"][0])
    assert result["child_dispatch"]["dispatched"] is False
    assert result["child_dispatch"]["reason"] == "NO_APPROVED_NEXT_TASK"
    assert report["violations"] == []


def test_worker_long_review_note_with_approved_child_preserves_dispatch() -> None:
    report = run_worker_metadata_probe(
        note=LONG_ENGLISH_NOTE, approved=approved_child(), times=1
    )

    assert len(report["dispatchCalls"]) == 1
    result = structured(report["results"][0])
    assert result["child_dispatch"]["dispatched"] is True
    child_task_id = result["child_dispatch"]["child_task_id"]
    assert child_task_id
    assert report["violations"] == []
    stored = report["stored"]
    assert stored["review_note"] == LONG_ENGLISH_NOTE
    assert stored["review_dispatch"]["child_task_id"] == child_task_id
    for put in report["putLog"]:
        assert put["metadata_bytes"] <= MAX_METADATA_BYTES


def test_worker_abnormal_large_fields_are_bounded_and_not_leaked() -> None:
    huge_title = "标题" * 500
    secret_blob = "token=super-secret-value " * 200
    task = metadata_task(title=huge_title, secret_blob=secret_blob)

    report = run_worker_metadata_probe(note=LONG_CHINESE_NOTE, task=task, times=1)

    assert report["violations"] == []
    metadata = report["metadata"]
    # Unknown oversized fields are not copied into metadata at all.
    assert "secret_blob" not in metadata
    assert "super-secret-value" not in json.dumps(metadata, ensure_ascii=False)
    # A pathological title is capped, never emitted whole.
    assert utf8_len(metadata["title"]) <= MAX_METADATA_BYTES
    assert metadata["title"] != huge_title
    # The full original content still round-trips through the value.
    assert report["stored"]["secret_blob"] == secret_blob
    assert report["stored"]["title"] == huge_title
