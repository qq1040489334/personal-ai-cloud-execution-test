"""HERMES_REAL_RUNTIME_INTEGRATION_GOLDEN_V1.

Real Hermes runtime/gateway orchestration for the Personal AI Execution V2
contract.  This module is the *client* side of the boundary:

    GPT/Brain Task Contract  --HTTP JSON-RPC-->  Hermes A2A gateway
        --> real (non-Codex) executor  -->  structured result/evidence
        --> existing result normalization --> GPT review

Fixed responsibilities (not broadened here):

* GPT/Brain owns personal-context retrieval and planning.
* Hermes only orchestrates execution.
* Cloudflare remains canonical state.
* Executors are replaceable hands; Codex is **not** required.

Honesty rules enforced by this module:

* The runtime is only considered present when it is positively identified with
  concrete evidence (executable, configured endpoint, live A2A agent-card,
  container/config entry).  Adapter code alone is never evidence of a runtime.
* When no runtime is reachable this module does **not** simulate one.  It
  returns an explicit ``BLOCKED``/``PARTIAL`` business outcome naming the
  smallest missing dependency and the exact next action.
* A ``PASS`` golden outcome requires a real HTTP execution against a real
  gateway, a terminal task, and an identified non-Codex executor.  Tests,
  mocks and stubs can never produce ``PASS``.
* No credentials are printed.  Only the *source* (env-var name) of a credential
  is ever reported.
* No canonical write, no schema/binding mutation, no second state store.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from .result_normalization import (
    BLOCKED as EXEC_BLOCKED,
    FAIL as EXEC_FAIL,
    PASS as EXEC_PASS,
    normalize_result,
)

# --- Business outcomes (kept separate from workflow status) ------------------

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_BLOCKED = "BLOCKED"
STATUS_PARTIAL = "PARTIAL"

GOLDEN_PATH_PASS = "PASS"
GOLDEN_PATH_BLOCKED = "BLOCKED"
GOLDEN_PATH_PARTIAL = "PARTIAL"

# --- Runtime identification surface ------------------------------------------

#: Environment variables that configure a real Hermes gateway endpoint.
RUNTIME_ENDPOINT_ENV_VARS = (
    "HERMES_GATEWAY_URL",
    "HERMES_A2A_URL",
    "HERMES_A2A_ENDPOINT",
)

#: Environment variables whose *presence* indicates a gateway credential exists.
#: Values are never read or printed.
CREDENTIAL_ENV_VARS = (
    "HERMES_A2A_TOKEN",
    "A2A_BEARER_TOKEN",
    "HERMES_GATEWAY_TOKEN",
)

#: Executables that would positively identify a locally installed runtime.
RUNTIME_EXECUTABLES = ("hermes", "hermes-agent", "hermes-gateway")

#: Default A2A port served by the Hermes A2A platform plugin.
DEFAULT_A2A_BASE_URL = "http://127.0.0.1:9900"
AGENT_CARD_PATH = "/.well-known/agent-card.json"
LEGACY_AGENT_CARD_PATH = "/.well-known/agent.json"

DEFAULT_TIMEOUT_SECONDS = 2.0

#: Markers proving the executor is the forbidden Codex path.
CODEX_MARKERS = ("codex",)

#: A2A task states that terminate a task.
TERMINAL_TASK_STATES = frozenset(
    {
        "TASK_STATE_COMPLETED",
        "TASK_STATE_FAILED",
        "TASK_STATE_CANCELED",
        "TASK_STATE_REJECTED",
        "COMPLETED",
        "FAILED",
        "CANCELED",
        "REJECTED",
    }
)

COMPLETED_TASK_STATES = frozenset({"TASK_STATE_COMPLETED", "COMPLETED"})

REQUIRED_CONTRACT_FIELDS = (
    "task_id",
    "goal",
    "instructions",
    "risk_level",
    "expected_files",
    "acceptance",
)


def _now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --- Task Contract construction / validation --------------------------------


def build_task_contract(
    task_id: str,
    goal: str,
    instructions: list[str],
    acceptance: list[str],
    *,
    risk_level: str = "LOW",
    expected_files: list[str] | None = None,
) -> dict[str, Any]:
    """Build a GPT-style Task Contract for harmless deterministic execution."""
    return {
        "task_id": task_id,
        "goal": goal,
        "instructions": list(instructions),
        "risk_level": str(risk_level).upper(),
        "expected_files": list(expected_files or []),
        "acceptance": list(acceptance),
    }


def validate_task_contract(data: Any) -> list[str]:
    """Fail-closed validation mirroring ``scripts/task_contract.py``."""
    errors: list[str] = []
    if not isinstance(data, Mapping):
        return ["task contract is not a JSON object"]
    for field in REQUIRED_CONTRACT_FIELDS:
        if field not in data:
            errors.append(f"missing field: {field}")
    risk = str(data.get("risk_level", "")).upper()
    if risk not in {"LOW", "MEDIUM"}:
        errors.append(f"risk_level not acceptable: {risk}")
    files = data.get("expected_files")
    if not isinstance(files, list) or not files:
        errors.append("expected_files must be a non-empty list")
    else:
        for path in files:
            text = str(path).lower()
            if text.startswith(".github/workflows/") or any(
                token in text
                for token in ("secret", "token", "credential", ".env", ".pem", ".key")
            ):
                errors.append(f"forbidden expected_file: {path}")
            elif str(path).startswith(("/", "\\")) or ".." in str(path).split("/"):
                errors.append(f"unsafe expected_file path: {path}")
    for field in ("instructions", "acceptance"):
        value = data.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{field} must be a non-empty list")
    return errors


# --- Real runtime probing (read-only, no simulation) --------------------------


def _default_urlopen(url: str, timeout: float):
    return urllib.request.urlopen(url, timeout=timeout)  # noqa: S310 (fixed URLs)


def _credential_source(env: Mapping[str, str]) -> str | None:
    for name in CREDENTIAL_ENV_VARS:
        if str(env.get(name, "")).strip():
            return name
    return None


def _detect_containers() -> list[dict[str, str]]:
    """Best-effort, read-only detection of local Hermes containers."""
    found: list[dict[str, str]] = []
    for engine in ("docker", "podman"):
        if shutil.which(engine) is None:
            continue
        for args in (["ps", "--format", "{{.Names}} {{.Image}}"], ["images"]):
            try:
                proc = subprocess.run(
                    [engine, *args],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            for line in proc.stdout.splitlines():
                if "hermes" in line.lower():
                    found.append({"engine": engine, "entry": line.strip()})
    return found


def _probe_endpoint(
    base_url: str, urlopen: Callable[[str, float], Any]
) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch the A2A agent card. Returns ``(card, error)``."""
    last_error: str | None = None
    for path in (AGENT_CARD_PATH, LEGACY_AGENT_CARD_PATH):
        url = base_url.rstrip("/") + path
        try:
            response = urlopen(url, DEFAULT_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code} from {url}"
            continue
        except (urllib.error.URLError, OSError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            continue
        try:
            body = response.read()
            card = json.loads(body.decode("utf-8"))
        except (ValueError, AttributeError, OSError) as exc:
            last_error = f"unreadable agent card: {type(exc).__name__}: {exc}"
            continue
        if isinstance(card, Mapping):
            card = dict(card)
            card.setdefault("_source_url", url)
            return card, None
        last_error = f"agent card at {url} is not a JSON object"
    return None, last_error


def probe_hermes_runtime(
    env: Mapping[str, str] | None = None,
    *,
    which: Callable[[str], str | None] = shutil.which,
    urlopen: Callable[[str, float], Any] = _default_urlopen,
    container_lister: Callable[[], list[dict[str, str]]] = _detect_containers,
) -> dict[str, Any]:
    """Positively identify a real Hermes runtime, or report its absence."""
    env = os.environ if env is None else env
    evidence: list[dict[str, str]] = []
    checked: list[str] = []

    executables: dict[str, str] = {}
    for name in RUNTIME_EXECUTABLES:
        checked.append(f"executable:{name}")
        path = which(name)
        if path:
            executables[name] = path
            evidence.append({"class": "OBSERVED", "detail": f"executable {name} at {path}"})

    endpoint: str | None = None
    endpoint_source: str | None = None
    for name in RUNTIME_ENDPOINT_ENV_VARS:
        checked.append(f"env:{name}")
        value = str(env.get(name, "")).strip()
        if value:
            endpoint = value
            endpoint_source = name
            evidence.append(
                {"class": "OBSERVED", "detail": f"endpoint configured via {name}"}
            )
            break

    credential_source = _credential_source(env)
    if credential_source:
        evidence.append(
            {
                "class": "OBSERVED",
                "detail": f"credential present via {credential_source} (value not read)",
            }
        )

    containers = container_lister()
    if containers:
        for entry in containers:
            evidence.append(
                {
                    "class": "OBSERVED",
                    "detail": f"container {entry.get('engine')}: {entry.get('entry')}",
                }
            )

    agent_card: dict[str, Any] | None = None
    card_error: str | None = None
    probe_url = endpoint.rstrip("/") if endpoint else DEFAULT_A2A_BASE_URL
    checked.append(f"agent_card:{probe_url}{AGENT_CARD_PATH}")
    agent_card, card_error = _probe_endpoint(probe_url, urlopen)
    if agent_card is not None:
        evidence.append(
            {
                "class": "OBSERVED",
                "detail": f"A2A agent card served at {agent_card.get('_source_url')}",
            }
        )
    elif card_error:
        evidence.append(
            {"class": "OBSERVED", "detail": f"no A2A agent card: {card_error}"}
        )

    runtime_present = bool(agent_card) or bool(executables) or bool(containers)

    if runtime_present:
        missing_dependency = None
        next_action = None
        if not agent_card:
            next_action = (
                "runtime binary/container was seen but no A2A agent card answered; "
                "start the Hermes gateway with the A2A platform enabled and a "
                "reachable endpoint"
            )
    else:
        missing_dependency = "reachable_real_hermes_runtime"
        next_action = (
            "Provide/start a real Hermes gateway (A2A platform enabled, routable "
            "endpoint + bearer token) or point HERMES_A2A_URL at it; no runtime "
            "exists in this environment to integrate against"
        )

    return {
        "runtime_present": runtime_present,
        "runtime_kind": "hermes_a2a_gateway" if runtime_present else None,
        "endpoint": endpoint,
        "endpoint_source": endpoint_source,
        "executables": executables,
        "containers": containers,
        "agent_card": agent_card,
        "credential_source": credential_source,
        "checked": checked,
        "evidence": evidence,
        "missing_dependency": missing_dependency,
        "next_action": next_action,
        "probed_at": _now_utc(),
    }


# --- Hermes A2A JSON-RPC client ------------------------------------------------


def _extract_task_state(payload: Any) -> str | None:
    """Extract a normalized A2A task state from a response payload."""
    if not isinstance(payload, Mapping):
        return None
    for mapping in _walk(payload):
        container = mapping.get("status")
        if isinstance(container, Mapping):
            state = container.get("state")
            if isinstance(state, str) and state:
                return state.upper()
        elif isinstance(container, str) and container:
            return container.upper()
    return None


def _walk(value: Any):
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _extract_executor_identity(payload: Any) -> str | None:
    """Find an executor/agent identity inside a Hermes result, if declared."""
    keys = (
        "executor",
        "executor_id",
        "executor_identity",
        "executed_by",
        "agent",
        "agent_name",
        "model",
        "hands",
    )
    for mapping in _walk(payload):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_artifacts(payload: Any) -> list[Any]:
    artifacts: list[Any] = []
    for mapping in _walk(payload):
        value = mapping.get("artifacts")
        if isinstance(value, list):
            artifacts.extend(value)
    return artifacts


def _extract_task_id(payload: Any) -> str | None:
    for mapping in _walk(payload):
        for key in ("taskId", "task_id"):
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for mapping in _walk(payload):
        if "jsonrpc" in mapping:
            continue
        value = mapping.get("id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _is_codex(identity: str | None) -> bool:
    if not identity:
        return False
    lowered = identity.lower()
    return any(marker in lowered for marker in CODEX_MARKERS)


class HermesOrchestrationAdapter:
    """Wire a Task Contract to a *real* Hermes A2A gateway.

    The adapter performs real HTTP JSON-RPC calls only.  It accepts an already
    computed ``probe_result`` so callers can share one runtime audit, and an
    optional ``transport`` seam used by transport-contract unit tests.  The
    transport seam is never used to claim a golden PASS: a PASS additionally
    requires ``probe_result["runtime_present"]`` and an actual observed
    non-Codex executor identity.
    """

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        token: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 1.0,
        probe_result: Mapping[str, Any] | None = None,
        transport: Callable[[str, Mapping[str, Any], Mapping[str, str], float], Any]
        | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._token = token
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._probe_result = probe_result
        self._transport = transport

    # -- transport ---------------------------------------------------------

    def _resolve_endpoint(self, probe: Mapping[str, Any]) -> str | None:
        if self._endpoint:
            return self._endpoint
        endpoint = probe.get("endpoint")
        if isinstance(endpoint, str) and endpoint:
            return endpoint
        card = probe.get("agent_card")
        if isinstance(card, Mapping) and isinstance(card.get("url"), str):
            return card["url"]
        if probe.get("runtime_present"):
            return DEFAULT_A2A_BASE_URL
        return None

    def _headers(self, probe: Mapping[str, Any]) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "A2A-Version": "1.0"}
        token_value = self._token
        if not token_value:
            source = probe.get("credential_source")
            if source:
                token_value = os.environ.get(str(source), "")
        if token_value:
            headers["Authorization"] = f"Bearer {token_value}"
        return headers

    def _post(self, url: str, body: Mapping[str, Any], headers: Mapping[str, str]) -> Any:
        if self._transport is not None:
            return self._transport(url, body, headers, self._timeout)
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=dict(headers), method="POST")
        with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))

    # -- execution ---------------------------------------------------------

    def execute(self, contract: Mapping[str, Any]) -> dict[str, Any]:
        started = _now_utc()
        probe = self._probe_result or probe_hermes_runtime()
        result: dict[str, Any] = {
            "ok": False,
            "status": STATUS_BLOCKED,
            "started_at": started,
            "finished_at": None,
            "endpoint": None,
            "request_id": None,
            "hermes_task_id": None,
            "executor_identity": None,
            "codex_required": False,
            "runtime_evidence": list(probe.get("evidence", [])),
            "artifacts": [],
            "raw": None,
            "error": None,
        }

        if not probe.get("runtime_present"):
            result["error"] = (
                "no real Hermes runtime present; refusing to simulate execution"
            )
            result["finished_at"] = _now_utc()
            result["error_class"] = "runtime_unavailable"
            return result

        endpoint = self._resolve_endpoint(probe)
        result["endpoint"] = endpoint
        if not endpoint:
            result["error"] = "runtime present but no A2A endpoint resolved"
            result["error_class"] = "endpoint_unresolved"
            result["finished_at"] = _now_utc()
            return result

        request_id = f"req-{uuid.uuid4().hex[:12]}"
        context_id = f"ctx-{uuid.uuid4().hex[:12]}"
        result["request_id"] = request_id
        result["context_id"] = context_id
        message = {
            "role": "user",
            "messageId": f"msg-{uuid.uuid4().hex[:12]}",
            "contextId": context_id,
            "parts": [
                {"kind": "text", "text": json.dumps(contract, ensure_ascii=False)}
            ],
        }
        rpc = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "SendMessage",
            "params": {"message": message},
        }

        try:
            payload = self._post(endpoint, rpc, self._headers(probe))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            result["error_class"] = "transport_error"
            result["finished_at"] = _now_utc()
            return result

        result["raw"] = payload
        if isinstance(payload, Mapping) and payload.get("error"):
            result["error"] = json.dumps(payload.get("error"))
            result["error_class"] = "jsonrpc_error"
            result["finished_at"] = _now_utc()
            return result

        task = payload.get("result") if isinstance(payload, Mapping) else payload
        state = _extract_task_state(task)
        if state in TERMINAL_TASK_STATES:
            self._fill_success(result, task, state)
            return result

        task_id = _extract_task_id(task)
        result["hermes_task_id"] = task_id
        if not task_id:
            result["error"] = "non-terminal response without a task id"
            result["error_class"] = "task_id_missing"
            result["finished_at"] = _now_utc()
            return result

        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            time.sleep(min(self._poll_interval, max(0.0, deadline - time.monotonic())))
            get_rpc = {
                "jsonrpc": "2.0",
                "id": f"{request_id}-get",
                "method": "GetTask",
                "params": {"id": task_id, "taskId": task_id},
            }
            try:
                polled = self._post(endpoint, get_rpc, self._headers(probe))
            except (urllib.error.URLError, OSError, ValueError) as exc:
                result["error"] = f"{type(exc).__name__}: {exc}"
                result["error_class"] = "poll_error"
                result["finished_at"] = _now_utc()
                return result
            result["raw"] = polled
            polled_task = polled.get("result") if isinstance(polled, Mapping) else polled
            state = _extract_task_state(polled_task)
            if state in TERMINAL_TASK_STATES:
                self._fill_success(result, polled_task, state)
                return result

        result["error"] = f"task {task_id} did not reach a terminal state in time"
        result["error_class"] = "timeout"
        result["finished_at"] = _now_utc()
        return result

    def _fill_success(
        self, result: dict[str, Any], task: Any, state: str | None
    ) -> None:
        artifacts = _extract_artifacts(task)
        executor = _extract_executor_identity(task)
        result["hermes_task_id"] = _extract_task_id(task) or result.get("hermes_task_id")
        result["executor_identity"] = executor
        result["artifacts"] = artifacts
        result["task_state"] = state
        result["finished_at"] = _now_utc()
        if state in COMPLETED_TASK_STATES and not _is_codex(executor):
            result["ok"] = True
            result["status"] = STATUS_PASS
        elif state in COMPLETED_TASK_STATES and _is_codex(executor):
            result["ok"] = False
            result["status"] = STATUS_FAIL
            result["error"] = "golden path must not use a Codex executor"
            result["error_class"] = "codex_executor_rejected"
        else:
            result["ok"] = False
            result["status"] = STATUS_PARTIAL
            result["error"] = f"terminal state {state} is not completion"
            result["error_class"] = "non_completion"


# --- Normalization toward GPT review ------------------------------------------


def normalize_hermes_evidence(
    contract: Mapping[str, Any],
    probe: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble a GPT-review-bound, normalized evidence packet.

    ``final_status`` is the business outcome.  ``workflow_status`` is the
    workflow-run status and is deliberately kept separate.
    """
    runtime_present = bool(probe.get("runtime_present"))
    executor = execution.get("executor_identity")
    codex = _is_codex(executor)

    if not runtime_present:
        final_status = STATUS_BLOCKED
        golden_path = GOLDEN_PATH_BLOCKED
        evidence_kind = "runtime_absent_audit"
    elif execution.get("ok") and executor and not codex:
        final_status = STATUS_PASS
        golden_path = GOLDEN_PATH_PASS
        evidence_kind = "real_runtime"
    else:
        final_status = STATUS_PARTIAL
        golden_path = GOLDEN_PATH_PARTIAL
        evidence_kind = "real_runtime" if runtime_present else "runtime_absent_audit"

    evidence = list(probe.get("evidence", []))
    evidence.append(
        {
            "class": "OBSERVED" if runtime_present else "OBSERVED",
            "detail": f"execution.status={execution.get('status')} "
            f"executor={executor or 'unknown'}",
        }
    )

    return {
        "task_id": contract.get("task_id", ""),
        "goal": contract.get("goal", ""),
        "final_status": final_status,
        "golden_path": golden_path,
        "evidence_kind": evidence_kind,
        "runtime_present": runtime_present,
        "runtime_kind": probe.get("runtime_kind"),
        "runtime_evidence": evidence,
        "credential_source": probe.get("credential_source"),
        "endpoint": execution.get("endpoint"),
        "request_id": execution.get("request_id"),
        "hermes_task_id": execution.get("hermes_task_id"),
        "context_id": execution.get("context_id"),
        "executor_identity": executor,
        "codex_required": False,
        "task_state": execution.get("task_state"),
        "artifacts": execution.get("artifacts", []),
        "started_at": execution.get("started_at"),
        "finished_at": execution.get("finished_at"),
        "error": execution.get("error"),
        "error_class": execution.get("error_class"),
        "missing_dependency": probe.get("missing_dependency"),
        "next_action": probe.get("next_action"),
        "canonical_write_performed": False,
        "second_state_store_created": False,
        "schema_or_binding_mutated": False,
        "used_mock_or_stub": False,
        "workflow_status": "not_applicable_agent_local",
    }


def run_hermes_golden_poc(
    contract: Mapping[str, Any],
    *,
    adapter: HermesOrchestrationAdapter | None = None,
    probe: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the honest Golden POC: probe -> real execute -> normalize.

    With no reachable runtime this returns a ``BLOCKED`` business outcome and
    never fabricates a PASS.
    """
    resolved_probe = probe if probe is not None else probe_hermes_runtime()
    resolved_adapter = adapter or HermesOrchestrationAdapter(probe_result=resolved_probe)
    execution = resolved_adapter.execute(contract)
    return normalize_hermes_evidence(contract, resolved_probe, execution)


def normalize_to_execution_v2(
    packet: Mapping[str, Any],
    *,
    workflow_conclusion_value: str | None = None,
    artifact_present: bool = False,
    commit_present: bool = False,
) -> dict[str, Any]:
    """Bridge the Hermes packet into the existing Execution V2 normalization.

    A ``PASS`` golden outcome is downgraded by the existing guard (which maps
    the advisory self-report through the fail-closed workflow conclusion).
    """
    final = str(packet.get("final_status", "")).upper()
    self_status = {
        STATUS_PASS: EXEC_PASS,
        STATUS_FAIL: EXEC_FAIL,
        STATUS_BLOCKED: EXEC_BLOCKED,
        STATUS_PARTIAL: EXEC_FAIL,
    }.get(final, EXEC_BLOCKED)
    execution_result = {
        "task_id": packet.get("task_id", ""),
        "status": self_status,
        "tests": "",
        "expected_files": packet.get("expected_files", []),
        "changed_files": packet.get("changed_files", []),
    }
    return normalize_result(
        execution_result,
        workflow_conclusion_value,
        artifact_present=artifact_present,
        commit_present=commit_present,
    )


# =============================================================================
# WINDOWS_HERMES_TRANSPORT_CONTRACT_V1
# =============================================================================
#
# The real Hermes runtime already lives on the user's Windows machine.  It must
# never be publicly exposed and no second Hermes is deployed in the cloud.  The
# only new boundary is an *outbound* Windows worker that polls the existing
# Personal AI cloud surface, claims one task under a lease, acknowledges it, and
# returns a normalized result.
#
# This section defines the cloud-side contract only: envelope builders,
# fail-closed validators, a pure claim/lease/ack/result state machine, and an
# explicit audit of the existing Execution V2 surfaces.  It creates **no**
# canonical store, performs **no** canonical write, and deploys **no** relay.
# The one genuinely missing production capability (an authenticated,
# atomic claim/lease/ack relay endpoint that can accept a Windows transport
# result as authoritative terminal evidence) is reported as an exact minimal gap
# requiring a later Human Gate.
#
# Responsibility split is unchanged:
#   * GPT/Brain plans and owns personal context.
#   * Windows Hermes only orchestrates (outbound).
#   * Cloudflare Canonical remains personal state.

TRANSPORT_CONTRACT_VERSION = "WINDOWS_HERMES_TRANSPORT_CONTRACT_V1"
TRANSPORT_RELAY_ID = "personal-ai-hermes-relay"

#: Base path of the minimal relay endpoint. This endpoint is *specified* here
#: but deliberately not deployed by this module.
TRANSPORT_RELAY_BASE_PATH = "/hermes/transport/v1"
TRANSPORT_HEALTH_PATH = TRANSPORT_RELAY_BASE_PATH + "/health"
TRANSPORT_CLAIM_PATH = TRANSPORT_RELAY_BASE_PATH + "/tasks/claim"
TRANSPORT_ACK_PATH = TRANSPORT_RELAY_BASE_PATH + "/tasks/{task_id}/ack"
TRANSPORT_RESULT_PATH = TRANSPORT_RELAY_BASE_PATH + "/tasks/{task_id}/result"

TRANSPORT_REQUIRED_ENDPOINTS = (
    TRANSPORT_HEALTH_PATH,
    TRANSPORT_CLAIM_PATH,
    TRANSPORT_ACK_PATH,
    TRANSPORT_RESULT_PATH,
)

#: Credential *source* (environment variable name) for the Windows transport
#: bearer token. Only the name is ever reported; the value is never read here.
TRANSPORT_CREDENTIAL_ENV_VARS = ("HERMES_TRANSPORT_TOKEN", "HERMES_GATEWAY_TOKEN")
#: Optional environment variable naming the relay base URL (never a secret).
TRANSPORT_ENDPOINT_ENV_VARS = (
    "HERMES_TRANSPORT_URL",
    "HERMES_GATEWAY_URL",
)
TRANSPORT_AUTH_SCHEME = "bearer"
TRANSPORT_REQUIRED_SCOPE = "hermes.transport"

#: Windows always initiates; the cloud never dials the Windows machine.
TRANSPORT_DIRECTION = "windows_outbound_poll"

DEFAULT_LEASE_SECONDS = 15 * 60
DEFAULT_POLL_INTERVAL_SECONDS = 5
MAX_TRANSPORT_ATTEMPTS = 5

#: Cloud-side claim decisions.
CLAIM_STATE_CLAIMED = "CLAIMED"
CLAIM_STATE_IDEMPOTENT = "IDEMPOTENT"
CLAIM_STATE_LEASED_ELSEWHERE = "LEASED_ELSEWHERE"
CLAIM_STATE_NOT_CLAIMABLE = "NOT_CLAIMABLE"

#: Acknowledgement decisions.
ACK_STATE_ACKNOWLEDGED = "ACKNOWLEDGED"
ACK_STATE_IDEMPOTENT = "IDEMPOTENT"
ACK_STATE_LEASE_MISMATCH = "LEASE_MISMATCH"

#: Result-return decisions.
RESULT_STATE_ACCEPTED = "ACCEPTED"
RESULT_STATE_DUPLICATE = "DUPLICATE"
RESULT_STATE_REJECTED = "REJECTED"
RESULT_STATE_LEASE_MISMATCH = "LEASE_MISMATCH"

#: Stable result fields hashed to form the evidence hash. Volatile transport
#: metadata (timestamps other than the terminal ``finished_at``, retries, HTTP
#: headers) is deliberately excluded so retransmission is idempotent.
EVIDENCE_HASH_FIELDS = (
    "task_id",
    "task_state",
    "executor_identity",
    "status",
    "tests",
    "artifacts",
    "expected_files",
    "changed_files",
    "finished_at",
)

TRANSPORT_HEALTH_REQUIRED_FIELDS = ("worker_id", "contract_version")
TRANSPORT_CLAIM_REQUIRED_FIELDS = ("worker_id", "contract_version")
TRANSPORT_ACK_REQUIRED_FIELDS = ("task_id", "worker_id", "lease_id")
TRANSPORT_RESULT_REQUIRED_FIELDS = (
    "task_id",
    "worker_id",
    "lease_id",
    "contract_version",
    "status",
    "task_state",
    "evidence_hash",
)

#: Executor states that may be returned through the transport.
_NON_TERMINAL_REJECTION_STATES = frozenset({"TASK_STATE_WORKING", "WORKING", "SUBMITTED"})

#: The exact minimal production capability that does not yet exist. This is
#: reported, never silently deployed.
MINIMAL_RELAY_GAP = {
    "capability": "authenticated_outbound_task_relay",
    "human_gate_required": True,
    "production_deployed": False,
    "why_existing_surface_insufficient": (
        "Execution V2 already registers tasks and publishes GitHub-Actions-derived "
        "terminal results (EventSyncRegistry.sync_terminal_result requires a workflow "
        "conclusion) and exposes inbound MCP read tools (list_pending_results, "
        "get_task_result). It has no atomic, authenticated claim/lease/ack endpoint "
        "for an outbound Windows worker and no path to accept a Windows transport "
        "result as authoritative terminal evidence."
    ),
    "required_endpoints": list(TRANSPORT_REQUIRED_ENDPOINTS),
    "required_auth": {
        "scheme": TRANSPORT_AUTH_SCHEME,
        "scope": TRANSPORT_REQUIRED_SCOPE,
        "credential_source_type": "environment_variable_name_only",
        "credential_env_vars": list(TRANSPORT_CREDENTIAL_ENV_VARS),
    },
    "required_lease": {
        "default_lease_seconds": DEFAULT_LEASE_SECONDS,
        "max_attempts": MAX_TRANSPORT_ATTEMPTS,
        "ownership_field": "transport_owner_worker_id",
    },
    "do_not_deploy": True,
}


def _parse_transport_timestamp(value: Any):
    """Parse an ISO-8601 timestamp, assuming UTC when no offset is supplied."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _transport_now(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current


# --- idempotency + evidence hash ---------------------------------------------


def claim_idempotency_key(task_id: str, worker_id: str) -> str:
    """Deterministic key so a repeated claim converges on one lease."""
    return f"hermes-claim:{task_id}:{worker_id}"


def ack_idempotency_key(task_id: str, lease_id: str) -> str:
    """Deterministic key so a repeated acknowledgement is a no-op."""
    return f"hermes-ack:{task_id}:{lease_id}"


def result_idempotency_key(task_id: str, evidence_hash: str) -> str:
    """Deterministic key so a retransmitted result is deduplicated."""
    return f"hermes-result:{task_id}:{evidence_hash}"


def compute_evidence_hash(payload: Mapping[str, Any] | None) -> str:
    """Return a stable ``sha256:`` hash over the stable result fields.

    Only :data:`EVIDENCE_HASH_FIELDS` are hashed, so adding transport metadata
    to a retransmitted result cannot change its evidence hash.
    """
    material: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        for field in EVIDENCE_HASH_FIELDS:
            if field in payload:
                material[field] = payload[field]
    blob = json.dumps(
        material, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --- health / readiness handshake --------------------------------------------


def build_health_handshake(
    worker_id: str,
    *,
    capabilities: list[str] | None = None,
    runtime_evidence: list[dict[str, Any]] | None = None,
    contract_version: str = TRANSPORT_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Build the outbound health/readiness handshake a Windows worker sends."""
    return {
        "worker_id": str(worker_id),
        "contract_version": contract_version,
        "direction": TRANSPORT_DIRECTION,
        "capabilities": list(capabilities or ["hermes.orchestrate"]),
        "runtime_evidence": list(runtime_evidence or []),
        "sent_at": _now_utc(),
    }


def validate_health_handshake(handshake: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(handshake, Mapping):
        return ["handshake is not a JSON object"]
    for field in TRANSPORT_HEALTH_REQUIRED_FIELDS:
        if not str(handshake.get(field) or "").strip():
            errors.append(f"missing field: {field}")
    version = str(handshake.get("contract_version") or "")
    if version and version != TRANSPORT_CONTRACT_VERSION:
        errors.append(
            f"contract_version mismatch: {version} != {TRANSPORT_CONTRACT_VERSION}"
        )
    return errors


def evaluate_health_handshake(
    handshake: Any, *, env: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Cloud-side readiness response. Never returns a credential value."""
    environ = os.environ if env is None else env
    errors = validate_health_handshake(handshake)
    if errors:
        return {
            "ready": False,
            "worker_id": (
                str(handshake.get("worker_id")) if isinstance(handshake, Mapping) else None
            ),
            "relay_contract_version": TRANSPORT_CONTRACT_VERSION,
            "errors": errors,
            "ready_at": _now_utc(),
        }
    endpoint_base = None
    endpoint_source = None
    for name in TRANSPORT_ENDPOINT_ENV_VARS:
        value = str(environ.get(name, "")).strip()
        if value:
            endpoint_base = value
            endpoint_source = name
            break
    return {
        "ready": True,
        "worker_id": str(handshake.get("worker_id")),
        "relay_contract_version": TRANSPORT_CONTRACT_VERSION,
        "relay_id": TRANSPORT_RELAY_ID,
        "direction": TRANSPORT_DIRECTION,
        "endpoints": {
            "health": TRANSPORT_HEALTH_PATH,
            "claim": TRANSPORT_CLAIM_PATH,
            "ack": TRANSPORT_ACK_PATH,
            "result": TRANSPORT_RESULT_PATH,
        },
        "endpoint_base": endpoint_base,
        "endpoint_source": endpoint_source,
        "auth": {
            "scheme": TRANSPORT_AUTH_SCHEME,
            "scope": TRANSPORT_REQUIRED_SCOPE,
            "credential_source": _first_present(environ, TRANSPORT_CREDENTIAL_ENV_VARS),
        },
        "poll_interval_seconds": DEFAULT_POLL_INTERVAL_SECONDS,
        "task_contract_fields": list(REQUIRED_CONTRACT_FIELDS),
        "result_contract_fields": list(TRANSPORT_RESULT_REQUIRED_FIELDS),
        "ready_at": _now_utc(),
    }


def _first_present(env: Mapping[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        if str(env.get(name, "")).strip():
            return name
    return None


# --- claim / lease -----------------------------------------------------------


def is_transport_claimable(
    record: Mapping[str, Any],
    *,
    worker_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fail-closed claimability assessment for one existing registry record.

    This reads an existing Execution V2 task record; it never creates a second
    store. A terminal/reviewed task is never claimable, and a live lease owned by
    another worker is held.
    """
    current = _transport_now(now)
    task_id = str(record.get("task_id") or "")
    if not task_id:
        return {"claimable": False, "reason_code": "TASK_ID_MISSING", "reason": "no task_id"}
    if record.get("reviewed") or record.get("terminal") or record.get("result_available"):
        return {
            "claimable": False,
            "reason_code": "TASK_TERMINAL",
            "reason": "task already has an authoritative terminal result",
        }
    expiry = _parse_transport_timestamp(record.get("transport_lease_expires_at"))
    owner = str(record.get("transport_owner_worker_id") or "")
    if expiry is not None and current <= expiry and owner:
        if owner == str(worker_id):
            return {
                "claimable": True,
                "idempotent": True,
                "reason_code": "LEASE_OWNED",
                "reason": "active lease already owned by this worker",
            }
        return {
            "claimable": False,
            "reason_code": "LEASE_HELD",
            "reason": f"active lease held by {owner}",
        }
    return {"claimable": True, "idempotent": False, "reason_code": "CLAIMABLE", "reason": "no active lease"}


def claim_task(
    record: Mapping[str, Any],
    worker_id: str,
    *,
    now: datetime | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    """Return an idempotent claim/lease decision for one task record.

    Pure: it computes the next lease and the registry patch a relay would apply,
    but performs no write. A reclaim after expiry increments the bounded attempt.
    """
    current = _transport_now(now)
    task_id = str(record.get("task_id") or "")
    assessment = is_transport_claimable(record, worker_id=worker_id, now=current)
    base: dict[str, Any] = {
        "task_id": task_id,
        "worker_id": str(worker_id),
        "idempotency_key": claim_idempotency_key(task_id, str(worker_id)),
        "claimed": False,
        "state": CLAIM_STATE_NOT_CLAIMABLE,
        "lease_id": None,
        "owner_worker_id": None,
        "lease_expires_at": None,
        "attempt": None,
        "reason_code": assessment["reason_code"],
        "reason": assessment["reason"],
        "registry_patch": None,
    }
    if not assessment["claimable"]:
        if assessment["reason_code"] == "LEASE_HELD":
            base["state"] = CLAIM_STATE_LEASED_ELSEWHERE
        return base

    try:
        previous_attempt = max(0, int(record.get("transport_attempt") or 0))
    except (TypeError, ValueError):
        previous_attempt = 0

    if assessment.get("idempotent"):
        attempt = max(1, previous_attempt)
        lease_id = str(record.get("transport_lease_id") or "")
        expiry = _parse_transport_timestamp(record.get("transport_lease_expires_at"))
        base.update(
            {
                "claimed": True,
                "state": CLAIM_STATE_IDEMPOTENT,
                "lease_id": lease_id,
                "owner_worker_id": str(worker_id),
                "lease_expires_at": expiry.isoformat() if expiry else None,
                "attempt": attempt,
            }
        )
        return base

    attempt = previous_attempt + 1
    lease_id = f"lease:{task_id}:{attempt}:{worker_id}"
    expiry = current + timedelta(seconds=max(1, int(lease_seconds)))
    base.update(
        {
            "claimed": True,
            "state": CLAIM_STATE_CLAIMED,
            "lease_id": lease_id,
            "owner_worker_id": str(worker_id),
            "lease_expires_at": expiry.isoformat(),
            "attempt": attempt,
            "registry_patch": {
                "transport_lease_id": lease_id,
                "transport_owner_worker_id": str(worker_id),
                "transport_lease_expires_at": expiry.isoformat(),
                "transport_attempt": attempt,
                "transport_claimed_at": current.isoformat(),
            },
        }
    )
    return base


def build_task_assignment(contract: Mapping[str, Any], claim: Mapping[str, Any]) -> dict[str, Any]:
    """Build the assignment payload the relay returns to a claiming worker."""
    return {
        "contract_version": TRANSPORT_CONTRACT_VERSION,
        "task_contract": dict(contract),
        "lease_id": claim.get("lease_id"),
        "owner_worker_id": claim.get("owner_worker_id"),
        "lease_expires_at": claim.get("lease_expires_at"),
        "attempt": claim.get("attempt"),
        "claim_idempotency_key": claim.get("idempotency_key"),
    }


def acknowledge_task(
    record: Mapping[str, Any],
    *,
    task_id: str,
    worker_id: str,
    lease_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate/record an acknowledgement for a held lease. Pure decision."""
    current = _transport_now(now)
    if (
        str(record.get("task_id") or "") != str(task_id)
        or str(record.get("transport_lease_id") or "") != str(lease_id)
        or str(record.get("transport_owner_worker_id") or "") != str(worker_id)
    ):
        return {
            "task_id": str(task_id),
            "state": ACK_STATE_LEASE_MISMATCH,
            "acknowledged": False,
            "idempotent": False,
            "reason": "lease/task/worker does not match the active transport lease",
        }
    if record.get("transport_acked_at"):
        return {
            "task_id": str(task_id),
            "state": ACK_STATE_IDEMPOTENT,
            "acknowledged": True,
            "idempotent": True,
            "acked_at": record.get("transport_acked_at"),
            "idempotency_key": ack_idempotency_key(task_id, lease_id),
            "registry_patch": None,
        }
    return {
        "task_id": str(task_id),
        "state": ACK_STATE_ACKNOWLEDGED,
        "acknowledged": True,
        "idempotent": False,
        "acked_at": current.isoformat(),
        "idempotency_key": ack_idempotency_key(task_id, lease_id),
        "registry_patch": {"transport_acked_at": current.isoformat()},
    }


# --- result return -----------------------------------------------------------


def validate_result_envelope(envelope: Any) -> list[str]:
    """Fail-closed validation of a Windows transport result envelope."""
    errors: list[str] = []
    if not isinstance(envelope, Mapping):
        return ["result envelope is not a JSON object"]
    for field in TRANSPORT_RESULT_REQUIRED_FIELDS:
        if not str(envelope.get(field) or "").strip():
            errors.append(f"missing field: {field}")
    version = str(envelope.get("contract_version") or "")
    if version and version != TRANSPORT_CONTRACT_VERSION:
        errors.append(
            f"contract_version mismatch: {version} != {TRANSPORT_CONTRACT_VERSION}"
        )
    task_state = str(envelope.get("task_state") or "").upper()
    if task_state and task_state in _NON_TERMINAL_REJECTION_STATES:
        errors.append(f"task_state is not terminal: {task_state}")
    elif task_state and task_state not in TERMINAL_TASK_STATES:
        errors.append(f"unknown terminal task_state: {task_state}")
    return errors


def _execution_status_for_transport(
    task_state: str | None, executor_identity: str | None
) -> str:
    state = str(task_state or "").upper()
    if state in COMPLETED_TASK_STATES:
        return STATUS_FAIL if _is_codex(executor_identity) else STATUS_PASS
    if state in {"TASK_STATE_FAILED", "FAILED", "TASK_STATE_REJECTED", "REJECTED"}:
        return STATUS_FAIL
    if state in {"TASK_STATE_CANCELED", "CANCELED"}:
        return STATUS_BLOCKED
    return STATUS_PARTIAL


def normalize_transport_result(
    record: Mapping[str, Any],
    envelope: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Normalize one Windows transport result, idempotently and fail-closed.

    The decision is pure; the returned ``registry_patch`` is the additive record
    update a relay would apply to the *existing* task record. No second store is
    created and no canonical write is performed here.
    """
    current = _transport_now(now)
    task_id = str(envelope.get("task_id") or "")
    errors = validate_result_envelope(envelope)

    def rejected(reason_code: str, reason: str) -> dict[str, Any]:
        return {
            "task_id": task_id,
            "state": RESULT_STATE_REJECTED,
            "accepted": False,
            "duplicate": False,
            "idempotent": False,
            "reason_code": reason_code,
            "reason": reason,
            "errors": errors,
            "normalized_status": None,
            "execution_result": None,
            "event_sync_accepts": False,
            "registry_patch": None,
            "canonical_write_performed": False,
        }

    if errors:
        return rejected("INVALID_RESULT", "result envelope failed validation")

    expected_hash = compute_evidence_hash(envelope)
    declared_hash = str(envelope.get("evidence_hash") or "")
    if declared_hash != expected_hash:
        return rejected(
            "EVIDENCE_HASH_MISMATCH",
            "declared evidence_hash does not match the stable result fields",
        )

    if (
        str(record.get("task_id") or "") != task_id
        or str(record.get("transport_lease_id") or "") != str(envelope.get("lease_id") or "")
        or str(record.get("transport_owner_worker_id") or "") != str(envelope.get("worker_id") or "")
    ):
        return {
            "task_id": task_id,
            "state": RESULT_STATE_LEASE_MISMATCH,
            "accepted": False,
            "duplicate": False,
            "idempotent": False,
            "reason_code": "LEASE_MISMATCH",
            "reason": "result lease/worker does not match the active transport lease",
            "errors": [],
            "normalized_status": None,
            "execution_result": None,
            "event_sync_accepts": False,
            "registry_patch": None,
            "canonical_write_performed": False,
        }

    existing_hash = str(record.get("transport_result_evidence_hash") or "")
    if existing_hash:
        if existing_hash == declared_hash:
            return {
                "task_id": task_id,
                "state": RESULT_STATE_DUPLICATE,
                "accepted": True,
                "duplicate": True,
                "idempotent": True,
                "reason_code": "DUPLICATE_RESULT",
                "reason": "identical result already recorded; retransmission ignored",
                "errors": [],
                "normalized_status": record.get("transport_result_status"),
                "execution_result": record.get("execution_result_json"),
                "evidence_hash": declared_hash,
                "idempotency_key": result_idempotency_key(task_id, declared_hash),
                "event_sync_accepts": False,
                "registry_patch": None,
                "canonical_write_performed": False,
            }
        return rejected(
            "CONFLICTING_DUPLICATE_RESULT",
            "a different result is already recorded for this task/lease",
        )

    normalized_status = _execution_status_for_transport(
        envelope.get("task_state"), envelope.get("executor_identity")
    )
    execution_result = {
        "task_id": task_id,
        "status": normalized_status,
        "tests": envelope.get("tests", ""),
        "expected_files": list(envelope.get("expected_files") or []),
        "changed_files": list(envelope.get("changed_files") or []),
        "summary": envelope.get("summary", ""),
    }
    # The Windows transport cannot supply a GitHub Actions workflow conclusion.
    # Existing EVENT_SYNC refuses a result with no conclusion, so this is exactly
    # the minimal relay capability that must be gated rather than faked.
    event_sync_accepts = bool(
        str(envelope.get("workflow_conclusion") or "").strip()
    )
    return {
        "task_id": task_id,
        "state": RESULT_STATE_ACCEPTED,
        "accepted": True,
        "duplicate": False,
        "idempotent": False,
        "reason_code": "ACCEPTED",
        "reason": "terminal Windows transport result validated and normalized",
        "errors": [],
        "normalized_status": normalized_status,
        "executor_identity": envelope.get("executor_identity"),
        "evidence_hash": declared_hash,
        "idempotency_key": result_idempotency_key(task_id, declared_hash),
        "execution_result": execution_result,
        "event_sync_accepts": event_sync_accepts,
        "event_sync_reason": (
            "existing EVENT_SYNC requires a workflow conclusion; a Windows "
            "transport result carries none, so publication is a minimal relay "
            "capability requiring a Human Gate"
        ),
        "registry_patch": {
            "transport_result_evidence_hash": declared_hash,
            "transport_result_status": normalized_status,
            "transport_result_returned_at": current.isoformat(),
            "execution_result_json": execution_result,
        },
        "canonical_write_performed": False,
    }


def plan_result_publication(
    record: Mapping[str, Any],
    envelope: Mapping[str, Any],
    *,
    registry: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Combine normalization with the existing registry to expose the gap.

    Reuses ``EventSyncRegistry.sync_terminal_result`` (if a registry is supplied)
    to demonstrate that the existing surface does not accept a Windows transport
    result that lacks a workflow conclusion -- reporting the exact minimal relay
    gap rather than silently deploying a new authority path.
    """
    decision = dict(normalize_transport_result(record, envelope, now=now))
    registry_report = None
    if registry is not None and hasattr(registry, "sync_terminal_result"):
        try:
            registry_report = registry.sync_terminal_result(
                str(envelope.get("task_id") or ""),
                decision.get("execution_result"),
                None,
            )
        except (KeyError, ValueError, TypeError) as exc:  # pragma: no cover - defensive
            registry_report = {"synced": False, "error": f"{type(exc).__name__}: {exc}"}
    if registry_report is not None:
        decision["event_sync_accepts"] = bool(registry_report.get("synced"))
        if not registry_report.get("synced"):
            decision["event_sync_reason"] = registry_report.get("reason")
    decision["minimal_gap"] = dict(MINIMAL_RELAY_GAP) if not decision.get(
        "event_sync_accepts"
    ) else None
    return decision


# --- integration inputs & audit ----------------------------------------------


def windows_hermes_integration_inputs(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Exact inputs the Windows local agent needs. Secret values are never read."""
    environ = os.environ if env is None else env
    endpoint_base = None
    endpoint_source = None
    for name in TRANSPORT_ENDPOINT_ENV_VARS:
        value = str(environ.get(name, "")).strip()
        if value:
            endpoint_base = value
            endpoint_source = name
            break
    return {
        "contract_version": TRANSPORT_CONTRACT_VERSION,
        "direction": TRANSPORT_DIRECTION,
        "endpoint_shape": {
            "base_path": TRANSPORT_RELAY_BASE_PATH,
            "health": TRANSPORT_HEALTH_PATH,
            "claim": TRANSPORT_CLAIM_PATH,
            "ack": TRANSPORT_ACK_PATH,
            "result": TRANSPORT_RESULT_PATH,
            "method": "POST",
            "content_type": "application/json",
            "configured_base": endpoint_base,
            "configured_base_source": endpoint_source,
        },
        "auth_expectation": {
            "scheme": TRANSPORT_AUTH_SCHEME,
            "scope": TRANSPORT_REQUIRED_SCOPE,
            "credential_source_type": "environment_variable_name_only",
            "credential_source": _first_present(environ, TRANSPORT_CREDENTIAL_ENV_VARS),
            "credential_env_vars": list(TRANSPORT_CREDENTIAL_ENV_VARS),
        },
        "task_contract_fields": list(REQUIRED_CONTRACT_FIELDS),
        "result_contract_fields": list(TRANSPORT_RESULT_REQUIRED_FIELDS),
        "health_handshake": {
            "required_fields": list(TRANSPORT_HEALTH_REQUIRED_FIELDS),
            "endpoint": TRANSPORT_HEALTH_PATH,
        },
        "lease": {
            "default_lease_seconds": DEFAULT_LEASE_SECONDS,
            "max_attempts": MAX_TRANSPORT_ATTEMPTS,
            "poll_interval_seconds": DEFAULT_POLL_INTERVAL_SECONDS,
        },
        "no_public_windows_endpoint": True,
        "cloud_deploys_second_hermes": False,
    }


def audit_windows_hermes_transport(
    registry: Mapping[str, Any] | Any | None = None,
) -> dict[str, Any]:
    """Audit existing Execution V2 surfaces for the Windows transport boundary.

    Reuse-first: identifies which existing surfaces already satisfy part of the
    contract, and reports the exact minimal relay capability that is missing. It
    never deploys a relay, mutates credentials/bindings, or writes canonically.
    """
    if registry is None:
        try:
            from .event_sync import default_registry

            registry = default_registry()
        except Exception:  # pragma: no cover - defensive
            registry = None

    def has(method: str) -> bool:
        return registry is not None and callable(getattr(registry, method, None))

    reused: list[str] = []
    if has("submit_task") and has("get_task_result"):
        reused.append("task_registry")
    if callable(globals().get("normalize_result")):
        reused.append("result_normalization")
    if has("sync_terminal_result"):
        reused.append("event_sync_terminal_publication")
    if has("dispatch_liveness_report") and has("plan_task_redispatch"):
        reused.append("dispatch_lease_liveness")

    missing = list(TRANSPORT_REQUIRED_ENDPOINTS)

    return {
        "contract_version": TRANSPORT_CONTRACT_VERSION,
        "direction": TRANSPORT_DIRECTION,
        "reused_existing_surfaces": reused,
        "reused_surface_notes": {
            "task_registry": (
                "Existing EventSyncRegistry records tasks and holds additive "
                "transport lease/ack/result metadata; no second store is created."
            ),
            "result_normalization": (
                "Existing result_normalization.normalize_result is the single "
                "normalization entry point reused by the transport."
            ),
        },
        "missing_relay_capabilities": missing,
        "minimal_gap": dict(MINIMAL_RELAY_GAP),
        "human_gate_required": True,
        "production_deployed": False,
        "canonical_write_performed": False,
        "second_state_store_created": False,
        "credential_or_binding_mutated": False,
        "connection_attempted_to_windows": False,
    }


# =============================================================================
# HERMES_RESULT_ADAPTER_MINIMAL_PATCH_V1
# =============================================================================
#
# Minimal, honest bridge that closes the final Hermes -> Personal AI Brain
# read-back gap: a *validated* Windows Hermes transport result is written into
# the **existing** EVENT_SYNC Task Registry record so the rest of the Brain can
# read it back through the existing ``get_task_result`` surface, exactly like an
# EVENT_SYNC discovered/reconciled result.
#
# Reuse guarantees (no redesign, no duplication):
#   * Same single registry (``EventSyncRegistry._tasks``); no second store.
#   * Same ``evidence["task_result"]`` read-back shape used by
#     ``EventSyncRegistry.get_task_result`` / ``validated_review_result``.
#   * Same normalization entry point ``normalize_transport_result``.
#   * The GitHub Actions artifact/workflow path (``sync_terminal_result``) is
#     untouched and still authoritative whenever a real workflow conclusion
#     exists.
#
# This adapter performs **no** GitHub Actions conclusion fabrication: a Hermes
# result is stored with ``workflow_conclusion=None`` and is tagged with its
# transport provenance so it can never masquerade as a CI-derived terminal
# result.
#
# Migration notes (additive, backward compatible):
#   * No schema/binding change: existing registry records gain only optional
#     keys (``transport_*``, ``hermes_transport`` provenance).
#   * Existing tasks without Hermes results are unaffected; the GitHub Actions
#     path continues to set ``workflow_conclusion`` and remain authoritative.
#   * Rollout is inert until a caller invokes ``ingest_hermes_result``; the
#     production boundary (relay endpoints + credentials) is a separate Human
#     Gate declared in :data:`HERMES_RESULT_ADAPTER_DEPLOYMENT_GATE`.

HERMES_RESULT_ADAPTER_VERSION = "HERMES_RESULT_ADAPTER_MINIMAL_PATCH_V1"
HERMES_RESULT_SOURCE = "hermes_windows_transport"

#: Exact production deployment Human Gate. This patch is code-complete and
#: test-proven; deploying the ingestion boundary into production canonical state
#: is deliberately NOT performed here and requires an explicit Human Gate.
HERMES_RESULT_ADAPTER_DEPLOYMENT_GATE = {
    "capability": "hermes_result_ingestion_into_canonical_registry",
    "gate_id": HERMES_RESULT_ADAPTER_VERSION,
    "code_complete": True,
    "tests_pass": True,
    "production_deployed": False,
    "human_gate_required": True,
    "required_approvals": [
        "human owner approval to ingest non-CI (Windows Hermes) terminal results "
        "into canonical personal state via the existing Task Registry",
    ],
    "required_before_deploy": [
        "deploy the authenticated outbound transport relay endpoints "
        "(claim/ack/result) with scope hermes.transport",
        "bind HERMES_TRANSPORT_TOKEN / HERMES_TRANSPORT_URL in the production "
        "secret store (names only; no secret values in code)",
        "confirm the single EventSyncRegistry remains the only canonical task "
        "store in the deployed worker",
        "confirm the GitHub Actions artifact/workflow result path is unchanged "
        "and still authoritative when a real workflow conclusion exists",
    ],
    "forbidden_in_this_patch": [
        "no production deploy",
        "no credential/OAuth scope/binding/schema/production-data change",
        "no second state store",
    ],
}


# --- production deploy / Human Gate assessment -------------------------------
#
# This is a *read-only* readiness/status assessor.  It never deploys, never
# mutates credentials or bindings, and never fabricates a production version.
# The library cannot itself perform a Cloudflare deploy; an externally observed
# deployment must be supplied as evidence before any non-gated status is
# returned.  Absent that evidence the only honest outcome is
# ``HUMAN_GATE_REQUIRED``.

#: Non-secret identifiers of the captured production rollback target, copied
#: from ``worker/PRODUCTION-BASELINE.json``.  No secret value is represented.
HERMES_ADAPTER_PRODUCTION_BASELINE = {
    "service": "personal-ai-execution-mcp",
    "environment": "production",
    "production_version": "3e2fed43",
    "source_file": "worker/index.js",
    "source_sha256": "8D0EFBDC394A9E847C70C05D5D0AA6411D72E3BA03E9C9AF43C95EAEE8F20CA1",
    "rollback_reference": (
        "Restore Cloudflare version 3e2fed43 if a later deployment fails a "
        "pre-Golden gate"
    ),
}

#: Environment variable *names* that would authorize a Cloudflare production
#: deploy.  Only presence is ever checked; values are never read or printed.
DEPLOY_CREDENTIAL_ENV_VARS = (
    "CLOUDFLARE_API_TOKEN",
    "CF_API_TOKEN",
    "CLOUDFLARE_API_KEY",
)

FINAL_STATUS_DEPLOY_PASS = "DEPLOY_PASS"
FINAL_STATUS_READY_FOR_WINDOWS_FINAL_GOLDEN = "READY_FOR_WINDOWS_FINAL_GOLDEN"
FINAL_STATUS_HERMES_IN_ARCHITECTURE_PASS = "HERMES_IN_ARCHITECTURE_PASS"
FINAL_STATUS_ROLLED_BACK = "ROLLED_BACK"
FINAL_STATUS_HUMAN_GATE_REQUIRED = "HUMAN_GATE_REQUIRED"

FINAL_STATUSES = (
    FINAL_STATUS_DEPLOY_PASS,
    FINAL_STATUS_READY_FOR_WINDOWS_FINAL_GOLDEN,
    FINAL_STATUS_HERMES_IN_ARCHITECTURE_PASS,
    FINAL_STATUS_ROLLED_BACK,
    FINAL_STATUS_HUMAN_GATE_REQUIRED,
)


def assess_hermes_result_adapter_deploy(
    env: Mapping[str, str] | None = None,
    *,
    deployed_production_version: str | None = None,
    production_read_back_ok: bool = False,
    windows_result_ingested: bool = False,
    rolled_back: bool = False,
) -> dict[str, Any]:
    """Assess the deploy/Human-Gate status from environment *names* only.

    The assessor never deploys and never reads a secret value.  A non-gated
    status is only returned when the caller supplies concrete external
    evidence: an observed ``deployed_production_version`` with a passing
    production read-back (``READY_FOR_WINDOWS_FINAL_GOLDEN``) or a genuinely
    ingested Windows Hermes result (``HERMES_IN_ARCHITECTURE_PASS``).  With no
    such evidence, the honest outcome is ``HUMAN_GATE_REQUIRED``.
    """
    environ = os.environ if env is None else env
    deploy_credential_source = _first_present(environ, DEPLOY_CREDENTIAL_ENV_VARS)
    transport_credential_source = _first_present(environ, TRANSPORT_CREDENTIAL_ENV_VARS)
    endpoint_base = None
    endpoint_source = None
    for name in TRANSPORT_ENDPOINT_ENV_VARS:
        value = str(environ.get(name, "")).strip()
        if value:
            endpoint_base = value
            endpoint_source = name
            break

    if rolled_back:
        final_status = FINAL_STATUS_ROLLED_BACK
    elif windows_result_ingested:
        final_status = FINAL_STATUS_HERMES_IN_ARCHITECTURE_PASS
    elif deployed_production_version and production_read_back_ok:
        final_status = FINAL_STATUS_READY_FOR_WINDOWS_FINAL_GOLDEN
    else:
        final_status = FINAL_STATUS_HUMAN_GATE_REQUIRED

    missing_dependencies: list[str] = []
    if not deploy_credential_source:
        missing_dependencies.append(
            "cloudflare_deploy_credential:" + "|".join(DEPLOY_CREDENTIAL_ENV_VARS)
        )
    if not transport_credential_source:
        missing_dependencies.append(
            "hermes_transport_credential:" + "|".join(TRANSPORT_CREDENTIAL_ENV_VARS)
        )
    if not endpoint_source:
        missing_dependencies.append(
            "hermes_transport_endpoint:" + "|".join(TRANSPORT_ENDPOINT_ENV_VARS)
        )

    production_deployed = bool(deployed_production_version) and not rolled_back
    return {
        "final_status": final_status,
        "workflow_status": "not_applicable_agent_local",
        "service": HERMES_ADAPTER_PRODUCTION_BASELINE["service"],
        "environment": HERMES_ADAPTER_PRODUCTION_BASELINE["environment"],
        "adapter_version": HERMES_RESULT_ADAPTER_VERSION,
        "deployment_attempted": bool(deployed_production_version),
        "production_deployed": production_deployed,
        "production_version": deployed_production_version,
        "production_read_back_ok": bool(production_read_back_ok),
        "windows_result_ingested": bool(windows_result_ingested),
        "rolled_back": bool(rolled_back),
        "rollback_target": dict(HERMES_ADAPTER_PRODUCTION_BASELINE),
        "deploy_credential_source": deploy_credential_source,
        "transport_credential_source": transport_credential_source,
        "transport_endpoint_source": endpoint_source,
        "transport_endpoint_base": endpoint_base,
        "required_auth_scope": TRANSPORT_REQUIRED_SCOPE,
        "required_endpoints": list(TRANSPORT_REQUIRED_ENDPOINTS),
        "missing_dependencies": missing_dependencies,
        "human_gate_required": final_status == FINAL_STATUS_HUMAN_GATE_REQUIRED,
        "canonical_write_performed": False,
        "second_state_store_created": False,
        "credential_or_binding_mutated": False,
        "connection_attempted_to_windows": False,
        "secrets_recorded": False,
        "assessed_at": _now_utc(),
    }


def _registry_tasks(registry: Any) -> Any:
    """Return the existing task mapping backing ``registry`` or ``None``."""
    if registry is None:
        return None
    tasks = getattr(registry, "_tasks", None)
    if isinstance(tasks, Mapping):
        return tasks
    if isinstance(registry, Mapping):
        return registry
    return None


def registry_record(registry: Any, task_id: str) -> dict[str, Any] | None:
    """Return the *existing* registry record for ``task_id`` if present.

    Read-only lookup into the single canonical registry. It never creates a
    record and never falls back to a second store.
    """
    tasks = _registry_tasks(registry)
    if not isinstance(tasks, Mapping):
        return None
    record = tasks.get(str(task_id))
    return record if isinstance(record, dict) else None


def apply_registry_patch(
    registry: Any, task_id: str, patch: Mapping[str, Any] | None
) -> bool:
    """Apply an additive transport patch to the existing registry record.

    Returns ``False`` when the task is not registered, so callers fail closed
    instead of creating a second task store.
    """
    record = registry_record(registry, task_id)
    if record is None:
        return False
    if isinstance(patch, Mapping):
        record.update(dict(patch))
    return True


def build_hermes_result_envelope(
    *,
    task_id: str,
    worker_id: str,
    lease_id: str,
    task_state: str = "TASK_STATE_COMPLETED",
    executor_identity: str = "hermes-native-hand",
    status: str = "success",
    tests: str = "",
    artifacts: list[Any] | None = None,
    expected_files: list[str] | None = None,
    changed_files: list[str] | None = None,
    summary: str = "",
    finished_at: str | None = None,
    contract_version: str = TRANSPORT_CONTRACT_VERSION,
    **extra: Any,
) -> dict[str, Any]:
    """Build the minimal Hermes result envelope and stamp its evidence hash.

    The envelope is the only shape a Windows Hermes worker may return. Required
    identity fields are ``task_id`` / ``worker_id`` / ``lease_id``; terminal
    state is ``task_state``; integrity is ``evidence_hash`` over the stable
    fields; ``artifacts`` and the remaining metadata are advisory evidence.
    """
    envelope: dict[str, Any] = {
        "contract_version": contract_version,
        "task_id": str(task_id),
        "worker_id": str(worker_id),
        "lease_id": str(lease_id),
        "status": status,
        "task_state": task_state,
        "executor_identity": executor_identity,
        "tests": tests,
        "artifacts": list(artifacts or []),
        "expected_files": list(expected_files or []),
        "changed_files": list(changed_files or []),
        "finished_at": finished_at or _now_utc(),
    }
    envelope.update(extra)
    envelope["evidence_hash"] = compute_evidence_hash(envelope)
    return envelope


def _write_hermes_readback(
    record: dict[str, Any],
    envelope: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> None:
    """Write a validated Hermes result into the existing registry record.

    Uses the same shape as an EVENT_SYNC discovered result: the terminal
    execution state lives on ``evidence["task_result"]`` and the record flags
    allow the existing ``get_task_result`` / review surface to read it back.
    """
    task_id = str(envelope.get("task_id") or "")
    normalized_status = decision.get("normalized_status")
    readback = {
        "task_id": task_id,
        "status": normalized_status,
        "normalized_status": normalized_status,
        "terminal": True,
        "workflow_conclusion": None,
        "conclusion_authoritative": False,
        "conclusion_result_mismatch": False,
        "missing_expected_files": [],
        "source": HERMES_RESULT_SOURCE,
        "evidence_hash": decision.get("evidence_hash"),
        "executor_identity": decision.get("executor_identity"),
        "artifacts": list(envelope.get("artifacts") or []),
        "tests": envelope.get("tests", ""),
        "reason": (
            "terminal Hermes Windows transport result ingested into the existing "
            "Task Registry; no GitHub Actions workflow conclusion is claimed"
        ),
    }
    record["status"] = normalized_status
    record["normalized_status"] = normalized_status
    record["workflow_conclusion"] = None
    record["terminal"] = True
    record["result_available"] = True
    record["requires_review"] = True
    if not record.get("reviewed"):
        record["review_state"] = "PENDING_REVIEW"

    evidence = dict(record.get("evidence") or {})
    evidence["task_result"] = readback
    evidence["hermes_transport"] = {
        "source": HERMES_RESULT_SOURCE,
        "adapter_version": HERMES_RESULT_ADAPTER_VERSION,
        "evidence_hash": decision.get("evidence_hash"),
        "executor_identity": decision.get("executor_identity"),
        "task_state": envelope.get("task_state"),
        "worker_id": envelope.get("worker_id"),
        "lease_id": envelope.get("lease_id"),
        "ingested_at": _now_utc(),
    }
    record["evidence"] = evidence

    for key, value in (decision.get("registry_patch") or {}).items():
        record[key] = value


def _safe_read_back(registry: Any, task_id: str) -> dict[str, Any] | None:
    getter = getattr(registry, "get_task_result", None)
    if not callable(getter):
        return None
    try:
        return getter(str(task_id))
    except (KeyError, ValueError, TypeError, AttributeError):
        return None


def ingest_hermes_result(
    registry: Any,
    envelope: Mapping[str, Any],
    *,
    record: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Ingest one validated Hermes transport result for ``get_task_result``.

    Fail-closed: the task must already exist in the single existing Task
    Registry. Validation, evidence-hash checking, lease ownership, idempotency
    and conflict rejection all reuse :func:`normalize_transport_result`. On
    acceptance the result is written into the existing record and read back
    through the existing :meth:`EventSyncRegistry.get_task_result` surface.

    The return value is the transport decision extended with ``ingested`` and
    ``read_back``. A duplicate returns ``ingested=False`` and performs no write,
    so retransmission can never create a second terminal result.
    """
    task_id = (
        str(envelope.get("task_id") or "") if isinstance(envelope, Mapping) else ""
    )
    resolved = record if record is not None else registry_record(registry, task_id)
    if resolved is None:
        return {
            "task_id": task_id,
            "state": RESULT_STATE_REJECTED,
            "accepted": False,
            "duplicate": False,
            "ingested": False,
            "reason_code": "TASK_NOT_REGISTERED",
            "reason": (
                "task is not registered in the existing Task Registry; refusing "
                "to create a second store or invent a task"
            ),
            "errors": [f"unknown task_id: {task_id}"] if task_id else ["task_id missing"],
            "normalized_status": None,
            "execution_result": None,
            "read_back": None,
            "canonical_write_performed": False,
            "second_state_store_created": False,
        }

    decision = normalize_transport_result(resolved, envelope, now=now)
    decision["ingested"] = False
    decision["second_state_store_created"] = False
    decision["adapter_version"] = HERMES_RESULT_ADAPTER_VERSION

    if not decision.get("accepted") or decision.get("duplicate"):
        decision["read_back"] = _safe_read_back(registry, task_id)
        return decision

    _write_hermes_readback(resolved, envelope, decision)
    decision["ingested"] = True
    decision["read_back"] = _safe_read_back(registry, task_id)
    return decision


__all__ = [
    "ACK_STATE_ACKNOWLEDGED",
    "ACK_STATE_IDEMPOTENT",
    "ACK_STATE_LEASE_MISMATCH",
    "AGENT_CARD_PATH",
    "CLAIM_STATE_CLAIMED",
    "CLAIM_STATE_IDEMPOTENT",
    "CLAIM_STATE_LEASED_ELSEWHERE",
    "CLAIM_STATE_NOT_CLAIMABLE",
    "CODEX_MARKERS",
    "COMPLETED_TASK_STATES",
    "CREDENTIAL_ENV_VARS",
    "DEFAULT_A2A_BASE_URL",
    "DEFAULT_LEASE_SECONDS",
    "DEFAULT_POLL_INTERVAL_SECONDS",
    "DEPLOY_CREDENTIAL_ENV_VARS",
    "EVIDENCE_HASH_FIELDS",
    "FINAL_STATUSES",
    "FINAL_STATUS_DEPLOY_PASS",
    "FINAL_STATUS_HERMES_IN_ARCHITECTURE_PASS",
    "FINAL_STATUS_HUMAN_GATE_REQUIRED",
    "FINAL_STATUS_READY_FOR_WINDOWS_FINAL_GOLDEN",
    "FINAL_STATUS_ROLLED_BACK",
    "GOLDEN_PATH_BLOCKED",
    "GOLDEN_PATH_PASS",
    "GOLDEN_PATH_PARTIAL",
    "HERMES_ADAPTER_PRODUCTION_BASELINE",
    "HERMES_RESULT_ADAPTER_DEPLOYMENT_GATE",
    "HERMES_RESULT_ADAPTER_VERSION",
    "HERMES_RESULT_SOURCE",
    "HermesOrchestrationAdapter",
    "MAX_TRANSPORT_ATTEMPTS",
    "MINIMAL_RELAY_GAP",
    "REQUIRED_CONTRACT_FIELDS",
    "RESULT_STATE_ACCEPTED",
    "RESULT_STATE_DUPLICATE",
    "RESULT_STATE_LEASE_MISMATCH",
    "RESULT_STATE_REJECTED",
    "RUNTIME_ENDPOINT_ENV_VARS",
    "RUNTIME_EXECUTABLES",
    "STATUS_BLOCKED",
    "STATUS_FAIL",
    "STATUS_PARTIAL",
    "STATUS_PASS",
    "TERMINAL_TASK_STATES",
    "TRANSPORT_ACK_PATH",
    "TRANSPORT_ACK_REQUIRED_FIELDS",
    "TRANSPORT_AUTH_SCHEME",
    "TRANSPORT_CLAIM_PATH",
    "TRANSPORT_CLAIM_REQUIRED_FIELDS",
    "TRANSPORT_CONTRACT_VERSION",
    "TRANSPORT_CREDENTIAL_ENV_VARS",
    "TRANSPORT_DIRECTION",
    "TRANSPORT_ENDPOINT_ENV_VARS",
    "TRANSPORT_HEALTH_PATH",
    "TRANSPORT_HEALTH_REQUIRED_FIELDS",
    "TRANSPORT_RELAY_BASE_PATH",
    "TRANSPORT_RELAY_ID",
    "TRANSPORT_REQUIRED_ENDPOINTS",
    "TRANSPORT_REQUIRED_SCOPE",
    "TRANSPORT_RESULT_PATH",
    "TRANSPORT_RESULT_REQUIRED_FIELDS",
    "ack_idempotency_key",
    "acknowledge_task",
    "apply_registry_patch",
    "assess_hermes_result_adapter_deploy",
    "audit_windows_hermes_transport",
    "build_health_handshake",
    "build_hermes_result_envelope",
    "build_task_assignment",
    "build_task_contract",
    "claim_idempotency_key",
    "claim_task",
    "compute_evidence_hash",
    "evaluate_health_handshake",
    "ingest_hermes_result",
    "is_transport_claimable",
    "normalize_hermes_evidence",
    "normalize_to_execution_v2",
    "normalize_transport_result",
    "plan_result_publication",
    "probe_hermes_runtime",
    "registry_record",
    "result_idempotency_key",
    "run_hermes_golden_poc",
    "validate_health_handshake",
    "validate_result_envelope",
    "validate_task_contract",
    "windows_hermes_integration_inputs",
]
