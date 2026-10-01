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
    ACK_STATE_ACKNOWLEDGED,
    ACK_STATE_IDEMPOTENT,
    ACK_STATE_LEASE_MISMATCH,
    CLAIM_STATE_CLAIMED,
    CLAIM_STATE_IDEMPOTENT,
    CLAIM_STATE_LEASED_ELSEWHERE,
    CLAIM_STATE_NOT_CLAIMABLE,
    GOLDEN_PATH_BLOCKED,
    GOLDEN_PATH_PARTIAL,
    RESULT_STATE_ACCEPTED,
    RESULT_STATE_DUPLICATE,
    RESULT_STATE_LEASE_MISMATCH,
    RESULT_STATE_REJECTED,
    STATUS_BLOCKED,
    STATUS_FAIL,
    STATUS_PARTIAL,
    STATUS_PASS,
    TRANSPORT_ACK_PATH,
    TRANSPORT_CLAIM_PATH,
    TRANSPORT_CONTRACT_VERSION,
    TRANSPORT_CREDENTIAL_ENV_VARS,
    TRANSPORT_HEALTH_PATH,
    TRANSPORT_RELAY_BASE_PATH,
    TRANSPORT_RESULT_PATH,
    HermesOrchestrationAdapter,
    acknowledge_task,
    audit_windows_hermes_transport,
    build_health_handshake,
    build_task_assignment,
    build_task_contract,
    claim_task,
    compute_evidence_hash,
    evaluate_health_handshake,
    is_transport_claimable,
    normalize_hermes_evidence,
    normalize_to_execution_v2,
    normalize_transport_result,
    plan_result_publication,
    probe_hermes_runtime,
    run_hermes_golden_poc,
    validate_result_envelope,
    validate_task_contract,
    windows_hermes_integration_inputs,
    _extract_executor_identity,
    _extract_task_state,
    _extract_task_id,
    _is_codex,
)

from personal_ai_execution.event_sync import EventSyncRegistry

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


# =============================================================================
# WINDOWS_HERMES_TRANSPORT_CONTRACT_V1
# =============================================================================


def _claimed_record(worker_id: str = "windows-hermes-1") -> tuple[dict, dict]:
    record = {"task_id": "cf-transport-001", "status": "PENDING"}
    claim = claim_task(record, worker_id)
    record.update(claim["registry_patch"])
    return record, claim


def _result_envelope(
    record: dict,
    *,
    task_state: str = "TASK_STATE_COMPLETED",
    executor_identity: str = "hermes-native-hand",
    **overrides,
) -> dict:
    envelope = {
        "contract_version": TRANSPORT_CONTRACT_VERSION,
        "task_id": record["task_id"],
        "worker_id": record["transport_owner_worker_id"],
        "lease_id": record["transport_lease_id"],
        "status": "success",
        "task_state": task_state,
        "executor_identity": executor_identity,
        "tests": "12 passed",
        "artifacts": [{"parts": [{"kind": "text", "text": "nonce-ok"}]}],
        "expected_files": [],
        "changed_files": [],
        "finished_at": "2026-10-01T00:00:00Z",
    }
    envelope.update(overrides)
    envelope["evidence_hash"] = compute_evidence_hash(envelope)
    return envelope


# --- contract surface / no deployment ----------------------------------------


def test_transport_contract_paths_and_direction():
    assert TRANSPORT_RELAY_BASE_PATH == "/hermes/transport/v1"
    assert TRANSPORT_HEALTH_PATH == "/hermes/transport/v1/health"
    assert TRANSPORT_CLAIM_PATH == "/hermes/transport/v1/tasks/claim"
    assert TRANSPORT_ACK_PATH.endswith("/ack")
    assert TRANSPORT_RESULT_PATH.endswith("/result")


def test_audit_reports_minimal_gap_and_no_deployment():
    audit = audit_windows_hermes_transport(EventSyncRegistry())
    assert TRANSPORT_CONTRACT_VERSION == audit["contract_version"]
    assert "task_registry" in audit["reused_existing_surfaces"]
    assert "result_normalization" in audit["reused_existing_surfaces"]
    assert len(audit["missing_relay_capabilities"]) == 4
    assert audit["minimal_gap"]["human_gate_required"] is True
    assert audit["minimal_gap"]["production_deployed"] is False
    assert audit["human_gate_required"] is True
    assert audit["production_deployed"] is False
    assert audit["canonical_write_performed"] is False
    assert audit["second_state_store_created"] is False
    assert audit["credential_or_binding_mutated"] is False
    assert audit["connection_attempted_to_windows"] is False


def test_integration_inputs_are_secret_free_and_complete():
    env = {
        "HERMES_TRANSPORT_TOKEN": "super-secret-transport-value",
        "HERMES_TRANSPORT_URL": "https://personal-ai.example",
    }
    inputs = windows_hermes_integration_inputs(env)
    assert inputs["endpoint_shape"]["base_path"] == TRANSPORT_RELAY_BASE_PATH
    assert inputs["auth_expectation"]["credential_source"] == "HERMES_TRANSPORT_TOKEN"
    assert inputs["auth_expectation"]["credential_env_vars"] == list(
        TRANSPORT_CREDENTIAL_ENV_VARS
    )
    assert inputs["task_contract_fields"]
    assert inputs["result_contract_fields"]
    assert inputs["health_handshake"]["required_fields"]
    assert inputs["no_public_windows_endpoint"] is True
    assert inputs["cloud_deploys_second_hermes"] is False
    assert "super-secret-transport-value" not in json.dumps(inputs)


# --- health handshake --------------------------------------------------------


def test_health_handshake_round_trip_reports_no_secrets():
    handshake = build_health_handshake(
        "windows-hermes-1", capabilities=["hermes.orchestrate"]
    )
    response = evaluate_health_handshake(
        handshake, env={"HERMES_TRANSPORT_TOKEN": "top-secret"}
    )
    assert response["ready"] is True
    assert response["relay_contract_version"] == TRANSPORT_CONTRACT_VERSION
    assert response["auth"]["credential_source"] == "HERMES_TRANSPORT_TOKEN"
    assert response["endpoints"]["claim"] == TRANSPORT_CLAIM_PATH
    assert "top-secret" not in json.dumps(response)


def test_health_handshake_rejects_contract_version_mismatch():
    handshake = build_health_handshake("windows-hermes-1")
    handshake["contract_version"] = "OLD_CONTRACT"
    response = evaluate_health_handshake(handshake)
    assert response["ready"] is False
    assert any("contract_version mismatch" in e for e in response["errors"])


# --- evidence hash + idempotency ---------------------------------------------


def test_evidence_hash_is_stable_and_excludes_volatile_metadata():
    record, _ = _claimed_record()
    envelope = _result_envelope(record)
    hash_a = compute_evidence_hash(envelope)
    envelope_with_extra = {**envelope, "http_retry": 7, "trace_id": "abc"}
    assert compute_evidence_hash(envelope_with_extra) == hash_a
    changed = {**envelope, "task_state": "TASK_STATE_FAILED"}
    assert compute_evidence_hash(changed) != hash_a


def test_idempotency_keys_are_deterministic():
    assert (
        compute_evidence_hash({"task_id": "t", "status": "success"})
        == compute_evidence_hash({"status": "success", "task_id": "t"})
    )


# --- claim / lease -----------------------------------------------------------


def test_claim_then_idempotent_reclaim_and_other_worker_held():
    record, claim = _claimed_record()
    assert claim["claimed"] is True
    assert claim["state"] == CLAIM_STATE_CLAIMED
    assert claim["lease_id"]
    assert claim["registry_patch"]["transport_owner_worker_id"] == "windows-hermes-1"

    repeat = claim_task(record, "windows-hermes-1")
    assert repeat["claimed"] is True
    assert repeat["state"] == CLAIM_STATE_IDEMPOTENT
    assert repeat["lease_id"] == claim["lease_id"]

    other = claim_task(record, "windows-hermes-2")
    assert other["claimed"] is False
    assert other["state"] == CLAIM_STATE_LEASED_ELSEWHERE


def test_claim_reclaims_after_lease_expiry_with_bounded_attempt():
    record, claim = _claimed_record()
    expired = "2000-01-01T00:00:00Z"
    record["transport_lease_expires_at"] = expired
    reclaim = claim_task(record, "windows-hermes-2")
    assert reclaim["claimed"] is True
    assert reclaim["state"] == CLAIM_STATE_CLAIMED
    assert reclaim["attempt"] == claim["attempt"] + 1


def test_terminal_or_reviewed_task_is_not_claimable():
    terminal = {"task_id": "t-terminal", "terminal": True}
    assessment = is_transport_claimable(terminal, worker_id="w")
    assert assessment["claimable"] is False
    assert assessment["reason_code"] == "TASK_TERMINAL"
    decision = claim_task(terminal, "w")
    assert decision["state"] == CLAIM_STATE_NOT_CLAIMABLE


def test_task_assignment_carries_contract_and_lease():
    record, claim = _claimed_record()
    assignment = build_task_assignment(harmless_contract(), claim)
    assert assignment["lease_id"] == claim["lease_id"]
    assert assignment["task_contract"]["task_id"] == "cf-harmless-001"
    assert assignment["contract_version"] == TRANSPORT_CONTRACT_VERSION


# --- ack ---------------------------------------------------------------------


def test_acknowledge_then_idempotent_and_mismatch():
    record, claim = _claimed_record()
    ack = acknowledge_task(
        record,
        task_id=record["task_id"],
        worker_id="windows-hermes-1",
        lease_id=claim["lease_id"],
    )
    assert ack["state"] == ACK_STATE_ACKNOWLEDGED
    assert ack["acknowledged"] is True

    record.update(ack["registry_patch"])
    repeat = acknowledge_task(
        record,
        task_id=record["task_id"],
        worker_id="windows-hermes-1",
        lease_id=claim["lease_id"],
    )
    assert repeat["state"] == ACK_STATE_IDEMPOTENT

    mismatch = acknowledge_task(
        record,
        task_id=record["task_id"],
        worker_id="windows-hermes-1",
        lease_id="lease:wrong",
    )
    assert mismatch["state"] == ACK_STATE_LEASE_MISMATCH


# --- result return -----------------------------------------------------------


def test_result_envelope_validation_requires_fields():
    record, _ = _claimed_record()
    envelope = _result_envelope(record)
    assert validate_result_envelope(envelope) == []
    broken = {k: v for k, v in envelope.items() if k != "evidence_hash"}
    assert any("evidence_hash" in e for e in validate_result_envelope(broken))


def test_non_terminal_task_state_is_rejected():
    record, _ = _claimed_record()
    envelope = _result_envelope(record, task_state="TASK_STATE_WORKING")
    errors = validate_result_envelope(envelope)
    assert any("not terminal" in e for e in errors)


def test_result_accepted_and_normalized_for_completed_non_codex():
    record, _ = _claimed_record()
    envelope = _result_envelope(record)
    decision = normalize_transport_result(record, envelope)
    assert decision["state"] == RESULT_STATE_ACCEPTED
    assert decision["accepted"] is True
    assert decision["normalized_status"] == STATUS_PASS
    assert decision["idempotency_key"].startswith("hermes-result:")
    assert decision["registry_patch"]["transport_result_status"] == STATUS_PASS
    assert decision["canonical_write_performed"] is False


def test_codex_executor_result_is_failed():
    record, _ = _claimed_record()
    envelope = _result_envelope(record, executor_identity="codex-cli")
    decision = normalize_transport_result(record, envelope)
    assert decision["state"] == RESULT_STATE_ACCEPTED
    assert decision["normalized_status"] == STATUS_FAIL


def test_duplicate_result_is_idempotent_and_conflicting_is_rejected():
    record, _ = _claimed_record()
    envelope = _result_envelope(record)
    first = normalize_transport_result(record, envelope)
    record.update(first["registry_patch"])

    duplicate = normalize_transport_result(record, envelope)
    assert duplicate["state"] == RESULT_STATE_DUPLICATE
    assert duplicate["idempotent"] is True

    conflicting = _result_envelope(record, task_state="TASK_STATE_FAILED")
    decision = normalize_transport_result(record, conflicting)
    assert decision["state"] == RESULT_STATE_REJECTED
    assert decision["reason_code"] == "CONFLICTING_DUPLICATE_RESULT"


def test_result_evidence_hash_mismatch_is_rejected():
    record, _ = _claimed_record()
    envelope = _result_envelope(record)
    envelope["evidence_hash"] = "sha256:" + "0" * 64
    decision = normalize_transport_result(record, envelope)
    assert decision["state"] == RESULT_STATE_REJECTED
    assert decision["reason_code"] == "EVIDENCE_HASH_MISMATCH"


def test_result_lease_mismatch_is_rejected():
    record, _ = _claimed_record()
    envelope = _result_envelope(record, lease_id="lease:not-held")
    decision = normalize_transport_result(record, envelope)
    assert decision["state"] == RESULT_STATE_LEASE_MISMATCH


def test_plan_result_publication_reuses_event_sync_and_reports_gap():
    registry = EventSyncRegistry()
    record, _ = _claimed_record()
    registry.submit_task(record["task_id"], goal="windows task")
    envelope = _result_envelope(record)
    decision = plan_result_publication(record, envelope, registry=registry)
    # Existing EVENT_SYNC requires a workflow conclusion, which a Windows
    # transport result cannot carry -- so this is an explicit minimal gap.
    assert decision["event_sync_accepts"] is False
    assert decision["minimal_gap"]["human_gate_required"] is True
    assert decision["minimal_gap"]["production_deployed"] is False


def test_transport_flow_is_secret_free_and_no_windows_inbound_required():
    record, claim = _claimed_record()
    ack = acknowledge_task(
        record,
        task_id=record["task_id"],
        worker_id="windows-hermes-1",
        lease_id=claim["lease_id"],
    )
    record.update(claim["registry_patch"])
    record.update(ack["registry_patch"])
    envelope = _result_envelope(record)
    decision = normalize_transport_result(record, envelope)
    serialized = json.dumps(decision)
    assert "token" not in serialized.lower()
    assert decision["canonical_write_performed"] is False
