"""``CLOUD_AGENT_SUBMIT_TASK_MODE_PASSTHROUGH_ADAPTER_V0.1`` focused tests.

The Cloud Agent ``submit_task`` surface must carry a bounded ``readonly`` /
``write`` mode from the MCP submit call through the ``repository_dispatch`` /
task payload into the already released Gate mode resolver
(``scripts/task_contract.py``). These tests execute the *production* Worker
source (``worker/index.js``) under Node with a mocked ``TASK_REGISTRY`` and
``fetch``, capture the exact ``client_payload.task`` that would be dispatched,
and then run the real Gate 1 evaluator against that captured contract.

Pinned behaviour:

* ``mode=readonly`` reaches the dispatched contract and the Gate resolver sees
  it (a readonly contract may declare ``expected_files = []``);
* ``mode=write`` reaches the dispatched contract and the Gate resolver sees it;
* a missing / empty mode defaults to ``write`` (and keeps the backwards
  compatible default allowlist);
* an unknown mode fails closed at the submit surface and dispatches nothing.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
TASK_CONTRACT_PATH = REPO_ROOT / "scripts" / "task_contract.py"

NODE = shutil.which("node")


def _load_gate():
    spec = importlib.util.spec_from_file_location("task_contract_under_test", TASK_CONTRACT_PATH)
    assert spec and spec.loader, "cannot load scripts/task_contract.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


task_contract = _load_gate()


SUBMIT_HARNESS = r"""
const kv = new Map();
const putLog = [];
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
    put: async function(key, value, opts) {
      putLog.push({ key: key, value: JSON.parse(value) });
      kv.set(key, value);
    },
    list: async function() { return { keys: [] }; }
  }
};
const dispatchCalls = [];
globalThis.fetch = async function(url, options) {
  dispatchCalls.push({ url: String(url), body: options && options.body ? JSON.parse(options.body) : null });
  return {
    ok: true,
    status: 204,
    headers: { get: function(n) { return n === "x-github-request-id" ? "req-1" : null; } },
    text: async function() { return ""; }
  };
};
const outcome = await toolSubmitTask(env, __ARGS_JS__);
console.log(JSON.stringify({
  outcome: outcome,
  dispatchCalls: dispatchCalls,
  kv: Object.fromEntries(Array.from(kv.entries()).map(function(e) { return [e[0], JSON.parse(e[1])]; }))
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


def run_submit(args: dict) -> dict:
    script = SUBMIT_HARNESS.replace("__ARGS_JS__", json.dumps(args))
    return run_worker_probe(script)


def _base_args(**overrides) -> dict:
    args = {
        "goal": "mode passthrough probe",
        "instructions": ["carry the mode to the gate"],
        "acceptance": ["mode reaches the gate"],
    }
    args.update(overrides)
    return args


def _dispatched_contract(report: dict) -> dict:
    assert len(report["dispatchCalls"]) == 1, report
    call = report["dispatchCalls"][0]
    assert call["url"].endswith("/repos/owner/repo/dispatches")
    assert call["body"]["event_type"] == "gpt_task"
    return call["body"]["client_payload"]["task"]


# --- submit surface -> dispatched contract ---------------------------------


def test_submit_readonly_mode_is_preserved_in_dispatched_contract() -> None:
    report = run_submit(_base_args(mode="readonly", expected_files=[]))
    assert json.loads(report["outcome"]["text"])["submitted"] is True
    contract = _dispatched_contract(report)
    assert contract["mode"] == "readonly"
    assert contract["expected_files"] == []


def test_submit_write_mode_is_preserved_in_dispatched_contract() -> None:
    report = run_submit(_base_args(mode="write", expected_files=["worker/index.js"]))
    contract = _dispatched_contract(report)
    assert contract["mode"] == "write"
    assert contract["expected_files"] == ["worker/index.js"]


def test_submit_missing_mode_defaults_to_write() -> None:
    report = run_submit(_base_args(expected_files=["worker/index.js"]))
    contract = _dispatched_contract(report)
    assert contract["mode"] == "write"


def test_submit_missing_mode_without_expected_files_keeps_default_allowlist() -> None:
    report = run_submit(_base_args())
    contract = _dispatched_contract(report)
    assert contract["mode"] == "write"
    assert contract["expected_files"] == ["hello.py", "test_hello.py"]


def test_submit_readonly_without_expected_files_defaults_to_empty_allowlist() -> None:
    report = run_submit(_base_args(mode="readonly"))
    contract = _dispatched_contract(report)
    assert contract["mode"] == "readonly"
    assert contract["expected_files"] == []


@pytest.mark.parametrize("mode", ["READONLY", "read_only", "read-only"])
def test_submit_readonly_aliases_are_canonicalized(mode: str) -> None:
    report = run_submit(_base_args(mode=mode))
    contract = _dispatched_contract(report)
    assert contract["mode"] == "readonly"


def test_submit_unknown_mode_fails_closed_and_dispatches_nothing() -> None:
    report = run_submit(_base_args(mode="wildcard", expected_files=["worker/index.js"]))
    assert report["outcome"]["isError"] is True
    assert "mode not acceptable" in report["outcome"]["text"]
    assert report["dispatchCalls"] == []


def test_submit_empty_mode_is_treated_as_write() -> None:
    report = run_submit(_base_args(mode="", expected_files=["worker/index.js"]))
    contract = _dispatched_contract(report)
    assert contract["mode"] == "write"


# --- dispatched contract -> real Gate 1 mode resolver ----------------------


def test_readonly_contract_reaches_gate_with_mode_preserved() -> None:
    report = run_submit(_base_args(mode="readonly", expected_files=[]))
    contract = _dispatched_contract(report)
    assert task_contract.task_mode(contract) == "readonly"
    assert task_contract.evaluate(contract) == []


def test_write_contract_reaches_gate_with_mode_preserved() -> None:
    report = run_submit(_base_args(mode="write", expected_files=["worker/index.js"]))
    contract = _dispatched_contract(report)
    assert task_contract.task_mode(contract) == "write"
    assert task_contract.evaluate(contract) == []


def test_missing_mode_contract_reaches_gate_as_write() -> None:
    report = run_submit(_base_args(expected_files=["worker/index.js"]))
    contract = _dispatched_contract(report)
    assert task_contract.task_mode(contract) == "write"
    assert task_contract.evaluate(contract) == []


def test_dispatched_contract_is_persisted_with_mode() -> None:
    report = run_submit(_base_args(mode="readonly", expected_files=[]))
    contract = _dispatched_contract(report)
    stored = report["kv"]["task:" + contract["task_id"]]
    assert stored["dispatch_contract"]["mode"] == "readonly"
    assert stored["dispatch_contract"]["expected_files"] == []


# --- worker source encodes the passthrough ---------------------------------


def test_worker_source_encodes_the_mode_passthrough() -> None:
    source = worker_source()
    for token in (
        "resolveMode",
        "READONLY_MODES",
        "WRITE_MODES",
        'mode: resolvedMode === null ? String(mode) : resolvedMode',
    ):
        assert token in source, f"worker is missing mode passthrough token {token}"
