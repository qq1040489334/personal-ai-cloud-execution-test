"""REALITY_PROMOTION_ADAPTER_IMPLEMENTATION_V0.1 -- controlled promotion adapter.

This is the *adapter* stage of the REALITY promotion path::

    Candidate -> Adapter -> Writer -> ASSET_DB -> Read-back

It materializes exactly one missing piece: the deterministic mapping from a
**Reviewed Candidate** (a Candidate Artifact whose read-only review returned
``review_status=PASS`` and ``promotion_status=PROMOTION_ELIGIBLE``) to the
request shape the **existing** Asset Worker writers already accept.

It reuses, without re-declaring or duplicating:

* :func:`personal_ai_execution.reality_canonical_writer.prepare_promotion` for
  the deterministic PREPARE plan (target, validated content hash, promoted
  provenance, idempotency key, intent hash and version intent);
* :mod:`personal_ai_execution.reality_candidate_handoff` for the structural
  Candidate Artifact validation;
* :func:`personal_ai_execution.reality_candidate_review.review_candidate_artifact`
  for the advisory review verdict when the caller does not supply one;
* the existing Worker writer entry points / contracts and the single
  ``ASSET_DB:assets/asset_versions`` canonical store.

It deliberately does **not**:

* create a new Reality writer or a second state store;
* call :func:`reality_canonical_writer.promote_reality_candidate` or any real
  production write surface;
* deploy, read a secret / credential or change a permission, binding or schema.

Production-refusing rules (fail-closed):

* the adapter only feeds an **explicitly marked in-memory simulation writer**
  (``mark_simulation_writer``); a callable flagged as a production writer, or any
  unmarked callable, is refused;
* without ``HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1`` authorization the adapter
  returns ``BLOCKED`` and never calls the writer;
* ``dry_run=True`` (the default) maps the request and returns ``ADAPTED`` without
  calling any writer at all;
* a repeated idempotency key returns ``IDEMPOTENT`` and never calls the writer.

Every conclusion in the returned report is an evidence item tagged with exactly
one of ``OBSERVED`` / ``STATED`` / ``INFERRED`` / ``UNKNOWN``.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Mapping, MutableMapping

from personal_ai_execution.provenance_contract import (
    PROVENANCE_CONTRACT_VERSION,
    STATUS_VERIFIED as PROVENANCE_VERIFIED,
)
from personal_ai_execution.reality_candidate_handoff import (
    HANDOFF_CONTRACT,
    validate_candidate_artifact,
)
from personal_ai_execution.reality_candidate_review import (
    PROMOTION_ELIGIBLE,
    review_candidate_artifact,
)
from personal_ai_execution.reality_canonical_writer import (
    CANONICAL_STORE,
    HUMAN_GATE,
    REALITY_ASSET_TYPE,
    REALITY_ROLE,
    TARGET_ASSET_TYPES,
    WRITER_CONTRACTS,
    WRITER_CONTRACT_VERSION,
    WRITER_ENTRYPOINTS,
    prepare_promotion,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_UNKNOWN,
)
from personal_ai_execution.result_normalization import BLOCKED, PASS

#: Version tag of the adapter goal / implementation.
ADAPTER_GOAL = "REALITY_PROMOTION_ADAPTER_IMPLEMENTATION_V0.1"
#: Stable report label emitted by the adapter.
ADAPTER_REPORT = ADAPTER_GOAL + "_REPORT"
#: Fully-qualified adapter contract id.
ADAPTER_CONTRACT = "PERSONAL_AI_REALITY_PROMOTION_ADAPTER_V0.1"
#: The adapter is non-production; writes are simulated only.
ADAPTER_MODE = "SIMULATION"

#: Explicit marker attributes; only marked simulation fakes are accepted.
SIMULATION_WRITER_ATTR = "__reality_promotion_simulation_writer__"
PRODUCTION_WRITER_ATTR = "__reality_promotion_production_writer__"

#: Adapter statuses. A production write is never represented here.
STATUS_ADAPTED = "ADAPTED"
STATUS_SIMULATED = "SIMULATED"
STATUS_IDEMPOTENT = "IDEMPOTENT"
STATUS_QUARANTINED = "QUARANTINED"
STATUS_BLOCKED = "BLOCKED"
ADAPTER_STATUSES = (
    STATUS_ADAPTED,
    STATUS_SIMULATED,
    STATUS_IDEMPOTENT,
    STATUS_QUARANTINED,
    STATUS_BLOCKED,
)

#: Evidence quality tiers (never upgraded).
EVIDENCE_TIERS = (
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_INFERRED,
    EPISTEMIC_UNKNOWN,
)

#: The exact input shape the existing Asset Worker writer entry points accept
#: (mirrors ``REALITY_WORKER_INPUT_FIELDS`` from the V0.1 design).
REALITY_WORKER_INPUT_FIELDS = (
    "asset_type",
    "asset_id",
    "title",
    "content",
    "content_hash",
    "schema_version",
    "created_by",
    "supersedes",
    "source_identity",
    "source_location",
    "source_version",
    "content_version",
    "source_content_hash",
    "captured_at",
    "promoted_at",
    "canonical_version",
    "promotion_decision",
    "promotion_event",
)

#: Worker-only fields the adapter adds (absent from a raw capture candidate).
ADAPTER_ADDED_FIELDS = ("title", "asset_id", "schema_version", "created_by", "supersedes")
#: Field remapping performed by the adapter (design V0.1).
ADAPTER_REMAPPED_FIELDS = (("proposed_version", "canonical_version"),)
ADAPTER_SCHEMA_VERSION = "v0.1"
ADAPTER_CREATED_BY = "cloud-agent"

#: A Worker write surface: takes the mapped request mapping, returns a response.
WriteSurface = Callable[[Mapping[str, Any]], Any]


def _meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _evidence(source: str, detail: str) -> dict[str, str]:
    tier = source if source in EVIDENCE_TIERS else EPISTEMIC_UNKNOWN
    return {"source": tier, "detail": detail}


def _tiers_present(evidence: list[dict[str, str]]) -> list[str]:
    found = {item.get("source") for item in evidence}
    return [tier for tier in EVIDENCE_TIERS if tier in found]


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"check": name, "status": PASS if passed else BLOCKED, "detail": detail}


def mark_simulation_writer(writer: Any) -> Any:
    """Explicitly mark an in-memory callable as a non-production fake writer."""
    if not callable(writer):
        raise TypeError("a simulation writer must be callable")
    if getattr(writer, PRODUCTION_WRITER_ATTR, False) is True:
        raise PermissionError(
            "a production writer cannot be marked as a simulation writer"
        )
    setattr(writer, SIMULATION_WRITER_ATTR, True)
    return writer


def is_simulation_writer(writer: Any) -> bool:
    """Return True only for an explicitly-marked, non-production fake writer."""
    if not callable(writer):
        return False
    if getattr(writer, PRODUCTION_WRITER_ATTR, False) is True:
        return False
    return getattr(writer, SIMULATION_WRITER_ATTR, False) is True


def make_recording_simulation_writer(target: str) -> Any:
    """Build an in-memory recording fake writer for one canonical target."""
    if target not in TARGET_ASSET_TYPES:
        raise ValueError("target is not in the canonical allowlist: " + str(target))
    calls: list[dict[str, Any]] = []

    def _writer(request: Any) -> dict[str, Any]:
        delivered = copy.deepcopy(dict(request)) if isinstance(request, Mapping) else request
        calls.append({"target": target, "request": delivered})
        return {
            "contract": WRITER_CONTRACTS[target],
            "asset_type": target,
            "status": "SIMULATED_WRITTEN",
            "content_hash": (
                delivered.get("content_hash") if isinstance(delivered, Mapping) else None
            ),
            "canonical_write_performed": False,
            "production_reached": False,
            "mode": ADAPTER_MODE,
        }

    _writer = mark_simulation_writer(_writer)
    _writer.calls = calls
    return _writer


def build_worker_request(
    plan: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
    *,
    title: Any = None,
) -> dict[str, Any] | None:
    """Map a PREPARE plan + candidate into the existing Worker input shape.

    Pure and side-effect free. Returns ``None`` when the plan is not an eligible
    prepared plan or the target is not an allowed canonical asset type (REALITY
    is source/provenance, never a target). The ``proposed_version`` field of the
    canonical plan is remapped to the Worker ``canonical_version`` field.
    """
    if not isinstance(plan, Mapping) or not isinstance(candidate, Mapping):
        return None
    request = plan.get("write_request")
    if not isinstance(request, Mapping):
        return None
    target = plan.get("target_asset_type")
    if target not in TARGET_ASSET_TYPES:
        return None

    candidate_id = request.get("candidate_id") or candidate.get("candidate_id")
    resolved_title = title if _meaningful(title) else candidate.get("title")
    if not _meaningful(resolved_title):
        resolved_title = str(target).title() + " " + str(candidate_id)

    worker_request: dict[str, Any] = {
        "asset_type": target,
        "asset_id": request.get("asset_id"),
        "title": str(resolved_title),
        "content": request.get("content", candidate.get("content")),
        "content_hash": request.get("content_hash") or candidate.get("content_hash"),
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "created_by": ADAPTER_CREATED_BY,
        "supersedes": list(request.get("supersedes") or []),
        "source_identity": request.get("source_identity") or candidate.get("source_identity"),
        "source_location": candidate.get("source_location"),
        "source_version": candidate.get("source_version"),
        "content_version": candidate.get("content_version"),
        "source_content_hash": candidate.get("source_content_hash"),
        "captured_at": candidate.get("captured_at"),
        "promoted_at": candidate.get("promoted_at"),
        # remap: proposed_version -> canonical_version
        "canonical_version": request.get("proposed_version"),
        "promotion_decision": candidate.get("promotion_decision"),
        "promotion_event": candidate.get("promotion_event"),
    }

    worker_request.update(
        {
            "candidate_id": candidate_id,
            "source_asset_type": REALITY_ASSET_TYPE,
            "reality_role": REALITY_ROLE,
            "provenance": request.get("provenance") or candidate.get("provenance"),
            "provenance_contract": PROVENANCE_CONTRACT_VERSION,
            "idempotency_key": request.get("idempotency_key"),
            "intent_hash": request.get("intent_hash"),
            "canonical_writer": request.get("canonical_writer"),
            "canonical_writer_contract": request.get("canonical_writer_contract"),
            "canonical_store": request.get("canonical_store"),
            "canonical_write_enabled": False,
        }
    )
    return worker_request


def _finalize(report: dict[str, Any]) -> dict[str, Any]:
    evidence = report["evidence"]
    worker_request = report.get("worker_request")
    request_fields_present = (
        isinstance(worker_request, Mapping)
        and all(field in worker_request for field in REALITY_WORKER_INPUT_FIELDS)
    )
    canonical_single = (
        report.get("canonical_store") == CANONICAL_STORE
        and report.get("second_state_store_created") is False
    )

    checks = [
        _check(
            "adapter is production-refusing (no real canonical write)",
            report["production_write_performed"] is False
            and report["canonical_write_performed"] is False
            and report["production_refusing"] is True,
            "production_write_performed=False; canonical_write_performed=False",
        ),
        _check(
            "single canonical store (no second state store / new writer)",
            canonical_single and report["reality_specific_writer_created"] is False,
            "canonical_store=" + str(report.get("canonical_store")),
        ),
        _check(
            "status is a declared adapter status",
            report["status"] in ADAPTER_STATUSES,
            "status=" + str(report["status"]),
        ),
        _check(
            "Human Gate remains required and is never auto-approved",
            report["requires_human_gate"] is True and report["human_gate"] == HUMAN_GATE,
            "human_gate=" + HUMAN_GATE,
        ),
        _check(
            "worker request matches the Asset Worker input contract",
            request_fields_present if worker_request is not None else True,
            "worker_input_fields=" + str(len(REALITY_WORKER_INPUT_FIELDS)),
        ),
        _check(
            "evidence items carry OBSERVED/STATED/INFERRED/UNKNOWN tags",
            bool(evidence) and all(item["source"] in EVIDENCE_TIERS for item in evidence),
            "evidence items=" + str(len(evidence)),
        ),
        _check(
            "no deploy / secret / permission / binding / schema change",
            report["deployment_performed"] is False
            and report["secret_accessed"] is False
            and report["permissions_changed"] is False
            and report["binding_changed"] is False
            and report["schema_changed"] is False,
            "no deployment, credential/secret access, permission, binding or schema change",
        ),
    ]
    report["checks"] = checks
    report["workflow_status"] = (
        PASS if all(check["status"] == PASS for check in checks) else BLOCKED
    )
    report["evidence_tiers_present"] = _tiers_present(evidence)
    report["final_status"] = (
        "ADAPTER_STATUS=" + str(report["status"]) + ";WRITE_PERFORMED=False"
    )
    report["markdown"] = _markdown(report)
    return report


def _markdown(report: Mapping[str, Any]) -> str:
    lines = [
        f"# {ADAPTER_GOAL}",
        "",
        f"- goal: {ADAPTER_GOAL}",
        f"- contract: {ADAPTER_CONTRACT}",
        f"- mode: {ADAPTER_MODE} (production-refusing)",
        f"- handoff_contract: {HANDOFF_CONTRACT}",
        f"- writer_contract: {WRITER_CONTRACT_VERSION}",
        f"- status: {report['status']}",
        f"- candidate_id: {report.get('candidate_id') or 'UNKNOWN'}",
        f"- review_status: {report.get('review_status') or 'UNKNOWN'}",
        f"- promotion_status: {report.get('promotion_status') or 'UNKNOWN'}",
        f"- target_asset_type: {report.get('target_asset_type') or 'UNKNOWN'}",
        f"- content_hash: {report.get('content_hash') or 'UNKNOWN'}",
        f"- idempotency_key: {report.get('idempotency_key') or 'UNKNOWN'}",
        f"- intent_hash: {report.get('intent_hash') or 'UNKNOWN'}",
        f"- canonical_version: {report.get('canonical_version') or 'UNKNOWN'}",
        f"- canonical_store: {report.get('canonical_store')}",
        f"- human_gate: {report.get('human_gate')}",
        f"- human_gate_authorized: {report.get('human_gate_authorized')}",
        f"- dry_run: {report.get('dry_run')}",
        "",
        "## Reasons",
    ]
    if report.get("reasons"):
        for reason in report["reasons"]:
            lines.append(f"- {reason}")
    else:
        lines.append("- (none)")
    lines += ["", "## Evidence"]
    for item in report["evidence"]:
        lines.append(f"- [{item['source']}] {item['detail']}")
    lines += [
        "",
        "## No-mutation statement",
        "- production_write_performed: False",
        "- canonical_write_performed: False",
        "- reality_canonical_written: False",
        "- knowledge_written: False",
        "- skill_written: False",
        "- decision_written: False",
        "- second_state_store_created: False",
        "- reality_specific_writer_created: False",
        "- deployment_performed: False",
        "- credentials_accessed: False",
        "- secret_accessed: False",
        "- permissions_changed: False",
        "- binding_changed: False",
        "- schema_changed: False",
        "",
        "## Checks",
    ]
    for check in report["checks"]:
        lines.append(f"- [{check['status']}] {check['check']}: {check['detail']}")
    lines += ["", f"FINAL_STATUS={report['final_status']}"]
    return "\n".join(lines)


def adapt_reviewed_candidate(
    artifact: Mapping[str, Any] | None,
    *,
    review: Mapping[str, Any] | None = None,
    target_asset_type: Any = None,
    existing_asset: Mapping[str, Any] | None = None,
    title: Any = None,
    ledger: MutableMapping[str, Any] | None = None,
    human_gate_authorized: bool = False,
    authorization: Any = None,
    write_surface: WriteSurface | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Adapt a Reviewed Candidate into the existing Asset Worker request shape.

    The input is a Candidate Artifact (``REALITY_CANDIDATE_HANDOFF_V0.1``) that
    has passed the read-only review. When ``review`` is not supplied the adapter
    derives it via :func:`review_candidate_artifact`. Only a
    ``review_status=PASS`` / ``promotion_status=PROMOTION_ELIGIBLE`` candidate is
    adapted; anything else fails closed.

    By default (``dry_run=True``) no writer is called: the adapter returns
    ``ADAPTED`` with the mapped ``worker_request``. When ``dry_run=False`` an
    explicitly-marked simulation ``write_surface`` may be invoked, and only when
    the Human Gate is authorized; production writers are always refused.
    """
    bounded = bool(human_gate_authorized) and authorization in (HUMAN_GATE, True)

    report: dict[str, Any] = {
        "report": ADAPTER_REPORT,
        "goal": ADAPTER_GOAL,
        "contract": ADAPTER_CONTRACT,
        "handoff_contract": HANDOFF_CONTRACT,
        "writer_contract": WRITER_CONTRACT_VERSION,
        "provenance_contract": PROVENANCE_CONTRACT_VERSION,
        "mode": ADAPTER_MODE,
        "phase": "ADAPT",
        "status": STATUS_BLOCKED,
        "candidate_id": None,
        "artifact_id": None,
        "artifact_location": None,
        "review_status": None,
        "promotion_status": None,
        "target_asset_type": None,
        "content_hash": None,
        "idempotency_key": None,
        "intent_hash": None,
        "proposed_version": None,
        "canonical_version": None,
        "canonical_store": CANONICAL_STORE,
        "reused_canonical_writer": None,
        "reused_writer_contract": None,
        "worker_request": None,
        "write_surface": None,
        "writer_response": None,
        "dry_run": bool(dry_run),
        "human_gate": HUMAN_GATE,
        "human_gate_authorized": bool(human_gate_authorized),
        "authorization_bounded": bounded,
        "requires_human_gate": True,
        "production_refusing": True,
        "reasons": [],
        "evidence": [],
        "unknowns": [],
        "read_only": True,
        "content_exposed": False,
        "message_content_exposed": False,
        "production_write_performed": False,
        "canonical_write_performed": False,
        "reality_canonical_written": False,
        "knowledge_written": False,
        "skill_written": False,
        "decision_written": False,
        "second_state_store_created": False,
        "reality_specific_writer_created": False,
        "deployment_performed": False,
        "credentials_accessed": False,
        "secret_accessed": False,
        "permissions_changed": False,
        "binding_changed": False,
        "schema_changed": False,
        "mark_reviewed_called": False,
    }

    validation = validate_candidate_artifact(artifact)
    source = artifact if isinstance(artifact, Mapping) else {}
    report["artifact_id"] = validation.get("artifact_id")
    report["artifact_location"] = validation.get("artifact_location")
    report["candidate_id"] = validation.get("candidate_id")

    if not validation.get("ok"):
        report["reasons"].append(
            "candidate artifact is not readable: "
            + ("; ".join(validation.get("reasons") or []) or "unknown reason")
        )
        report["unknowns"].append("candidate identity, provenance and review verdict")
        report["evidence"].append(
            _evidence(
                EPISTEMIC_UNKNOWN,
                "Candidate Artifact failed structural validation; adapter blocked",
            )
        )
        return _finalize(report)

    report["evidence"].append(
        _evidence(
            EPISTEMIC_OBSERVED,
            "read a valid " + HANDOFF_CONTRACT + " Candidate Artifact",
        )
    )

    if not isinstance(review, Mapping):
        review = review_candidate_artifact(source)
    report["review_status"] = review.get("review_status")
    report["promotion_status"] = review.get("promotion_status")

    if report["review_status"] != PASS or report["promotion_status"] != PROMOTION_ELIGIBLE:
        report["reasons"].append(
            "Reviewed Candidate is not PASS / "
            + PROMOTION_ELIGIBLE
            + " (review_status="
            + str(report["review_status"])
            + "; promotion_status="
            + str(report["promotion_status"])
            + ")"
        )
        report["unknowns"].append("promotion eligibility")
        report["evidence"].append(
            _evidence(
                EPISTEMIC_STATED,
                "advisory review did not return PASS / "
                + PROMOTION_ELIGIBLE
                + "; adapter refuses to build a writer request",
            )
        )
        return _finalize(report)

    plan = prepare_promotion(
        source,
        target_asset_type=target_asset_type,
        existing_asset=existing_asset,
    )
    report["target_asset_type"] = plan.get("target_asset_type")
    report["content_hash"] = plan.get("content_hash")
    report["idempotency_key"] = plan.get("idempotency_key")
    report["intent_hash"] = plan.get("intent_hash")
    report["proposed_version"] = plan.get("proposed_version")
    report["canonical_store"] = plan.get("canonical_store", CANONICAL_STORE)
    report["reused_canonical_writer"] = plan.get("reused_canonical_writer")
    report["reused_writer_contract"] = plan.get("reused_writer_contract")

    if not plan.get("eligible") or not isinstance(plan.get("write_request"), Mapping):
        report["status"] = STATUS_QUARANTINED
        report["reasons"].extend(plan.get("reasons") or ["plan is not eligible"])
        report["unknowns"].append("promoted provenance / hash integrity")
        report["evidence"].append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "prepare_promotion refused the candidate (hash / provenance / target)",
            )
        )
        return _finalize(report)

    if (
        report["canonical_store"] != CANONICAL_STORE
        or plan.get("second_state_store_created") is not False
    ):
        report["status"] = STATUS_QUARANTINED
        report["reasons"].append(
            "canonical store is not the single existing store; adapter refused"
        )
        return _finalize(report)

    report["promoted_provenance_status"] = PROVENANCE_VERIFIED
    candidate = source.get("candidate")
    candidate = candidate if isinstance(candidate, Mapping) else {}
    worker_request = build_worker_request(plan, candidate, title=title)
    if worker_request is None:
        report["status"] = STATUS_QUARANTINED
        report["reasons"].append("candidate does not map into the Worker input shape")
        return _finalize(report)

    report["worker_request"] = worker_request
    report["canonical_version"] = worker_request.get("canonical_version")
    report["status"] = STATUS_ADAPTED
    report["evidence"].append(
        _evidence(
            EPISTEMIC_OBSERVED,
            "mapped Reviewed Candidate to the existing Worker input shape via "
            + str(report["reused_canonical_writer"])
            + "; proposed_version -> canonical_version="
            + str(report["canonical_version"]),
        )
    )
    report["evidence"].append(
        _evidence(
            EPISTEMIC_OBSERVED,
            "content_hash integrity verified and provenance promoted to "
            + PROVENANCE_VERIFIED,
        )
    )

    key = report["idempotency_key"]
    if isinstance(ledger, MutableMapping) and key in ledger:
        report["status"] = STATUS_IDEMPOTENT
        report["writer_response"] = ledger[key]
        report["reasons"].append(
            "idempotency key already admitted; duplicate promotion suppressed"
        )
        report["evidence"].append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "idempotency key already present in the caller ledger; no writer call",
            )
        )
        return _finalize(report)

    if plan.get("replay"):
        report["status"] = STATUS_IDEMPOTENT
        report["reasons"].append(
            "existing canonical version already holds the same content hash; "
            "no new version"
        )
        report["evidence"].append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "existing canonical content_hash equals proposed content_hash; "
                "replay detected",
            )
        )
        return _finalize(report)

    if dry_run:
        report["evidence"].append(
            _evidence(
                EPISTEMIC_STATED,
                "dry-run: writer request built, no writer called and no write performed",
            )
        )
        return _finalize(report)

    if not bounded:
        report["status"] = STATUS_BLOCKED
        report["reasons"].append("blocked: " + HUMAN_GATE + " is not authorized")
        report["evidence"].append(
            _evidence(
                EPISTEMIC_STATED,
                "Human Gate not authorized; adapter refused to call the writer",
            )
        )
        return _finalize(report)

    if write_surface is None:
        report["status"] = STATUS_BLOCKED
        report["reasons"].append(
            "blocked: no simulation write surface supplied -- the adapter never "
            "creates a production write path"
        )
        return _finalize(report)

    if not is_simulation_writer(write_surface):
        report["status"] = STATUS_BLOCKED
        report["reasons"].append(
            "blocked: the supplied write surface is not an explicitly-marked "
            "simulation writer; production writers are refused"
        )
        report["evidence"].append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "unmarked / production write surface refused before any call",
            )
        )
        return _finalize(report)

    report["write_surface"] = getattr(write_surface, "__name__", "simulation_writer")
    try:
        response = write_surface(copy.deepcopy(worker_request))
    except Exception as exc:  # pragma: no cover - defensive fail-closed
        report["status"] = STATUS_BLOCKED
        report["reasons"].append(
            "simulation write surface raised: " + type(exc).__name__
        )
        return _finalize(report)

    if isinstance(ledger, MutableMapping):
        ledger[key] = {
            "version": report["proposed_version"],
            "intent_hash": report["intent_hash"],
            "simulated": True,
        }
    report["status"] = STATUS_SIMULATED
    report["writer_response"] = (
        dict(response) if isinstance(response, Mapping) else response
    )
    report["evidence"].append(
        _evidence(
            EPISTEMIC_STATED,
            "non-production simulation: delegated to "
            + str(report["reused_canonical_writer"])
            + " with a marked fake writer; canonical write remains disabled",
        )
    )
    return _finalize(report)


def promotion_adapter_matrix() -> tuple[dict[str, Any], ...]:
    """Documented adapter decision matrix (a defensive copy)."""
    rows = (
        (
            "readable, PASS / PROMOTION_ELIGIBLE, unique target (dry-run)",
            STATUS_ADAPTED,
            "worker request mapped; no writer called",
        ),
        (
            "authorized Human Gate + marked simulation writer",
            STATUS_SIMULATED,
            "in-memory fake writer called; canonical write still disabled",
        ),
        (
            "same content hash already canonical, or idempotency key admitted",
            STATUS_IDEMPOTENT,
            "no new version and no writer call",
        ),
        (
            "PASS candidate but no unique canonical target (invalid / absent)",
            STATUS_QUARANTINED,
            "prepare_promotion refuses before any writer",
        ),
        (
            "hash mismatch / incomplete capture / not PASS, unauthorized gate, "
            "no simulation surface, or a production writer",
            STATUS_BLOCKED,
            "fail-closed; production writes are never performed",
        ),
    )
    return tuple(
        {"scenario": scenario, "status": status, "outcome": outcome}
        for scenario, status, outcome in rows
    )
