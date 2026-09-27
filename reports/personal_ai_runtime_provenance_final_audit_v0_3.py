"""PERSONAL_AI_RUNTIME_PROVENANCE_FINAL_AUDIT_V0.3.

Task: ``cf-619649c43aa2`` (risk: LOW).

Read-only, fail-closed final audit of the production Personal AI execution
Worker provenance chain, performed *after* the authorized controlled
deployment attempt (``cf-7afde7d95cdb``). It answers, from authoritative
in-repo evidence only:

* what production deployment/version identity is declared, and whether it is
  only self-declared or independently confirmed;
* the exact canonical Git commit and ``worker/index.js`` source hash;
* whether the chain ``Git commit -> source hash -> Cloudflare
  deployment/version -> live runtime`` is ``VERIFIED``, ``PARTIAL`` or
  ``UNVERIFIED``;
* whether the recent status-contract and asset-provenance Worker changes are
  proven included in the deployed runtime, or explicitly ``BLOCKED``;
* which execution-relevant commits remain unproven, separating report-only
  documentation commits from required-but-undeployed runtime changes.

Hard invariants (mirroring the earlier V0.1/V0.2 audits):

* No production mutation of any kind. The module only reads files and runs
  ``git`` read commands. It never deploys, never reads secret values, never
  touches D1/KV, workflows or production assets.
* A relationship is never upgraded on inference. The only thing that yields
  ``VERIFIED`` is a canonical commit blob whose sha256 equals the declared
  production source hash *and* a linked Cloudflare deployment/version record.
* No live endpoint is queried by this module, so a live-verified PASS is never
  fabricated.
* ``OVERALL=PASS`` is only possible when the source-to-live-runtime
  relationship is ``VERIFIED`` and no required runtime change is unproven.
  Otherwise the verdict is ``BLOCKED`` with the exact remaining gap.

Emit the committed evidence artifacts with::

    python reports/personal_ai_runtime_provenance_final_audit_v0_3.py --write

which writes ``reports/personal_ai_runtime_provenance_final_audit_v0.3.json``
and ``RUNTIME_PROVENANCE_FINAL_AUDIT_V0.3.md``.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

GOAL = "PERSONAL_AI_RUNTIME_PROVENANCE_FINAL_AUDIT_V0.3"
TASK_ID = "cf-619649c43aa2"
REPORT_NAME = "PERSONAL_AI_RUNTIME_PROVENANCE_FINAL_AUDIT_V0.3_REPORT"

BASELINE_PATH = "worker/PRODUCTION-BASELINE.json"
CANONICAL_SOURCE = "worker/index.js"
WRANGLER_CONFIG = "worker/wrangler.toml"
DEPLOY_REPORT_PATH = "reports/production_deploy_v0.1.json"
RECOVERY_TAG = "production-recovered-3e2fed43-20260926"

JSON_ARTIFACT = "reports/personal_ai_runtime_provenance_final_audit_v0.3.json"
MARKDOWN_ARTIFACT = "RUNTIME_PROVENANCE_FINAL_AUDIT_V0.3.md"

#: Path prefixes relevant to the production execution infrastructure.
EXECUTION_PATH_PREFIXES = (
    "worker/",
    "scripts/",
    "src/personal_ai_execution/",
    ".github/workflows/",
)

#: Environment variable names that (if present) are authoritative live-runtime
#: deployment identity evidence. Only names and non-secret version strings are
#: ever read; credential values are never read or recorded.
DEPLOYMENT_VERSION_ENVS = (
    "CLOUDFLARE_DEPLOYMENT_ID",
    "LATEST_DEPLOYMENT_ID",
    "DEPLOYED_VERSION",
    "RUNTIME_VERSION",
    "PRODUCTION_VERSION",
    "CLOUDFLARE_WORKER_VERSION_ID",
    "WORKER_VERSION_ID",
)
DEPLOYMENT_COMMIT_ENVS = ("DEPLOYED_COMMIT", "RUNTIME_COMMIT", "GITHUB_SHA")
DEPLOY_CREDENTIAL_ENVS = ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_API_KEY")

#: Worker source tokens that must be present for the status contract and asset
#: provenance runtime changes to be considered included in canonical source.
STATUS_CONTRACT_TOKENS = (
    "EXECUTION_STATUS_PENDING",
    "EXECUTION_STATUS_PASS",
    "EXECUTION_STATUS_FAIL",
    "EXECUTION_STATUS_BLOCKED",
    "WORKFLOW_CONCLUSION_STATUS",
    "TERMINAL_EXECUTION_STATUSES",
    "normalized_status",
    "execution_status",
    "review_verdict",
    "persistTerminalExecution",
)
ASSET_PROVENANCE_TOKENS = (
    "ASSET_PROVENANCE_CONTRACT",
    "evaluateAssetProvenance",
    "provenance_status",
    "provenance_missing",
    "search_assets",
)

RELATIONSHIP_VERIFIED = "VERIFIED"
RELATIONSHIP_PARTIAL = "PARTIAL"
RELATIONSHIP_UNVERIFIED = "UNVERIFIED"
RELATIONSHIP_STATUSES = (
    RELATIONSHIP_VERIFIED,
    RELATIONSHIP_PARTIAL,
    RELATIONSHIP_UNVERIFIED,
)

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

REPORT_FIELDS = (
    "report",
    "goal",
    "task_id",
    "generated_at",
    "read_only",
    "production_mutated",
    "secrets_exposed",
    "live_endpoint_checked",
    "repository_presence_is_not_deployment_evidence",
    "audit_context",
    "deployment_identity",
    "deployment_identity_status",
    "deployment_identity_evidence",
    "declared_source",
    "canonical_source",
    "candidate_source_commits",
    "matching_source_commits",
    "relationship_status",
    "relationship_reason",
    "runtime_changes",
    "undeployed_source_commits",
    "execution_relevant_undeployed_commits",
    "report_only_commits",
    "remaining_gap",
    "live_endpoint_checks",
    "checks",
    "overall",
    "markdown",
)


# ---------------------------------------------------------------------------
# git read helpers (never mutate)
# ---------------------------------------------------------------------------
def _run_git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT), capture_output=True
    )


def _git(*args: str) -> str:
    return _run_git(*args).stdout.decode("utf-8", "replace").strip()


def _git_ok(*args: str) -> bool:
    return _run_git(*args).returncode == 0


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _blob_at(commit: str, path: str) -> bytes | None:
    proc = _run_git("show", f"{commit}:{path}")
    if proc.returncode != 0:
        return None
    return proc.stdout


def _commit_present(commit: str) -> bool:
    return bool(commit) and _git_ok("cat-file", "-e", commit + "^{commit}")


def _commit_on_history(commit: str) -> bool:
    if not _commit_present(commit):
        return False
    return _git_ok("merge-base", "--is-ancestor", commit, "HEAD")


def _commit_meta(commit: str) -> dict[str, Any]:
    return {
        "commit": commit,
        "short": commit[:12],
        "date": _git("show", "-s", "--format=%cI", commit),
        "subject": _git("show", "-s", "--format=%s", commit),
        "author": _git("show", "-s", "--format=%an", commit),
        "tags": [t for t in _git("tag", "--points-at", commit).splitlines() if t],
    }


def _changed_paths(commit: str) -> list[str]:
    raw = _git("show", "--name-only", "--format=", commit)
    return [line for line in raw.splitlines() if line.strip()]


def _commits_touching(path: str) -> list[str]:
    raw = _git("log", "--format=%H", "--", path)
    return [line for line in raw.splitlines() if line.strip()]


def _descendants_of(commit: str) -> list[str]:
    if not _commit_present(commit):
        return []
    raw = _git("rev-list", f"{commit}..HEAD")
    return [line for line in raw.splitlines() if line.strip()]


def _recovery_baseline_commit() -> str | None:
    tagged = _git("rev-list", "-n1", RECOVERY_TAG)
    if tagged:
        return tagged
    raw = _git("log", "--format=%H", "--", BASELINE_PATH)
    for line in raw.splitlines():
        if line.strip():
            return line.strip()
    return None


def _is_execution_relevant(path: str) -> bool:
    return path.startswith(EXECUTION_PATH_PREFIXES)


# ---------------------------------------------------------------------------
# evidence helpers
# ---------------------------------------------------------------------------
def _load_json(rel: str) -> dict[str, Any] | None:
    path = REPO_ROOT / rel
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(loaded, str):
        try:
            loaded = json.loads(loaded)
        except json.JSONDecodeError:
            return None
    return loaded if isinstance(loaded, dict) else None


def _metadata_str(mapping: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _metadata_int(mapping: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return int(value.strip())
            except ValueError:
                continue
    return None


def _env_value(names: tuple[str, ...]) -> tuple[str | None, list[str]]:
    """Return the first set (non-secret) env value and the names that were set."""
    present = [name for name in names if os.environ.get(name)]
    if present:
        return os.environ[present[0]].strip(), present
    return None, []


def _env_names_present(names: tuple[str, ...]) -> list[str]:
    return [name for name in names if os.environ.get(name)]


def _candidate_source_commit(commit: str, declared_hash: str | None) -> dict[str, Any]:
    meta = _commit_meta(commit)
    blob = _blob_at(commit, CANONICAL_SOURCE)
    info: dict[str, Any] = dict(meta)
    info["touches_canonical_source"] = blob is not None
    info["source_sha256"] = _sha256_bytes(blob) if blob is not None else None
    info["source_bytes"] = len(blob) if blob is not None else None
    info["source_lines"] = (
        len(blob.decode("utf-8", "replace").splitlines()) if blob is not None else None
    )
    info["on_current_history"] = _commit_on_history(commit)
    info["matches_declared_hash"] = bool(
        declared_hash
        and info["source_sha256"]
        and info["source_sha256"].lower() == declared_hash.lower()
    )
    return info


# ---------------------------------------------------------------------------
# evidence collection
# ---------------------------------------------------------------------------
def collect_evidence() -> dict[str, Any]:
    """Collect all read-only provenance evidence from the repository."""
    baseline = _load_json(BASELINE_PATH)
    metadata_present = baseline is not None
    baseline = baseline or {}

    head = _git("rev-parse", "HEAD")
    origin_main = _git("rev-parse", "origin/main")

    declared_file = _metadata_str(baseline, "source_file", "source_path", "entrypoint")
    declared_hash = _metadata_str(baseline, "source_sha256", "source_hash", "sha256")
    declared_bytes = _metadata_int(baseline, "source_bytes", "bytes")
    declared_lines = _metadata_int(baseline, "source_lines", "lines")
    declared_version = _metadata_str(
        baseline, "production_version", "version", "version_id", "versionId"
    )
    declared_service = _metadata_str(baseline, "service", "worker_name", "name")
    declared_environment = _metadata_str(baseline, "environment", "env", "stage")

    env_version, version_env_names = _env_value(DEPLOYMENT_VERSION_ENVS)
    env_commit, commit_env_names = _env_value(DEPLOYMENT_COMMIT_ENVS)
    credential_env_names = _env_names_present(DEPLOY_CREDENTIAL_ENVS)

    deploy_report = _load_json(DEPLOY_REPORT_PATH)
    deploy_chain = (
        deploy_report.get("provenance_chain", {})
        if isinstance(deploy_report, dict)
        else {}
    )
    deploy_record_version = (
        deploy_chain.get("cloudflare_version") if isinstance(deploy_chain, dict) else None
    )
    deploy_record_id = (
        deploy_chain.get("cloudflare_deployment_id")
        if isinstance(deploy_chain, dict)
        else None
    )
    deploy_record_timestamp = (
        deploy_chain.get("deployment_timestamp")
        if isinstance(deploy_chain, dict)
        else None
    )
    deploy_link_status = (
        deploy_chain.get("link_status") if isinstance(deploy_chain, dict) else None
    )
    deploy_attempted = bool(
        deploy_report.get("deployment_attempted") if deploy_report else False
    )

    canonical_path = REPO_ROOT / CANONICAL_SOURCE
    canonical_present = canonical_path.is_file()
    canonical_head_hash = _sha256_file(canonical_path) if canonical_present else None
    canonical_head_bytes = canonical_path.stat().st_size if canonical_present else None
    canonical_text = (
        canonical_path.read_text(encoding="utf-8", errors="ignore")
        if canonical_present
        else ""
    )
    canonical_head_lines = (
        len(canonical_text.splitlines()) if canonical_present else None
    )
    canonical_source_commit = _git("log", "-1", "--format=%H", "--", CANONICAL_SOURCE)

    candidates = [
        _candidate_source_commit(commit, declared_hash)
        for commit in _commits_touching(CANONICAL_SOURCE)
    ]
    matching = [c for c in candidates if c["matches_declared_hash"]]
    matching_on_history = [c for c in matching if c["on_current_history"]]

    recovery_commit = _recovery_baseline_commit()

    undeployed_source = []
    for candidate in candidates:
        if candidate["matches_declared_hash"]:
            continue
        entry = {
            "commit": candidate["commit"],
            "short": candidate["short"],
            "date": candidate["date"],
            "subject": candidate["subject"],
            "tags": candidate["tags"],
            "on_current_history": candidate["on_current_history"],
            "after_recovery_baseline": bool(
                recovery_commit
                and _git_ok(
                    "merge-base", "--is-ancestor", recovery_commit, candidate["commit"]
                )
                and candidate["commit"] != recovery_commit
            ),
            "reason": (
                "repository presence alone is not deployment evidence; no "
                "deployment record ties this source commit to the declared "
                f"production version {declared_version or 'UNKNOWN'}"
            ),
        }
        undeployed_source.append(entry)

    descendants = _descendants_of(recovery_commit) if recovery_commit else []
    execution_undeployed = []
    report_only = []
    for commit in dict.fromkeys(descendants):
        paths = _changed_paths(commit)
        relevant = [p for p in paths if _is_execution_relevant(p)]
        meta = _commit_meta(commit)
        if relevant:
            execution_undeployed.append(
                {
                    "commit": commit,
                    "short": commit[:12],
                    "date": meta["date"],
                    "subject": meta["subject"],
                    "execution_paths": relevant,
                    "touches_worker_source": CANONICAL_SOURCE in paths,
                    "touches_workflow": any(
                        p.startswith(".github/workflows/") for p in relevant
                    ),
                    "changed_paths": paths,
                    "proven_deployed": bool(
                        matching_on_history
                        and any(p == CANONICAL_SOURCE for p in paths)
                    ),
                    "reason": (
                        "no deployment record ties this execution-infrastructure "
                        "commit to the declared production runtime; repository "
                        "presence alone is not deployment evidence"
                    ),
                }
            )
        else:
            report_only.append(
                {
                    "commit": commit,
                    "short": commit[:12],
                    "date": meta["date"],
                    "subject": meta["subject"],
                    "changed_paths": paths,
                    "reason": (
                        "does not touch execution-relevant paths; documentation/"
                        "report-only commit, not a required-but-undeployed "
                        "runtime change"
                    ),
                }
            )

    status_commits = [
        c
        for c in _commits_touching(CANONICAL_SOURCE)
        if "src/personal_ai_execution/status_contract.py"
        in _changed_paths(c)
    ]
    provenance_commits = [
        c
        for c in _commits_touching(CANONICAL_SOURCE)
        if "src/personal_ai_execution/provenance_contract.py"
        in _changed_paths(c)
    ]

    return {
        "head": head,
        "origin_main": origin_main,
        "metadata_present": metadata_present,
        "declared_file": declared_file,
        "declared_hash": declared_hash,
        "declared_bytes": declared_bytes,
        "declared_lines": declared_lines,
        "declared_version": declared_version,
        "declared_service": declared_service,
        "declared_environment": declared_environment,
        "env_version": env_version,
        "version_env_names": version_env_names,
        "env_commit": env_commit,
        "commit_env_names": commit_env_names,
        "credential_env_names": credential_env_names,
        "deploy_record_present": deploy_report is not None,
        "deploy_record_version": deploy_record_version,
        "deploy_record_id": deploy_record_id,
        "deploy_record_timestamp": deploy_record_timestamp,
        "deploy_link_status": deploy_link_status,
        "deploy_attempted": deploy_attempted,
        "canonical_present": canonical_present,
        "canonical_head_hash": canonical_head_hash,
        "canonical_head_bytes": canonical_head_bytes,
        "canonical_head_lines": canonical_head_lines,
        "canonical_text": canonical_text,
        "canonical_source_commit": canonical_source_commit,
        "candidates": candidates,
        "matching": matching,
        "matching_on_history": matching_on_history,
        "recovery_commit": recovery_commit,
        "undeployed_source": undeployed_source,
        "execution_undeployed": execution_undeployed,
        "report_only": report_only,
        "status_commits": status_commits,
        "provenance_commits": provenance_commits,
    }


# ---------------------------------------------------------------------------
# classification (pure, fail-closed)
# ---------------------------------------------------------------------------
def classify_relationship(
    *,
    metadata_present: bool,
    declared_hash: str | None,
    matching_on_history: bool,
    matching_any: bool,
    deployment_record_linked: bool,
) -> str:
    """Classify the canonical source -> deployed runtime relationship.

    Fail-closed rubric:

    * no deployment metadata or no declared source hash -> ``UNVERIFIED``;
    * a canonical commit whose blob equals the declared hash, on current
      history, *and* a linked Cloudflare deployment/version record ->
      ``VERIFIED``;
    * a matching blob exists (or a match is only off current history) but the
      deployment link is missing -> ``PARTIAL``;
    * a declared hash that matches no canonical commit at all -> ``UNVERIFIED``.
    """
    if not metadata_present or not declared_hash:
        return RELATIONSHIP_UNVERIFIED
    if not matching_any:
        return RELATIONSHIP_UNVERIFIED
    if matching_on_history and deployment_record_linked:
        return RELATIONSHIP_VERIFIED
    return RELATIONSHIP_PARTIAL


def classify_deployment_identity(
    *,
    metadata_present: bool,
    version: str | None,
    service: str | None,
    authoritative_evidence: bool,
) -> str:
    """Classify production deployment identity confidence.

    * an authoritative (live/environment or recorded Cloudflare deployment)
      source confirms the version -> ``VERIFIED``;
    * only a self-declared in-repo baseline identifies the version -> ``PARTIAL``
      (declared, not independently confirmed);
    * nothing identifies a version -> ``UNVERIFIED``.
    """
    if authoritative_evidence and version:
        return RELATIONSHIP_VERIFIED
    if metadata_present and version and service:
        return RELATIONSHIP_PARTIAL
    if version or service:
        return RELATIONSHIP_PARTIAL
    return RELATIONSHIP_UNVERIFIED


def _deployment_record_linked(ev: dict[str, Any]) -> bool:
    return bool(ev["deploy_record_version"] or ev["deploy_record_id"])


def _authoritative_identity_evidence(ev: dict[str, Any]) -> bool:
    return bool(ev["env_version"] or _deployment_record_linked(ev))


def _relationship_reason(ev: dict[str, Any], status: str) -> str:
    if status == RELATIONSHIP_VERIFIED:
        match = ev["matching_on_history"][0] if ev["matching_on_history"] else {}
        return (
            "declared production source hash "
            f"{ev['declared_hash']} matches canonical commit "
            f"{match.get('short', '')} on current history and a Cloudflare "
            "deployment/version record links it to the live runtime"
        )
    if status == RELATIONSHIP_PARTIAL:
        return (
            "declared production source hash matches a canonical commit but the "
            "Cloudflare deployment/version link to the live runtime is missing; "
            "provenance is partial and cannot be upgraded to VERIFIED"
        )
    if not ev["metadata_present"]:
        return "no deployment metadata present; deployed runtime cannot be traced"
    if not ev["declared_hash"]:
        return "deployment metadata present but no source hash recorded; cannot trace"
    return (
        f"declared production source hash {ev['declared_hash']} matches no "
        f"canonical commit of {CANONICAL_SOURCE} in the repository history; "
        f"current HEAD source hash is {ev['canonical_head_hash']}; no Cloudflare "
        "deployment/version record exists to link source to the live runtime; "
        "the deployed runtime is not traceable to a canonical source commit"
    )


def _runtime_change_section(
    ev: dict[str, Any],
    *,
    label: str,
    tokens: tuple[str, ...],
    commits: list[str],
    deployed_inclusion_proven: bool,
) -> dict[str, Any]:
    missing = [token for token in tokens if token not in ev["canonical_text"]]
    canonical_includes = not missing
    commits_sorted = list(dict.fromkeys(commits))
    return {
        "label": label,
        "required_tokens": list(tokens),
        "missing_tokens": missing,
        "canonical_source_includes_change": canonical_includes,
        "canonical_source_sha256": ev["canonical_head_hash"],
        "source_commits": commits_sorted,
        "source_commits_on_history": all(
            _commit_on_history(c) for c in commits_sorted
        )
        if commits_sorted
        else False,
        "deployed_inclusion_proven": deployed_inclusion_proven,
        "status": PASS if deployed_inclusion_proven else BLOCKED,
        "detail": (
            f"{label} tokens present in canonical source and the deployed source "
            "hash is linked to a canonical commit"
            if deployed_inclusion_proven
            else f"{label} tokens are present in canonical source "
            f"(sha256={ev['canonical_head_hash']}) but the deployed production "
            "source hash cannot be tied to a canonical commit, so inclusion in "
            "the live runtime is not proven"
        ),
    }


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def build_report() -> dict[str, Any]:
    """Build the complete V0.3 final runtime provenance audit (read-only)."""
    ev = collect_evidence()

    deployment_record_linked = _deployment_record_linked(ev)
    relationship_status = classify_relationship(
        metadata_present=ev["metadata_present"],
        declared_hash=ev["declared_hash"],
        matching_on_history=bool(ev["matching_on_history"]),
        matching_any=bool(ev["matching"]),
        deployment_record_linked=deployment_record_linked,
    )
    identity_status = classify_deployment_identity(
        metadata_present=ev["metadata_present"],
        version=ev["declared_version"],
        service=ev["declared_service"],
        authoritative_evidence=_authoritative_identity_evidence(ev),
    )
    relationship_reason = _relationship_reason(ev, relationship_status)

    source_match = bool(
        ev["declared_hash"]
        and ev["canonical_head_hash"]
        and ev["declared_hash"].lower() == ev["canonical_head_hash"].lower()
    )
    deployed_inclusion_proven = bool(ev["matching_on_history"] and deployment_record_linked)

    status_section = _runtime_change_section(
        ev,
        label="status-contract",
        tokens=STATUS_CONTRACT_TOKENS,
        commits=ev["status_commits"],
        deployed_inclusion_proven=deployed_inclusion_proven,
    )
    provenance_section = _runtime_change_section(
        ev,
        label="asset-provenance",
        tokens=ASSET_PROVENANCE_TOKENS,
        commits=ev["provenance_commits"],
        deployed_inclusion_proven=deployed_inclusion_proven,
    )

    remaining_gap: list[str] = []
    if not _authoritative_identity_evidence(ev):
        remaining_gap.append(
            "production deployment/version identity is only self-declared "
            f"({BASELINE_PATH} version={ev['declared_version']}); no authoritative "
            "live-runtime or Cloudflare deployment/version interface confirmed it"
        )
    if not ev["credential_env_names"]:
        remaining_gap.append(
            "no Cloudflare production deploy credential is available "
            f"(checked names: {', '.join(DEPLOY_CREDENTIAL_ENVS)}); the controlled "
            "deploy cf-7afde7d95cdb was BLOCKED before any deployment was attempted"
        )
    if ev["deploy_record_present"]:
        remaining_gap.append(
            f"{DEPLOY_REPORT_PATH} records cloudflare_deployment_id="
            f"{ev['deploy_record_id']!r}, cloudflare_version="
            f"{ev['deploy_record_version']!r}, deployment_timestamp="
            f"{ev['deploy_record_timestamp']!r}, link_status="
            f"{ev['deploy_link_status']!r}"
        )
    remaining_gap.append(
        f"declared production source sha256 {ev['declared_hash']} matches no "
        f"canonical {CANONICAL_SOURCE} commit; current HEAD source hash is "
        f"{ev['canonical_head_hash']} (last source commit "
        f"{ev['canonical_source_commit'] or 'unknown'})"
    )
    if relationship_status != RELATIONSHIP_VERIFIED:
        remaining_gap.append(
            "to reach VERIFIED: deploy the canonical worker source with a "
            "Cloudflare credential, record cloudflare_deployment_id/version and "
            "deployment_timestamp, and write the deployed worker/index.js sha256 "
            "into the production baseline so the commit -> hash -> version -> "
            "runtime chain closes"
        )
    if not deployed_inclusion_proven:
        remaining_gap.append(
            "status-contract and asset-provenance Worker changes are present in "
            "canonical source but not proven included in the live runtime because "
            "the deployed source hash cannot be tied to a canonical commit"
        )

    checks: list[dict[str, str]] = [
        {
            "check": "deployment metadata present",
            "status": PASS if ev["metadata_present"] else BLOCKED,
            "detail": (
                f"deployment baseline present: {BASELINE_PATH}"
                if ev["metadata_present"]
                else f"no deployment metadata at {BASELINE_PATH}"
            ),
        },
        {
            "check": "production deployment/version identity independently verified",
            "status": (
                PASS
                if identity_status == RELATIONSHIP_VERIFIED
                else BLOCKED
            ),
            "detail": (
                f"identity independently confirmed from authoritative evidence: "
                f"version={ev['env_version'] or ev['deploy_record_version']}"
                if identity_status == RELATIONSHIP_VERIFIED
                else "identity only self-declared: service="
                f"{ev['declared_service']} environment={ev['declared_environment']} "
                f"version={ev['declared_version']} (source: {BASELINE_PATH}); no "
                "authoritative live/deployment confirmation available"
            ),
        },
        {
            "check": "canonical source present",
            "status": PASS if ev["canonical_present"] else FAIL,
            "detail": (
                f"canonical source present: {CANONICAL_SOURCE} "
                f"(sha256={ev['canonical_head_hash']}, bytes="
                f"{ev['canonical_head_bytes']}, lines={ev['canonical_head_lines']})"
                if ev["canonical_present"]
                else f"canonical source {CANONICAL_SOURCE} not found"
            ),
        },
        {
            "check": "canonical commit and exact worker source hash verified",
            "status": PASS if ev["canonical_present"] else FAIL,
            "detail": (
                f"HEAD source {CANONICAL_SOURCE} sha256={ev['canonical_head_hash']} "
                f"({ev['canonical_head_bytes']} bytes / {ev['canonical_head_lines']} "
                f"lines); last source commit {ev['canonical_source_commit']}"
                if ev["canonical_present"]
                else "canonical source hash could not be computed"
            ),
        },
        {
            "check": "declared production source hash matches a canonical commit",
            "status": PASS if ev["matching"] else BLOCKED,
            "detail": (
                "declared hash "
                f"{ev['declared_hash']} matches commit(s): "
                + ", ".join(c["short"] for c in ev["matching"])
                if ev["matching"]
                else "declared production source hash "
                f"{ev['declared_hash'] or 'UNAVAILABLE'} matches no canonical "
                f"{CANONICAL_SOURCE} commit "
                f"({len(ev['candidates'])} candidate commits checked); "
                f"current HEAD source hash is {ev['canonical_head_hash']}"
            ),
        },
        {
            "check": "source hash -> Cloudflare deployment/version link",
            "status": PASS if deployment_record_linked else BLOCKED,
            "detail": (
                f"Cloudflare deployment id={ev['deploy_record_id']} "
                f"version={ev['deploy_record_version']}"
                if deployment_record_linked
                else "no Cloudflare deployment id/version recorded; the link from "
                "the canonical source hash to a live deployment is absent"
            ),
        },
        {
            "check": "canonical source -> live runtime relationship",
            "status": PASS if relationship_status == RELATIONSHIP_VERIFIED else BLOCKED,
            "detail": f"[{relationship_status}] {relationship_reason}",
        },
        {
            "check": "status-contract and asset-provenance runtime changes proven included",
            "status": (
                PASS
                if status_section["status"] == PASS
                and provenance_section["status"] == PASS
                else BLOCKED
            ),
            "detail": (
                f"status-contract={status_section['status']}: "
                f"{status_section['detail']}; asset-provenance="
                f"{provenance_section['status']}: {provenance_section['detail']}"
            ),
        },
        {
            "check": "execution-relevant commits proven deployed",
            "status": PASS if not ev["execution_undeployed"] else BLOCKED,
            "detail": (
                "all execution-relevant commits have deployment evidence"
                if not ev["execution_undeployed"]
                else f"{len(ev['execution_undeployed'])} execution-relevant "
                "commit(s) after the recovered baseline are not proven deployed "
                "(source presence != deployment)"
            ),
        },
        {
            "check": "no production mutation",
            "status": PASS,
            "detail": "read-only audit: no deploy, upload, secret change, "
            "D1/KV mutation, workflow mutation or asset mutation performed",
        },
    ]

    runtime_inclusion_proven = (
        status_section["status"] == PASS and provenance_section["status"] == PASS
    )
    if any(c["status"] == FAIL for c in checks):
        overall = FAIL
    elif (
        relationship_status == RELATIONSHIP_VERIFIED
        and identity_status == RELATIONSHIP_VERIFIED
        and runtime_inclusion_proven
        and not ev["execution_undeployed"]
    ):
        overall = PASS if all(c["status"] == PASS for c in checks) else BLOCKED
    else:
        overall = BLOCKED

    declared_source = {
        "file": ev["declared_file"],
        "sha256": ev["declared_hash"],
        "bytes": ev["declared_bytes"],
        "lines": ev["declared_lines"],
    }
    canonical_source = {
        "file": CANONICAL_SOURCE,
        "present": ev["canonical_present"],
        "head_commit": ev["head"],
        "head_sha256": ev["canonical_head_hash"],
        "head_bytes": ev["canonical_head_bytes"],
        "head_lines": ev["canonical_head_lines"],
        "last_source_commit": ev["canonical_source_commit"],
        "matches_declared_hash": source_match,
    }
    deployment_identity = {
        "service": ev["declared_service"],
        "environment": ev["declared_environment"],
        "production_version": ev["declared_version"],
        "metadata_path": BASELINE_PATH if ev["metadata_present"] else None,
        "declared_source": (
            f"in-repo deployment baseline {BASELINE_PATH} (self-declared; "
            "Cloudflare Quick Edit provenance)"
            if ev["metadata_present"]
            else None
        ),
        "cloudflare_deployment_id": ev["deploy_record_id"],
        "cloudflare_version": ev["deploy_record_version"],
        "deployment_timestamp": ev["deploy_record_timestamp"],
        "env_version": ev["env_version"],
        "env_version_names": ev["version_env_names"],
        "env_commit": ev["env_commit"],
        "env_commit_names": ev["commit_env_names"],
        "deploy_attempted": ev["deploy_attempted"],
        "deploy_link_status": ev["deploy_link_status"],
    }
    deployment_identity_evidence = {
        "authoritative": _authoritative_identity_evidence(ev),
        "authoritative_sources": [
            s
            for s in (
                "environment: " + "|".join(ev["version_env_names"])
                if ev["env_version"]
                else None,
                f"{DEPLOY_REPORT_PATH} (cloudflare deployment/version record)"
                if deployment_record_linked
                else None,
            )
            if s
        ],
        "self_declared_sources": [BASELINE_PATH] if ev["metadata_present"] else [],
        "cloudflare_deploy_credential_names_present": ev["credential_env_names"],
        "cloudflare_deploy_credential_names_checked": list(DEPLOY_CREDENTIAL_ENVS),
        "secrets_exposed": False,
    }

    report: dict[str, Any] = {
        "report": REPORT_NAME,
        "goal": GOAL,
        "task_id": TASK_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "production_mutated": False,
        "secrets_exposed": False,
        "live_endpoint_checked": False,
        "repository_presence_is_not_deployment_evidence": True,
        "audit_context": {
            "repository_head": ev["head"],
            "origin_main": ev["origin_main"],
            "github_sha": ev["env_commit"],
            "recovery_baseline_commit": ev["recovery_commit"],
        },
        "deployment_identity": deployment_identity,
        "deployment_identity_status": identity_status,
        "deployment_identity_evidence": deployment_identity_evidence,
        "declared_source": declared_source,
        "canonical_source": canonical_source,
        "candidate_source_commits": ev["candidates"],
        "matching_source_commits": [
            {
                "commit": c["commit"],
                "short": c["short"],
                "source_sha256": c["source_sha256"],
                "on_current_history": c["on_current_history"],
                "tags": c["tags"],
            }
            for c in ev["matching"]
        ],
        "relationship_status": relationship_status,
        "relationship_reason": relationship_reason,
        "runtime_changes": {
            "status_contract": status_section,
            "asset_provenance": provenance_section,
        },
        "undeployed_source_commits": ev["undeployed_source"],
        "execution_relevant_undeployed_commits": ev["execution_undeployed"],
        "report_only_commits": ev["report_only"],
        "remaining_gap": remaining_gap,
        "live_endpoint_checks": {
            "performed": False,
            "reason": (
                "no Cloudflare credential or live interface available in the "
                "audit environment; a bounded read-only health probe was not "
                "possible, so live runtime evidence is not fabricated"
            ),
            "planned_read_only_checks": [
                {
                    "check": "health endpoint",
                    "request": "GET /healthz",
                    "expect": "200 JSON containing "
                    '{"status":"ok","name":"personal-ai-execution-mcp"}',
                },
                {
                    "check": "auth boundary",
                    "request": "POST /mcp without Authorization",
                    "expect": "401 unauthorized",
                },
                {
                    "check": "MCP tools/list schema",
                    "request": "POST /mcp (authorized) method=tools/list",
                    "expect": "tool schema includes submit_task, "
                    "get_task_result, search_assets",
                },
            ],
        },
        "checks": checks,
        "overall": overall,
    }
    report["markdown"] = render_markdown(report)
    return report


# ---------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------
def render_markdown(report: dict[str, Any]) -> str:
    identity = report["deployment_identity"]
    declared = report["declared_source"]
    canonical = report["canonical_source"]
    runtime = report["runtime_changes"]

    lines = [
        f"# {REPORT_NAME}",
        "",
        f"- goal: {report['goal']}",
        f"- task_id: {report['task_id']}",
        f"- generated_at: {report['generated_at']}",
        f"- read_only: {report['read_only']}",
        f"- production_mutated: {report['production_mutated']}",
        f"- secrets_exposed: {report['secrets_exposed']}",
        f"- live_endpoint_checked: {report['live_endpoint_checked']}",
        "",
        "## Production deployment / version identity",
        f"- service: {identity['service'] or 'UNKNOWN'}",
        f"- environment: {identity['environment'] or 'UNKNOWN'}",
        f"- production_version: {identity['production_version'] or 'UNKNOWN'}",
        f"- metadata: {identity['metadata_path'] or 'absent'}",
        f"- cloudflare_deployment_id: {identity['cloudflare_deployment_id']!r}",
        f"- cloudflare_version: {identity['cloudflare_version']!r}",
        f"- deployment_timestamp: {identity['deployment_timestamp']!r}",
        f"- deploy_attempted: {identity['deploy_attempted']}",
        f"- deploy_link_status: {identity['deploy_link_status']!r}",
        f"- identity_status: {report['deployment_identity_status']}",
        "",
        "## Canonical source vs declared production source",
        f"- canonical source: {canonical['file']}",
        f"- canonical HEAD commit: {canonical['head_commit']}",
        f"- canonical HEAD sha256: {canonical['head_sha256'] or 'UNAVAILABLE'} "
        f"({canonical['head_bytes']} bytes / {canonical['head_lines']} lines)",
        f"- declared production sha256: {declared['sha256'] or 'UNAVAILABLE'} "
        f"({declared['bytes']} bytes / {declared['lines']} lines)",
        f"- canonical HEAD matches declared: {canonical['matches_declared_hash']}",
        f"- canonical source last commit: {canonical['last_source_commit'] or 'unknown'}",
        "",
        "## Source-to-live-runtime relationship",
        f"- relationship_status: {report['relationship_status']}",
        f"- reason: {report['relationship_reason']}",
        "",
        "## Recent runtime changes (inclusion in deployed runtime)",
    ]
    for key in ("status_contract", "asset_provenance"):
        section = runtime[key]
        lines.append(
            f"- {section['label']}: status={section['status']} "
            f"canonical_source_includes="
            f"{section['canonical_source_includes_change']} "
            f"deployed_inclusion_proven={section['deployed_inclusion_proven']} "
            f"source_commits={[c[:12] for c in section['source_commits']]}"
        )
        lines.append(f"  - {section['detail']}")

    lines += ["", "## Candidate source commits"]
    for candidate in report["candidate_source_commits"]:
        lines.append(
            f"- {candidate['short']} {candidate['date']} "
            f"sha256={candidate['source_sha256'] or 'n/a'} "
            f"bytes={candidate['source_bytes']} lines={candidate['source_lines']} "
            f"on_history={candidate['on_current_history']} "
            f"matches_declared={candidate['matches_declared_hash']} "
            f"tags={candidate['tags'] or '[]'} | {candidate['subject']}"
        )

    lines += ["", "## Execution-relevant commits not proven deployed"]
    if report["execution_relevant_undeployed_commits"]:
        for entry in report["execution_relevant_undeployed_commits"]:
            lines.append(
                f"- {entry['short']} worker={entry['touches_worker_source']} "
                f"workflow={entry['touches_workflow']} "
                f"proven_deployed={entry['proven_deployed']} "
                f"| {entry['subject']}"
            )
    else:
        lines.append("- none")

    lines += ["", "## Report-only (non-runtime) commits"]
    if report["report_only_commits"]:
        for entry in report["report_only_commits"]:
            lines.append(
                f"- {entry['short']} | {entry['subject']} "
                f"({len(entry['changed_paths'])} path(s))"
            )
    else:
        lines.append("- none")

    lines += ["", "## Live endpoint checks"]
    live = report["live_endpoint_checks"]
    lines.append(f"- performed: {live['performed']}")
    lines.append(f"- reason: {live['reason']}")
    for check in live["planned_read_only_checks"]:
        lines.append(f"- planned: {check['check']} ({check['request']})")

    lines += ["", "## Checks"]
    for check in report["checks"]:
        lines.append(f"- [{check['status']}] {check['check']}: {check['detail']}")

    lines += ["", "## Remaining gap to VERIFIED"]
    if report["remaining_gap"]:
        for gap in report["remaining_gap"]:
            lines.append(f"- {gap}")
    else:
        lines.append("- none")

    lines += [
        "",
        "## Verdict",
        f"DEPLOYED_VERSION={identity['production_version'] or 'UNVERIFIED'}",
        f"CLOUDFLARE_DEPLOYMENT_ID={identity['cloudflare_deployment_id'] or 'UNAVAILABLE'}",
        f"CLOUDFLARE_VERSION={identity['cloudflare_version'] or 'UNAVAILABLE'}",
        f"DEPLOYMENT_IDENTITY_STATUS={report['deployment_identity_status']}",
        f"RELATIONSHIP_STATUS={report['relationship_status']}",
        f"CANONICAL_SOURCE_SHA256={canonical['head_sha256'] or 'UNAVAILABLE'}",
        "PRODUCTION_MUTATED=False",
        "SECRETS_EXPOSED=False",
        f"OVERALL={report['overall']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# artifact writing
# ---------------------------------------------------------------------------
def write_artifacts() -> tuple[Path, Path]:
    """Write the committed JSON + markdown evidence artifacts."""
    report = build_report()
    json_path = REPO_ROOT / JSON_ARTIFACT
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    md_path = REPO_ROOT / MARKDOWN_ARTIFACT
    md_path.write_text(report["markdown"] + "\n", encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":  # pragma: no cover - manual artifact build
    if "--write" in sys.argv:
        written = write_artifacts()
        for path in written:
            print(f"wrote {path.relative_to(REPO_ROOT)}")
    else:
        print(json.dumps(build_report(), indent=2, ensure_ascii=False))
