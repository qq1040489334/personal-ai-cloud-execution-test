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

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
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


__all__ = [
    "AGENT_CARD_PATH",
    "CODEX_MARKERS",
    "COMPLETED_TASK_STATES",
    "CREDENTIAL_ENV_VARS",
    "DEFAULT_A2A_BASE_URL",
    "GOLDEN_PATH_BLOCKED",
    "GOLDEN_PATH_PASS",
    "GOLDEN_PATH_PARTIAL",
    "HermesOrchestrationAdapter",
    "REQUIRED_CONTRACT_FIELDS",
    "RUNTIME_ENDPOINT_ENV_VARS",
    "RUNTIME_EXECUTABLES",
    "STATUS_BLOCKED",
    "STATUS_FAIL",
    "STATUS_PARTIAL",
    "STATUS_PASS",
    "TERMINAL_TASK_STATES",
    "build_task_contract",
    "normalize_hermes_evidence",
    "normalize_to_execution_v2",
    "probe_hermes_runtime",
    "run_hermes_golden_poc",
    "validate_task_contract",
]
