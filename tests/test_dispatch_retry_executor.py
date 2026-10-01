"""Tests for CLOUD_AGENT_DISPATCH_RETRY_EXECUTOR_V0.1.

This is the bounded, non-production retry executor follow-up to
``CLOUD_AGENT_QUEUED_RUN_CANCELLATION_FIX_V0.1``. It exercises the *production*
Worker source (``worker/index.js``) under Node with a mocked KV ``TASK_REGISTRY``,
a mocked D1 ``ASSET_DB`` (``task_dispatch_markers`` with ``INSERT OR IGNORE``
semantics) and a mocked ``fetch``.

Behaviour under test:

* ``toolSubmitTask`` pre-writes the bounded dispatch lease *before* the outbound
  ``repository_dispatch`` HTTP call and finalizes it truthfully to ``ACCEPTED``
  or ``DISPATCH_FAILED`` (never a silent permanent ``PENDING``).
* the retry executor consumes the read-only ``plan_task_redispatch`` decision,
  claims the deterministic ``retry:<task_id>:<attempt>`` key through the existing
  D1 marker before any redispatch, and re-issues the *same* ``task_id``.
* concurrent retries converge on exactly one accepted redispatch and never
  duplicate the registry record.
* retries are bounded; exhaustion surfaces as ``inspect`` instead of an infinite
  loop or a silent ``PENDING``.
* authoritative (completed / reviewed) results are never downgraded or retried.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from personal_ai_execution import (
    ACTION_INSPECT,
    ACTION_RETRY,
    MAX_DISPATCH_ATTEMPTS,
    TASK_DISPATCH_STATE_ACCEPTED,
    TASK_DISPATCH_STATE_CONFIRMED,
    TASK_DISPATCH_STATE_EXHAUSTED,
    TASK_DISPATCH_STATE_FAILED,
    TASK_DISPATCH_STATE_PENDING,
    TASK_DISPATCH_STATE_RETRY,
    plan_dispatch_retry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
NODE = shutil.which("node")

TASK_ID = "cf-retry-executor"


# -- task/contract fixtures --------------------------------------------------


def dispatch_contract(task_id: str = TASK_ID) -> dict:
    return {
        "task_id": task_id,
        "goal": "queued dispatch cancelled",
        "instructions": ["redispatch the same task"],
        "acceptance": ["bounded retry completed"],
        "risk_level": "LOW",
        "expected_files": ["worker/index.js"],
    }


_OMIT = object()


def retryable_task(
    task_id: str = TASK_ID,
    *,
    attempt: int = 1,
    state: str = TASK_DISPATCH_STATE_ACCEPTED,
    accepted_seconds_ago: int = 16 * 60,
    contract: object = _OMIT,
    **extra: object,
) -> dict:
    accepted = datetime.now(timezone.utc) - timedelta(seconds=accepted_seconds_ago)
    record: dict[str, object] = {
        "task_id": task_id,
        "status": "PENDING",
        "normalized_status": None,
        "execution_status": "PENDING",
        "terminal": False,
        "result_available": False,
        "reviewed": False,
        "review_verdict": None,
        "title": "queued dispatch cancelled",
        "dispatch_state": state,
        "dispatch_attempt": attempt,
        "dispatch_accepted_at": accepted.isoformat(),
        "dispatch_contract": dispatch_contract(task_id) if contract is _OMIT else contract,
    }
    record.update(extra)
    return record


# -- shared harness fragments ------------------------------------------------


KV_MOCK = r"""
const kv = new Map();
const putLog = [];
const order = [];
function seedTask(task) { kv.set("task:" + task.task_id, JSON.stringify(task)); }
"""

KV_ENV = r"""
  TASK_REGISTRY: {
    get: async function(key, type) {
      const raw = kv.has(key) ? kv.get(key) : null;
      if (raw == null) return null;
      return type === "json" ? JSON.parse(raw) : raw;
    },
    put: async function(key, value, opts) {
      order.push("put:" + key);
      putLog.push({ key: key, value: JSON.parse(value), metadata: opts && opts.metadata });
      kv.set(key, value);
    },
    list: async function() { return { keys: [] }; }
  }
"""

D1_MOCK = r"""
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
"""

SUBMIT_HARNESS = (
    KV_MOCK
    + r"""
const env = {
  GITHUB_REPO: "owner/repo",
  GITHUB_TOKEN: "test-token",
"""
    + KV_ENV
    + r"""
};
const dispatchCalls = [];
globalThis.fetch = async function(url, options) {
  order.push("fetch");
  if (__FETCH_THROW__) throw new Error("network down");
  dispatchCalls.push({ url: String(url), body: options && options.body ? JSON.parse(options.body) : null });
  return {
    ok: __FETCH_OK__,
    status: __FETCH_STATUS__,
    headers: { get: function(n) { return n === "x-github-request-id" ? "req-1" : null; } },
    text: async function() { return ""; }
  };
};
const outcome = await toolSubmitTask(env, __ARGS_JS__);
console.log(JSON.stringify({
  outcome: outcome,
  kv: Object.fromEntries(Array.from(kv.entries()).map(function(e) { return [e[0], JSON.parse(e[1])]; })),
  putLog: putLog,
  dispatchCalls: dispatchCalls,
  order: order
}));
"""
)

RETRY_HARNESS = (
    KV_MOCK
    + D1_MOCK
    + r"""
const env = {
  GITHUB_REPO: "owner/repo",
  GITHUB_TOKEN: "test-token",
  ASSET_DB: makeD1(),
"""
    + KV_ENV
    + r"""
};
const dispatchCalls = [];
const artifactCalls = [];
globalThis.fetch = async function(url, options) {
  const u = String(url);
  if (u.indexOf("/actions/artifacts?") !== -1) {
    artifactCalls.push(u);
    return {
      ok: true, status: 200,
      headers: { get: function() { return null; } },
      json: async function() { return { artifacts: __ARTIFACTS__ }; },
      text: async function() { return ""; }
    };
  }
  dispatchCalls.push({ url: u, body: options && options.body ? JSON.parse(options.body) : null });
  return {
    ok: __FETCH_OK__,
    status: __FETCH_STATUS__,
    headers: { get: function(n) { return n === "x-github-request-id" ? "req-1" : null; } },
    text: async function() { return ""; }
  };
};
const TASK_ID = __CALL_TASK_ID__;
seedTask(__TASK_JSON__);
const calls = [];
for (let i = 0; i < __TIMES__; i++) calls.push(retryDispatchTask(env, { task_id: TASK_ID }));
const results = await Promise.all(calls);
console.log(JSON.stringify({
  results: results,
  dispatchCalls: dispatchCalls,
  artifactCalls: artifactCalls,
  markerRows: Array.from(markerRows.values()),
  kv: Object.fromEntries(Array.from(kv.entries()).map(function(e) { return [e[0], JSON.parse(e[1])]; })),
  putLog: putLog
}));
"""
)


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


def run_submit_probe(
    *,
    fetch_ok: bool = True,
    fetch_status: int = 204,
    fetch_throw: bool = False,
) -> dict:
    script = SUBMIT_HARNESS
    script = script.replace("__FETCH_THROW__", "true" if fetch_throw else "false")
    script = script.replace("__FETCH_OK__", "true" if fetch_ok else "false")
    script = script.replace("__FETCH_STATUS__", str(fetch_status))
    args = {
        "goal": "queue and dispatch",
        "instructions": ["do it"],
        "acceptance": ["done"],
        "expected_files": ["worker/index.js"],
    }
    script = script.replace("__ARGS_JS__", json.dumps(args))
    return run_worker_probe(script)


def run_retry_probe(
    task: dict,
    *,
    times: int = 1,
    fetch_ok: bool = True,
    fetch_status: int = 204,
    artifacts: list | None = None,
    call_task_id: str | None = None,
) -> dict:
    script = RETRY_HARNESS
    script = script.replace("__TASK_JSON__", json.dumps(task))
    script = script.replace(
        "__CALL_TASK_ID__", json.dumps(call_task_id or task["task_id"])
    )
    script = script.replace("__TIMES__", str(times))
    script = script.replace("__FETCH_OK__", "true" if fetch_ok else "false")
    script = script.replace("__FETCH_STATUS__", str(fetch_status))
    script = script.replace("__ARTIFACTS__", json.dumps(artifacts or []))
    return run_worker_probe(script)


def entry(probe_result: dict) -> dict:
    return probe_result.get("structuredContent", json.loads(probe_result["text"]))


# -- submit: lease pre-write + truthful finalize -----------------------------


def test_submit_task_prewrites_lease_before_dispatch_and_finalizes_accepted() -> None:
    report = run_submit_probe()
    outcome = report["outcome"]

    assert outcome["isError"] is False
    assert report["order"][0].startswith("put:")
    assert report["order"][1] == "fetch"
    assert len(report["dispatchCalls"]) == 1

    task = report["dispatchCalls"][0]["body"]["client_payload"]["task"]
    stored = report["kv"]["task:" + task["task_id"]]
    assert stored["dispatch_state"] == TASK_DISPATCH_STATE_ACCEPTED
    assert stored["dispatch_attempt"] == 1
    assert stored["dispatch_accepted_at"]
    assert stored["dispatch_confirm_deadline"]
    assert stored["status"] == "PENDING"
    assert stored["terminal"] is False
    assert stored["result_available"] is False
    assert stored["dispatch_contract"]["goal"] == "queue and dispatch"

    result = entry(outcome)
    assert result["dispatch_state"] == TASK_DISPATCH_STATE_ACCEPTED
    assert result["dispatch_status"] == "accepted"

    # The contract is persisted in the value only, never in KV metadata
    # (which has a 1024-byte limit).
    assert "dispatch_contract" not in report["putLog"][0]["metadata"]
    assert report["putLog"][0]["value"]["dispatch_contract"]["goal"] == "queue and dispatch"


def test_submit_task_github_rejection_finalizes_dispatch_failed() -> None:
    report = run_submit_probe(fetch_ok=False, fetch_status=422)
    outcome = report["outcome"]

    assert outcome["isError"] is True
    task = report["dispatchCalls"][0]["body"]["client_payload"]["task"]
    stored = report["kv"]["task:" + task["task_id"]]
    assert stored["dispatch_state"] == TASK_DISPATCH_STATE_FAILED
    assert stored["status"] == "PENDING"
    assert stored["terminal"] is False

    result = entry(outcome)
    assert result["dispatch_state"] == TASK_DISPATCH_STATE_FAILED
    assert result["dispatch_status"] == "github_rejected"
    # A failed task is still inspectable rather than silently absent.
    assert len(report["putLog"]) >= 2


def test_submit_task_network_error_finalizes_dispatch_failed() -> None:
    report = run_submit_probe(fetch_throw=True)
    outcome = report["outcome"]

    # The pre-write still happened, so no permanent silent PENDING is possible.
    assert len(report["putLog"]) >= 1
    assert outcome["isError"] is True
    result = entry(outcome)
    assert result["dispatch_state"] == TASK_DISPATCH_STATE_FAILED
    assert result["dispatch_status"] == "network_error"


# -- bounded retry executor --------------------------------------------------


def test_unconfirmed_timeout_redispatches_same_task_id() -> None:
    report = run_retry_probe(retryable_task())
    assert len(report["dispatchCalls"]) == 1
    assert len(report["results"]) == 1

    result = entry(report["results"][0])
    assert result["retried"] is True
    assert result["dispatched"] is True
    assert result["dispatch_state"] == TASK_DISPATCH_STATE_RETRY
    assert result["reason"] == "REDISPATCHED"
    assert result["idempotency_key"] == f"retry:{TASK_ID}:2"
    assert result["next_attempt"] == 2

    # Re-dispatched with the SAME task_id.
    task = report["dispatchCalls"][0]["body"]["client_payload"]["task"]
    assert task["task_id"] == TASK_ID

    # Exactly one deterministic claim, and the registry record is not duplicated.
    assert len(report["markerRows"]) == 1
    marker = report["markerRows"][0]
    assert marker["dispatch_key"] == f"retry:{TASK_ID}:2"
    assert marker["child_task_id"] == TASK_ID
    assert marker["review_verdict"] == "RETRY"
    assert marker["dispatch_state"] == "DISPATCHED"
    assert list(report["kv"].keys()) == ["task:" + TASK_ID]

    stored = report["kv"]["task:" + TASK_ID]
    assert stored["dispatch_attempt"] == 2
    assert stored["dispatch_state"] == TASK_DISPATCH_STATE_RETRY
    # Non-authoritative execution state is preserved, never fabricated.
    assert stored["status"] == "PENDING"
    assert stored["terminal"] is False
    assert stored["result_available"] is False
    assert stored["reviewed"] is False


def test_concurrent_retries_converge_to_one_redispatch() -> None:
    report = run_retry_probe(retryable_task(), times=2)

    results = [entry(r) for r in report["results"]]
    assert len(report["dispatchCalls"]) == 1
    assert len(report["markerRows"]) == 1
    assert sum(1 for r in results if r["retried"] is True) == 1
    assert sum(1 for r in results if r["idempotent"] is True) == 1
    losers = [r for r in results if r["idempotent"] is True]
    assert losers[0]["reason"] == "ALREADY_RETRIED"
    assert losers[0]["idempotency_key"] == f"retry:{TASK_ID}:2"
    # No duplicate execution record.
    assert list(report["kv"].keys()) == ["task:" + TASK_ID]


def test_retry_exhaustion_is_inspectable_not_permanent_pending() -> None:
    report = run_retry_probe(
        retryable_task(attempt=MAX_DISPATCH_ATTEMPTS), times=1
    )

    assert report["dispatchCalls"] == []
    assert report["markerRows"] == []
    result = entry(report["results"][0])
    assert result["retried"] is False
    assert result["dispatch_state"] == TASK_DISPATCH_STATE_EXHAUSTED
    assert result["recommended_action"] == ACTION_INSPECT
    assert result["reason"] == "NOT_RETRYABLE"
    # No write at all: exhaustion is surfaced, not looped.
    assert report["putLog"] == []


def test_failed_redispatch_is_bounded_and_marks_failed() -> None:
    report = run_retry_probe(
        retryable_task(), fetch_ok=False, fetch_status=422
    )

    assert len(report["dispatchCalls"]) == 1
    result = entry(report["results"][0])
    assert result["dispatched"] is False
    assert result["dispatch_state"] == TASK_DISPATCH_STATE_FAILED
    assert result["reason"] == "RETRY_DISPATCH_FAILED"
    assert result["next_attempt"] == 2
    assert len(report["markerRows"]) == 1
    assert report["markerRows"][0]["dispatch_state"] == "FAILED"

    stored = report["kv"]["task:" + TASK_ID]
    assert stored["dispatch_attempt"] == 2
    assert stored["dispatch_state"] == TASK_DISPATCH_STATE_FAILED
    assert stored["status"] == "PENDING"

    # A second retry attempt is still bounded by the max-attempt policy; the
    # next attempt key is deterministic.
    report2 = run_retry_probe(
        retryable_task(attempt=2, state=TASK_DISPATCH_STATE_FAILED)
    )
    result2 = entry(report2["results"][0])
    assert result2["idempotency_key"] == f"retry:{TASK_ID}:3"
    assert result2["retried"] is True


def test_authoritative_completed_result_is_never_retried() -> None:
    report = run_retry_probe(
        retryable_task(
            terminal=True,
            result_available=True,
            normalized_status="PASS",
        )
    )

    assert report["dispatchCalls"] == []
    assert report["markerRows"] == []
    result = entry(report["results"][0])
    assert result["retried"] is False
    assert result["dispatch_state"] == TASK_DISPATCH_STATE_CONFIRMED
    assert result["reason"] == "AUTHORITATIVE_RESULT"
    # No lease/status mutation whatsoever.
    assert report["putLog"] == []


def test_authoritative_reviewed_task_is_never_retried() -> None:
    report = run_retry_probe(
        retryable_task(reviewed=True, review_verdict="PASS")
    )

    assert report["dispatchCalls"] == []
    assert report["markerRows"] == []
    result = entry(report["results"][0])
    assert result["retried"] is False
    assert result["reason"] == "AUTHORITATIVE_RESULT"


def test_missing_dispatch_contract_fails_closed() -> None:
    report = run_retry_probe(retryable_task(contract=None))

    assert report["dispatchCalls"] == []
    assert report["markerRows"] == []
    result = entry(report["results"][0])
    assert result["retried"] is False
    assert result["reason"] == "NO_DISPATCH_CONTRACT"
    assert result["errors"]


def test_retry_unknown_task_fails_closed() -> None:
    report = run_retry_probe(
        retryable_task(task_id="cf-seeded"),
        times=1,
        call_task_id="cf-missing",
    )
    assert report["dispatchCalls"] == []
    assert report["markerRows"] == []
    assert report["results"][0]["isError"] is True
    assert "UNKNOWN_TASK" in report["results"][0]["text"]


def test_fresh_lease_is_not_retried() -> None:
    report = run_retry_probe(retryable_task(accepted_seconds_ago=30))

    assert report["dispatchCalls"] == []
    assert report["markerRows"] == []
    result = entry(report["results"][0])
    assert result["retried"] is False
    assert result["reason"] == "NOT_RETRYABLE"


# -- Python-level invariants -------------------------------------------------


def test_python_planner_never_retries_authoritative_records() -> None:
    for keyword in ({"terminal": True}, {"result_available": True}, {"reviewed": True}):
        record = retryable_task(accepted_seconds_ago=16 * 60, **keyword)
        plan = plan_dispatch_retry(record)
        assert plan["should_retry"] is False
        assert plan["idempotency_key"] is None


def test_python_planner_retry_key_is_deterministic() -> None:
    first = plan_dispatch_retry(retryable_task())
    second = plan_dispatch_retry(retryable_task())
    assert first["should_retry"] is True
    assert first["recommended_action"] == ACTION_RETRY
    assert first["idempotency_key"] == second["idempotency_key"] == f"retry:{TASK_ID}:2"
    assert first["same_task_id"] is True


def test_worker_source_encodes_the_retry_executor() -> None:
    source = worker_source()
    for token in (
        "retry_task_dispatch",
        "retryDispatchTask",
        "retryDispatchKey",
        "retry:",
        "claimDispatchMarker",
        "updateDispatchLease",
        "dispatch_contract",
        "REDISPATCHED",
        "ALREADY_RETRIED",
        "AUTHORITATIVE_RESULT",
        "NOT_RETRYABLE",
        "NO_DISPATCH_CONTRACT",
        "PENDING_DISPATCH",
        "DISPATCH_FAILED",
    ):
        assert token in source, f"worker is missing retry executor token {token}"
