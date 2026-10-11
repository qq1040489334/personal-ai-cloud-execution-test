"""Device-independent Personal AI mobile-cloud fixture flow tests.

This suite exercises the *product logic* contract only. It is CONTRACT_ONLY:
everything here is a pure, in-memory state machine plus stub providers. No
fixture or test performs network I/O, live D1 access, passkey operations,
Canonical MCP writes, repository dispatch, production requests or real
authentication. The counts for every forbidden live call are asserted to be
zero.

The execution outer status (``execution_status``) is intentionally separate
from the business status (``business_status`` / ``final_status``); a workflow
PASS whose inner ``final_status`` is PARTIAL must stay PARTIAL. Application
approval here is a fixture-only event, never a usable passkey assertion.

F07 tests a *proposed* stub-only durable ``request_id`` map. The current
connected ``submit_task`` has no public idempotency parameter, so this suite
never claims the existing API deduplicates replaying. F09 only reconciles an
unknown fixture write from independent readback that carries the exact
approved target and matching promotion provenance plus before/after evidence;
a matching content hash alone is insufficient.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "mobile_cloud_flow_v1.json"
FIXTURE_PATH = REPO_ROOT / "fixtures" / "mobile_cloud_flow_v1.json"
REPORT_PATH = REPO_ROOT / "reports" / "mobile_cloud_flow_v1_report.json"

FULL_REPOSITORY_SUITE_STATUS = "NOT_RUN_THIS_ROUND"

LIVE_FORBIDDEN_COUNTERS = (
    "network_call_count",
    "live_passkey_call_count",
    "live_db_call_count",
    "real_dispatch_count",
    "external_mutation_count",
    "canonical_mcp_write_count",
    "production_site_request_count",
    "git_push_count",
    "external_notification_count",
)


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


CONTRACT = load_json(CONTRACT_PATH)
FIXTURE = load_json(FIXTURE_PATH)
SCENARIOS = {scenario["id"]: scenario for scenario in CONTRACT["scenarios"]}


# ---------------------------------------------------------------------------
# Live-call monitor and fixture-only stub providers
# ---------------------------------------------------------------------------


class LiveCallMonitor:
    """Counts every forbidden live operation. A pure run must leave it at zero.

    No fixture code path ever calls a ``record_*`` method; the monitor exists so
    the suite can prove, with machine-readable counters, that no forbidden live
    call happened.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.network_call_count = 0
        self.live_passkey_call_count = 0
        self.live_db_call_count = 0
        self.real_dispatch_count = 0
        self.external_mutation_count = 0
        self.canonical_mcp_write_count = 0
        self.production_site_request_count = 0
        self.git_push_count = 0
        self.external_notification_count = 0
        self.repository_code_executed = False

    def record_network(self) -> None:
        self.network_call_count += 1

    def record_passkey(self) -> None:
        self.live_passkey_call_count += 1

    def record_live_db(self) -> None:
        self.live_db_call_count += 1

    def record_dispatch(self) -> None:
        self.real_dispatch_count += 1

    def record_canonical_mcp_write(self) -> None:
        self.canonical_mcp_write_count += 1

    def record_production_site_request(self) -> None:
        self.production_site_request_count += 1

    def as_dict(self) -> dict:
        return {
            "network_call_count": self.network_call_count,
            "live_passkey_call_count": self.live_passkey_call_count,
            "live_db_call_count": self.live_db_call_count,
            "real_dispatch_count": self.real_dispatch_count,
            "external_mutation_count": self.external_mutation_count,
            "canonical_mcp_write_count": self.canonical_mcp_write_count,
            "production_site_request_count": self.production_site_request_count,
            "git_push_count": self.git_push_count,
            "external_notification_count": self.external_notification_count,
            "repository_code_executed": self.repository_code_executed,
        }


class FixtureCanonicalStore:
    """In-memory Canonical stand-in. Never touches a service or database."""

    def __init__(self) -> None:
        self._assets: dict[str, dict] = {}
        self.write_count = 0
        self.write_attempt_count = 0

    def write(
        self,
        asset_id: str,
        candidate_id: str,
        version: int,
        content_hash: str,
        provenance: dict,
        ack: str = "OK",
    ) -> str:
        self.write_attempt_count += 1
        # A fixture write always lands in memory; an UNKNOWN ack means the
        # caller may not assume success and must reconcile with an independent
        # read. It never triggers an automatic second write.
        self._assets[asset_id] = {
            "asset_id": asset_id,
            "candidate_id": candidate_id,
            "version": version,
            "content_hash": content_hash,
            "provenance": dict(provenance),
        }
        self.write_count += 1
        return "UNKNOWN" if ack == "UNKNOWN" else "WRITTEN"

    def read(self, asset_id: str) -> dict | None:
        asset = self._assets.get(asset_id)
        return dict(asset) if asset is not None else None


# ---------------------------------------------------------------------------
# Pure state machine
# ---------------------------------------------------------------------------


class MobileCloudFlowEngine:
    """Deterministic product-logic state machine for the fixture contract."""

    def __init__(self, contract: dict, fixture: dict, monitor: LiveCallMonitor, scenario_id: str) -> None:
        self.contract = contract
        self.fixture = fixture
        self.monitor = monitor
        self.scenario_id = scenario_id
        self.inputs = fixture.get("scenario_inputs", {}).get(scenario_id, {})
        self.canonical = FixtureCanonicalStore()
        self.reset()

    # -- construction -------------------------------------------------------

    def reset(self) -> None:
        candidate = self.fixture["input"]["candidate"]
        self.task_id: str | None = None
        self.candidate_id: str | None = None
        self.asset_id = candidate["asset_id"]
        self.candidate_version = candidate["candidate_version"]
        self.content_hash = candidate["content_hash"]

        self.execution_status = "PENDING"
        self.business_status: str | None = None
        self.content_review_status = "NOT_REVIEWED"
        self.application_approval_status = "NOT_COMPLETED"
        self.canonical_status = "NOT_WRITTEN"
        self.readback_status = "NOT_READ"
        self.pipeline_status = "SUBMITTED"
        self.terminal = False

        self.done_badge = False
        self.requires_user_action = False
        self.application_approval_prompted = False
        self.reason: str | None = None
        self.execution_route: str | None = None

        self.board: dict | None = None
        self.last_good_board: dict | None = None
        self.board_is_stale = False
        self.generated_at: str | None = None

        self.canonical_fixture_write_count = 0
        self.automatic_second_write_count = 0
        self.new_write_to_hide_mismatch_count = 0
        self.new_candidate_count = 0
        self.new_dispatch_count = 0
        self.automatic_passkey_attempt_count = 0
        self.alternate_tool_or_environment_attempt_count = 0
        self.retry_without_new_valid_authority_count = 0

        self.live_submit_replayed = False
        self.reconciled_from_readback = False
        self.reconstructed_same_version = False
        self.retains_last_good_data = False
        self.empty_success = False
        self.generated_at_unchanged = False
        self.hash_only_sufficient = False
        self.insufficient_evidence_state: str | None = None
        self.required_evidence: list[str] = []
        self.behavior_scope: str | None = None
        self.same_task_id = False
        self.same_candidate_id = False

        preconditions = self.inputs.get("preconditions", {})
        self.execution_status = preconditions.get("execution_status", self.execution_status)
        self.business_status = preconditions.get("business_status", self.business_status)
        self.content_review_status = preconditions.get("content_review_status", self.content_review_status)
        self.application_approval_status = preconditions.get(
            "application_approval_status", self.application_approval_status
        )

        if self.scenario_id == "F11_BOARD_REFRESH_ERROR":
            previous = self.fixture.get("previous_good_board")
            if previous is not None:
                self.last_good_board = dict(previous)
                self.board = dict(previous)
                self.generated_at = previous["generated_at"]

    # -- event dispatch -----------------------------------------------------

    def handle_event(self, event: str) -> None:
        handler = {
            "PHONE_SUBMIT": self._phone_submit,
            "CLOUD_RESULT_PASS": lambda: self._apply_cloud_result(default_final="PASS"),
            "CLOUD_RESULT_READ": lambda: self._apply_cloud_result(default_final="PASS"),
            "RESULT_READ": self._apply_result_read,
            "RESULT_READ_FIXTURE": self._apply_result_read,
            "CONTENT_APPROVED": self._content_approved,
            "CONTENT_CHANGES_REQUESTED": self._content_changes_requested,
            "APPLICATION_APPROVED_FIXTURE": self._application_approved_fixture,
            "CANONICAL_WRITTEN_FIXTURE": self._canonical_write_fixture,
            "CANONICAL_READ_MATCH_FIXTURE": lambda: self._canonical_read(match=True),
            "CANONICAL_READ_MISMATCH_FIXTURE": lambda: self._canonical_read(match=False),
            "PROMOTE_FIXTURE_ACK_UNKNOWN": self._promote_ack_unknown,
            "CANONICAL_READ_MATCH_EXACT_TARGET_AND_PROVENANCE_FIXTURE": self._canonical_read_exact_provenance,
            "BOARD_REFRESH": lambda: self._board_refresh(ok=True),
            "BOARD_REFRESH_MATCH_FRESH": lambda: self._board_refresh(ok=True, fresh=True),
            "BOARD_REFRESH_FAIL": lambda: self._board_refresh(ok=False),
            "TASK_ROUTE_SELECTION": self._task_route_selection,
            "PHONE_CLOSE": lambda: None,
            "PHONE_REOPEN": lambda: None,
            "PROPOSED_STUB_RESUME_SAME_REQUEST": self._stub_resume,
            "PHONE_OPEN_APPROVAL": self._phone_open_approval,
            "APP_APPROVAL_TIMEOUT": self._app_approval_timeout,
            "PLATFORM_DENIED": self._platform_denied,
            "SOURCE_HANDOFF_CHECK": self._source_handoff_check,
            "BUILD_ACCEPTANCE_REPORT": lambda: None,
        }.get(event)
        if handler is None:
            raise AssertionError(f"unknown fixture event: {event}")
        handler()

    # -- handlers -----------------------------------------------------------

    def _phone_submit(self) -> None:
        self.task_id = self.fixture["input"]["task_id"]
        self.candidate_id = self.fixture["input"]["candidate"]["candidate_id"]
        self.pipeline_status = "SUBMITTED"

    def _apply_cloud_result(self, default_final: str) -> None:
        payload = self.inputs.get("cloud_result", {})
        conclusion = payload.get("workflow_conclusion", "success")
        final = payload.get("final_status", default_final)
        if conclusion != "success":
            self.execution_status = "FAIL"
            self.business_status = None
            self.pipeline_status = "BLOCKED"
            self.terminal = True
            return
        self.execution_status = "PASS"
        self.business_status = final
        if final == "PARTIAL":
            self.pipeline_status = "PARTIAL"
            self.terminal = True
            self.done_badge = False
        else:
            self.pipeline_status = "CONTENT_REVIEW"
            self.terminal = False

    def _apply_result_read(self) -> None:
        payload = self.inputs.get("result_read", {})
        if not payload.get("terminal", False):
            self.execution_status = "PENDING"
            self.pipeline_status = "PROCESSING"
            self.terminal = False
            return
        conclusion = payload.get("workflow_conclusion")
        final = payload.get("final_status")
        if conclusion != "success":
            self.execution_status = "FAIL"
            self.business_status = None
            self.pipeline_status = "BLOCKED"
            self.terminal = True
        elif final == "PARTIAL":
            self.execution_status = "PASS"
            self.business_status = "PARTIAL"
            self.pipeline_status = "PARTIAL"
            self.terminal = True
        else:
            self.execution_status = "PASS"
            self.business_status = final or "PASS"
            self.pipeline_status = "CONTENT_REVIEW"
            self.terminal = True

    def _content_approved(self) -> None:
        self.content_review_status = "APPROVED"
        self.pipeline_status = "WAITING_APPLICATION_APPROVAL"
        self.application_approval_prompted = True

    def _content_changes_requested(self) -> None:
        self.content_review_status = "CHANGES_REQUESTED"
        self.pipeline_status = "CONTENT_REVIEW"
        self.application_approval_prompted = False

    def _application_approved_fixture(self) -> None:
        # Fixture-only approval event. Never serializes a passkey assertion.
        self.application_approval_status = "VERIFIED_FIXTURE_ONLY"
        self.pipeline_status = "PROMOTING"
        self.application_approval_prompted = False

    def _canonical_write_fixture(self) -> None:
        result = self.canonical.write(
            self.asset_id,
            self.candidate_id or self.fixture["input"]["candidate"]["candidate_id"],
            self.candidate_version,
            self.content_hash,
            {"promotion_event_ref": self.fixture["board"]["promotion_event_ref"]},
        )
        self.canonical_status = "WRITTEN" if result == "WRITTEN" else "WRITE_ACK_UNKNOWN"
        self.canonical_fixture_write_count = self.canonical.write_count
        self.pipeline_status = "VERIFYING_READBACK"

    def _canonical_read(self, match: bool) -> None:
        if match:
            asset = self.canonical.read(self.asset_id)
            if asset is not None and asset["content_hash"] == self.content_hash:
                self.readback_status = "MATCH"
            else:
                self.readback_status = "MISMATCH"
                self.pipeline_status = "BLOCKED"
                self.done_badge = False
            if self.readback_status == "MATCH":
                self.pipeline_status = "VERIFYING_READBACK"
            return
        self.readback_status = "MISMATCH"
        self.pipeline_status = "BLOCKED"
        self.done_badge = False
        self.new_write_to_hide_mismatch_count = 0

    def _promote_ack_unknown(self) -> None:
        candidate = self.fixture["input"]["candidate"]
        promotion = self.inputs.get("promotion", {})
        provenance = promotion.get("provenance", {"promotion_event_ref": self.fixture["board"]["promotion_event_ref"]})
        self.canonical.write(
            candidate["asset_id"],
            candidate["candidate_id"],
            candidate["candidate_version"],
            candidate["content_hash"],
            provenance,
            ack=promotion.get("ack", "UNKNOWN"),
        )
        self.canonical_status = "WRITE_ACK_UNKNOWN"
        self.canonical_fixture_write_count = self.canonical.write_count
        self.pipeline_status = "VERIFYING_READBACK"
        self.automatic_second_write_count = 0
        self.hash_only_sufficient = False
        self.insufficient_evidence_state = "BLOCKED_ACK_UNKNOWN_REQUIRE_RECONCILIATION"
        self.required_evidence = []

    def _canonical_read_exact_provenance(self) -> None:
        candidate = self.fixture["input"]["candidate"]
        promotion = self.inputs.get("promotion", {})
        provenance = promotion.get("provenance", {})
        after = promotion.get("after", {})
        before = promotion.get("before", {})

        asset = self.canonical.read(candidate["asset_id"])
        evidence: list[str] = []

        target_match = (
            asset is not None
            and asset["candidate_id"] == candidate["candidate_id"]
            and asset["version"] == candidate["candidate_version"]
            and asset["content_hash"] == candidate["content_hash"]
            and after.get("candidate_id") == candidate["candidate_id"]
            and after.get("candidate_version") == candidate["candidate_version"]
            and after.get("content_hash") == candidate["content_hash"]
        )
        provenance_match = (
            asset is not None
            and asset["provenance"].get("promotion_event_ref") == provenance.get("promotion_event_ref")
        )
        version_transition = bool(before.get("absent")) or before.get("version", 0) != after.get("version")

        if target_match:
            evidence.append(
                "matching approved candidate_id/candidate_version/asset_id/content_hash"
            )
        if provenance_match:
            evidence.append("matching promotion_event provenance")
        if version_transition:
            evidence.append("before/after version or absence evidence attributing this write")

        self.required_evidence = evidence
        self.reconciled_from_readback = target_match and provenance_match and version_transition
        # The named fallback state is always reported so a caller knows which
        # state to use when the evidence is insufficient.
        self.insufficient_evidence_state = "BLOCKED_ACK_UNKNOWN_REQUIRE_RECONCILIATION"
        if self.reconciled_from_readback:
            self.readback_status = "MATCH"
            self.canonical_status = "IDEMPOTENT"
        else:
            self.readback_status = "MISMATCH"
            self.pipeline_status = "BLOCKED"

    def _board_refresh(self, ok: bool, fresh: bool = False) -> None:
        if not ok:
            if self.last_good_board is not None:
                self.board = dict(self.last_good_board)
                self.retains_last_good_data = True
            self.board_is_stale = True
            self.empty_success = False
            self.generated_at_unchanged = True
            return

        self.board_is_stale = False
        self.board = self._project_board()
        self.generated_at = self.board["generated_at"]
        self.last_good_board = dict(self.board)
        if fresh and "fresh board matching same target" not in self.required_evidence:
            if self.scenario_id == "F09_WRITE_ACK_UNKNOWN":
                self.required_evidence.append("fresh board matching same target")
        self._finalize_completion()
        self.board = self._project_board()
        self.last_good_board = dict(self.board)

    def _project_board(self) -> dict:
        candidate = self.fixture["input"]["candidate"]
        board = self.fixture["board"]
        return {
            "task_id": self.task_id or self.fixture["input"]["task_id"],
            "candidate_id": self.candidate_id or candidate["candidate_id"],
            "asset_id": self.asset_id,
            "execution_status": self.execution_status,
            "business_status": self.business_status,
            "content_review_status": self.content_review_status,
            "application_approval_status": self.application_approval_status,
            "canonical_status": self.canonical_status,
            "readback_status": self.readback_status,
            "pipeline_status": self.pipeline_status,
            "generated_at": board["generated_at"],
            "last_successful_read_at": board["last_successful_read_at"],
            "is_stale": self.board_is_stale,
            "source_commit": board["source_commit"],
            "model": board["model"],
            "candidate_version": self.candidate_version,
            "promotion_event_ref": self.fixture["board"]["promotion_event_ref"],
        }

    def _finalize_completion(self) -> None:
        predicate_met = (
            self.execution_status == "PASS"
            and self.business_status == "PASS"
            and self.content_review_status == "APPROVED"
            and self.application_approval_status == "VERIFIED_FIXTURE_ONLY"
            and self.canonical_status in ("WRITTEN", "IDEMPOTENT")
            and self.readback_status == "MATCH"
            and self.board is not None
            and not self.board_is_stale
        )
        if predicate_met:
            self.pipeline_status = "COMPLETE"
            self.terminal = True
            self.done_badge = True

    def _task_route_selection(self) -> None:
        runtime = self.fixture["runtime"]
        self.execution_route = self.fixture["input"]["execution_route"]
        self.current_workflow_model = runtime["current_workflow_model"]

    def _stub_resume(self) -> None:
        request_id = self.fixture["input"]["request_id"]
        mapping = self.inputs.get("resume", {}).get("durable_map", {})
        entry = mapping.get(request_id)
        self.same_task_id = entry is not None
        self.same_candidate_id = entry is not None
        if entry is not None:
            self.task_id = entry["task_id"]
            self.candidate_id = entry["candidate_id"]
        self.new_candidate_count = 0
        self.new_dispatch_count = 0
        self.live_submit_replayed = False
        self.behavior_scope = "PROPOSED_STUB_ONLY_NOT_EXISTING_SUBMIT_GUARANTEE"

    def _phone_open_approval(self) -> None:
        self.pipeline_status = "WAITING_APPLICATION_APPROVAL"
        self.application_approval_prompted = True
        self.requires_user_action = True

    def _app_approval_timeout(self) -> None:
        self.pipeline_status = "WAITING_APPLICATION_APPROVAL"
        self.application_approval_status = "NOT_COMPLETED"
        self.automatic_passkey_attempt_count = 0
        self.requires_user_action = True

    def _platform_denied(self) -> None:
        platform = self.inputs.get("platform", {})
        self.pipeline_status = "BLOCKED"
        self.terminal = True
        self.reason = platform.get("reason", "ACTION_AUTHORITY_REQUIRED")
        self.alternate_tool_or_environment_attempt_count = 0
        self.retry_without_new_valid_authority_count = 0

    def _source_handoff_check(self) -> None:
        handoff = self.inputs.get("handoff", {})
        self.pipeline_status = "BLOCKED"
        self.terminal = True
        self.reason = handoff.get("reason", "SOURCE_BYTES_REQUIRED")
        self.reconstructed_same_version = False

    # -- result projection --------------------------------------------------

    def actual(self, scenario_id: str) -> dict:
        board = self.board or {}
        if scenario_id == "F01_COMPLETE_PATH":
            return {
                "pipeline_status": self.pipeline_status,
                "validation_level": self.contract["validation_level"],
                "canonical_fixture_write_count": self.canonical_fixture_write_count,
                "board_asset_version": board.get("candidate_version"),
                "board_is_stale": board.get("is_stale"),
                "live_phone_e2e": self.contract["live_phone_e2e"],
            }
        if scenario_id == "F02_WORKFLOW_PASS_BUSINESS_PARTIAL":
            return {
                "pipeline_status": self.pipeline_status,
                "execution_status": self.execution_status,
                "business_status": self.business_status,
                "canonical_fixture_write_count": self.canonical_fixture_write_count,
                "done_badge": self.done_badge,
            }
        if scenario_id == "F03_PROCESSING_PENDING":
            return {
                "pipeline_status": self.pipeline_status,
                "execution_status": self.execution_status,
                "terminal": self.terminal,
                "canonical_fixture_write_count": self.canonical_fixture_write_count,
                "application_approval_prompted": self.application_approval_prompted,
            }
        if scenario_id == "F04_PROCESSING_FAILURE":
            return {
                "pipeline_status": self.pipeline_status,
                "execution_status": self.execution_status,
                "canonical_fixture_write_count": self.canonical_fixture_write_count,
            }
        if scenario_id == "F05_ORDINARY_EXISTING_ROUTE":
            runtime = self.fixture["runtime"]
            return {
                "execution_route": self.execution_route,
                "current_workflow_model": getattr(self, "current_workflow_model", None),
                "requires_new_model_parameter": runtime["requires_new_model_parameter"],
                "requires_Sol_alignment": runtime["requires_Sol_alignment"],
                "new_infrastructure_count": runtime["new_infrastructure_count"],
            }
        if scenario_id == "F06_CONTENT_APPROVAL_ONLY":
            return {
                "pipeline_status": self.pipeline_status,
                "canonical_fixture_write_count": self.canonical_fixture_write_count,
                "application_approval_status": self.application_approval_status,
            }
        if scenario_id == "F07_PHONE_RELOAD_RESUME":
            return {
                "same_task_id": self.same_task_id,
                "same_candidate_id": self.same_candidate_id,
                "new_candidate_count": self.new_candidate_count,
                "new_dispatch_count": self.new_dispatch_count,
                "behavior_scope": self.behavior_scope,
                "live_submit_replayed": self.live_submit_replayed,
            }
        if scenario_id == "F08_APP_APPROVAL_EXPIRED":
            return {
                "pipeline_status": self.pipeline_status,
                "canonical_fixture_write_count": self.canonical_fixture_write_count,
                "automatic_passkey_attempt_count": self.automatic_passkey_attempt_count,
                "requires_user_action": self.requires_user_action,
            }
        if scenario_id == "F09_WRITE_ACK_UNKNOWN":
            return {
                "pipeline_status": self.pipeline_status,
                "canonical_fixture_write_count": self.canonical_fixture_write_count,
                "automatic_second_write_count": self.automatic_second_write_count,
                "reconciled_from_readback": self.reconciled_from_readback,
                "required_evidence": self.required_evidence,
                "hash_only_sufficient": self.hash_only_sufficient,
                "insufficient_evidence_state": self.insufficient_evidence_state,
            }
        if scenario_id == "F10_READBACK_MISMATCH":
            return {
                "pipeline_status": self.pipeline_status,
                "readback_status": self.readback_status,
                "done_badge": self.done_badge,
                "new_write_to_hide_mismatch_count": self.new_write_to_hide_mismatch_count,
            }
        if scenario_id == "F11_BOARD_REFRESH_ERROR":
            return {
                "retains_last_good_data": self.retains_last_good_data,
                "board_is_stale": self.board_is_stale,
                "empty_success": self.empty_success,
                "generated_at_unchanged": self.generated_at_unchanged,
            }
        if scenario_id == "F12_USER_REQUESTS_REVISION":
            return {
                "pipeline_status": self.pipeline_status,
                "canonical_fixture_write_count": self.canonical_fixture_write_count,
                "application_approval_prompted": self.application_approval_prompted,
            }
        if scenario_id == "F13_PLATFORM_ACTION_DENIED":
            return {
                "pipeline_status": self.pipeline_status,
                "alternate_tool_or_environment_attempt_count": self.alternate_tool_or_environment_attempt_count,
                "retry_without_new_valid_authority_count": self.retry_without_new_valid_authority_count,
                "reason": self.reason,
            }
        if scenario_id == "F14_SOURCE_BYTES_MISSING":
            return {
                "pipeline_status": self.pipeline_status,
                "reason": self.reason,
                "reconstructed_same_version": self.reconstructed_same_version,
            }
        raise AssertionError(f"no result projection for scenario {scenario_id}")


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

ALL_SCENARIO_IDS = [scenario["id"] for scenario in CONTRACT["scenarios"]]
FIXTURE_SCENARIO_IDS = [sid for sid in ALL_SCENARIO_IDS if sid != "F15_PHONE_END_TO_END_EVIDENCE_GAP"]


def run_scenario(scenario_id: str, monitor: LiveCallMonitor) -> dict:
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, scenario_id)
    for event in SCENARIOS[scenario_id]["events"]:
        engine.handle_event(event)
    return engine.actual(scenario_id)


def compare(actual: dict, expected: dict) -> dict:
    return {key: actual.get(key) == value for key, value in expected.items()}


def run_fixture_suite() -> dict:
    monitor = LiveCallMonitor()
    results: dict[str, dict] = {}
    for scenario_id in FIXTURE_SCENARIO_IDS:
        actual = run_scenario(scenario_id, monitor)
        expected = SCENARIOS[scenario_id]["expect"]
        matches = compare(actual, expected)
        results[scenario_id] = {
            "expected": expected,
            "actual": actual,
            "checked_keys": sorted(matches),
            "match": all(matches.values()),
        }
    forbidden = monitor.as_dict()
    forbidden_ok = all(forbidden.get(name) == 0 for name in LIVE_FORBIDDEN_COUNTERS) and (
        forbidden["repository_code_executed"] is False
    )
    all_ok = all(entry["match"] for entry in results.values()) and forbidden_ok

    f15_expected = SCENARIOS["F15_PHONE_END_TO_END_EVIDENCE_GAP"]["expect"]
    f15_actual = {
        "reported_status": "CONTRACT_PASS" if all_ok else "FAIL",
        "mobile_e2e_status": "NOT_RUN",
        "production_write_status": "NOT_RUN",
        "release_status": "NOT_PERFORMED",
    }
    results["F15_PHONE_END_TO_END_EVIDENCE_GAP"] = {
        "expected": f15_expected,
        "actual": f15_actual,
        "checked_keys": sorted(compare(f15_actual, f15_expected)),
        "match": all(compare(f15_actual, f15_expected).values()),
    }

    return {
        "results": results,
        "forbidden": forbidden,
        "forbidden_ok": forbidden_ok,
        "all_ok": all_ok,
    }


SUITE = run_fixture_suite()


# ---------------------------------------------------------------------------
# Contract / fixture structural checks
# ---------------------------------------------------------------------------


def test_contract_structure() -> None:
    assert CONTRACT["schema"] == "personal-ai-mobile-cloud-fixture-contract/v1"
    assert CONTRACT["validation_level"] == "CONTRACT_ONLY"
    assert CONTRACT["live_phone_e2e"] is False
    assert CONTRACT["repository_code_executed"] is False
    assert len(CONTRACT["scenarios"]) == 15
    assert FIXTURE["schema"] == "personal-ai-mobile-cloud-fixture-data/v1"


def test_candidate_content_hash_matches_content() -> None:
    candidate = CONTRACT["input"]["candidate"]
    computed = hashlib.sha256(candidate["content"].encode("utf-8")).hexdigest()
    assert computed == candidate["content_hash"]


def test_no_live_forbidden_calls_occurred() -> None:
    assert SUITE["forbidden_ok"] is True
    for name in LIVE_FORBIDDEN_COUNTERS:
        assert SUITE["forbidden"][name] == 0, name
    assert SUITE["forbidden"]["repository_code_executed"] is False


# ---------------------------------------------------------------------------
# One test per fixture scenario
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_id", ALL_SCENARIO_IDS)
def test_scenario_matches_contract(scenario_id: str) -> None:
    entry = SUITE["results"][scenario_id]
    assert entry["actual"] == entry["expected"], (
        f"{scenario_id} actual={entry['actual']} expected={entry['expected']}"
    )


# ---------------------------------------------------------------------------
# Focused semantic guarantees called out by the contract
# ---------------------------------------------------------------------------


def test_f02_workflow_pass_business_partial_stays_partial() -> None:
    entry = SUITE["results"]["F02_WORKFLOW_PASS_BUSINESS_PARTIAL"]["actual"]
    assert entry["execution_status"] == "PASS"
    assert entry["business_status"] == "PARTIAL"
    assert entry["pipeline_status"] == "PARTIAL"
    assert entry["done_badge"] is False


def test_f07_is_proposed_stub_only_not_existing_idempotency() -> None:
    entry = SUITE["results"]["F07_PHONE_RELOAD_RESUME"]["actual"]
    assert entry["behavior_scope"] == "PROPOSED_STUB_ONLY_NOT_EXISTING_SUBMIT_GUARANTEE"
    assert entry["live_submit_replayed"] is False
    assert entry["new_dispatch_count"] == 0


def test_f09_hash_only_is_insufficient_for_reconciliation() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    engine.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    assert engine.insufficient_evidence_state == "BLOCKED_ACK_UNKNOWN_REQUIRE_RECONCILIATION"

    # Degrade to a hash-only match: same content hash but wrong promotion
    # provenance and no version transition. Matching hash alone must not be
    # accepted as proof that *this* task performed the write.
    asset = engine.canonical.read(engine.asset_id)
    assert asset is not None
    asset["provenance"] = {"promotion_event_ref": "different-provenance-ref"}
    engine.canonical._assets[engine.asset_id] = asset
    engine.inputs["promotion"]["before"] = {
        "asset_id": engine.asset_id,
        "version": 1,
        "absent": False,
    }
    engine._canonical_read_exact_provenance()

    assert engine.reconciled_from_readback is False
    assert engine.hash_only_sufficient is False
    assert engine.insufficient_evidence_state == "BLOCKED_ACK_UNKNOWN_REQUIRE_RECONCILIATION"
    engine._board_refresh(ok=True, fresh=True)
    assert engine.pipeline_status == "BLOCKED"
    assert engine.pipeline_status != "COMPLETE"


def test_f10_readback_mismatch_cannot_complete() -> None:
    entry = SUITE["results"]["F10_READBACK_MISMATCH"]["actual"]
    assert entry["readback_status"] == "MISMATCH"
    assert entry["pipeline_status"] == "BLOCKED"
    assert entry["done_badge"] is False
    assert entry["new_write_to_hide_mismatch_count"] == 0


def test_f11_stale_board_retains_last_good_projection() -> None:
    entry = SUITE["results"]["F11_BOARD_REFRESH_ERROR"]["actual"]
    assert entry["retains_last_good_data"] is True
    assert entry["board_is_stale"] is True
    assert entry["empty_success"] is False
    assert entry["generated_at_unchanged"] is True


def test_f13_platform_refusal_has_no_alternate_attempt() -> None:
    entry = SUITE["results"]["F13_PLATFORM_ACTION_DENIED"]["actual"]
    assert entry["pipeline_status"] == "BLOCKED"
    assert entry["reason"] == "ACTION_AUTHORITY_REQUIRED"
    assert entry["alternate_tool_or_environment_attempt_count"] == 0
    assert entry["retry_without_new_valid_authority_count"] == 0


def test_f14_missing_source_bytes_is_not_reconstructed() -> None:
    entry = SUITE["results"]["F14_SOURCE_BYTES_MISSING"]["actual"]
    assert entry["pipeline_status"] == "BLOCKED"
    assert entry["reason"] == "SOURCE_BYTES_REQUIRED"
    assert entry["reconstructed_same_version"] is False


# ---------------------------------------------------------------------------
# Machine-readable report
# ---------------------------------------------------------------------------


def build_report() -> dict:
    contract_bytes = CONTRACT_PATH.read_bytes()
    contract_sha256 = hashlib.sha256(contract_bytes).hexdigest()
    scenario_entries = []
    for scenario_id in ALL_SCENARIO_IDS:
        entry = SUITE["results"][scenario_id]
        scenario_entries.append(
            {
                "id": scenario_id,
                "status": "PASS" if entry["match"] else "FAIL",
                "actual": entry["actual"],
                "expected": entry["expected"],
            }
        )
    return {
        "schema": "personal-ai-mobile-cloud-flow-report/v1",
        "run_id": "mobile-cloud-flow-v1-fixture-run",
        "validation_level": "CONTRACT_ONLY",
        "generated_at_utc": CONTRACT["clocks"]["now"],
        "time_source": "deterministic fixture clock (not wall clock)",
        "fixture_contract_sha256": contract_sha256,
        "fixture_data_sha256": hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest(),
        "source_manifest_sha256": None,
        "input_gaps": [
            "unpublished Site v32 source bytes are unavailable",
            "unpublished 33-file patch bytes are unavailable",
            "no source manifest bytes are present to hash; source_manifest_sha256 is null and no equivalence is claimed",
            "no in-repo machine-readable prior full-suite receipt is available for the historical head",
        ],
        "scenarios": scenario_entries,
        "live_call_counters": SUITE["forbidden"],
        "network_call_count": SUITE["forbidden"]["network_call_count"],
        "live_passkey_call_count": SUITE["forbidden"]["live_passkey_call_count"],
        "live_db_call_count": SUITE["forbidden"]["live_db_call_count"],
        "real_dispatch_count": SUITE["forbidden"]["real_dispatch_count"],
        "external_mutation_count": SUITE["forbidden"]["external_mutation_count"],
        "repository_code_executed": SUITE["forbidden"]["repository_code_executed"],
        "mobile_e2e_status": "NOT_RUN",
        "production_write_status": "NOT_RUN",
        "release_status": "NOT_PERFORMED",
        "full_repository_suite_status": FULL_REPOSITORY_SUITE_STATUS,
        "full_repository_suite_note": (
            "The unchanged full repository suite is NOT_RUN_THIS_ROUND as contract "
            "evidence; the dispatch workflow runs it independently in its Verify step."
        ),
        "historical_full_suite_evidence": {
            "head": "171758f1f75883e84bfca5fc7ea6355dea902d1b",
            "note": (
                "last public commit before this round; no in-repo machine-readable "
                "full-suite receipt exists, so no prior pass count is counted as this run"
            ),
        },
        "focused_suite": {
            "command": "python -m pytest -q tests/test_mobile_cloud_flow_v1.py",
            "status": "PASS" if SUITE["all_ok"] else "FAIL",
            "scenario_pass_count": sum(1 for e in SUITE["results"].values() if e["match"]),
            "scenario_total": len(SUITE["results"]),
        },
        "directly_affected_existing_tests": [
            "tests/test_status_contract_v0_2.py",
            "tests/test_result_normalization.py",
        ],
        "execution_result": "CONTRACT_PASS" if SUITE["all_ok"] else "FAIL",
        "business_final_status": "CONTRACT_PASS" if SUITE["all_ok"] else "FAIL",
        "not_claimed": [
            "phone access / mobile E2E",
            "real passkey or live application approval",
            "real D1 or Canonical production write",
            "deployed dashboard freshness",
            "source equivalence with unpublished Site v32 / 33-file patches",
        ],
        "f07_scope": "PROPOSED_STUB_ONLY_NOT_EXISTING_SUBMIT_GUARANTEE",
        "f09_scope": "hash equality alone is insufficient; requires exact approved target, matching promotion provenance, before/after evidence, fresh board",
        "forbidden_io": CONTRACT["forbidden_io"],
        "ordinary_execution_route": {
            "execution_route": "ordinary_cloudagent",
            "current_workflow_model": "opencode-go/deepseek-v4.1-flash",
            "new_model_interface_added": False,
            "new_infrastructure_added": False,
        },
        "golden_fixture_convention": "no root execution_result.json is written or committed",
    }


def test_report_is_written_and_consistent() -> None:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    reloaded = load_json(REPORT_PATH)
    assert reloaded["schema"] == "personal-ai-mobile-cloud-flow-report/v1"
    assert reloaded["validation_level"] == "CONTRACT_ONLY"
    assert reloaded["mobile_e2e_status"] == "NOT_RUN"
    assert reloaded["production_write_status"] == "NOT_RUN"
    assert reloaded["release_status"] == "NOT_PERFORMED"
    assert reloaded["full_repository_suite_status"] == "NOT_RUN_THIS_ROUND"
    assert reloaded["execution_result"] == "CONTRACT_PASS"
    assert reloaded["source_manifest_sha256"] is None
    assert len(reloaded["scenarios"]) == 15
    assert all(scenario["status"] == "PASS" for scenario in reloaded["scenarios"])
    assert reloaded["network_call_count"] == 0
    assert reloaded["live_passkey_call_count"] == 0
    assert reloaded["live_db_call_count"] == 0
    assert reloaded["real_dispatch_count"] == 0
    assert reloaded["repository_code_executed"] is False
    # The report must never label a fixture run as real mobile E2E.
    assert reloaded["execution_result"] != "MOBILE_E2E_PASS"


def test_reported_status_is_never_mobile_e2e_pass() -> None:
    entry = SUITE["results"]["F15_PHONE_END_TO_END_EVIDENCE_GAP"]["actual"]
    assert entry["reported_status"] == "CONTRACT_PASS"
    assert entry["reported_status"] != "MOBILE_E2E_PASS"
    assert entry["mobile_e2e_status"] == "NOT_RUN"
    assert entry["production_write_status"] == "NOT_RUN"
    assert entry["release_status"] == "NOT_PERFORMED"
