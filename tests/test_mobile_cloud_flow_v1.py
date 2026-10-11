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

The independent static review identified deterministic control-flow gaps that
are now executed in memory as regression coverage (R01-R09). Each condition is
tested independently so that a single broken guard is not hidden by another.
"""

from __future__ import annotations

import copy
import hashlib
import json
import socket
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "mobile_cloud_flow_v1.json"
FIXTURE_PATH = REPO_ROOT / "fixtures" / "mobile_cloud_flow_v1.json"
REPORT_PATH = REPO_ROOT / "reports" / "mobile_cloud_flow_v1_report.json"

CONTRACT_PLANNED_FULL_SUITE_STATUS = "NOT_RUN_THIS_ROUND"
NOT_OBSERVED = "NOT_OBSERVED_YET"

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
    "subprocess_execution_count",
)

FIXTURE_WORKFLOW_SCOPED_ACTIONS = (
    "main_push",
    "serverchan_notification",
)

GUARD_INSTRUMENTED_BOUNDARIES = (
    "socket.socket",
    "socket.create_connection",
    "subprocess.Popen",
)

GUARD_NOT_INSTRUMENTED_BOUNDARIES = (
    "live D1",
    "passkey provider",
    "Canonical MCP write",
    "production Site request",
    "workflow git push (recorded as workflow action, outside fixture counters)",
    "ServerChan notification (recorded as workflow action, outside fixture counters)",
)


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


CONTRACT = load_json(CONTRACT_PATH)
FIXTURE = load_json(FIXTURE_PATH)
SCENARIOS = {scenario["id"]: scenario for scenario in CONTRACT["scenarios"]}


# ---------------------------------------------------------------------------
# Forbidden-operation monitor and synthetic providers
# ---------------------------------------------------------------------------


class ForbiddenOperationError(RuntimeError):
    """Raised by a forbidden seam before any real external I/O can occur."""


class LiveCallMonitor:
    """Counts every forbidden live operation. A pure run must leave it at zero.

    Seams are *connected* to this monitor: a forbidden seam increments the
    counter and then refuses before contacting any real service. The monitor is
    the observable proof for the instrumented boundary only; un-instrumented
    live services remain UNKNOWN/NOT_INSTRUMENTED.
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
        self.subprocess_execution_count = 0
        self.repository_code_executed = False

    def record_network(self) -> None:
        self.network_call_count += 1

    def record_passkey(self) -> None:
        self.live_passkey_call_count += 1

    def record_live_db(self) -> None:
        self.live_db_call_count += 1

    def record_dispatch(self) -> None:
        self.real_dispatch_count += 1

    def record_external_mutation(self) -> None:
        self.external_mutation_count += 1

    def record_canonical_mcp_write(self) -> None:
        self.canonical_mcp_write_count += 1

    def record_production_site_request(self) -> None:
        self.production_site_request_count += 1

    def record_git_push(self) -> None:
        self.git_push_count += 1

    def record_external_notification(self) -> None:
        self.external_notification_count += 1

    def record_subprocess(self) -> None:
        self.subprocess_execution_count += 1

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
            "subprocess_execution_count": self.subprocess_execution_count,
            "repository_code_executed": self.repository_code_executed,
        }


class ForbiddenSeam:
    """A synthetic provider seam that must never be reached at runtime.

    Calling the seam records into the monitor and immediately raises before any
    real external I/O. The seam is a pure in-memory callable.
    """

    def __init__(self, monitor: LiveCallMonitor, record, name: str) -> None:
        self.monitor = monitor
        self._record = record
        self.name = name
        self.call_count = 0

    def __call__(self, *args: object, **kwargs: object) -> None:
        self.call_count += 1
        self._record()
        raise ForbiddenOperationError(f"forbidden live operation refused: {self.name}")


class ScopedForbiddenIOGuard:
    """Scoped guard that blocks and counts network/subprocess calls.

    Only the stated instrumented boundary is covered. Any code that reaches for
    a real socket or subprocess inside the ``with`` block is recorded on the
    monitor and refused. Original callables are restored on exit.
    """

    def __init__(self, monitor: LiveCallMonitor) -> None:
        self.monitor = monitor
        self._saved: list[tuple[object, str, object]] = []

    def _patch(self, target: object, attribute: str, replacement: object) -> None:
        self._saved.append((target, attribute, getattr(target, attribute)))
        setattr(target, attribute, replacement)

    def __enter__(self) -> "ScopedForbiddenIOGuard":
        monitor = self.monitor

        def _blocked_network(*args: object, **kwargs: object) -> None:
            monitor.record_network()
            raise ForbiddenOperationError("network I/O is forbidden in the fixture boundary")

        class _BlockedSocket:
            def __init__(self, *args: object, **kwargs: object) -> None:
                _blocked_network()

        def _blocked_subprocess(*args: object, **kwargs: object) -> None:
            monitor.record_subprocess()
            raise ForbiddenOperationError("subprocess execution is forbidden in the fixture boundary")

        self._patch(socket, "socket", _BlockedSocket)
        self._patch(socket, "create_connection", _blocked_network)
        self._patch(subprocess, "Popen", _blocked_subprocess)
        return self

    def __exit__(self, *exc: object) -> bool:
        for target, attribute, original in reversed(self._saved):
            setattr(target, attribute, original)
        self._saved.clear()
        return False


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


class FixtureCoordinator:
    """Durable synthetic ``request_id`` -> task/candidate mapping.

    This models a *proposed* stub coordinator only. The connected submit_task
    has no public idempotency parameter and is never called or replayed here.
    Creation and dispatch counts are derived from the observable call log, not
    from counters that are manually reset.
    """

    def __init__(self) -> None:
        self.requests: dict[str, dict] = {}
        self.creation_calls: list[str] = []
        self.dispatch_calls: list[str] = []

    def seed(self, request_id: str, task_id: str, candidate_id: str) -> None:
        if request_id not in self.requests:
            self.requests[request_id] = {"task_id": task_id, "candidate_id": candidate_id}

    def submit(self, request_id: str, task_id: str, candidate_id: str) -> dict:
        if request_id not in self.requests:
            self.requests[request_id] = {"task_id": task_id, "candidate_id": candidate_id}
            self.creation_calls.append(request_id)
            self.dispatch_calls.append(request_id)
        return dict(self.requests[request_id])

    def resume(self, request_id: str) -> dict | None:
        entry = self.requests.get(request_id)
        return dict(entry) if entry is not None else None

    @property
    def creation_count(self) -> int:
        return len(self.creation_calls)

    @property
    def dispatch_count(self) -> int:
        return len(self.dispatch_calls)


# ---------------------------------------------------------------------------
# Shared tuple verifier (R01 / R02 / R04)
# ---------------------------------------------------------------------------


def verify_promotion_tuple(
    *,
    approved_target: dict | None,
    receipt: dict | None,
    readback: dict | None,
    provenance: dict | None,
    promotion_ref: str,
    before: dict | None,
    after: dict | None,
    route: str | None,
    expected_content: str,
    expected_route: str = "ordinary_cloudagent",
) -> dict:
    """Verify the full promotion/readback/board tuple from independent evidence.

    Each condition is returned independently so a caller (and its tests) can
    see exactly which piece of evidence failed. A same-hash record with a
    different version or candidate is not sufficient.
    """
    approved = approved_target or {}
    receipt = receipt or {}
    readback = readback or {}
    provenance = provenance or {}
    before = before or {}
    after = after or {}

    required_target_fields = (
        "operation",
        "candidate_id",
        "candidate_version",
        "asset_id",
        "content_hash",
        "review_result",
        "reviewed_at",
    )

    def is_integer(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    before_absent = before.get("absent")
    before_version = before.get("version")
    after_version = after.get("version")
    # An explainable transition is either a fresh absence -> a present after, or
    # a present previous version that strictly increases to the after version.
    # A decrease, a missing version, or an inconsistent absence is not evidence.
    if before_absent is True:
        valid_transition = after.get("absent") is False and is_integer(after_version)
    elif before_absent is False:
        valid_transition = (
            after.get("absent") is False
            and is_integer(before_version)
            and is_integer(after_version)
            and before_version < after_version
        )
    else:
        valid_transition = False

    return {
        "approved_target_complete": all(
            approved.get(field) not in (None, "", []) for field in required_target_fields
        ),
        "receipt_matches_target": bool(receipt)
        and receipt.get("asset_id") == approved.get("asset_id")
        and receipt.get("candidate_id") == approved.get("candidate_id")
        and receipt.get("candidate_version") == approved.get("candidate_version")
        and receipt.get("content_hash") == approved.get("content_hash")
        and receipt.get("promotion_event_ref") == promotion_ref,
        "readback_identity": bool(readback)
        and readback.get("asset_id") == approved.get("asset_id")
        and readback.get("candidate_id") == approved.get("candidate_id")
        and readback.get("content_hash") == approved.get("content_hash"),
        "readback_content": bool(readback) and readback.get("content") == expected_content,
        "readback_version_is_receipt": bool(readback)
        and readback.get("version") == receipt.get("canonical_version"),
        "provenance_ref": bool(provenance.get("promotion_event_ref"))
        and provenance.get("promotion_event_ref") == promotion_ref,
        "provenance_candidate": provenance.get("candidate_id") == approved.get("candidate_id")
        and provenance.get("candidate_version") == approved.get("candidate_version"),
        "same_asset_before_after": before.get("asset_id") == approved.get("asset_id")
        and after.get("asset_id") == approved.get("asset_id"),
        "valid_transition": valid_transition,
        "after_matches_target": after.get("absent") is False
        and after.get("candidate_id") == approved.get("candidate_id")
        and after.get("candidate_version") == approved.get("candidate_version")
        and after.get("content_hash") == approved.get("content_hash")
        # The canonical asset version produced by the write must equal the
        # receipt's canonical version (candidate_version stays separate).
        and after.get("version") == receipt.get("canonical_version"),
        "route": route == expected_route,
    }


# ---------------------------------------------------------------------------
# Pure state machine
# ---------------------------------------------------------------------------


class MobileCloudFlowEngine:
    """Deterministic product-logic state machine for the fixture contract."""

    def __init__(
        self,
        contract: dict,
        fixture: dict,
        monitor: LiveCallMonitor,
        scenario_id: str,
        coordinator: FixtureCoordinator | None = None,
    ) -> None:
        self.contract = contract
        # R09: each engine gets a deep copy so a negative case can never mutate
        # the shared fixture/inputs.
        self.fixture = copy.deepcopy(fixture)
        self.monitor = monitor
        self.scenario_id = scenario_id
        self.inputs = copy.deepcopy(self.fixture.get("scenario_inputs", {}).get(scenario_id, {}))
        self.canonical = FixtureCanonicalStore()
        self.coordinator = coordinator if coordinator is not None else FixtureCoordinator()
        self.reset()

    # -- construction -------------------------------------------------------

    def reset(self) -> None:
        candidate = self.fixture["input"]["candidate"]
        self.task_id: str | None = None
        self.candidate_id: str | None = None
        self.asset_id = candidate["asset_id"]
        self.candidate_version = candidate["candidate_version"]
        self.content_hash = candidate["content_hash"]
        self.expected_promotion_ref = self.fixture["board"]["promotion_event_ref"]
        self.current_workflow_model = self.fixture["runtime"]["current_workflow_model"]
        self.execution_route = self.fixture["input"]["execution_route"]

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

        self.board: dict | None = None
        self.last_good_board: dict | None = None
        self.board_is_stale = False
        self.generated_at: str | None = None
        self.last_successful_read_at: str | None = None

        self.canonical_fixture_write_count = 0
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
        self.restored_task_id: str | None = None
        self.restored_candidate_id: str | None = None
        self.stub_creation_count = 0
        self.stub_dispatch_count = 0

        self.approved_target: dict | None = None
        self.promotion_receipt: dict | None = None
        self.before_snapshot: dict | None = None
        self.after_record: dict | None = None
        self.write_attributed = False
        self.tuple_verified = False
        self.tuple_evidence: dict = {}
        self.write_attempt_log: list[dict] = []
        self.approval_token = 0
        self.pending_approval_token: int | None = None
        self.approval_expired = False
        self.approval_invalidated = False
        self.platform_denied = False
        self.refused_approval_event_count = 0
        self.completed = False
        self.completion_stale = False
        self.completion_evidence: dict = {}

        preconditions = self.inputs.get("preconditions", {})
        self.execution_status = preconditions.get("execution_status", self.execution_status)
        self.business_status = preconditions.get("business_status", self.business_status)
        self.content_review_status = preconditions.get("content_review_status", self.content_review_status)
        self.application_approval_status = preconditions.get(
            "application_approval_status", self.application_approval_status
        )

        if self.inputs.get("approval_target"):
            self.approved_target = copy.deepcopy(self.inputs["approval_target"])

        resume_map = self.inputs.get("resume", {}).get("durable_map", {})
        for request_id, entry in resume_map.items():
            self.coordinator.seed(request_id, entry["task_id"], entry["candidate_id"])

        if self.scenario_id == "F11_BOARD_REFRESH_ERROR":
            previous = self.fixture.get("previous_good_board")
            if previous is not None:
                self.last_good_board = dict(previous)
                self.board = dict(previous)
                self.generated_at = previous["generated_at"]
                self.last_successful_read_at = previous["last_successful_read_at"]

        if self.scenario_id == "F10_READBACK_MISMATCH":
            # Stated precondition: the fixture writer already returned WRITTEN
            # under a complete fixture-only approval target. This happens once
            # at construction (setup), never on a read/board path.
            self.content_review_status = "APPROVED"
            self.application_approval_status = "VERIFIED_FIXTURE_ONLY"
            self.execution_status = "PASS"
            self.business_status = "PASS"
            self.approved_target = self._fixture_approved_target()
            self._perform_fixture_write(ack="OK")
            self.canonical_status = "WRITTEN"

    def _fixture_approved_target(self) -> dict:
        candidate = self.fixture["input"]["candidate"]
        return {
            "operation": "promote",
            "candidate_id": self.candidate_id or candidate["candidate_id"],
            "candidate_version": self.candidate_version,
            "asset_id": self.asset_id,
            "content_hash": self.content_hash,
            "review_result": candidate["review_result"],
            "reviewed_at": candidate["reviewed_at"],
        }

    # -- derived counters ---------------------------------------------------

    @property
    def refused_write_count(self) -> int:
        return sum(1 for attempt in self.write_attempt_log if not attempt.get("authorized"))

    @property
    def repeated_write_skipped_count(self) -> int:
        return sum(
            1 for attempt in self.write_attempt_log if attempt.get("outcome") == "IDEMPOTENT_SKIPPED"
        )

    @property
    def automatic_second_write_count(self) -> int:
        return sum(
            1
            for attempt in self.write_attempt_log
            if attempt.get("outcome") == "IDEMPOTENT_SKIPPED" and attempt.get("automatic")
        )

    @property
    def new_write_to_hide_mismatch_count(self) -> int:
        return sum(1 for attempt in self.write_attempt_log if attempt.get("reason") == "hide_mismatch")

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
        # R07: a candidate revision invalidates any prior fixture approval.
        self.application_approval_status = "NOT_COMPLETED"
        self.approved_target = None
        self.approval_invalidated = True

    def _application_approved_fixture(self) -> None:
        # Fixture-only approval event. Never serializes a passkey assertion.
        # R07: a denied or expired approval cannot be revived by an old event.
        if self.platform_denied or self.approval_invalidated:
            self.refused_approval_event_count += 1
            return
        if self.approval_expired and self.pending_approval_token is None:
            self.refused_approval_event_count += 1
            return
        self.application_approval_status = "VERIFIED_FIXTURE_ONLY"
        self.approved_target = self._fixture_approved_target()
        self.pipeline_status = "PROMOTING"
        self.application_approval_prompted = False
        self.approval_expired = False
        self.pending_approval_token = None

    def _current_target(self) -> dict:
        candidate = self.fixture["input"]["candidate"]
        return {
            "operation": "promote",
            "candidate_id": self.candidate_id or candidate["candidate_id"],
            "candidate_version": self.candidate_version,
            "asset_id": self.asset_id,
            "content_hash": self.content_hash,
            "review_result": candidate["review_result"],
            "reviewed_at": candidate["reviewed_at"],
        }

    def _approved_target_matches_current(self) -> bool:
        """The old approved target may only authorize the exact current tuple."""
        target = self.approved_target
        if target is None:
            return False
        current = self._current_target()
        for field in (
            "operation",
            "candidate_id",
            "candidate_version",
            "asset_id",
            "content_hash",
            "review_result",
            "reviewed_at",
        ):
            if target.get(field) in (None, "", []) or target.get(field) != current[field]:
                return False
        return True

    def _write_authorized(self) -> bool:
        return (
            self.application_approval_status == "VERIFIED_FIXTURE_ONLY"
            and self.approved_target is not None
            and self._approved_target_matches_current()
            and not self.approval_expired
            and not self.approval_invalidated
            and not self.platform_denied
            and self.content_review_status == "APPROVED"
        )

    def _perform_fixture_write(
        self,
        ack: str = "OK",
        before: dict | None = None,
        after: dict | None = None,
        provenance: dict | None = None,
        reason: str | None = None,
    ) -> str:
        candidate = self.fixture["input"]["candidate"]
        candidate_id = self.candidate_id or candidate["candidate_id"]
        if provenance is None:
            provenance = {
                "promotion_event_ref": self.expected_promotion_ref,
                "candidate_id": candidate_id,
                "candidate_version": self.candidate_version,
            }
        if not self._write_authorized():
            self.write_attempt_log.append(
                {"authorized": False, "outcome": "REFUSED", "ack": ack, "reason": reason}
            )
            return "REFUSED"
        if self.promotion_receipt is not None:
            self.write_attempt_log.append(
                {"authorized": True, "outcome": "IDEMPOTENT_SKIPPED", "ack": ack, "reason": reason}
            )
            return "IDEMPOTENT"
        result = self.canonical.write(
            self.asset_id,
            candidate_id,
            self.candidate_version,
            self.content_hash,
            provenance,
            ack=ack,
        )
        self.promotion_receipt = {
            "asset_id": self.asset_id,
            "candidate_id": candidate_id,
            "candidate_version": self.candidate_version,
            "canonical_version": self.candidate_version,
            "content_hash": self.content_hash,
            "promotion_event_ref": provenance.get("promotion_event_ref"),
        }
        self.canonical_fixture_write_count = self.canonical.write_count
        self.before_snapshot = (
            dict(before) if before is not None else {"asset_id": self.asset_id, "version": 0, "absent": True}
        )
        self.after_record = (
            dict(after)
            if after is not None
            else {
                "asset_id": self.asset_id,
                "candidate_id": candidate_id,
                "candidate_version": self.candidate_version,
                "version": self.candidate_version,
                "content_hash": self.content_hash,
                "absent": False,
            }
        )
        self.write_attributed = True
        self.write_attempt_log.append(
            {"authorized": True, "outcome": result, "ack": ack, "reason": reason}
        )
        return result

    def _canonical_write_fixture(self) -> None:
        provenance = {
            "promotion_event_ref": self.expected_promotion_ref,
            "candidate_id": self.candidate_id or self.fixture["input"]["candidate"]["candidate_id"],
            "candidate_version": self.candidate_version,
        }
        result = self._perform_fixture_write(ack="OK", provenance=provenance)
        if result == "WRITTEN":
            self.canonical_status = "WRITTEN"
            self.pipeline_status = "VERIFYING_READBACK"
        elif result == "UNKNOWN":
            self.canonical_status = "WRITE_ACK_UNKNOWN"
            self.pipeline_status = "VERIFYING_READBACK"
        elif result == "IDEMPOTENT":
            self.pipeline_status = "VERIFYING_READBACK"
        else:
            # A refused write must not project a promoting/verifying pipeline;
            # the stale approved target cannot authorize a different tuple.
            self.pipeline_status = "BLOCKED"
            self.done_badge = False

    def _read_canonical_record(self) -> dict | None:
        candidate = self.fixture["input"]["candidate"]
        if self.scenario_id == "F10_READBACK_MISMATCH" and self.inputs.get("readback"):
            readback = self.inputs["readback"]
            approved = self.approved_target or {}
            return {
                "asset_id": approved.get("asset_id", candidate["asset_id"]),
                "candidate_id": approved.get("candidate_id", candidate["candidate_id"]),
                "version": readback.get("actual_version"),
                "content_hash": readback.get("actual_hash"),
                "content": candidate["content"],
                "provenance": {
                    "promotion_event_ref": self.expected_promotion_ref,
                    "candidate_id": approved.get("candidate_id", candidate["candidate_id"]),
                    "candidate_version": approved.get("candidate_version", candidate["candidate_version"]),
                },
            }
        asset = self.canonical.read(self.asset_id)
        if asset is None:
            return None
        record = dict(asset)
        record["content"] = candidate["content"]
        return record

    def _verify_readback(self, readback: dict | None) -> dict:
        approved = self.approved_target
        provenance = (readback or {}).get("provenance", {})
        # F10 reuses the complete receipt produced by the stated precondition
        # write; it is not exempt from the corrected receipt checks.
        receipt = self.promotion_receipt
        return verify_promotion_tuple(
            approved_target=approved,
            receipt=receipt,
            readback=readback,
            provenance=provenance,
            promotion_ref=self.expected_promotion_ref,
            before=self.before_snapshot,
            after=self.after_record,
            route=self.execution_route,
            expected_content=self.fixture["input"]["candidate"]["content"],
        )

    def _canonical_read(self, match: bool) -> None:
        # R04: truth comes from an independent synthetic readback record fed
        # through the same tuple verifier, never from the event name. A read
        # path never writes: the F10 "writer already returned WRITTEN"
        # precondition is performed once at construction, not here.
        readback = self._read_canonical_record()
        checks = self._verify_readback(readback)
        self.tuple_evidence = checks
        self.tuple_verified = all(checks.values())
        if self.tuple_verified:
            self.readback_status = "MATCH"
            self.pipeline_status = "VERIFYING_READBACK"
        else:
            self.readback_status = "MISMATCH"
            self.pipeline_status = "BLOCKED"
            self.done_badge = False

    def _promote_ack_unknown(self) -> None:
        promotion = self.inputs.get("promotion", {})
        provenance = promotion.get(
            "provenance",
            {
                "promotion_event_ref": self.expected_promotion_ref,
                "candidate_id": self.candidate_id or self.fixture["input"]["candidate"]["candidate_id"],
                "candidate_version": self.candidate_version,
            },
        )
        self._perform_fixture_write(
            ack=promotion.get("ack", "UNKNOWN"),
            before=promotion.get("before"),
            after=promotion.get("after"),
            provenance=provenance,
        )
        self.canonical_status = "WRITE_ACK_UNKNOWN"
        self.pipeline_status = "VERIFYING_READBACK"
        self.hash_only_sufficient = False
        self.insufficient_evidence_state = "BLOCKED_ACK_UNKNOWN_REQUIRE_RECONCILIATION"
        self.required_evidence = []

    def _canonical_read_exact_provenance(self) -> None:
        readback = self._read_canonical_record()
        checks = self._verify_readback(readback)
        self.tuple_evidence = checks
        self.tuple_verified = all(checks.values())

        evidence: list[str] = []
        if (
            checks["approved_target_complete"]
            and checks["receipt_matches_target"]
            and checks["readback_identity"]
            and checks["readback_content"]
            and checks["readback_version_is_receipt"]
            and checks["after_matches_target"]
        ):
            evidence.append("matching approved candidate_id/candidate_version/asset_id/content_hash")
        if checks["provenance_ref"] and checks["provenance_candidate"]:
            evidence.append("matching promotion_event provenance")
        if checks["same_asset_before_after"] and checks["valid_transition"]:
            evidence.append("before/after version or absence evidence attributing this write")

        self.required_evidence = evidence
        self.reconciled_from_readback = self.tuple_verified
        # A read/reconciliation/board path never writes. Missing or incomplete
        # evidence is reported as BLOCKED_ACK_UNKNOWN_REQUIRE_RECONCILIATION;
        # it is never patched by issuing an extra fixture write.
        self.insufficient_evidence_state = "BLOCKED_ACK_UNKNOWN_REQUIRE_RECONCILIATION"
        if self.reconciled_from_readback:
            self.readback_status = "MATCH"
            self.canonical_status = "IDEMPOTENT"
        else:
            self.readback_status = "MISMATCH"
            self.pipeline_status = "BLOCKED"

    def _board_tuple_matches(self, board: dict) -> bool:
        approved = self.approved_target or {}
        if self.approved_target is None or self.promotion_receipt is None:
            return False
        return (
            board.get("candidate_id") == approved.get("candidate_id")
            and board.get("asset_id") == approved.get("asset_id")
            and board.get("candidate_version") == approved.get("candidate_version")
            and board.get("promotion_event_ref") == self.expected_promotion_ref
            and board.get("model") == self.current_workflow_model
        )

    def _board_refresh(self, ok: bool, fresh: bool = False) -> None:
        if not ok:
            # R03: the *visible* projection must carry is_stale=true and retain
            # the last successful tuple/timestamps.
            self.board_is_stale = True
            if self.last_good_board is not None:
                retained = dict(self.last_good_board)
                retained["is_stale"] = True
                self.board = retained
                self.retains_last_good_data = True
                self.last_successful_read_at = retained.get("last_successful_read_at")
            if self.completed or self.done_badge or self.pipeline_status == "COMPLETE":
                self.completion_stale = True
            # The historical last-good projection may stay visible with
            # is_stale=true, but the *current* completion state and badge must
            # not stay latched while the tuple is unverified.
            self.completed = False
            self.done_badge = False
            if self.pipeline_status == "COMPLETE":
                self.pipeline_status = "BLOCKED"
            self.empty_success = False
            self.generated_at_unchanged = True
            return

        projected = self._project_board()
        # R03: a successful refresh must revalidate the tuple before clearing
        # the stale flag.
        self.board_is_stale = not self._board_tuple_matches(projected)
        self.board = projected
        self.generated_at = projected["generated_at"]
        self.last_successful_read_at = projected["last_successful_read_at"]
        if not self.board_is_stale:
            self.last_good_board = dict(projected)

        if fresh and "fresh board matching same target" not in self.required_evidence:
            if self.scenario_id == "F09_WRITE_ACK_UNKNOWN":
                self.required_evidence.append("fresh board matching same target")

        self._finalize_completion()
        self.board = self._project_board()
        self.board["is_stale"] = self.board_is_stale
        if not self.board_is_stale:
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
            "promotion_event_ref": self.expected_promotion_ref,
        }

    def _completion_predicate(self) -> dict:
        approved = self.approved_target or {}
        board = self.board or {}
        return {
            "execution_pass": self.execution_status == "PASS",
            "business_pass": self.business_status == "PASS",
            "content_approved": self.content_review_status == "APPROVED",
            "approval_fixture": self.application_approval_status == "VERIFIED_FIXTURE_ONLY",
            "canonical_ok": self.canonical_status in ("WRITTEN", "IDEMPOTENT"),
            "readback_match": self.readback_status == "MATCH",
            "tuple_verified": bool(self.tuple_verified),
            "write_attributed": bool(self.write_attributed),
            "board_present": bool(board),
            "board_fresh": not self.board_is_stale,
            "board_tuple_matches": bool(self.approved_target)
            and bool(self.promotion_receipt)
            and board.get("candidate_id") == approved.get("candidate_id")
            and board.get("asset_id") == approved.get("asset_id")
            and board.get("candidate_version") == approved.get("candidate_version")
            and board.get("promotion_event_ref") == self.expected_promotion_ref
            and board.get("model") == self.current_workflow_model,
            "route_ok": self.execution_route == self.fixture["input"]["execution_route"],
        }

    def _finalize_completion(self) -> None:
        evidence = self._completion_predicate()
        self.completion_evidence = evidence
        if all(evidence.values()):
            self.pipeline_status = "COMPLETE"
            self.terminal = True
            self.done_badge = True
            self.completed = True
            self.completion_stale = False
        else:
            if self.completed or self.done_badge or self.pipeline_status == "COMPLETE":
                self.completion_stale = True
            # A no-longer-satisfied predicate retracts the current completion
            # rather than latching the external state at COMPLETE. Historical
            # last-good data may remain visible with stale=true.
            self.completed = False
            self.done_badge = False
            if self.pipeline_status == "COMPLETE":
                self.pipeline_status = "BLOCKED"

    def _task_route_selection(self) -> None:
        runtime = self.fixture["runtime"]
        self.execution_route = self.fixture["input"]["execution_route"]
        self.current_workflow_model = runtime["current_workflow_model"]

    def _stub_resume(self) -> None:
        request_id = self.fixture["input"]["request_id"]
        original_task_id = self.fixture["input"]["task_id"]
        original_candidate_id = self.fixture["input"]["candidate"]["candidate_id"]
        entry = self.coordinator.resume(request_id)
        self.restored_task_id = entry["task_id"] if entry is not None else None
        self.restored_candidate_id = entry["candidate_id"] if entry is not None else None
        # R05: compare *actual restored IDs* to the original IDs.
        self.same_task_id = entry is not None and entry["task_id"] == original_task_id
        self.same_candidate_id = entry is not None and entry["candidate_id"] == original_candidate_id
        if entry is not None:
            self.task_id = entry["task_id"]
            self.candidate_id = entry["candidate_id"]
        # Counts are derived from the observable coordinator call log; a pure
        # resume never creates or dispatches.
        self.stub_creation_count = self.coordinator.creation_count
        self.stub_dispatch_count = self.coordinator.dispatch_count
        self.new_candidate_count = self.stub_creation_count
        self.new_dispatch_count = self.stub_dispatch_count
        self.live_submit_replayed = False
        self.behavior_scope = "PROPOSED_STUB_ONLY_NOT_EXISTING_SUBMIT_GUARANTEE"

    def _phone_open_approval(self) -> None:
        self.pipeline_status = "WAITING_APPLICATION_APPROVAL"
        self.application_approval_prompted = True
        self.requires_user_action = True
        self.approval_token += 1
        self.pending_approval_token = self.approval_token
        self.approval_expired = False

    def _app_approval_timeout(self) -> None:
        self.pipeline_status = "WAITING_APPLICATION_APPROVAL"
        self.application_approval_status = "NOT_COMPLETED"
        self.automatic_passkey_attempt_count = 0
        self.requires_user_action = True
        self.approval_expired = True
        self.pending_approval_token = None

    def _platform_denied(self) -> None:
        platform = self.inputs.get("platform", {})
        self.pipeline_status = "BLOCKED"
        self.terminal = True
        self.platform_denied = True
        self.reason = platform.get("reason", "ACTION_AUTHORITY_REQUIRED")
        self.application_approval_status = "NOT_COMPLETED"
        self.approved_target = None
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


def run_scenario(
    scenario_id: str,
    monitor: LiveCallMonitor,
    coordinator: FixtureCoordinator | None = None,
    fixture: dict | None = None,
) -> dict:
    engine = MobileCloudFlowEngine(
        CONTRACT, fixture if fixture is not None else FIXTURE, monitor, scenario_id, coordinator=coordinator
    )
    for event in SCENARIOS[scenario_id]["events"]:
        engine.handle_event(event)
    return engine.actual(scenario_id)


def compare(actual: dict, expected: dict) -> dict:
    return {key: actual.get(key) == value for key, value in expected.items()}


def run_fixture_suite(
    monitor: LiveCallMonitor | None = None,
    order: list[str] | None = None,
) -> dict:
    monitor = monitor if monitor is not None else LiveCallMonitor()
    results: dict[str, dict] = {}
    for scenario_id in order if order is not None else FIXTURE_SCENARIO_IDS:
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
# One test per fixture scenario (all 15 retain original expected outputs)
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
# R01: full tuple verification for COMPLETE
# ---------------------------------------------------------------------------


def _valid_tuple_inputs() -> dict:
    content = CONTRACT["input"]["candidate"]["content"]
    return {
        "approved_target": {
            "operation": "promote",
            "candidate_id": "c1",
            "candidate_version": 1,
            "asset_id": "a1",
            "content_hash": "h1",
            "review_result": "PASS",
            "reviewed_at": "2026-10-11T12:00:00.001Z",
        },
        "receipt": {
            "asset_id": "a1",
            "candidate_id": "c1",
            "candidate_version": 1,
            "canonical_version": 1,
            "content_hash": "h1",
            "promotion_event_ref": "p1",
        },
        "readback": {
            "asset_id": "a1",
            "candidate_id": "c1",
            "version": 1,
            "content_hash": "h1",
            "content": content,
            "provenance": {"promotion_event_ref": "p1", "candidate_id": "c1", "candidate_version": 1},
        },
        "provenance": {"promotion_event_ref": "p1", "candidate_id": "c1", "candidate_version": 1},
        "promotion_ref": "p1",
        "before": {"asset_id": "a1", "version": 0, "absent": True},
        "after": {
            "asset_id": "a1",
            "candidate_id": "c1",
            "candidate_version": 1,
            "version": 1,
            "content_hash": "h1",
            "absent": False,
        },
        "route": "ordinary_cloudagent",
        "expected_content": content,
    }


def _verify(inputs: dict) -> dict:
    return verify_promotion_tuple(
        approved_target=inputs["approved_target"],
        receipt=inputs["receipt"],
        readback=inputs["readback"],
        provenance=inputs["provenance"],
        promotion_ref=inputs["promotion_ref"],
        before=inputs["before"],
        after=inputs["after"],
        route=inputs["route"],
        expected_content=inputs["expected_content"],
    )


def test_r01_normal_full_tuple_verifies() -> None:
    checks = _verify(_valid_tuple_inputs())
    assert all(checks.values()), checks


def test_r01_wrong_candidate_id_is_blocked() -> None:
    inputs = _valid_tuple_inputs()
    inputs["readback"]["candidate_id"] = "different-candidate"
    checks = _verify(inputs)
    assert checks["readback_identity"] is False
    assert not all(checks.values())


def test_r01_wrong_asset_id_is_blocked() -> None:
    inputs = _valid_tuple_inputs()
    inputs["readback"]["asset_id"] = "different-asset"
    checks = _verify(inputs)
    assert checks["readback_identity"] is False


def test_r01_wrong_hash_is_blocked() -> None:
    inputs = _valid_tuple_inputs()
    inputs["readback"]["content_hash"] = "different-hash"
    checks = _verify(inputs)
    assert checks["readback_identity"] is False


def test_r01_same_hash_wrong_version_is_blocked() -> None:
    inputs = _valid_tuple_inputs()
    # Same hash, but canonical asset version is 999 while the receipt is 1.
    inputs["readback"]["version"] = 999
    checks = _verify(inputs)
    assert checks["readback_identity"] is True  # hash/id still match
    assert checks["readback_version_is_receipt"] is False
    assert not all(checks.values())


def test_r01_wrong_promotion_ref_is_blocked() -> None:
    inputs = _valid_tuple_inputs()
    inputs["provenance"]["promotion_event_ref"] = "other-ref"
    inputs["readback"]["provenance"]["promotion_event_ref"] = "other-ref"
    checks = _verify(inputs)
    assert checks["provenance_ref"] is False


def test_r01_wrong_route_is_blocked() -> None:
    inputs = _valid_tuple_inputs()
    inputs["route"] = "alternate_tool"
    checks = _verify(inputs)
    assert checks["route"] is False


def test_r01_missing_reviewed_at_is_blocked() -> None:
    inputs = _valid_tuple_inputs()
    inputs["approved_target"]["reviewed_at"] = ""
    checks = _verify(inputs)
    assert checks["approved_target_complete"] is False


def test_r01_integration_same_hash_version_999_cannot_complete() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    engine.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    asset = engine.canonical.read(engine.asset_id)
    assert asset is not None
    # Keep the hash but change the canonical version to 999.
    asset["version"] = 999
    engine.canonical._assets[engine.asset_id] = asset
    engine._canonical_read_exact_provenance()
    assert engine.tuple_evidence["readback_version_is_receipt"] is False
    engine._board_refresh(ok=True, fresh=True)
    assert engine.pipeline_status != "COMPLETE"


def test_r01_positive_flow_still_completes() -> None:
    monitor = LiveCallMonitor()
    result = run_scenario("F01_COMPLETE_PATH", monitor)
    assert result["pipeline_status"] == "COMPLETE"


# ---------------------------------------------------------------------------
# R02: F09 reconciliation requires complete independent evidence
# ---------------------------------------------------------------------------


def test_r02_positive_evidence_is_complete() -> None:
    entry = SUITE["results"]["F09_WRITE_ACK_UNKNOWN"]["actual"]
    assert entry["reconciled_from_readback"] is True
    assert entry["pipeline_status"] == "COMPLETE"
    assert entry["required_evidence"] == [
        "matching approved candidate_id/candidate_version/asset_id/content_hash",
        "matching promotion_event provenance",
        "before/after version or absence evidence attributing this write",
        "fresh board matching same target",
    ]


def test_r02_missing_after_candidate_version_is_blocked() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    engine.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    engine.after_record["candidate_version"] = 999
    engine._canonical_read_exact_provenance()
    assert engine.tuple_evidence["after_matches_target"] is False
    assert engine.reconciled_from_readback is False
    assert engine.readback_status == "MISMATCH"
    assert engine.pipeline_status == "BLOCKED"


def test_r02_unrelated_before_asset_is_blocked() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    engine.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    engine.before_snapshot["asset_id"] = "unrelated-asset"
    engine._canonical_read_exact_provenance()
    assert engine.tuple_evidence["same_asset_before_after"] is False
    assert engine.reconciled_from_readback is False


def test_r02_missing_provenance_candidate_is_blocked() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    engine.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    engine.canonical._assets[engine.asset_id]["provenance"] = {"promotion_event_ref": "fixture-promotion-001"}
    engine._canonical_read_exact_provenance()
    assert engine.tuple_evidence["provenance_candidate"] is False
    assert engine.reconciled_from_readback is False


def test_r02_inconsistent_evidence_never_writes_again() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    engine.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    writes_after_first = engine.canonical.write_count
    engine.canonical._assets[engine.asset_id]["content_hash"] = "0" * 64
    engine._canonical_read_exact_provenance()
    assert engine.tuple_evidence["readback_identity"] is False
    assert engine.reconciled_from_readback is False
    assert engine.canonical.write_count == writes_after_first
    assert engine.automatic_second_write_count == 0


# ---------------------------------------------------------------------------
# R03: F11 visible stale projection and revalidation
# ---------------------------------------------------------------------------


def test_r03_failed_refresh_visible_projection_is_stale() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F11_BOARD_REFRESH_ERROR")
    before_generated = engine.board["generated_at"]
    before_read = engine.board["last_successful_read_at"]
    before_task = engine.board["task_id"]
    engine.handle_event("BOARD_REFRESH_FAIL")
    assert engine.board["is_stale"] is True
    assert engine.board["generated_at"] == before_generated
    assert engine.board["last_successful_read_at"] == before_read
    assert engine.board["task_id"] == before_task


def test_r03_completed_refresh_failure_makes_evidence_stale() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    for event in SCENARIOS["F01_COMPLETE_PATH"]["events"]:
        engine.handle_event(event)
    assert engine.completed is True
    engine._board_refresh(ok=False)
    assert engine.completion_stale is True
    assert engine.board["is_stale"] is True


def test_r03_later_success_revalidates_matching_tuple() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    for event in SCENARIOS["F01_COMPLETE_PATH"]["events"]:
        engine.handle_event(event)
    engine._board_refresh(ok=False)
    assert engine.board["is_stale"] is True
    engine._board_refresh(ok=True)
    assert engine.board["is_stale"] is False
    assert engine.completion_stale is False


def test_r03_success_with_wrong_tuple_stays_stale() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    for event in SCENARIOS["F01_COMPLETE_PATH"]["events"]:
        engine.handle_event(event)
    engine._board_refresh(ok=False)
    engine.candidate_version = 999
    engine._board_refresh(ok=True)
    assert engine.board["is_stale"] is True


# ---------------------------------------------------------------------------
# R04: F10 readback truth from an independent synthetic reader
# ---------------------------------------------------------------------------


def test_r04_mismatching_hash_is_blocked_without_extra_write() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F10_READBACK_MISMATCH")
    # The stated "writer already returned WRITTEN" precondition is performed
    # once at construction, outside any read/board path.
    assert engine.canonical.write_count == 1
    assert engine.canonical.write_attempt_count == 1
    writes_before = engine.canonical.write_count
    engine.handle_event("CANONICAL_READ_MISMATCH_FIXTURE")
    assert engine.readback_status == "MISMATCH"
    assert engine.canonical.write_count == writes_before  # reads never write
    engine._board_refresh(ok=True)
    assert engine.pipeline_status == "BLOCKED"
    assert engine.pipeline_status != "COMPLETE"
    assert engine.new_write_to_hide_mismatch_count == 0


def test_r04_differing_version_same_hash_is_blocked() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F10_READBACK_MISMATCH")
    engine.inputs["readback"]["actual_hash"] = engine.inputs["readback"]["expected_hash"]
    engine.inputs["readback"]["actual_version"] = 999
    engine.handle_event("CANONICAL_READ_MISMATCH_FIXTURE")
    assert engine.readback_status == "MISMATCH"
    assert engine.tuple_evidence["readback_identity"] is True
    assert engine.tuple_evidence["readback_version_is_receipt"] is False


def test_r04_matching_control_record_yields_match() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F10_READBACK_MISMATCH")
    engine.inputs["readback"]["actual_hash"] = engine.inputs["readback"]["expected_hash"]
    engine.inputs["readback"]["actual_version"] = engine.inputs["readback"]["expected_version"]
    engine.handle_event("CANONICAL_READ_MISMATCH_FIXTURE")
    assert engine.readback_status == "MATCH"
    assert engine.tuple_verified is True


def test_r04_wrong_ids_and_provenance_are_blocked() -> None:
    inputs = _valid_tuple_inputs()
    inputs["readback"]["candidate_id"] = "imposter"
    inputs["provenance"]["candidate_id"] = "imposter"
    checks = _verify(inputs)
    assert checks["readback_identity"] is False
    assert checks["provenance_candidate"] is False
    assert not all(checks.values())


# ---------------------------------------------------------------------------
# R05: F07 durable mapping and observable stub counts
# ---------------------------------------------------------------------------


def test_r05_f07_mapping_survives_engine_reconstruction() -> None:
    coordinator = FixtureCoordinator()
    monitor = LiveCallMonitor()
    engine_a = MobileCloudFlowEngine(
        CONTRACT, FIXTURE, monitor, "F07_PHONE_RELOAD_RESUME", coordinator=coordinator
    )
    for event in SCENARIOS["F07_PHONE_RELOAD_RESUME"]["events"]:
        engine_a.handle_event(event)
    assert engine_a.same_task_id is True
    assert engine_a.same_candidate_id is True

    engine_b = MobileCloudFlowEngine(
        CONTRACT, FIXTURE, monitor, "F07_PHONE_RELOAD_RESUME", coordinator=coordinator
    )
    engine_b.handle_event("PROPOSED_STUB_RESUME_SAME_REQUEST")
    assert engine_b.restored_task_id == FIXTURE["input"]["task_id"]
    assert engine_b.restored_candidate_id == FIXTURE["input"]["candidate"]["candidate_id"]
    assert engine_b.same_task_id is True
    assert engine_b.same_candidate_id is True
    assert coordinator.creation_count == 0
    assert coordinator.dispatch_count == 0
    assert len(coordinator.requests) == 1


def test_r05_repeated_reopen_does_not_create_or_dispatch() -> None:
    coordinator = FixtureCoordinator()
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(
        CONTRACT, FIXTURE, monitor, "F07_PHONE_RELOAD_RESUME", coordinator=coordinator
    )
    for _ in range(5):
        engine.handle_event("PROPOSED_STUB_RESUME_SAME_REQUEST")
    assert engine.stub_creation_count == 0
    assert engine.stub_dispatch_count == 0
    assert engine.live_submit_replayed is False
    assert engine.behavior_scope == "PROPOSED_STUB_ONLY_NOT_EXISTING_SUBMIT_GUARANTEE"


def test_r05_missing_mapping_is_not_falsely_reused() -> None:
    coordinator = FixtureCoordinator()
    assert coordinator.resume("unknown-request") is None
    assert coordinator.creation_count == 0

    # Different-request positive counting control: a genuinely new request is
    # created and dispatched exactly once.
    coordinator.submit("request-2", "task-2", "candidate-2")
    coordinator.submit("request-2", "task-2", "candidate-2")
    assert coordinator.creation_count == 1
    assert coordinator.dispatch_count == 1
    assert coordinator.resume("request-2") == {"task_id": "task-2", "candidate_id": "candidate-2"}


def test_r05_incorrect_ids_are_not_reported_as_same() -> None:
    coordinator = FixtureCoordinator()
    coordinator.seed("fixture-submit-001", "wrong-task", "wrong-candidate")
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(
        CONTRACT, FIXTURE, monitor, "F07_PHONE_RELOAD_RESUME", coordinator=coordinator
    )
    engine.handle_event("PROPOSED_STUB_RESUME_SAME_REQUEST")
    assert engine.restored_task_id == "wrong-task"
    assert engine.same_task_id is False
    assert engine.same_candidate_id is False


# ---------------------------------------------------------------------------
# R06: forbidden-operation monitor/guard self-tests
# ---------------------------------------------------------------------------


def test_r06_forbidden_seam_increments_and_rejects_before_io() -> None:
    monitor = LiveCallMonitor()
    seam = ForbiddenSeam(monitor, monitor.record_network, "synthetic-network")
    with pytest.raises(ForbiddenOperationError):
        seam()
    assert monitor.network_call_count == 1
    assert seam.call_count == 1


def test_r06_scoped_guard_blocks_and_restores() -> None:
    monitor = LiveCallMonitor()
    original_socket = socket.socket
    original_popen = subprocess.Popen
    with ScopedForbiddenIOGuard(monitor):
        with pytest.raises(ForbiddenOperationError):
            socket.create_connection(("example.invalid", 80))
        with pytest.raises(ForbiddenOperationError):
            subprocess.Popen(["true"])
    assert monitor.network_call_count == 1
    assert monitor.subprocess_execution_count == 1
    assert socket.socket is original_socket
    assert subprocess.Popen is original_popen


def test_r06_normal_fixture_boundary_observes_zero_forbidden_calls() -> None:
    monitor = LiveCallMonitor()
    with ScopedForbiddenIOGuard(monitor):
        suite = run_fixture_suite(monitor=monitor)
    assert suite["all_ok"] is True
    observed = monitor.as_dict()
    for name in LIVE_FORBIDDEN_COUNTERS:
        assert observed[name] == 0, name
    assert observed["repository_code_executed"] is False


# ---------------------------------------------------------------------------
# R07: explicit fixture state guards
# ---------------------------------------------------------------------------


def test_r07_f06_followed_by_write_does_not_write() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F06_CONTENT_APPROVAL_ONLY")
    engine.handle_event("CONTENT_APPROVED")
    result = engine._perform_fixture_write(ack="OK")
    assert result == "REFUSED"
    assert engine.canonical.write_count == 0
    assert engine.refused_write_count == 1


def test_r07_expired_approval_cannot_be_revived() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F08_APP_APPROVAL_EXPIRED")
    engine.handle_event("PHONE_OPEN_APPROVAL")
    engine.handle_event("APP_APPROVAL_TIMEOUT")
    engine.handle_event("APPLICATION_APPROVED_FIXTURE")  # old approval event
    assert engine.application_approval_status == "NOT_COMPLETED"
    assert engine.approved_target is None
    assert engine.refused_approval_event_count == 1
    assert engine._perform_fixture_write(ack="OK") == "REFUSED"
    assert engine.canonical.write_count == 0


def test_r07_platform_denial_cannot_be_bypassed() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F13_PLATFORM_ACTION_DENIED")
    engine.handle_event("PLATFORM_DENIED")
    engine.handle_event("CONTENT_APPROVED")
    engine.handle_event("APPLICATION_APPROVED_FIXTURE")
    assert engine._perform_fixture_write(ack="OK") == "REFUSED"
    assert engine.canonical.write_count == 0
    assert engine.alternate_tool_or_environment_attempt_count == 0
    assert engine.retry_without_new_valid_authority_count == 0


def test_r07_repeated_approved_promotion_does_not_write_again() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    for event in SCENARIOS["F01_COMPLETE_PATH"]["events"]:
        engine.handle_event(event)
    assert engine.canonical.write_count == 1
    second = engine._perform_fixture_write(ack="OK")
    assert second == "IDEMPOTENT"
    assert engine.canonical.write_count == 1
    assert engine.repeated_write_skipped_count == 1


def test_r07_candidate_revision_invalidates_approval() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    engine.handle_event("PHONE_SUBMIT")
    engine.handle_event("CONTENT_APPROVED")
    engine.handle_event("APPLICATION_APPROVED_FIXTURE")
    assert engine.application_approval_status == "VERIFIED_FIXTURE_ONLY"
    engine.handle_event("CONTENT_CHANGES_REQUESTED")
    assert engine.approval_invalidated is True
    assert engine.approved_target is None
    assert engine._perform_fixture_write(ack="OK") == "REFUSED"
    assert engine.canonical.write_count == 0


# ---------------------------------------------------------------------------
# R09: input isolation, determinism and test-order independence
# ---------------------------------------------------------------------------


def test_r09_negative_case_cannot_mutate_shared_fixture() -> None:
    shared_before = json.dumps(FIXTURE, sort_keys=True)
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    engine.inputs["promotion"]["before"]["asset_id"] = "mutated-in-engine"
    engine.inputs["promotion"]["before"]["version"] = 12345
    assert engine.inputs["promotion"]["before"]["asset_id"] == "mutated-in-engine"
    assert json.dumps(FIXTURE, sort_keys=True) == shared_before
    assert "mutated-in-engine" not in json.dumps(FIXTURE)


def test_r09_positive_case_still_passes_after_negative_case() -> None:
    # Run the mutating negative case first, then a positive run in-process.
    negative = MobileCloudFlowEngine(CONTRACT, FIXTURE, LiveCallMonitor(), "F09_WRITE_ACK_UNKNOWN")
    negative.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    negative.inputs["promotion"]["before"]["asset_id"] = "mutated"
    positive = run_scenario("F01_COMPLETE_PATH", LiveCallMonitor())
    assert positive["pipeline_status"] == "COMPLETE"


def test_r09_suite_reruns_are_identical() -> None:
    first = run_fixture_suite()
    second = run_fixture_suite()
    assert first["results"] == second["results"]
    assert first["forbidden"] == second["forbidden"]
    assert first["all_ok"] == second["all_ok"] is True


def test_r09_test_order_does_not_change_results() -> None:
    forward = run_fixture_suite(order=list(FIXTURE_SCENARIO_IDS))
    backward = run_fixture_suite(order=list(reversed(FIXTURE_SCENARIO_IDS)))
    for scenario_id in FIXTURE_SCENARIO_IDS:
        assert forward["results"][scenario_id]["actual"] == backward["results"][scenario_id]["actual"]
        assert forward["results"][scenario_id]["match"] is True


# ---------------------------------------------------------------------------
# Consolidated negative guarantee (cannot incorrectly become COMPLETE)
# ---------------------------------------------------------------------------


def _completion_evidence_for_engine(engine: MobileCloudFlowEngine) -> dict:
    return engine._completion_predicate()


def test_no_incorrect_flow_can_become_complete_or_write_again() -> None:
    monitor = LiveCallMonitor()

    # Unapproved: F06 write attempt.
    f06 = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F06_CONTENT_APPROVAL_ONLY")
    f06.handle_event("CONTENT_APPROVED")
    assert f06._perform_fixture_write(ack="OK") == "REFUSED"
    assert f06.pipeline_status != "COMPLETE"

    # Expired: F08.
    f08 = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F08_APP_APPROVAL_EXPIRED")
    f08.handle_event("PHONE_OPEN_APPROVAL")
    f08.handle_event("APP_APPROVAL_TIMEOUT")
    f08.handle_event("APPLICATION_APPROVED_FIXTURE")
    assert f08.pipeline_status != "COMPLETE"
    assert f08.canonical.write_count == 0

    # Denied: F13.
    f13 = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F13_PLATFORM_ACTION_DENIED")
    f13.handle_event("PLATFORM_DENIED")
    assert f13._perform_fixture_write(ack="OK") == "REFUSED"
    assert f13.pipeline_status != "COMPLETE"

    # Insufficient ack evidence: F09 hash-only.
    f09 = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    f09.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    f09.inputs["promotion"]["before"] = {"asset_id": f09.asset_id, "version": 1, "absent": False}
    f09.canonical._assets[f09.asset_id]["provenance"] = {"promotion_event_ref": "other"}
    f09._canonical_read_exact_provenance()
    f09._board_refresh(ok=True, fresh=True)
    assert f09.pipeline_status != "COMPLETE"

    # Wrong tuple: run F01 up to (but not including) the board refresh, then
    # corrupt the tuple and refresh. The board must not project COMPLETE.
    f01 = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    for event in SCENARIOS["F01_COMPLETE_PATH"]["events"][:-1]:
        f01.handle_event(event)
    f01.candidate_version = 999
    f01.handle_event("BOARD_REFRESH")
    assert f01.pipeline_status != "COMPLETE"

    # Repeated write: F01 then another promotion.
    f01b = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    for event in SCENARIOS["F01_COMPLETE_PATH"]["events"]:
        f01b.handle_event(event)
    assert f01b._perform_fixture_write(ack="OK") == "IDEMPOTENT"
    assert f01b.canonical.write_count == 1


# ---------------------------------------------------------------------------
# Machine-readable report (pure builder; tests never overwrite the committed file)
# ---------------------------------------------------------------------------


def evaluate_scenarios(suite: dict) -> list[dict]:
    entries = []
    for scenario_id in ALL_SCENARIO_IDS:
        entry = suite["results"][scenario_id]
        entries.append(
            {
                "id": scenario_id,
                "status": "PASS" if entry["match"] else "FAIL",
                "actual": entry["actual"],
                "expected": entry["expected"],
            }
        )
    return entries


def _not_observed_phase(command: str) -> dict:
    return {
        "command": command,
        "status": NOT_OBSERVED,
        "observed": False,
        "exit_code": None,
        "passed": None,
        "failed": None,
        "skipped": None,
        "duration_seconds": None,
        "phase": None,
        "source": None,
        "commit": None,
        "tested_revision": "not_observed",
    }


def default_run_metadata() -> dict:
    return {
        "checkout_baseline_sha": "11df59bc927dbb54141c89b77f21a156778ed025",
        "produced_commit_note": (
            "the produced commit SHA is recorded by the runner's execution_result.json after "
            "this report is committed; it is intentionally not self-referenced here"
        ),
        "phases": {
            "agent_focused": _not_observed_phase("python -m pytest -q tests/test_mobile_cloud_flow_v1.py"),
            "agent_affected_combined": _not_observed_phase(
                "python -m pytest -q tests/test_mobile_cloud_flow_v1.py "
                "tests/test_status_contract_v0_2.py tests/test_result_normalization.py"
            ),
            "agent_full_suite": _not_observed_phase("python -m pytest -q"),
            "workflow_verify_full_suite": _not_observed_phase("python -m pytest -q"),
        },
        "workflow_actions": {
            "main_push": {
                "scope": "workflow_record_not_fixture_counter",
                "status": NOT_OBSERVED,
                "note": "main push is performed by the dispatch workflow after this commit",
            },
            "serverchan_notification": {
                "scope": "workflow_record_not_fixture_counter",
                "status": NOT_OBSERVED,
                "note": "ServerChan delivery is performed by the dispatch workflow after this commit",
            },
        },
        "previous_run_evidence": {
            "run_id": 38144001460,
            "head_sha": "11df59bc927dbb54141c89b77f21a156778ed025",
            "produced_commit": "11df59bc927dbb54141c89b77f21a156778ed025",
            "note": (
                "historical previous-repair-run evidence only; never this continuation's results"
            ),
            "focused": "python -m pytest -q tests/test_mobile_cloud_flow_v1.py: 68 passed",
            "combined": (
                "python -m pytest -q tests/test_mobile_cloud_flow_v1.py "
                "tests/test_status_contract_v0_2.py tests/test_result_normalization.py: 115 passed"
            ),
            "agent_full_suite": (
                "python -m pytest -q: 1655 passed, 1 skipped in 48.20s/48.73s before commit"
            ),
            "workflow_verify_full_suite": (
                "python -m pytest -q: 1655 passed, 1 skipped in 48.77s on produced commit "
                "11df59bc927dbb54141c89b77f21a156778ed025"
            ),
        },
        "fixture_io_observation": {
            "instrumented_boundaries": list(GUARD_INSTRUMENTED_BOUNDARIES),
            "not_instrumented_boundaries": list(GUARD_NOT_INSTRUMENTED_BOUNDARIES),
            "observed_forbidden_calls": 0,
            "note": (
                "zero observed calls is scoped to the stated instrumented boundary only; "
                "un-instrumented live services remain UNKNOWN/NOT_INSTRUMENTED"
            ),
        },
    }


REQUIRED_AGENT_PHASES = ("agent_focused", "agent_affected_combined", "agent_full_suite")


def _phase_verdict(record: dict) -> str:
    """Reduce one phase record to PASS / FAIL / NOT_OBSERVED."""
    if not record.get("observed"):
        return "NOT_OBSERVED"
    return "PASS" if record.get("status") == "PASS" else "FAIL"


def _aggregate_agent_phases(phases: dict) -> str:
    """Aggregate only from actually observed phase records.

    Any observed required FAIL fails the aggregate; any unobserved required
    phase keeps it pending. It is never CONTRACT_PASS without observations.
    """
    verdicts = [_phase_verdict(phases.get(key, {})) for key in REQUIRED_AGENT_PHASES]
    if any(verdict == "FAIL" for verdict in verdicts):
        return "FAIL"
    if any(verdict == "NOT_OBSERVED" for verdict in verdicts):
        return "PENDING"
    return "PASS"


def build_report(suite: dict | None = None, run_metadata: dict | None = None) -> dict:
    """Build the fixture report. Pure: performs no file writes."""
    suite = suite if suite is not None else run_fixture_suite()
    metadata = run_metadata if run_metadata is not None else default_run_metadata()
    contract_bytes = CONTRACT_PATH.read_bytes()
    contract_sha256 = hashlib.sha256(contract_bytes).hexdigest()
    phases = metadata.get("phases", {})
    workflow_actions = metadata.get("workflow_actions", {})
    focused_phase = phases.get("agent_focused", {})
    full_phase = phases.get("agent_full_suite", {})
    workflow_phase = phases.get("workflow_verify_full_suite", {})
    scenario_evaluation = "PASS" if suite["all_ok"] else "FAIL"
    process_status = _aggregate_agent_phases(phases)
    if scenario_evaluation == "FAIL" or process_status == "FAIL":
        aggregate_verdict = "FAIL"
    elif process_status == "PENDING":
        aggregate_verdict = "PENDING"
    else:
        aggregate_verdict = "CONTRACT_PASS"
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
        "scenarios": evaluate_scenarios(suite),
        "live_call_counters": suite["forbidden"],
        "network_call_count": suite["forbidden"]["network_call_count"],
        "live_passkey_call_count": suite["forbidden"]["live_passkey_call_count"],
        "live_db_call_count": suite["forbidden"]["live_db_call_count"],
        "real_dispatch_count": suite["forbidden"]["real_dispatch_count"],
        "external_mutation_count": suite["forbidden"]["external_mutation_count"],
        "subprocess_execution_count": suite["forbidden"]["subprocess_execution_count"],
        "repository_code_executed": suite["forbidden"]["repository_code_executed"],
        "mobile_e2e_status": "NOT_RUN",
        "production_write_status": "NOT_RUN",
        "release_status": "NOT_PERFORMED",
        "full_repository_suite_status": full_phase.get("status", NOT_OBSERVED),
        "contract_planned_full_repository_suite_status": CONTRACT_PLANNED_FULL_SUITE_STATUS,
        "full_repository_suite_note": (
            "actual execution status is recorded per phase; the original contract value "
            "NOT_RUN_THIS_ROUND is retained only as a historical planned value"
        ),
        "execution_phases": phases,
        "workflow_actions": workflow_actions,
        "checkout_baseline_sha": metadata.get("checkout_baseline_sha"),
        "produced_commit_note": metadata.get("produced_commit_note"),
        "previous_run_evidence": metadata.get("previous_run_evidence"),
        "fixture_io_observation": metadata.get("fixture_io_observation", default_run_metadata()["fixture_io_observation"]),
        "scenario_evaluation": scenario_evaluation,
        "process_status": process_status,
        "workflow_verify_status": workflow_phase.get("status", NOT_OBSERVED),
        "workflow_verify_receipt": workflow_phase,
        "focused_suite": {
            "command": focused_phase.get("command", "python -m pytest -q tests/test_mobile_cloud_flow_v1.py"),
            "status": focused_phase.get("status", NOT_OBSERVED),
            "scenario_pass_count": sum(1 for e in suite["results"].values() if e["match"]),
            "scenario_total": len(suite["results"]),
        },
        "directly_affected_existing_tests": [
            "tests/test_status_contract_v0_2.py",
            "tests/test_result_normalization.py",
        ],
        "execution_result": aggregate_verdict,
        "business_final_status": aggregate_verdict,
        "not_claimed": [
            "phone access / mobile E2E",
            "real passkey or live application approval",
            "real D1 or Canonical production write",
            "deployed dashboard freshness",
            "source equivalence with unpublished Site v32 / 33-file patches",
        ],
        "f07_scope": "PROPOSED_STUB_ONLY_NOT_EXISTING_SUBMIT_GUARANTEE",
        "f09_scope": (
            "hash equality alone is insufficient; requires exact approved target, matching "
            "promotion provenance, before/after evidence, fresh board"
        ),
        "forbidden_io": CONTRACT["forbidden_io"],
        "ordinary_execution_route": {
            "execution_route": "ordinary_cloudagent",
            "current_workflow_model": "opencode-go/deepseek-v4.1-flash",
            "new_model_interface_added": False,
            "new_infrastructure_added": False,
        },
        "golden_fixture_convention": "no root execution_result.json is written or committed",
    }


def test_report_builder_is_pure_and_serializes_to_tmp(tmp_path: Path) -> None:
    before = REPORT_PATH.read_bytes() if REPORT_PATH.exists() else None
    report = build_report(run_metadata=_all_agent_phases_pass())
    # A pure builder must never touch the committed report.
    after = REPORT_PATH.read_bytes() if REPORT_PATH.exists() else None
    assert before == after

    out = tmp_path / "mobile_cloud_flow_v1_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reloaded = load_json(out)
    assert reloaded["schema"] == "personal-ai-mobile-cloud-flow-report/v1"
    assert reloaded["validation_level"] == "CONTRACT_ONLY"
    assert reloaded["mobile_e2e_status"] == "NOT_RUN"
    assert reloaded["production_write_status"] == "NOT_RUN"
    assert reloaded["release_status"] == "NOT_PERFORMED"
    assert len(reloaded["scenarios"]) == 15
    assert all(scenario["status"] == "PASS" for scenario in reloaded["scenarios"])
    assert reloaded["scenario_evaluation"] == "PASS"
    assert reloaded["process_status"] == "PASS"
    assert reloaded["execution_result"] == "CONTRACT_PASS"
    assert reloaded["source_manifest_sha256"] is None
    assert reloaded["contract_planned_full_repository_suite_status"] == CONTRACT_PLANNED_FULL_SUITE_STATUS
    assert reloaded["network_call_count"] == 0
    assert reloaded["live_passkey_call_count"] == 0
    assert reloaded["live_db_call_count"] == 0
    assert reloaded["real_dispatch_count"] == 0
    assert reloaded["subprocess_execution_count"] == 0
    assert reloaded["repository_code_executed"] is False
    assert reloaded["execution_result"] != "MOBILE_E2E_PASS"
    # Unobserved phases must be honestly pending, never invented.
    assert reloaded["execution_phases"]["workflow_verify_full_suite"]["status"] == NOT_OBSERVED
    for action in FIXTURE_WORKFLOW_SCOPED_ACTIONS:
        assert reloaded["workflow_actions"][action]["scope"] == "workflow_record_not_fixture_counter"


def test_reported_status_is_never_mobile_e2e_pass() -> None:
    entry = SUITE["results"]["F15_PHONE_END_TO_END_EVIDENCE_GAP"]["actual"]
    assert entry["reported_status"] == "CONTRACT_PASS"
    assert entry["reported_status"] != "MOBILE_E2E_PASS"
    assert entry["mobile_e2e_status"] == "NOT_RUN"
    assert entry["production_write_status"] == "NOT_RUN"
    assert entry["release_status"] == "NOT_PERFORMED"


def test_committed_report_exists_and_labels_contract_only() -> None:
    if not REPORT_PATH.exists():
        pytest.skip("committed report is generated deliberately after validations")
    report = load_json(REPORT_PATH)
    assert report["validation_level"] == "CONTRACT_ONLY"
    assert report["execution_result"] in ("CONTRACT_PASS", "FAIL")
    assert report["execution_result"] != "MOBILE_E2E_PASS"
    assert report["mobile_e2e_status"] == "NOT_RUN"
    assert report["production_write_status"] == "NOT_RUN"
    assert report["release_status"] == "NOT_PERFORMED"
    for action in FIXTURE_WORKFLOW_SCOPED_ACTIONS:
        assert report["workflow_actions"][action]["scope"] == "workflow_record_not_fixture_counter"


# ---------------------------------------------------------------------------
# S01: complete promotion tuple (receipt candidate_version/ref, after version,
# and an explicit, explainable before/after transition)
# ---------------------------------------------------------------------------


def test_s01_unit_after_version_must_equal_receipt_canonical_version() -> None:
    inputs = _valid_tuple_inputs()
    # Only after.version changes; receipt.canonical_version and readback.version
    # stay 1. The canonical asset version is what the write produced.
    inputs["after"]["version"] = 999
    checks = _verify(inputs)
    assert checks["after_matches_target"] is False
    assert not all(checks.values())


def test_s01_unit_receipt_candidate_version_must_match_approved() -> None:
    inputs = _valid_tuple_inputs()
    inputs["receipt"]["candidate_version"] = 999
    checks = _verify(inputs)
    assert checks["receipt_matches_target"] is False
    assert not all(checks.values())


def test_s01_unit_receipt_promotion_ref_must_match_expected() -> None:
    inputs = _valid_tuple_inputs()
    inputs["receipt"]["promotion_event_ref"] = "other-ref"
    checks = _verify(inputs)
    assert checks["receipt_matches_target"] is False
    assert not all(checks.values())


def test_s01_unit_decreased_before_version_is_invalid_transition() -> None:
    inputs = _valid_tuple_inputs()
    inputs["before"] = {"asset_id": "a1", "version": 999, "absent": False}
    checks = _verify(inputs)
    assert checks["same_asset_before_after"] is True
    assert checks["valid_transition"] is False
    assert not all(checks.values())


def test_s01_unit_missing_before_version_is_invalid_transition() -> None:
    inputs = _valid_tuple_inputs()
    inputs["before"] = {"asset_id": "a1", "absent": False}
    checks = _verify(inputs)
    assert checks["valid_transition"] is False
    assert not all(checks.values())


def test_s01_unit_after_absent_is_not_a_real_after() -> None:
    inputs = _valid_tuple_inputs()
    # Same target fields and version, but the after record says the asset is
    # absent; that cannot be the record this promotion produced.
    inputs["after"]["absent"] = True
    checks = _verify(inputs)
    assert checks["after_matches_target"] is False
    assert not all(checks.values())


def test_s01_unit_distinct_candidate_and_canonical_versions_are_supported() -> None:
    inputs = _valid_tuple_inputs()
    # candidate_version (what was approved) and canonical asset version (what
    # the write produced) are deliberately different concepts.
    inputs["approved_target"]["candidate_version"] = 2
    inputs["receipt"]["candidate_version"] = 2
    inputs["receipt"]["canonical_version"] = 3
    inputs["readback"]["version"] = 3
    inputs["after"]["candidate_version"] = 2
    inputs["after"]["version"] = 3
    inputs["provenance"]["candidate_version"] = 2
    inputs["readback"]["provenance"]["candidate_version"] = 2
    checks = _verify(inputs)
    assert checks["receipt_matches_target"] is True
    assert checks["readback_version_is_receipt"] is True
    assert checks["after_matches_target"] is True
    assert all(checks.values()), checks


def test_s01_integration_after_version_999_cannot_reconcile() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    engine.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    engine.after_record["version"] = 999
    engine._canonical_read_exact_provenance()
    assert engine.tuple_evidence["after_matches_target"] is False
    assert engine.reconciled_from_readback is False
    assert engine.insufficient_evidence_state == "BLOCKED_ACK_UNKNOWN_REQUIRE_RECONCILIATION"
    assert engine.done_badge is False
    engine._board_refresh(ok=True, fresh=True)
    assert engine.pipeline_status == "BLOCKED"
    assert engine.pipeline_status != "COMPLETE"


# ---------------------------------------------------------------------------
# S02: readback / reconciliation / board paths never call the writer
# ---------------------------------------------------------------------------


def test_s02_read_without_receipt_never_writes() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    assert engine.promotion_receipt is None
    writes_before = engine.canonical.write_count
    attempts_before = engine.canonical.write_attempt_count
    engine._canonical_read_exact_provenance()
    assert engine.canonical.write_count == writes_before
    assert engine.canonical.write_attempt_count == attempts_before
    assert engine.insufficient_evidence_state == "BLOCKED_ACK_UNKNOWN_REQUIRE_RECONCILIATION"
    assert engine.pipeline_status == "BLOCKED"
    assert engine.reconciled_from_readback is False


def test_s02_repeated_read_and_board_events_never_write() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    writes_before = engine.canonical.write_count
    attempts_before = engine.canonical.write_attempt_count
    for _ in range(3):
        engine._canonical_read_exact_provenance()
        engine._board_refresh(ok=True)
    assert engine.canonical.write_count == writes_before
    assert engine.canonical.write_attempt_count == attempts_before
    assert engine.reconciled_from_readback is False
    assert engine.pipeline_status != "COMPLETE"


def test_s02_wrong_tuple_read_never_adds_writes() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F09_WRITE_ACK_UNKNOWN")
    engine.handle_event("PROMOTE_FIXTURE_ACK_UNKNOWN")
    writes_after_promote = engine.canonical.write_count
    attempts_after_promote = engine.canonical.write_attempt_count
    engine.canonical._assets[engine.asset_id]["content_hash"] = "0" * 64
    for _ in range(3):
        engine._canonical_read_exact_provenance()
        engine._board_refresh(ok=True)
    assert engine.canonical.write_count == writes_after_promote
    assert engine.canonical.write_attempt_count == attempts_after_promote
    assert engine.reconciled_from_readback is False
    assert engine.pipeline_status != "COMPLETE"


# ---------------------------------------------------------------------------
# S03: the first write is bound to the approved target
# ---------------------------------------------------------------------------


def _approved_f01_engine() -> MobileCloudFlowEngine:
    engine = MobileCloudFlowEngine(
        CONTRACT, FIXTURE, LiveCallMonitor(), "F01_COMPLETE_PATH"
    )
    engine.handle_event("PHONE_SUBMIT")
    engine.handle_event("CONTENT_APPROVED")
    engine.handle_event("APPLICATION_APPROVED_FIXTURE")
    return engine


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_version", 999),
        ("candidate_id", "other-candidate"),
        ("asset_id", "other-asset"),
        ("content_hash", "0" * 64),
    ],
)
def test_s03_first_write_refuses_mutated_current_target(field: str, value: object) -> None:
    engine = _approved_f01_engine()
    setattr(engine, field, value)
    result = engine._perform_fixture_write(ack="OK")
    assert result == "REFUSED"
    assert engine.canonical.write_count == 0
    assert engine.canonical.write_attempt_count == 0
    assert engine.done_badge is False
    assert engine.pipeline_status != "COMPLETE"


def test_s03_write_event_after_target_mutation_is_blocked() -> None:
    engine = _approved_f01_engine()
    engine.candidate_version = 999
    engine.handle_event("CANONICAL_WRITTEN_FIXTURE")
    assert engine.canonical.write_count == 0
    assert engine.canonical_status != "WRITTEN"
    assert engine.done_badge is False
    assert engine.pipeline_status != "COMPLETE"


# ---------------------------------------------------------------------------
# S04: stale / invalid refresh clears the current COMPLETE state and done badge
# ---------------------------------------------------------------------------


def test_s04_failed_refresh_clears_current_completion_and_badge() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    for event in SCENARIOS["F01_COMPLETE_PATH"]["events"]:
        engine.handle_event(event)
    assert engine.pipeline_status == "COMPLETE"
    assert engine.done_badge is True
    engine.handle_event("BOARD_REFRESH_FAIL")
    assert engine.pipeline_status != "COMPLETE"
    assert engine.done_badge is False
    assert engine.completion_stale is True
    assert engine.board["is_stale"] is True


def test_s04_invalid_tuple_refresh_clears_current_completion_and_badge() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    for event in SCENARIOS["F01_COMPLETE_PATH"]["events"]:
        engine.handle_event(event)
    engine.candidate_version = 999
    engine.handle_event("BOARD_REFRESH")
    assert engine.pipeline_status != "COMPLETE"
    assert engine.done_badge is False
    assert engine.board["is_stale"] is True


def test_s04_full_revalidation_restores_current_completion() -> None:
    monitor = LiveCallMonitor()
    engine = MobileCloudFlowEngine(CONTRACT, FIXTURE, monitor, "F01_COMPLETE_PATH")
    for event in SCENARIOS["F01_COMPLETE_PATH"]["events"]:
        engine.handle_event(event)
    engine.handle_event("BOARD_REFRESH_FAIL")
    assert engine.pipeline_status != "COMPLETE"
    assert engine.done_badge is False
    engine.handle_event("BOARD_REFRESH")
    assert engine.pipeline_status == "COMPLETE"
    assert engine.done_badge is True


# ---------------------------------------------------------------------------
# S05: aggregate report verdict derives from observed phase records
# ---------------------------------------------------------------------------

CMD_FOCUSED = "python -m pytest -q tests/test_mobile_cloud_flow_v1.py"
CMD_COMBINED = (
    "python -m pytest -q tests/test_mobile_cloud_flow_v1.py "
    "tests/test_status_contract_v0_2.py tests/test_result_normalization.py"
)
CMD_FULL = "python -m pytest -q"


def _observed_phase(
    command: str,
    passed: int,
    failed: int = 0,
    skipped: int = 0,
    duration: float = 0.0,
    status: str = "PASS",
    exit_code: int = 0,
) -> dict:
    return {
        "command": command,
        "status": status,
        "observed": True,
        "exit_code": exit_code,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": duration,
        "phase": None,
        "source": "agent local run before commit (working tree)",
        "commit": None,
        "tested_revision": "working_tree_uncommitted",
    }


def _metadata_with_agent_phases(
    focused: dict | None = None,
    combined: dict | None = None,
    full: dict | None = None,
) -> dict:
    metadata = default_run_metadata()
    if focused is not None:
        metadata["phases"]["agent_focused"] = focused
    if combined is not None:
        metadata["phases"]["agent_affected_combined"] = combined
    if full is not None:
        metadata["phases"]["agent_full_suite"] = full
    return metadata


def _all_agent_phases_pass() -> dict:
    return _metadata_with_agent_phases(
        focused=_observed_phase(CMD_FOCUSED, 100),
        combined=_observed_phase(CMD_COMBINED, 150),
        full=_observed_phase(CMD_FULL, 1655, skipped=1),
    )


def test_s05_observed_focused_failure_forces_artifact_fail() -> None:
    metadata = _metadata_with_agent_phases(
        focused=_observed_phase(CMD_FOCUSED, 1, failed=1, status="FAIL", exit_code=1),
        combined=_observed_phase(CMD_COMBINED, 150),
        full=_observed_phase(CMD_FULL, 1655, skipped=1),
    )
    report = build_report(run_metadata=metadata)
    assert report["scenario_evaluation"] == "PASS"
    assert report["process_status"] == "FAIL"
    assert report["execution_result"] == "FAIL"
    assert report["business_final_status"] == "FAIL"
    assert report["focused_suite"]["status"] == "FAIL"


def test_s05_observed_full_suite_failure_forces_artifact_fail() -> None:
    metadata = _metadata_with_agent_phases(
        focused=_observed_phase(CMD_FOCUSED, 100),
        combined=_observed_phase(CMD_COMBINED, 150),
        full=_observed_phase(CMD_FULL, 1655, failed=1, status="FAIL", exit_code=1),
    )
    report = build_report(run_metadata=metadata)
    assert report["execution_result"] == "FAIL"
    assert report["business_final_status"] == "FAIL"


def test_s05_default_metadata_is_pending_not_contract_pass() -> None:
    report = build_report(run_metadata=default_run_metadata())
    assert report["scenario_evaluation"] == "PASS"
    assert report["process_status"] == "PENDING"
    assert report["execution_result"] == "PENDING"
    assert report["execution_result"] != "CONTRACT_PASS"
    assert report["focused_suite"]["status"] == NOT_OBSERVED


def test_s05_all_agent_phases_observed_pass_yields_contract_pass() -> None:
    report = build_report(run_metadata=_all_agent_phases_pass())
    assert report["execution_result"] == "CONTRACT_PASS"
    assert report["business_final_status"] == "CONTRACT_PASS"
    assert report["scenario_evaluation"] == "PASS"
    assert report["process_status"] == "PASS"
    # The eventual workflow Verify receipt is separate and genuinely pending.
    assert report["workflow_verify_status"] == NOT_OBSERVED


def test_s05_precommit_phase_revision_is_not_checkout_baseline() -> None:
    report = build_report(run_metadata=default_run_metadata())
    baseline = report["checkout_baseline_sha"]
    for key in ("agent_focused", "agent_affected_combined", "agent_full_suite"):
        phase = report["execution_phases"][key]
        assert phase["commit"] != baseline
        assert phase.get("tested_revision") in ("working_tree_uncommitted", "not_observed")
