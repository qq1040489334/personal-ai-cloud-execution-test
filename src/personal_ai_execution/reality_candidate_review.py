"""REALITY_FIRST_CANDIDATE_REVIEW_V0.2 -- read-only review of a Candidate Artifact.

This module is the *review* half of the reality-first chain. It consumes the
**Candidate Artifact** and/or the **Candidate Review Input** produced by
``REALITY_CANDIDATE_HANDOFF_V0.1`` and returns an advisory review verdict plus a
promotion status. It never writes Reality Canonical, Knowledge, Skill or Decision
state and never deploys, reads a secret / credential or changes a permission,
binding or schema.

Design rules (mirroring the handoff contract it builds on):

* **read-only and advisory** -- the review is never auto-approved and never calls
  ``mark_reviewed``;
* **fail-closed** -- an unreadable artifact, a hash mismatch or a non-``VERIFIED``
  candidate is ``BLOCKED`` / ``PROMOTION_BLOCKED``; insufficient evidence is
  ``PARTIAL`` / ``NEEDS_MORE_EVIDENCE`` and is never guessed into eligibility;
* **evidence-first** -- every conclusion is an evidence item tagged with exactly
  one of ``OBSERVED`` / ``STATED`` / ``INFERRED`` / ``UNKNOWN``;
* **consistent** -- ``promotion_status`` is a pure function of ``review_status``
  (see :func:`promotion_status_for_review`) and the recorded evidence gaps.

The chain is::

    Snapshot -> Candidate artifact (HANDOFF_V0.1)
             -> Candidate Review input (HANDOFF_V0.1)
             -> this read-only review -> advisory verdict + promotion status

Nothing here resolves a production path, opens a store, mutates the input or
creates a second state store.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from personal_ai_execution.provenance_contract import evaluate_provenance
from personal_ai_execution.reality_candidate_handoff import (
    HANDOFF_CONTRACT,
    REVIEW_INPUT_CONTRACT,
    candidate_artifact_to_review_input,
    read_candidate_artifact,
    validate_candidate_artifact,
    validate_review_input,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_UNKNOWN,
    REQUIRED_CAPTURE_FIELDS,
    STATUS_HASH_MISMATCH,
    STATUS_VERIFIED,
)
from personal_ai_execution.result_normalization import BLOCKED, FAIL, PASS

#: Version tag of this review contract.
REVIEW_GOAL = "REALITY_FIRST_CANDIDATE_REVIEW_V0.2"
#: Stable report label emitted by every review.
REVIEW_REPORT = "REALITY_FIRST_CANDIDATE_REVIEW_V0.2_REPORT"
#: Fully-qualified contract id.
REVIEW_CONTRACT = "PERSONAL_AI_REALITY_FIRST_CANDIDATE_REVIEW_V0.2"

#: The only review verdicts this reviewer may emit.
PARTIAL = "PARTIAL"
REVIEW_STATUSES = (PASS, PARTIAL, BLOCKED)

#: Promotion statuses. ``promotion_status`` is always consistent with the review
#: verdict -- see :func:`promotion_status_for_review`.
PROMOTION_ELIGIBLE = "PROMOTION_ELIGIBLE"
PROMOTION_BLOCKED = "PROMOTION_BLOCKED"
NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
PROMOTION_STATUSES = (
    PROMOTION_ELIGIBLE,
    PROMOTION_BLOCKED,
    NEEDS_MORE_EVIDENCE,
)

#: Evidence quality tiers, weakest -> strongest. A missing field is ``UNKNOWN``
#: and is never upgraded.
EVIDENCE_TIERS = (
    EPISTEMIC_UNKNOWN,
    EPISTEMIC_INFERRED,
    EPISTEMIC_STATED,
    EPISTEMIC_OBSERVED,
)
EVIDENCE_SOURCES = EVIDENCE_TIERS
_EVIDENCE_ORDER = {tier: index for index, tier in enumerate(EVIDENCE_TIERS)}

#: Optional live-run metadata the reviewer can cite. Its absence is recorded as
#: an evidence gap, never fabricated.
REVIEW_RUN_FIELDS = (
    "run_id",
    "reader_version",
    "source_db",
    "window_start",
    "window_end",
    "produced_at",
)

#: How the review subject reached :func:`review_candidate_artifact`.
INPUT_ARTIFACT = "CANDIDATE_ARTIFACT"
INPUT_REVIEW_INPUT = "CANDIDATE_REVIEW_INPUT"
INPUT_ARTIFACT_FROM_STORE = "CANDIDATE_ARTIFACT_FROM_STORE"
INPUT_NONE = "NO_INPUT"


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _evidence(source: str, detail: str) -> dict[str, str]:
    """Build a source-tagged evidence item (only the four tiers are allowed)."""
    tier = source if source in _EVIDENCE_ORDER else EPISTEMIC_UNKNOWN
    return {"source": tier, "detail": detail}


def _weakest(tiers: Any) -> str:
    values = [tier for tier in tiers if tier in _EVIDENCE_ORDER]
    if not values:
        return EPISTEMIC_UNKNOWN
    return min(values, key=lambda tier: _EVIDENCE_ORDER[tier])


def promotion_status_for_review(review_status: Any) -> str:
    """Return the promotion status implied by a review verdict, fail-closed."""
    return {
        PASS: PROMOTION_ELIGIBLE,
        PARTIAL: NEEDS_MORE_EVIDENCE,
        BLOCKED: PROMOTION_BLOCKED,
    }.get(review_status, PROMOTION_BLOCKED)


def _run_metadata(run: Any) -> dict[str, Any]:
    record = run if isinstance(run, Mapping) else {}
    return {
        "run_id": _text(record.get("run_id")),
        "reader_version": _text(record.get("reader_version")),
        "source_db": _text(record.get("source_db")),
        "window_start": _text(record.get("window_start")),
        "window_end": _text(record.get("window_end")),
        "produced_at": _text(record.get("produced_at")),
        "source_class": _text(record.get("source_class")),
    }


def _summary_from_epistemic(epistemic: Mapping[str, Any]) -> dict[str, list[str]]:
    summary: dict[str, list[str]] = {
        "observed": [],
        "stated": [],
        "inferred": [],
        "unknown": [],
    }
    buckets = {
        EPISTEMIC_OBSERVED: "observed",
        EPISTEMIC_STATED: "stated",
        EPISTEMIC_INFERRED: "inferred",
        EPISTEMIC_UNKNOWN: "unknown",
    }
    for field in sorted(epistemic):
        bucket = buckets.get(epistemic[field])
        if bucket is not None:
            summary[bucket].append(field)
    return summary


def _view_from_artifact(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    """Build the internal review view from a Candidate Artifact, read-only."""
    validation = validate_candidate_artifact(artifact)
    review_input = candidate_artifact_to_review_input(artifact)
    review = _dict(review_input.get("review"))
    source = artifact if isinstance(artifact, Mapping) else {}

    candidate = source.get("candidate")
    content_present: bool | None = None
    if isinstance(candidate, Mapping):
        content_present = _meaningful(candidate.get("content"))

    provenance_block = source.get("provenance")
    if not isinstance(provenance_block, Mapping):
        provenance_block = None

    return {
        "kind": INPUT_ARTIFACT,
        "readable": bool(validation["ok"]),
        "validation_reasons": list(validation["reasons"]),
        "candidate_id": source.get("candidate_id"),
        "artifact_id": source.get("artifact_id"),
        "artifact_location": source.get("artifact_location"),
        "asset_type": source.get("asset_type"),
        "capture_status": source.get("status"),
        "verified": bool(source.get("verified")),
        "promotion_eligible": bool(source.get("promotion_eligible")),
        "missing": list(source.get("missing") or []),
        "invalid": list(source.get("invalid") or []),
        "hash_match": source.get("hash_match"),
        "content_hash": source.get("content_hash"),
        "epistemic": _dict(source.get("epistemic")),
        "epistemic_summary": _dict(source.get("epistemic_summary")),
        "artifact_provenance": _dict(source.get("artifact_provenance")),
        "provenance": dict(provenance_block) if provenance_block is not None else None,
        "provenance_completeness": _dict(source.get("provenance_completeness")),
        "content_present": content_present,
        "review": review,
        "review_input": review_input,
    }


def _view_from_review_input(review_input: Mapping[str, Any] | None) -> dict[str, Any]:
    """Build the internal review view from a Candidate Review Input."""
    validation = validate_review_input(review_input)
    source = review_input if isinstance(review_input, Mapping) else {}
    epistemic = _dict(source.get("epistemic"))
    provenance_block = source.get("provenance")
    if not isinstance(provenance_block, Mapping):
        provenance_block = None

    return {
        "kind": INPUT_REVIEW_INPUT,
        "readable": bool(validation["ok"] and source.get("readable")),
        "validation_reasons": list(validation["reasons"]),
        "candidate_id": source.get("candidate_id"),
        "artifact_id": source.get("artifact_id"),
        "artifact_location": source.get("artifact_location"),
        "asset_type": source.get("asset_type"),
        "capture_status": source.get("status"),
        "verified": bool(source.get("verified")),
        "promotion_eligible": bool(source.get("promotion_eligible")),
        "missing": list(source.get("missing") or []),
        "invalid": [],
        "hash_match": source.get("hash_match"),
        "content_hash": source.get("content_hash"),
        "epistemic": epistemic,
        "epistemic_summary": _summary_from_epistemic(epistemic),
        "artifact_provenance": _dict(source.get("artifact_provenance")),
        "provenance": dict(provenance_block) if provenance_block is not None else None,
        "provenance_completeness": evaluate_provenance(
            provenance_block if provenance_block is not None else {}
        ),
        "content_present": None,
        "review": _dict(source.get("review")),
        "review_input": dict(source),
    }


def _resolve_view(
    artifact: Mapping[str, Any] | None,
    review_input: Mapping[str, Any] | None,
    store: MutableMapping[str, Any] | None,
    location: Any,
) -> tuple[dict[str, Any] | None, str, list[str]]:
    if artifact is not None:
        return _view_from_artifact(artifact), INPUT_ARTIFACT, []
    if review_input is not None:
        return _view_from_review_input(review_input), INPUT_REVIEW_INPUT, []
    if store is not None or _meaningful(location):
        resolved, errors = read_candidate_artifact(store, location)
        if resolved is None:
            return None, INPUT_NONE, list(errors)
        return _view_from_artifact(resolved), INPUT_ARTIFACT_FROM_STORE, []
    return None, INPUT_NONE, []


def _blocked_report(
    *,
    input_kind: str,
    read_errors: list[str],
    run_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail-closed report when no readable Candidate Artifact is available."""
    evidence: list[dict[str, str]] = []
    gaps: list[str] = []
    unknowns: list[str] = []

    gaps.append(
        "no readable Candidate Artifact / Review Input was supplied to the review"
    )
    unknowns.append("candidate identity, provenance and epistemic breakdown")
    if read_errors:
        for error in read_errors:
            gaps.append("candidate artifact could not be read: " + str(error))
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "attempted a fail-closed read of the Candidate Artifact and "
                "observed no readable artifact",
            )
        )
    evidence.append(
        _evidence(
            EPISTEMIC_UNKNOWN,
            "no candidate evidence is observable; promotion cannot be assessed",
        )
    )
    return _finalize_report(
        input_kind=input_kind,
        view=None,
        read_errors=read_errors,
        run_meta=run_meta,
        evidence=evidence,
        gaps=gaps,
        unknowns=unknowns,
        review_status=BLOCKED,
        promotion_status=PROMOTION_BLOCKED,
        provenance_status=None,
        evidence_status=EPISTEMIC_UNKNOWN,
    )


def _finalize_report(
    *,
    input_kind: str,
    view: Mapping[str, Any] | None,
    read_errors: list[str],
    run_meta: Mapping[str, Any],
    evidence: list[dict[str, str]],
    gaps: list[str],
    unknowns: list[str],
    review_status: str,
    promotion_status: str,
    provenance_status: Any,
    evidence_status: str,
) -> dict[str, Any]:
    subject = view if isinstance(view, Mapping) else {}
    review = _dict(subject.get("review"))
    provenance_block = subject.get("provenance")
    if not isinstance(provenance_block, Mapping) or not provenance_block:
        provenance_block = _dict(subject.get("artifact_provenance")) or None
    promotion_eligible = bool(
        review_status == PASS and subject.get("promotion_eligible")
    )
    expected_promotion = promotion_status_for_review(review_status)

    checks = [
        {
            "check": "review executed read-only",
            "status": PASS,
            "detail": "advisory review; no file write, no catalog mutation",
        },
        {
            "check": "review status is PASS / PARTIAL / BLOCKED",
            "status": PASS if review_status in REVIEW_STATUSES else FAIL,
            "detail": f"review_status={review_status}",
        },
        {
            "check": "promotion status is valid and consistent with review",
            "status": (
                PASS
                if promotion_status in PROMOTION_STATUSES
                and promotion_status == expected_promotion
                else FAIL
            ),
            "detail": f"promotion_status={promotion_status}",
        },
        {
            "check": "evidence gaps explicit when promotion is not eligible",
            "status": (
                PASS
                if promotion_status == PROMOTION_ELIGIBLE or bool(gaps)
                else FAIL
            ),
            "detail": f"evidence_gaps={len(gaps)}",
        },
        {
            "check": "evidence items carry OBSERVED/STATED/INFERRED/UNKNOWN tags",
            "status": (
                PASS
                if evidence and all(item["source"] in EVIDENCE_SOURCES for item in evidence)
                else FAIL
            ),
            "detail": "every evidence item is source-tagged",
        },
        {
            "check": "no Reality Canonical / Knowledge / Skill / Decision write",
            "status": PASS,
            "detail": (
                "no canonical/reality/knowledge/skill/decision write and no "
                "second state store"
            ),
        },
        {
            "check": "no deploy / secret / permission / binding / schema change",
            "status": PASS,
            "detail": (
                "no deployment, credential or secret access, permission, "
                "binding or schema production change"
            ),
        },
    ]
    workflow_status = (
        PASS if all(check["status"] == PASS for check in checks) else FAIL
    )

    final_status = (
        f"REVIEW_STATUS={review_status};PROMOTION_STATUS={promotion_status}"
    )

    lines = [
        f"# {REVIEW_GOAL}",
        "",
        f"- goal: {REVIEW_GOAL}",
        "- mode: read-only/advisory review",
        f"- handoff_contract: {HANDOFF_CONTRACT}",
        f"- input: {input_kind}",
        f"- workflow_status: {workflow_status}",
        f"- review_status: {review_status}",
        f"- promotion_status: {promotion_status}",
        f"- candidate_id: {subject.get('candidate_id') or 'UNKNOWN'}",
        f"- capture_status: {subject.get('capture_status') or 'UNKNOWN'}",
        f"- provenance_status: {provenance_status or 'UNKNOWN'}",
        f"- evidence_status: {evidence_status}",
        "",
        "## Epistemic breakdown",
    ]
    epistemic_summary = _dict(subject.get("epistemic_summary"))
    for tier in ("observed", "stated", "inferred", "unknown"):
        lines.append(
            f"- {tier}: {', '.join(epistemic_summary.get(tier) or []) or '[]'}"
        )
    lines += ["", "## Evidence gaps"]
    if gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- (none; promotion eligible)")
    lines += ["", "## Unknowns"]
    if unknowns:
        for item in unknowns:
            lines.append(f"- {item}")
    else:
        lines.append("- (none recorded)")
    lines += ["", "## Evidence"]
    for item in evidence:
        lines.append(f"- [{item['source']}] {item['detail']}")
    lines += [
        "",
        "## No-mutation statement",
        "- production_mutated: False",
        "- deployment_performed: False",
        "- credentials_accessed: False",
        "- secret_accessed: False",
        "- permissions_changed: False",
        "- binding_changed: False",
        "- schema_changed: False",
        "- reality_canonical_written: False",
        "- knowledge_written: False",
        "- skill_written: False",
        "- decision_written: False",
        "",
        "## Checks",
    ]
    for check in checks:
        lines.append(f"- [{check['status']}] {check['check']}: {check['detail']}")
    lines += ["", f"FINAL_STATUS={final_status}"]

    return {
        "report": REVIEW_REPORT,
        "goal": REVIEW_GOAL,
        "contract": REVIEW_CONTRACT,
        "handoff_contract": HANDOFF_CONTRACT,
        "review_input_contract": REVIEW_INPUT_CONTRACT,
        "mode": "read_only_advisory_review",
        "input": input_kind,
        "workflow_status": workflow_status,
        "status": workflow_status,
        "review_status": review_status,
        "promotion_status": promotion_status,
        "promotion_eligible": promotion_eligible,
        "final_status": final_status,
        "candidate_id": subject.get("candidate_id"),
        "artifact_id": subject.get("artifact_id"),
        "artifact_location": subject.get("artifact_location"),
        "asset_type": subject.get("asset_type"),
        "capture_status": subject.get("capture_status"),
        "verified": bool(subject.get("verified")),
        "readable": bool(subject.get("readable")),
        "provenance": dict(provenance_block) if provenance_block is not None else None,
        "artifact_provenance": _dict(subject.get("artifact_provenance")),
        "provenance_status": provenance_status,
        "epistemic": _dict(subject.get("epistemic")),
        "epistemic_summary": epistemic_summary,
        "evidence_status": evidence_status,
        "evidence": evidence,
        "evidence_gaps": gaps,
        "unknowns": unknowns,
        "review": review,
        "read_errors": list(read_errors),
        "run": dict(run_meta),
        "run_fields_present": [
            field for field in REVIEW_RUN_FIELDS if run_meta.get(field)
        ],
        "run_fields_absent": [
            field for field in REVIEW_RUN_FIELDS if not run_meta.get(field)
        ],
        "checks": checks,
        "content_exposed": False,
        "message_content_exposed": False,
        "read_only": True,
        "write_performed": False,
        "production_write_performed": False,
        "canonical_write_performed": False,
        "reality_written": False,
        "reality_canonical_written": False,
        "canonical_written": False,
        "knowledge_written": False,
        "skill_written": False,
        "decision_written": False,
        "deployment_performed": False,
        "credentials_accessed": False,
        "secret_accessed": False,
        "permissions_changed": False,
        "binding_changed": False,
        "schema_changed": False,
        "mark_reviewed_called": False,
        "second_state_store_created": False,
        "markdown": "\n".join(lines),
    }


def review_candidate_artifact(
    artifact: Mapping[str, Any] | None = None,
    *,
    review_input: Mapping[str, Any] | None = None,
    store: MutableMapping[str, Any] | None = None,
    location: Any = None,
    run: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Review a handoff Candidate Artifact / Review Input, read-only.

    Accepts exactly one of:

    * a Candidate Artifact mapping (HANDOFF_V0.1);
    * a Candidate Review Input mapping (HANDOFF_V0.1);
    * a ``store`` + ``location`` from which the artifact is read fail-closed.

    Returns an advisory report with ``review_status`` in
    ``PASS`` / ``PARTIAL`` / ``BLOCKED`` and a ``promotion_status`` in
    ``PROMOTION_ELIGIBLE`` / ``PROMOTION_BLOCKED`` / ``NEEDS_MORE_EVIDENCE`` that
    is always consistent with the review verdict. When no readable artifact is
    present the review fails closed: ``BLOCKED`` / ``PROMOTION_BLOCKED`` with the
    evidence gaps made explicit and nothing guessed. Nothing is written, staged,
    deployed or mutated.
    """
    run_meta = _run_metadata(run)
    evidence: list[dict[str, str]] = []
    unknowns: list[str] = []
    gaps: list[str] = []

    view, input_kind, read_errors = _resolve_view(artifact, review_input, store, location)

    for field in REVIEW_RUN_FIELDS:
        value = run_meta.get(field)
        if value:
            evidence.append(
                _evidence(
                    EPISTEMIC_OBSERVED,
                    f"live-run metadata cited for review: {field}={value}",
                )
            )
        else:
            unknowns.append(f"live-run {field}")

    if view is None:
        return _blocked_report(
            input_kind=input_kind,
            read_errors=read_errors,
            run_meta=run_meta,
        )

    evidence.append(
        _evidence(
            EPISTEMIC_OBSERVED,
            "read the " + view["kind"] + " produced by " + HANDOFF_CONTRACT,
        )
    )
    evidence.append(
        _evidence(
            EPISTEMIC_OBSERVED,
            "capture status="
            + str(view.get("capture_status"))
            + "; verified="
            + str(view.get("verified"))
            + "; promotion_eligible="
            + str(view.get("promotion_eligible")),
        )
    )

    for field in REQUIRED_CAPTURE_FIELDS:
        tag = view["epistemic"].get(field)
        if field in view["missing"]:
            gaps.append(f"required field {field!r} is missing")
            unknowns.append(f"required field {field!r} value")
        elif field in view["invalid"]:
            gaps.append(
                f"required field {field!r} has an unrecognized epistemic status"
            )
            unknowns.append(f"required field {field!r} epistemic status")
        elif tag != EPISTEMIC_OBSERVED:
            gaps.append(
                f"required field {field!r} is {tag or EPISTEMIC_UNKNOWN}, not "
                f"{EPISTEMIC_OBSERVED}"
            )

    if view.get("content_present") is False:
        gaps.append("candidate has no reusable content payload (no semantic value)")
    elif view.get("content_present") is None:
        unknowns.append("candidate content payload (not carried by the review input)")

    if view.get("capture_status") == STATUS_HASH_MISMATCH or view.get("hash_match") is False:
        gaps.append(
            "declared content_hash disagrees with the recomputed content hash"
        )

    epistemic_evidence_tier = (
        EPISTEMIC_OBSERVED
        if view["epistemic_summary"].get("observed")
        else EPISTEMIC_UNKNOWN
    )
    evidence.append(
        _evidence(
            epistemic_evidence_tier,
            "epistemic breakdown observed="
            + str(view["epistemic_summary"].get("observed") or [])
            + "; stated="
            + str(view["epistemic_summary"].get("stated") or [])
            + "; inferred="
            + str(view["epistemic_summary"].get("inferred") or [])
            + "; unknown="
            + str(view["epistemic_summary"].get("unknown") or []),
        )
    )

    provenance_status = view["provenance_completeness"].get("status")
    if view["artifact_provenance"]:
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "artifact provenance contract="
                + str(view["artifact_provenance"].get("handoff_contract"))
                + "; capture_contract="
                + str(view["artifact_provenance"].get("capture_contract"))
                + "; source_identity="
                + str(view["artifact_provenance"].get("source_identity"))
                + "; provenance_status="
                + str(provenance_status),
            )
        )
    else:
        unknowns.append("candidate artifact provenance")

    handoff_verdict = view["review"].get("verdict")
    if not view["readable"]:
        review_status = BLOCKED
        promotion_status = PROMOTION_BLOCKED
        gaps.append(
            "candidate artifact is not readable: "
            + ("; ".join(view["validation_reasons"]) or "unknown reason")
        )
        unknowns.append("candidate identity and structural integrity")
        evidence.append(
            _evidence(
                EPISTEMIC_UNKNOWN,
                "candidate artifact failed structural validation; review blocked",
            )
        )
    elif view.get("capture_status") == STATUS_HASH_MISMATCH or view.get("hash_match") is False:
        review_status = BLOCKED
        promotion_status = PROMOTION_BLOCKED
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "candidate content hash is inconsistent; review blocked",
            )
        )
    elif handoff_verdict == FAIL:
        review_status = BLOCKED
        promotion_status = PROMOTION_BLOCKED
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "handoff review verdict FAIL; review blocked",
            )
        )
    elif not view.get("verified"):
        review_status = BLOCKED
        promotion_status = PROMOTION_BLOCKED
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "candidate capture is not VERIFIED; review blocked",
            )
        )
    elif gaps:
        review_status = PARTIAL
        promotion_status = NEEDS_MORE_EVIDENCE
        evidence.append(
            _evidence(
                EPISTEMIC_STATED,
                "candidate is VERIFIED but promotion evidence is incomplete; "
                "more evidence required before promotion",
            )
        )
    elif view.get("promotion_eligible"):
        review_status = PASS
        promotion_status = PROMOTION_ELIGIBLE
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "candidate is VERIFIED with every required field OBSERVED and a "
                "consistent provenance: promotion eligible (advisory only)",
            )
        )
    else:
        review_status = PARTIAL
        promotion_status = NEEDS_MORE_EVIDENCE
        gaps.append(
            "candidate is VERIFIED but not promotion_eligible; a human must "
            "confirm the inferred fields before any Canonical promotion"
        )
        evidence.append(
            _evidence(
                EPISTEMIC_STATED,
                "candidate is VERIFIED but not promotion_eligible; more evidence "
                "required before promotion",
            )
        )

    if view.get("content_present") is False and review_status == BLOCKED:
        unknowns.append("whether the candidate carries any reusable content")

    required_tiers = [
        view["epistemic"].get(field) or EPISTEMIC_UNKNOWN
        for field in REQUIRED_CAPTURE_FIELDS
    ]
    evidence_status = (
        EPISTEMIC_UNKNOWN if not view["readable"] else _weakest(required_tiers)
    )

    return _finalize_report(
        input_kind=input_kind,
        view=view,
        read_errors=read_errors,
        run_meta=run_meta,
        evidence=evidence,
        gaps=gaps,
        unknowns=unknowns,
        review_status=review_status,
        promotion_status=promotion_status,
        provenance_status=provenance_status,
        evidence_status=evidence_status,
    )


def reality_candidate_review_matrix() -> tuple[dict[str, Any], ...]:
    """Documented review decision matrix (a defensive copy)."""
    rows = (
        (
            "readable, VERIFIED, every required field OBSERVED, promotion eligible",
            PASS,
            PROMOTION_ELIGIBLE,
            "advisory PASS; human gate still required before promotion",
        ),
        (
            "readable, VERIFIED, but at least one required field not OBSERVED",
            PARTIAL,
            NEEDS_MORE_EVIDENCE,
            "more evidence required; never guessed into eligibility",
        ),
        (
            "readable but not VERIFIED (INCOMPLETE)",
            BLOCKED,
            PROMOTION_BLOCKED,
            "candidate is not verified; promotion blocked",
        ),
        (
            "declared content hash disagrees with the recomputed hash",
            BLOCKED,
            PROMOTION_BLOCKED,
            "hash mismatch; promotion blocked",
        ),
        (
            "malformed / unreadable artifact or no input",
            BLOCKED,
            PROMOTION_BLOCKED,
            "fail-closed; review blocked",
        ),
    )
    return tuple(
        {
            "scenario": scenario,
            "review_status": review_status,
            "promotion_status": promotion_status,
            "outcome": outcome,
        }
        for scenario, review_status, promotion_status, outcome in rows
    )
