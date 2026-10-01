"""HERMES_REAL_RUNTIME_INTEGRATION_GOLDEN_V1 tests.

These tests prove the honesty contract of
``src/personal_ai_execution/hermes_orchestration.py``:

* A real runtime must be positively identified; adapter code is not evidence.
* With no runtime present the Golden POC returns ``BLOCKED``/``PARTIAL`` and
  names the smallest missing dependency.  It never fabricates ``PASS``.
* Mocks/stubs are never used as Golden evidence.
* A Codex executor can never be accepted on the Golden path.
* The produced expected files satisfy the existing Execution V2 publication
  guard.

A real end-to-end Golden run is gated behind ``HERMES_GOLDEN_RUNTIME=1`` and
skipped otherwise; it requires an actual Hermes gateway.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from personal_ai_execution.hermes_orchestration import (
    GOLDEN_PATH_BLOCKED,
    GOLDEN_PATH_PARTIAL,
    STATUS_BLOCKED,
    STATUS_FAIL,
    STATUS_PARTIAL,
    STATUS_PASS,
    HermesOrchestrationAdapter,
    build_task_contract,
    normalize_hermes_evidence,
    normalize_to_execution_v2,
    probe_hermes_runtime,
    run_hermes_golden_poc,
    validate_task_contract,
    _extract_executor_identity,
    _extract_task_state,
    _extract_task_id,
    _is_codex,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = [
    REPO_ROOT / "src" / "personal_ai_execution" / "hermes_orchestration.py",
    REPO_ROOT / "tests" / "test_hermes_golden_poc.py",
]


# --- helpers -----------------------------------------------------------------


def _absent_env() -> dict[str, str]:
    return {}


def _no_executable(_name: str) -> None:
    return None


def _unreachable(_url: str, _timeout: float):
    raise OSError("connection refused")


def _no_containers() -> list:
    return []


def absent_probe() -> dict:
    return probe_hermes_runtime(
        _absent_env(),
        which=_no_executable,
        urlopen=_unreachable,
        container_lister=_no_containers,
    )


def harmless_contract() -> dict:
    return build_task_contract(
        task_id="cf-harmless-001",
        goal="Return a deterministic nonce through a real Hermes executor.",
        instructions=[
            "Echo the deterministic nonce and nothing else.",
            "Do not write to any canonical store.",
        ],
        acceptance=["Structured result with echoed nonce and executor identity."],
        expected_files=["src/personal_ai_execution/hermes_orchestration.py"],
    )


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> bool:
        return False


def _agent_card_urlopen(_url: str, _timeout: float):
    return _FakeResponse(
        {
            "name": "hermes-agent",
            "version": "1.0.0",
            "url": "https://hermes.example/a2a",
            "protocolVersion": "1.0",
            "capabilities": {"streaming": True},
        }
    )


def _completed_payload(executor: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": "req-1",
        "result": {
            "id": "task-real-001",
            "status": {"state": "TASK_STATE_COMPLETED"},
            "artifacts": [{"parts": [{"kind": "text", "text": "nonce-ok"}]}],
            "metadata": {"executor": executor},
        },
    }


# --- runtime identification --------------------------------------------------


def test_probe_reports_runtime_absent_with_minimal_dependency():
    probe = absent_probe()
    assert probe["runtime_present"] is False
    assert probe["missing_dependency"] == "reachable_real_hermes_runtime"
    assert probe["next_action"]
    assert probe["agent_card"] is None
    assert any("no A2A agent card" in e["detail"] for e in probe["evidence"])


def test_probe_detects_runtime_from_live_agent_card():
    probe = probe_hermes_runtime(
        _absent_env(),
        which=_no_executable,
        urlopen=_agent_card_urlopen,
        container_lister=_no_containers,
    )
    assert probe["runtime_present"] is True
    assert probe["runtime_kind"] == "hermes_a2a_gateway"
    assert probe["agent_card"]["name"] == "hermes-agent"
    assert probe["missing_dependency"] is None


def test_probe_detects_runtime_from_executable_only():
    probe = probe_hermes_runtime(
        _absent_env(),
        which=lambda name: "/usr/local/bin/hermes" if name == "hermes" else None,
        urlopen=_unreachable,
        container_lister=_no_containers,
    )
    assert probe["runtime_present"] is True
    assert "hermes" in probe["executables"]


def test_probe_never_reads_credential_values():
    env = {"A2A_BEARER_TOKEN": "super-secret-value"}
    probe = probe_hermes_runtime(
        env,
        which=_no_executable,
        urlopen=_unreachable,
        container_lister=_no_containers,
    )
    assert probe["credential_source"] == "A2A_BEARER_TOKEN"
    serialized = json.dumps(probe)
    assert "super-secret-value" not in serialized


# --- honest golden outcome ---------------------------------------------------


def test_golden_poc_blocks_when_no_runtime_and_names_dependency():
    packet = run_hermes_golden_poc(harmless_contract(), probe=absent_probe())
    assert packet["final_status"] == STATUS_BLOCKED
    assert packet["golden_path"] == GOLDEN_PATH_BLOCKED
    assert packet["runtime_present"] is False
    assert packet["missing_dependency"] == "reachable_real_hermes_runtime"
    assert packet["next_action"]


def test_golden_poc_never_fabricates_pass_without_runtime():
    packet = run_hermes_golden_poc(harmless_contract(), probe=absent_probe())
    assert packet["final_status"] != STATUS_PASS
    assert packet["golden_path"] != "PASS"
    assert packet["used_mock_or_stub"] is False
    assert packet["evidence_kind"] == "runtime_absent_audit"


def test_golden_poc_declares_no_side_effects():
    packet = run_hermes_golden_poc(harmless_contract(), probe=absent_probe())
    assert packet["canonical_write_performed"] is False
    assert packet["second_state_store_created"] is False
    assert packet["schema_or_binding_mutated"] is False
    assert packet["codex_required"] is False


def test_execution_blocked_does_not_call_transport():
    called = {"n": 0}

    def forbidden_transport(*_args, **_kwargs):
        called["n"] += 1
        raise AssertionError("transport must not be called without a runtime")

    adapter = HermesOrchestrationAdapter(
        probe_result=absent_probe(), transport=forbidden_transport
    )
    execution = adapter.execute(harmless_contract())
    assert execution["ok"] is False
    assert execution["status"] == STATUS_BLOCKED
    assert execution["error_class"] == "runtime_unavailable"
    assert called["n"] == 0


# --- non-Codex requirement ---------------------------------------------------


def test_codex_executor_is_never_accepted():
    probe = {"runtime_present": True, "endpoint": "https://hermes.example/a2a"}
    adapter = HermesOrchestrationAdapter(
        probe_result=probe,
        transport=lambda *_args: _completed_payload("codex-cli"),
    )
    execution = adapter.execute(harmless_contract())
    assert execution["status"] == STATUS_FAIL
    assert execution["ok"] is False
    assert execution["error_class"] == "codex_executor_rejected"


def test_executor_identity_extraction_and_codex_detection():
    payload = _completed_payload("hermes-native-hand")
    assert _extract_executor_identity(payload) == "hermes-native-hand"
    assert _is_codex("hermes-native-hand") is False
    assert _is_codex("Codex CLI") is True
    assert _is_codex("") is False


def test_task_state_and_id_extraction():
    payload = _completed_payload("hermes-native-hand")
    assert _extract_task_state(payload) == "TASK_STATE_COMPLETED"
    assert _extract_task_id(payload) == "task-real-001"


# --- normalization toward GPT review ----------------------------------------


def test_normalization_uses_existing_fail_closed_guard():
    packet = run_hermes_golden_poc(harmless_contract(), probe=absent_probe())
    # A workflow failure must override any advisory self-report.
    normalized = normalize_to_execution_v2(
        packet, workflow_conclusion_value="failure"
    )
    assert normalized["authoritative_status"] == "FAIL"
    assert normalized["conclusion_authoritative"] is True


def test_normalization_marks_missing_expected_files():
    packet = run_hermes_golden_poc(harmless_contract(), probe=absent_probe())
    packet = dict(packet)
    packet["final_status"] = STATUS_PASS
    packet["expected_files"] = ["src/a.py"]
    packet["changed_files"] = []
    normalized = normalize_to_execution_v2(
        packet, workflow_conclusion_value="success"
    )
    assert normalized["authoritative_status"] == "FAIL"
    assert normalized["missing_expected_files"] == ["src/a.py"]


def test_normalize_hermes_evidence_marks_partial_when_runtime_present_but_not_proven():
    probe = {"runtime_present": True, "endpoint": "https://hermes.example/a2a"}
    execution = {
        "ok": False,
        "status": STATUS_PARTIAL,
        "endpoint": "https://hermes.example/a2a",
    }
    packet = normalize_hermes_evidence(harmless_contract(), probe, execution)
    assert packet["final_status"] == STATUS_PARTIAL
    assert packet["golden_path"] == GOLDEN_PATH_PARTIAL


# --- task contract -----------------------------------------------------------


def test_task_contract_builder_and_validation():
    contract = harmless_contract()
    assert validate_task_contract(contract) == []
    broken = dict(contract)
    broken.pop("acceptance")
    assert any("acceptance" in e for e in validate_task_contract(broken))


def test_task_contract_rejects_forbidden_expected_file():
    contract = harmless_contract()
    contract["expected_files"] = [".github/workflows/ci.yml"]
    errors = validate_task_contract(contract)
    assert any("forbidden" in e for e in errors)


# --- publication guard (fixes expected-files downgrade) ----------------------


def test_expected_files_produced_for_publication_guard():
    for path in EXPECTED_FILES:
        assert path.is_file(), f"expected file not produced: {path}"


# --- optional real integration (requires an actual runtime) ------------------


@pytest.mark.skipif(
    os.environ.get("HERMES_GOLDEN_RUNTIME") != "1",
    reason="set HERMES_GOLDEN_RUNTIME=1 and provide a real Hermes gateway",
)
def test_real_hermes_runtime_golden_optional():
    probe = probe_hermes_runtime()
    if not probe["runtime_present"]:
        pytest.skip(f"no real Hermes runtime: {probe['missing_dependency']}")
    packet = run_hermes_golden_poc(harmless_contract(), probe=probe)
    assert packet["evidence_kind"] == "real_runtime"
    assert packet["executor_identity"]
    assert packet["hermes_task_id"]
    assert packet["final_status"] in {STATUS_PASS, STATUS_PARTIAL, STATUS_FAIL}
