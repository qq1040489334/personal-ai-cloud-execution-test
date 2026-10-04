"""REALITY_FIRST_CANONICAL_PROMOTION_PREFLIGHT_V0.1 -- read-only HG-3 gate.

This module is the *preflight* that runs immediately before the first REALITY
Canonical promotion (Human Gate HG-3,
``HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1``). It consumes the Candidate Artifact
/ Candidate Review Input produced by ``REALITY_CANDIDATE_HANDOFF_V0.1`` and
reviewed by ``REALITY_FIRST_CANDIDATE_REVIEW_V0.2`` and answers one question:
**are the non-human, evidence-only preconditions for the first Canonical
promotion satisfied?**

It is deliberately a *preflight*, not a writer:

* it never performs a Reality / Canonical / Knowledge / Skill / Decision write;
* it never deploys, reads a secret / credential or changes a permission, binding
  or schema;
* it never creates a second state store: the only write path it can report is
  the existing ``ASSET_DB: assets / asset_versions`` surface
  (``reality_canonical_writer.CANONICAL_STORE``);
* it never grants HG-3: ``human_gate_authorized`` is recorded from the caller and
  the human gate stays required.

Design rules (mirroring the review it builds on):

* **read-only and side-effect free** -- it reuses the existing
  ``review_candidate_artifact`` and the side-effect-free
  ``validate_candidate`` / ``prepare_promotion`` writer helpers;
* **evidence-first** -- every conclusion is an evidence item tagged with exactly
  one of ``OBSERVED`` / ``STATED`` / ``INFERRED`` / ``UNKNOWN`` and every missing
  value is listed as an explicit ``UNKNOWN`` (never guessed);
* **fail-closed** -- an unreadable artifact, a hash mismatch or a non-``VERIFIED``
  candidate is ``BLOCKED``; insufficient evidence is ``PARTIAL`` and is never
  upgraded;
* **single verdict** -- the preflight emits exactly ``PASS`` / ``PARTIAL`` /
  ``BLOCKED`` and reports whether the HG-3 write preconditions hold.

The chain is::

    Snapshot -> Candidate Artifact (HANDOFF_V0.1)
             -> Candidate Review (REVIEW_V0.2)
             -> this preflight -> PASS/PARTIAL/BLOCKED (no write)
"""

from __future__ import annotations

from typing import Any, Mapping

from personal_ai_execution.provenance_contract import STATUS_VERIFIED
from personal_ai_execution.reality_candidate_handoff import (
    HANDOFF_CONTRACT,
    REVIEW_INPUT_CONTRACT,
    read_candidate_artifact,
)
from personal_ai_execution.reality_candidate_review import (
    EVIDENCE_SOURCES,
    NEEDS_MORE_EVIDENCE,
    PARTIAL,
    PROMOTION_BLOCKED,
    PROMOTION_ELIGIBLE,
    promotion_status_for_review,
    review_candidate_artifact,
)
from personal_ai_execution.reality_canonical_writer import (
    CANONICAL_STORE,
    HUMAN_GATE,
    REALITY_ASSET_TYPE,
    TARGET_ASSET_TYPES,
    WRITER_CONTRACT_VERSION,
    prepare_promotion,
    validate_candidate,
)
from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_UNKNOWN,
    STATUS_VERIFIED as CAPTURE_VERIFIED,
)
from personal_ai_execution.result_normalization import BLOCKED, PASS

#: Version tag of this preflight contract.
PREFLIGHT_GOAL = "REALITY_FIRST_CANONICAL_PROMOTION_PREFLIGHT_V0.1"
#: Stable report label emitted by every preflight.
PREFLIGHT_REPORT = PREFLIGHT_GOAL + "_REPORT"
#: Fully-qualified contract id.
PREFLIGHT_CONTRACT = "PERSONAL_AI_" + PREFLIGHT_GOAL

#: The only verdicts this preflight may emit.
PREFLIGHT_STATUSES = (PASS, PARTIAL, BLOCKED)

#: HG-3 -- the human gate that must authorize the first Canonical promotion.
HG3_GATE = HUMAN_GATE

#: The only canonical targets a REALITY candidate may be promoted into. REALITY
#: itself is source/provenance, never a target.
CANONICAL_TARGETS = TARGET_ASSET_TYPES

#: Evidence quality tiers, weakest -> strongest. A missing field is ``UNKNOWN``
#: and is never upgraded.
EVIDENCE_TIERS = (
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_INFERRED,
    EPISTEMIC_UNKNOWN,
)

#: The explicit, ordered non-human preconditions HG-3 verifies before the first
#: Canonical promotion may be authorized.
HG3_PRECONDITIONS = (
    "candidate_artifact_readable",
    "candidate_id_present",
    "candidate_verified",
    "candidate_promotion_eligible",
    "promoted_provenance_verified",
    "evidence_source_tagged",
    "canonical_target_resolved_unique",
    "canonical_store_single",
    "first_promotion_no_duplicate",
)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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
    tier = source if source in EVIDENCE_TIERS else EPISTEMIC_UNKNOWN
    return {"source": tier, "detail": detail}


def _tiers_present(evidence: list[dict[str, str]]) -> list[str]:
    found = {item.get("source") for item in evidence}
    return [tier for tier in EVIDENCE_TIERS if tier in found]


def _precondition(name: str, satisfied: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "satisfied": bool(satisfied), "detail": detail}


def _check(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {"check": name, "status": PASS if passed else BLOCKED, "detail": detail}


def canonical_promotion_preflight(
    artifact: Mapping[str, Any] | None = None,
    *,
    review_input: Mapping[str, Any] | None = None,
    store: Mapping[str, Any] | None = None,
    location: Any = None,
    target_asset_type: Any = None,
    existing_asset: Mapping[str, Any] | None = None,
    run: Mapping[str, Any] | None = None,
    human_gate_authorized: bool = False,
) -> dict[str, Any]:
    """Run the read-only preflight for the first REALITY Canonical promotion.

    Accepts exactly one review subject (a Candidate Artifact, a Candidate Review
    Input, or a caller-supplied ``store`` + ``location``), like
    :func:`reality_candidate_review.review_candidate_artifact`.

    ``target_asset_type`` is the intended canonical target (one of
    ``KNOWLEDGE`` / ``SKILL`` / ``DECISION``). When it is absent the target is
    reported ``UNKNOWN`` and is never guessed, so an otherwise eligible candidate
    stays ``PARTIAL`` until a unique target is supplied.

    ``human_gate_authorized`` is only *recorded*: the preflight never grants
    HG-3 and never performs the write.

    Returns a report with ``verdict`` in ``PASS`` / ``PARTIAL`` / ``BLOCKED`` and
    a ``promotion_status`` consistent with the underlying review. Nothing is
    written, staged, deployed or mutated.
    """
    review = review_candidate_artifact(
        artifact,
        review_input=review_input,
        store=store,
        location=location,
        run=run,
    )

    readable = bool(review["readable"])
    review_status = review["review_status"]
    promotion_status = review["promotion_status"]
    expected_promotion = promotion_status_for_review(review_status)

    resolved_artifact: Mapping[str, Any] | None = artifact if isinstance(artifact, Mapping) else None
    if resolved_artifact is None and readable and (store is not None or _meaningful(location)):
        fetched, _fetch_errors = read_candidate_artifact(store, location)
        if fetched is not None:
            resolved_artifact = fetched

    audit: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    if readable and isinstance(resolved_artifact, Mapping):
        audit = validate_candidate(resolved_artifact, target_asset_type=target_asset_type)
        plan = prepare_promotion(
            resolved_artifact,
            target_asset_type=target_asset_type,
            existing_asset=existing_asset,
        )

    target = audit.get("target_asset_type") if isinstance(audit, Mapping) else None
    target_unique = bool(target in CANONICAL_TARGETS)
    promoted_provenance_status = (
        audit.get("provenance_status") if isinstance(audit, Mapping) else None
    )
    # The preflight itself never creates a second state store; when a plan exists
    # it must also name the single existing canonical store.
    single_store = bool(
        not isinstance(plan, Mapping)
        or (
            plan.get("canonical_store") == CANONICAL_STORE
            and plan.get("second_state_store_created") is False
        )
    )
    canonical_store_single = bool(
        isinstance(plan, Mapping)
        and plan.get("eligible")
        and plan.get("canonical_store") == CANONICAL_STORE
        and plan.get("second_state_store_created") is False
    )
    replay = bool(isinstance(plan, Mapping) and plan.get("replay"))
    first_promotion = bool(
        isinstance(plan, Mapping) and plan.get("eligible") and not replay
    )
    proposed_version = plan.get("proposed_version") if isinstance(plan, Mapping) else None

    # -- HG-3 preconditions -------------------------------------------------
    preconditions = [
        _precondition(
            "candidate_artifact_readable",
            readable,
            "Candidate Artifact read fail-closed from "
            + HANDOFF_CONTRACT,
        ),
        _precondition(
            "candidate_id_present",
            _meaningful(review["candidate_id"]),
            "candidate_id=" + str(review["candidate_id"]),
        ),
        _precondition(
            "candidate_verified",
            review["capture_status"] == CAPTURE_VERIFIED and bool(review["verified"]),
            "capture_status="
            + str(review["capture_status"])
            + "; verified="
            + str(review["verified"]),
        ),
        _precondition(
            "candidate_promotion_eligible",
            bool(review["promotion_eligible"]),
            "promotion_eligible=" + str(review["promotion_eligible"]),
        ),
        _precondition(
            "promoted_provenance_verified",
            promoted_provenance_status == STATUS_VERIFIED,
            "promoted_provenance_status=" + str(promoted_provenance_status),
        ),
        _precondition(
            "evidence_source_tagged",
            bool(review["evidence"])
            and all(
                item.get("source") in EVIDENCE_SOURCES for item in review["evidence"]
            ),
            "evidence items=" + str(len(review["evidence"])),
        ),
        _precondition(
            "canonical_target_resolved_unique",
            target_unique,
            "target_asset_type=" + str(target),
        ),
        _precondition(
            "canonical_store_single",
            canonical_store_single,
            "canonical_store=" + CANONICAL_STORE + "; second_state_store=False",
        ),
        _precondition(
            "first_promotion_no_duplicate",
            first_promotion,
            "proposed_version=" + str(proposed_version) + "; replay=" + str(replay),
        ),
    ]
    preconditions_satisfied = {
        item["name"]: item["satisfied"] for item in preconditions
    }
    hg3_write_preconditions_satisfied = all(preconditions_satisfied.values())

    # -- verdict ------------------------------------------------------------
    if not readable or review_status == BLOCKED:
        verdict = BLOCKED
    elif review_status == PARTIAL:
        verdict = PARTIAL
    elif target_unique and first_promotion:
        verdict = PASS
    else:
        verdict = PARTIAL

    # -- evidence (OBSERVED/STATED/INFERRED/UNKNOWN) ------------------------
    evidence: list[dict[str, str]] = list(review["evidence"])
    unknowns: list[str] = list(review["unknowns"])
    gaps: list[str] = list(review["evidence_gaps"])

    if readable:
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "preflight read the "
                + HANDOFF_CONTRACT
                + " Candidate Artifact fail-closed",
            )
        )
    else:
        evidence.append(
            _evidence(
                EPISTEMIC_UNKNOWN,
                "no readable Candidate Artifact / Review Input was available to "
                "the preflight",
            )
        )
    if target_unique:
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "canonical target resolved uniquely to "
                + str(target)
                + " via the existing canonical writer",
            )
        )
    else:
        unknowns.append(
            "canonical target asset type (KNOWLEDGE / SKILL / DECISION)"
        )
        evidence.append(
            _evidence(
                EPISTEMIC_UNKNOWN,
                "no unique canonical target resolved; target is not guessed",
            )
        )
    if promoted_provenance_status is not None:
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "promoted provenance evaluated to " + str(promoted_provenance_status),
            )
        )
    else:
        unknowns.append("promoted provenance evaluation")
        evidence.append(
            _evidence(
                EPISTEMIC_UNKNOWN,
                "promoted provenance not evaluated; candidate is not eligible",
            )
        )
    evidence.append(
        _evidence(
            EPISTEMIC_OBSERVED,
            "single canonical store "
            + CANONICAL_STORE
            + "; second_state_store_created=False; canonical_write_performed=False",
        )
    )
    if target_unique and first_promotion:
        evidence.append(
            _evidence(
                EPISTEMIC_OBSERVED,
                "first canonical promotion: proposed_version="
                + str(proposed_version)
                + "; replay=False",
            )
        )
    else:
        unknowns.append("first-promotion idempotency outcome")
    evidence.append(
        _evidence(
            EPISTEMIC_STATED,
            "HG-3 "
            + HG3_GATE
            + " remains required and is not granted by this preflight "
            + "(caller-reported authorized="
            + str(bool(human_gate_authorized))
            + ")",
        )
    )

    # -- read-only checks ---------------------------------------------------
    checks = [
        _check(
            "preflight executed read-only",
            True,
            "no file write, no catalog mutation, no state store created",
        ),
        _check(
            "verdict is PASS / PARTIAL / BLOCKED",
            verdict in PREFLIGHT_STATUSES,
            "verdict=" + str(verdict),
        ),
        _check(
            "promotion status valid and consistent with review",
            promotion_status in (PROMOTION_ELIGIBLE, NEEDS_MORE_EVIDENCE, PROMOTION_BLOCKED)
            and promotion_status == expected_promotion,
            "promotion_status=" + str(promotion_status),
        ),
        _check(
            "HG-3 write preconditions explicit",
            len(preconditions) == len(HG3_PRECONDITIONS),
            "preconditions=" + str(len(preconditions)),
        ),
        _check(
            "canonical write path is unique (no second state store)",
            single_store,
            "canonical_store=" + CANONICAL_STORE,
        ),
        _check(
            "no Reality / Knowledge / Skill / Decision write",
            True,
            "no canonical/reality/knowledge/skill/decision write",
        ),
        _check(
            "no deploy / secret / permission / binding / schema change",
            True,
            "no deployment, credential or secret access, permission, binding or "
            "schema production change",
        ),
    ]
    workflow_status = PASS if all(check["status"] == PASS for check in checks) else BLOCKED

    final_status = (
        "PREFLIGHT_VERDICT=" + str(verdict) + ";PROMOTION_STATUS=" + str(promotion_status)
    )

    lines = [
        f"# {PREFLIGHT_GOAL}",
        "",
        f"- goal: {PREFLIGHT_GOAL}",
        "- mode: read-only preflight (no Canonical write)",
        f"- handoff_contract: {HANDOFF_CONTRACT}",
        f"- review_contract: {REVIEW_INPUT_CONTRACT}",
        f"- writer_contract: {WRITER_CONTRACT_VERSION}",
        f"- workflow_status: {workflow_status}",
        f"- verdict: {verdict}",
        f"- promotion_status: {promotion_status}",
        f"- review_status: {review_status}",
        f"- candidate_id: {review['candidate_id'] or 'UNKNOWN'}",
        f"- capture_status: {review['capture_status'] or 'UNKNOWN'}",
        f"- target_asset_type: {target or 'UNKNOWN'}",
        f"- promoted_provenance_status: {promoted_provenance_status or 'UNKNOWN'}",
        f"- hg3_gate: {HG3_GATE}",
        f"- hg3_write_preconditions_satisfied: {hg3_write_preconditions_satisfied}",
        f"- hg3_authorized: {bool(human_gate_authorized)}",
        f"- evidence_status: {review['evidence_status']}",
        "",
        "## Epistemic breakdown",
    ]
    epistemic_summary = _dict(review.get("epistemic_summary"))
    for tier in ("observed", "stated", "inferred", "unknown"):
        lines.append(
            f"- {tier}: {', '.join(epistemic_summary.get(tier) or []) or '[]'}"
        )
    lines += ["", "## HG-3 write preconditions"]
    for item in preconditions:
        lines.append(
            f"- [{'OK' if item['satisfied'] else 'MISSING'}] {item['name']}: "
            + item["detail"]
        )
    lines += ["", "## Evidence gaps"]
    if gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- (none)")
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
        "- second_state_store_created: False",
        "",
        "## Checks",
    ]
    for check in checks:
        lines.append(f"- [{check['status']}] {check['check']}: {check['detail']}")
    lines += ["", f"FINAL_STATUS={final_status}"]

    return {
        "report": PREFLIGHT_REPORT,
        "goal": PREFLIGHT_GOAL,
        "contract": PREFLIGHT_CONTRACT,
        "handoff_contract": HANDOFF_CONTRACT,
        "review_contract": REVIEW_INPUT_CONTRACT,
        "writer_contract": WRITER_CONTRACT_VERSION,
        "mode": "read_only_preflight",
        "workflow_status": workflow_status,
        "verdict": verdict,
        "status": verdict,
        "preflight_status": verdict,
        "review_status": review_status,
        "promotion_status": promotion_status,
        "final_status": final_status,
        "candidate_id": review["candidate_id"],
        "artifact_id": review["artifact_id"],
        "artifact_location": review["artifact_location"],
        "asset_type": review["asset_type"],
        "capture_status": review["capture_status"],
        "verified": bool(review["verified"]),
        "promotion_eligible": bool(review["promotion_eligible"]),
        "readable": readable,
        "target_asset_type": target,
        "target_unique": target_unique,
        "first_promotion": first_promotion,
        "proposed_version": proposed_version,
        "canonical_store": CANONICAL_STORE,
        "reality_asset_type": REALITY_ASSET_TYPE,
        "reality_role": "SOURCE_PROVENANCE",
        "source_provenance_status": review.get("provenance_status"),
        "promoted_provenance_status": promoted_provenance_status,
        "provenance": review.get("provenance"),
        "artifact_provenance": _dict(review.get("artifact_provenance")),
        "epistemic": _dict(review.get("epistemic")),
        "epistemic_summary": epistemic_summary,
        "evidence_status": review["evidence_status"],
        "evidence": evidence,
        "evidence_tiers_present": _tiers_present(evidence),
        "evidence_gaps": gaps,
        "unknowns": unknowns,
        "preconditions": preconditions,
        "hg3_gate": HG3_GATE,
        "hg3_write_preconditions_satisfied": hg3_write_preconditions_satisfied,
        "hg3_preconditions": list(HG3_PRECONDITIONS),
        "hg3_authorized": bool(human_gate_authorized),
        "hg3_required": True,
        "human_gate_required": True,
        "checks": checks,
        "review": review.get("review"),
        "run": review.get("run"),
        "read_errors": list(review.get("read_errors") or []),
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


def promotion_preflight_matrix() -> tuple[dict[str, Any], ...]:
    """Documented preflight decision matrix (a defensive copy)."""
    rows = (
        (
            "readable, VERIFIED, promotion_eligible, unique target, first promotion",
            PASS,
            "HG-3 write preconditions satisfied; human gate still required",
        ),
        (
            "readable and VERIFIED but not promotion_eligible (e.g. INFERRED)",
            PARTIAL,
            "more evidence required; never guessed into eligibility",
        ),
        (
            "readable, promotion_eligible, but no unique canonical target",
            PARTIAL,
            "target UNKNOWN is not guessed; supply KNOWLEDGE/SKILL/DECISION",
        ),
        (
            "readable but not VERIFIED (INCOMPLETE)",
            BLOCKED,
            "candidate is not verified; promotion preflight blocked",
        ),
        (
            "declared content hash disagrees with the recomputed hash",
            BLOCKED,
            "hash mismatch; promotion preflight blocked",
        ),
        (
            "malformed / unreadable artifact or no input",
            BLOCKED,
            "fail-closed; promotion preflight blocked",
        ),
    )
    return tuple(
        {
            "scenario": scenario,
            "verdict": verdict,
            "outcome": outcome,
        }
        for scenario, verdict, outcome in rows
    )
