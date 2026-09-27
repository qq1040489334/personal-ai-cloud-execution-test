"""PERSONAL_AI_RUNTIME_PROVENANCE_V0.2 -- auditable production runtime chain.

Task: ``cf-883c3502ff24`` (risk: LOW).

This module is the read-only audit engine for the production runtime provenance
chain of the Personal AI execution infrastructure. It answers, from in-repo
evidence only:

* what production runtime/deployment identity is declared, and from what
  evidence;
* whether the canonical repository source can be tied to that deployed runtime
  (``VERIFIED`` / ``PARTIAL`` / ``UNVERIFIED``);
* which recent commits are *not* proven to be deployed, so that repository
  presence is never mistaken for production reality.

Hard invariants:

* No production mutation of any kind: this module only runs ``git`` read
  commands and reads files. It never deploys, never touches secrets, D1/KV,
  workflows or assets.
* A relationship is never upgraded on inference. A commit blob hash matching
  the declared production source hash is the *only* thing that yields
  ``VERIFIED``; repository presence alone yields ``UNVERIFIED``.
* A live endpoint is never queried, so a live-verified PASS is never fabricated.

The module can emit the committed evidence artifacts::

    python tests/runtime_provenance_v0_2.py --write

which writes ``reports/runtime_provenance_v0.2.json`` and
``RUNTIME_PROVENANCE_V0.2.md``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

GOAL = "PERSONAL_AI_RUNTIME_PROVENANCE_V0.2"
TASK_ID = "cf-883c3502ff24"
REPORT_NAME = "PERSONAL_AI_RUNTIME_PROVENANCE_V0.2_REPORT"

BASELINE_PATH = "worker/PRODUCTION-BASELINE.json"
CANONICAL_SOURCE = "worker/index.js"
WRANGLER_CONFIG = "worker/wrangler.toml"
RECOVERY_TAG = "production-recovered-3e2fed43-20260926"

JSON_ARTIFACT = "reports/runtime_provenance_v0.2.json"
MARKDOWN_ARTIFACT = "RUNTIME_PROVENANCE_V0.2.md"

#: Path prefixes whose changes are relevant to the production execution
#: infrastructure (worker runtime, execution gates, dispatch workflows).
EXECUTION_PATH_PREFIXES = (
    "worker/",
    "scripts/",
    "src/personal_ai_execution/",
    ".github/workflows/",
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

#: The explicit commits called out by the task: the execution-workflow repair
#: commit and the subsequent execution/status/provenance commits. They are
#: checked to be classified as unproven rather than assumed live.
REPAIR_COMMIT = "ed3ca64977a1d1a6e562ba3640820730b71a8447"
SUBSEQUENT_COMMITS = (
    "39949a75ce5d0e2df78a2c255d68169d2ab00be5",
    "698ac2998c6712b9aa5152aed8f53e8db7f3345f",
    "0c3ac20392bf86bfecb68cbaadd77a7a2a398665",
    "824bd4c415554e111787d3fc1b1632e28863179b",
    "592e7c29af4a5e72e3ec12bb458538629011896b",
)
TRACKED_EXECUTION_COMMITS = (REPAIR_COMMIT,) + SUBSEQUENT_COMMITS

REPORT_FIELDS = (
    "report",
    "goal",
    "task_id",
    "generated_at",
    "read_only",
    "production_mutated",
    "live_endpoint_checked",
    "repository_presence_is_not_deployment_evidence",
    "deployment_identity",
    "deployment_identity_status",
    "declared_source",
    "canonical_source",
    "recovery_baseline_commit",
    "candidate_source_commits",
    "matching_source_commits",
    "relationship_status",
    "relationship_reason",
    "undeployed_source_commits",
    "execution_relevant_undeployed_commits",
    "tracked_execution_commits",
    "checks",
    "overall",
    "markdown",
)


# ---------------------------------------------------------------------------
# git read helpers (never mutate)
# ---------------------------------------------------------------------------
def _run_git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
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
# evidence collection
# ---------------------------------------------------------------------------
def _load_baseline() -> dict[str, Any] | None:
    path = REPO_ROOT / BASELINE_PATH
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


def collect_evidence() -> dict[str, Any]:
    """Collect all read-only provenance evidence from the repository."""
    baseline = _load_baseline()
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

    canonical_path = REPO_ROOT / CANONICAL_SOURCE
    canonical_present = canonical_path.is_file()
    canonical_head_hash = _sha256_file(canonical_path) if canonical_present else None
    canonical_head_bytes = canonical_path.stat().st_size if canonical_present else None
    canonical_head_lines = (
        len(canonical_path.read_text(encoding="utf-8", errors="ignore").splitlines())
        if canonical_present
        else None
    )
    canonical_source_commit = _git("log", "-1", "--format=%H", "--", CANONICAL_SOURCE)

    candidates = [
        _candidate_source_commit(commit, declared_hash)
        for commit in _commits_touching(CANONICAL_SOURCE)
    ]
    matching = [c for c in candidates if c["matches_declared_hash"]]

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
                and _git_ok("merge-base", "--is-ancestor", recovery_commit, candidate["commit"])
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
    tracked_descendants = [
        commit
        for commit in TRACKED_EXECUTION_COMMITS
        if commit in descendants or (recovery_commit and _commit_on_history(commit))
    ]
    ordered_commits = list(dict.fromkeys(descendants + tracked_descendants))

    execution_undeployed = []
    for commit in ordered_commits:
        paths = _changed_paths(commit)
        relevant = [p for p in paths if _is_execution_relevant(p)]
        if not relevant and commit not in TRACKED_EXECUTION_COMMITS:
            continue
        meta = _commit_meta(commit)
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
                "is_tracked_task_commit": commit in TRACKED_EXECUTION_COMMITS,
                "proven_deployed": False,
                "reason": (
                    "no deployment record ties this execution-infrastructure "
                    "commit to the declared production runtime; repository "
                    "presence alone is not deployment evidence"
                ),
            }
        )

    tracked_commits = []
    for commit in TRACKED_EXECUTION_COMMITS:
        meta = _commit_meta(commit)
        paths = _changed_paths(commit)
        tracked_commits.append(
            {
                "commit": commit,
                "short": commit[:12],
                "date": meta["date"],
                "subject": meta["subject"],
                "paths": paths,
                "on_current_history": _commit_on_history(commit),
                "touches_worker_source": CANONICAL_SOURCE in paths,
                "touches_workflow": any(
                    p.startswith(".github/workflows/") for p in paths
                ),
                "proven_deployed": commit
                in {
                    c["commit"]
                    for c in matching
                    if c["on_current_history"]
                },
            }
        )

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
        "canonical_present": canonical_present,
        "canonical_head_hash": canonical_head_hash,
        "canonical_head_bytes": canonical_head_bytes,
        "canonical_head_lines": canonical_head_lines,
        "canonical_source_commit": canonical_source_commit,
        "candidates": candidates,
        "matching": matching,
        "matching_on_history": [c for c in matching if c["on_current_history"]],
        "recovery_commit": recovery_commit,
        "undeployed_source": undeployed_source,
        "execution_undeployed": execution_undeployed,
        "tracked_commits": tracked_commits,
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
) -> str:
    """Classify the canonical source commit -> deployed runtime relationship.

    Fail-closed rubric:

    * no deployment metadata or no declared source hash -> ``UNVERIFIED``;
    * a canonical commit whose blob equals the declared hash, on current
      history -> ``VERIFIED``;
    * a matching blob that is not reachable from current history -> ``PARTIAL``;
    * a declared hash that matches no canonical commit at all -> ``UNVERIFIED``.
    """
    if not metadata_present or not declared_hash:
        return RELATIONSHIP_UNVERIFIED
    if matching_on_history:
        return RELATIONSHIP_VERIFIED
    if matching_any:
        return RELATIONSHIP_PARTIAL
    return RELATIONSHIP_UNVERIFIED


def classify_deployment_identity(
    *, metadata_present: bool, version: str | None, service: str | None
) -> str:
    if not metadata_present:
        return RELATIONSHIP_UNVERIFIED
    if version and service:
        return RELATIONSHIP_VERIFIED
    if version or service:
        return RELATIONSHIP_PARTIAL
    return RELATIONSHIP_UNVERIFIED


def _relationship_reason(ev: dict[str, Any], status: str) -> str:
    if status == RELATIONSHIP_VERIFIED:
        return (
            "declared production source hash "
            f"{ev['declared_hash']} matches canonical commit "
            f"{(ev['matching_on_history'][0]['short'] if ev['matching_on_history'] else '')} "
            "on current history"
        )
    if status == RELATIONSHIP_PARTIAL:
        return (
            "declared production source hash matches a commit that is not on "
            "current history; provenance is partial"
        )
    if not ev["metadata_present"]:
        return "no deployment metadata present; deployed runtime cannot be traced"
    if not ev["declared_hash"]:
        return "deployment metadata present but no source hash recorded; cannot trace"
    return (
        f"declared production source hash {ev['declared_hash']} matches no "
        f"canonical commit of {CANONICAL_SOURCE} in the repository history; "
        f"current HEAD source hash is {ev['canonical_head_hash']}; the deployed "
        "runtime is not traceable to a canonical source commit"
    )


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def build_report() -> dict[str, Any]:
    """Build the complete V0.2 runtime provenance report (read-only)."""
    ev = collect_evidence()

    relationship_status = classify_relationship(
        metadata_present=ev["metadata_present"],
        declared_hash=ev["declared_hash"],
        matching_on_history=bool(ev["matching_on_history"]),
        matching_any=bool(ev["matching"]),
    )
    identity_status = classify_deployment_identity(
        metadata_present=ev["metadata_present"],
        version=ev["declared_version"],
        service=ev["declared_service"],
    )
    relationship_reason = _relationship_reason(ev, relationship_status)

    source_match = bool(
        ev["declared_hash"]
        and ev["canonical_head_hash"]
        and ev["declared_hash"].lower() == ev["canonical_head_hash"].lower()
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
            "check": "deployment identity identified",
            "status": PASS if identity_status == RELATIONSHIP_VERIFIED else BLOCKED,
            "detail": (
                f"service={ev['declared_service']} environment="
                f"{ev['declared_environment']} version={ev['declared_version']} "
                f"(source: {BASELINE_PATH})"
                if identity_status != RELATIONSHIP_UNVERIFIED
                else "deployment identity could not be identified"
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
            "check": "canonical source -> deployed runtime relationship",
            "status": PASS if relationship_status == RELATIONSHIP_VERIFIED else BLOCKED,
            "detail": f"[{relationship_status}] {relationship_reason}",
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

    if any(c["status"] == FAIL for c in checks):
        overall = FAIL
    elif relationship_status == RELATIONSHIP_VERIFIED and identity_status == RELATIONSHIP_VERIFIED:
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
        "source": (
            f"in-repo deployment baseline {BASELINE_PATH} (self-declared; "
            "Cloudflare Quick Edit provenance)"
            if ev["metadata_present"]
            else None
        ),
    }

    report: dict[str, Any] = {
        "report": REPORT_NAME,
        "goal": GOAL,
        "task_id": TASK_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "production_mutated": False,
        "live_endpoint_checked": False,
        "repository_presence_is_not_deployment_evidence": True,
        "deployment_identity": deployment_identity,
        "deployment_identity_status": identity_status,
        "declared_source": declared_source,
        "canonical_source": canonical_source,
        "recovery_baseline_commit": ev["recovery_commit"],
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
        "undeployed_source_commits": ev["undeployed_source"],
        "execution_relevant_undeployed_commits": ev["execution_undeployed"],
        "tracked_execution_commits": ev["tracked_commits"],
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

    lines = [
        f"# {REPORT_NAME}",
        "",
        f"- goal: {report['goal']}",
        f"- task_id: {report['task_id']}",
        f"- generated_at: {report['generated_at']}",
        f"- read_only: {report['read_only']}",
        f"- production_mutated: {report['production_mutated']}",
        f"- live_endpoint_checked: {report['live_endpoint_checked']}",
        "",
        "## Production runtime / deployment identity",
        f"- service: {identity['service'] or 'UNKNOWN'}",
        f"- environment: {identity['environment'] or 'UNKNOWN'}",
        f"- production_version: {identity['production_version'] or 'UNKNOWN'}",
        f"- metadata: {identity['metadata_path'] or 'absent'}",
        f"- identity_status: {report['deployment_identity_status']}",
        f"- evidence: {identity['source'] or 'none'}",
        "",
        "## Canonical source vs declared production source",
        f"- canonical source: {canonical['file']}",
        f"- canonical HEAD sha256: {canonical['head_sha256'] or 'UNAVAILABLE'} "
        f"({canonical['head_bytes']} bytes / {canonical['head_lines']} lines)",
        f"- declared production sha256: {declared['sha256'] or 'UNAVAILABLE'} "
        f"({declared['bytes']} bytes / {declared['lines']} lines)",
        f"- canonical HEAD matches declared: {canonical['matches_declared_hash']}",
        f"- canonical source last commit: {canonical['last_source_commit'] or 'unknown'}",
        "",
        "## Canonical source commit -> deployed runtime relationship",
        f"- relationship_status: {report['relationship_status']}",
        f"- reason: {report['relationship_reason']}",
        f"- recovery baseline commit: {report['recovery_baseline_commit'] or 'unknown'}",
        "",
        "### Candidate source commits",
    ]
    for candidate in report["candidate_source_commits"]:
        lines.append(
            f"- {candidate['short']} {candidate['date']} "
            f"sha256={candidate['source_sha256'] or 'n/a'} "
            f"bytes={candidate['source_bytes']} lines={candidate['source_lines']} "
            f"on_history={candidate['on_current_history']} "
            f"matches_declared={candidate['matches_declared_hash']} "
            f"tags={candidate['tags'] or '[]'} | {candidate['subject']}"
        )

    lines += ["", "## Undeployed-or-unproven source commits"]
    if report["undeployed_source_commits"]:
        for entry in report["undeployed_source_commits"]:
            lines.append(
                f"- {entry['short']} after_baseline={entry['after_recovery_baseline']} "
                f"| {entry['subject']}: {entry['reason']}"
            )
    else:
        lines.append("- none: every canonical source commit is proven deployed")

    lines += ["", "## Execution-relevant commits not proven deployed"]
    if report["execution_relevant_undeployed_commits"]:
        for entry in report["execution_relevant_undeployed_commits"]:
            lines.append(
                f"- {entry['short']} worker={entry['touches_worker_source']} "
                f"workflow={entry['touches_workflow']} "
                f"tracked_task_commit={entry['is_tracked_task_commit']} "
                f"| {entry['subject']}"
            )
    else:
        lines.append("- none")

    lines += ["", "## Checks"]
    for check in report["checks"]:
        lines.append(f"- [{check['status']}] {check['check']}: {check['detail']}")

    lines += [
        "",
        "## Verdict",
        f"DEPLOYED_VERSION={identity['production_version'] or 'UNVERIFIED'}",
        f"RELATIONSHIP_STATUS={report['relationship_status']}",
        f"DEPLOYMENT_IDENTITY_STATUS={report['deployment_identity_status']}",
        "PRODUCTION_MUTATED=False",
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
