"""Minimal module for the cloud execution golden test."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
PARTIAL = "PARTIAL"

WORKER_EVIDENCE = (
    "wrangler.toml",
    "wrangler.json",
    "wrangler.jsonc",
    "worker.js",
    "worker.ts",
    "src/worker.js",
    "src/worker.ts",
    "src/index.js",
    "src/index.ts",
)
D1_EVIDENCE = ("migrations", "schema.sql", "d1", "db/schema.sql")
AUDIT_EVIDENCE = ("execution_result.json", "gpt_verification.json")

DEPLOY_VERIFY_TASK_ID = "cf-5ce9f24c8aa1"
DEPLOY_VERIFY_COMMIT = "b3474609bb325ef31854d65c934d8eb431b67eba"
REQUIRED_RESULT_FIELDS = (
    "execution_summary",
    "commit",
    "tests",
    "artifacts",
    "execution_result_json",
    "evidence",
)
DEPLOY_WORKFLOW_HINTS = ("deploy", "wrangler", "cloudflare", "mcp")


def hello() -> str:
    """Return a greeting."""
    return "hello from cloud execution golden test"


def goodbye() -> str:
    """Return a farewell."""
    return "goodbye from cloud execution golden test"


def cloud_agent_test() -> str:
    """Return the cloud agent execution marker."""
    return "executed inside github actions"


def cloud_agent_test_2() -> str:
    """Return the second cloud agent execution marker."""
    return "second cloud run"


def trigger_bridge_test() -> str:
    """Return the bridge test marker."""
    return "triggered from github issue"


def security_test() -> str:
    """Return the security gate marker."""
    return "security gate ok"


def gpt_bridge_test() -> str:
    """Return the gpt bridge test marker."""
    return "gpt bridge ok"


def mcp_bridge_test() -> str:
    """Return the mcp bridge test marker."""
    return "mcp bridge ok"


def cloudflare_mcp_test() -> str:
    """Return the cloudflare mcp test marker."""
    return "cloudflare mcp ok"


def oauth_mcp_test() -> str:
    """Return the oauth mcp test marker."""
    return "oauth mcp ok"


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _first_present(names: tuple[str, ...]) -> str | None:
    for name in names:
        if (REPO_ROOT / name).exists():
            return name
    return None


def cloud_asset_status() -> dict:
    """Return the real, read-only status report of the cloud asset layer."""
    checks: list[dict] = []

    worker = _first_present(WORKER_EVIDENCE)
    checks.append(
        {
            "component": "Worker",
            "status": PASS if worker else BLOCKED,
            "detail": (
                f"worker configuration present: {worker}"
                if worker
                else "no Cloudflare Worker configuration or entrypoint found"
            ),
            "evidence": worker or "wrangler.toml|wrangler.jsonc|worker entrypoint (absent)",
        }
    )

    d1 = _first_present(D1_EVIDENCE)
    checks.append(
        {
            "component": "D1",
            "status": PASS if d1 else BLOCKED,
            "detail": (
                f"D1 binding or migrations present: {d1}"
                if d1
                else "no D1 binding or migration directory found"
            ),
            "evidence": d1 or "migrations/|schema.sql|d1 binding (absent)",
        }
    )

    canonical = (REPO_ROOT / "hello.py").is_file()
    checks.append(
        {
            "component": "Canonical Asset",
            "status": PASS if canonical else FAIL,
            "detail": "hello.py canonical module present" if canonical else "hello.py missing",
            "evidence": "hello.py",
        }
    )

    head = _git("rev-parse", "HEAD")
    remote = _git("remote", "get-url", "origin")
    checks.append(
        {
            "component": "Promotion",
            "status": PASS if head else BLOCKED,
            "detail": (
                f"asset committed and promoted at {head[:12]}"
                if head
                else "no git commit found; asset not promoted"
            ),
            "evidence": f"git rev-parse HEAD (origin={remote or 'none'})",
        }
    )

    gate = _first_present(("scripts/scope_guard.py", "scripts/plan_gate.py"))
    audit = _first_present(AUDIT_EVIDENCE)
    if gate and audit:
        audit_status = PASS
        audit_detail = f"governance gates and audit record present: {audit}"
    elif gate:
        audit_status = BLOCKED
        audit_detail = "governance gates present but no audit record produced in this environment"
    else:
        audit_status = FAIL
        audit_detail = "governance gate/audit mechanism missing"
    checks.append(
        {
            "component": "Governance Audit",
            "status": audit_status,
            "detail": audit_detail,
            "evidence": (
                f"{gate or 'governance gate (absent)'}; {audit or 'execution_result.json (absent)'}"
            ),
        }
    )

    if any(c["status"] == FAIL for c in checks):
        overall = FAIL
    elif any(c["status"] == BLOCKED for c in checks):
        overall = BLOCKED
    else:
        overall = PASS

    return {
        "task_id": "cf-175495049c41",
        "asset": "personal-ai-cloud-execution-test",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "checks": checks,
        "overall": overall,
        "next_steps": [
            f"{c['component']}: {c['detail']}"
            for c in checks
            if c["status"] != PASS
        ],
    }


ARTIFACT_CANDIDATES = ("hello.py", "test_hello.py", "execution_result.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _collect_artifacts() -> list[dict]:
    artifacts: list[dict] = []
    for rel in ARTIFACT_CANDIDATES:
        path = REPO_ROOT / rel
        if path.is_file():
            artifacts.append(
                {
                    "name": path.name,
                    "path": rel,
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                }
            )
    return artifacts


def _read_execution_result() -> dict | None:
    path = REPO_ROOT / "execution_result.json"
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


def _derive_status(execution_result: dict | None) -> str:
    if execution_result is None:
        return BLOCKED
    raw_status = str(execution_result.get("status", "")).strip().lower()
    tests = str(execution_result.get("tests", "")).strip().lower()
    if "fail" in tests or raw_status in {"fail", "failed", "error"}:
        return FAIL
    if raw_status in {"success", "succeed", "pass", "passed", "ok"} or "passed" in tests:
        return PASS
    return BLOCKED


def get_task_result(task_id: str) -> dict:
    """Return a fully self-contained task result for phone-side verification.

    The payload carries every field needed to decide PASS / FAIL / BLOCKED
    without re-opening the execution environment.
    """
    execution_result = _read_execution_result()
    status = _derive_status(execution_result)
    commit = _git("rev-parse", "HEAD")
    artifacts = _collect_artifacts()

    tests_summary = (
        str(execution_result.get("tests", "")).strip()
        if execution_result and execution_result.get("tests")
        else "not available: no test summary recorded in execution_result.json"
    )
    summary = (
        str(execution_result.get("summary", "")).strip()
        if execution_result and execution_result.get("summary")
        else "task result derived from repository evidence"
    )
    try:
        round_number = int(execution_result.get("round", 1)) if execution_result else 1
    except (TypeError, ValueError):
        round_number = 1

    evidence = {
        "acceptance": [
            "PASS / FAIL / BLOCKED is decidable from this payload alone",
            f"execution_result.json present: {execution_result is not None}",
            f"artifacts hashed: {[a['path'] for a in artifacts]}",
            f"git commit recorded: {bool(commit)}",
        ],
        "logs": _git("log", "--oneline", "-5").splitlines(),
        "validation": {
            "pytest": tests_summary,
            "execution_result_present": execution_result is not None,
            "artifacts_present": [a["path"] for a in artifacts],
        },
        "decision": {
            "status": status,
            "reason": (
                "execution_result.json missing; cannot verify remotely"
                if execution_result is None
                else f"execution_result.json status={execution_result.get('status')!r} tests={tests_summary!r}"
            ),
        },
    }

    return {
        "execution_summary": {
            "task_id": task_id,
            "status": status,
            "round": round_number,
            "summary": summary,
        },
        "commit": commit,
        "tests": tests_summary,
        "artifacts": artifacts,
        "execution_result_json": execution_result if execution_result is not None else {},
        "evidence": evidence,
    }


def _git_ok(*args: str) -> bool:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
    except OSError:
        return False
    return result.returncode == 0


def _workflow_names() -> list[str]:
    directory = REPO_ROOT / ".github" / "workflows"
    if not directory.is_dir():
        return []
    names: list[str] = []
    for pattern in ("*.yml", "*.yaml"):
        names.extend(p.name for p in directory.glob(pattern))
    return sorted(names)


def _deploy_pipeline_workflows() -> list[str]:
    matches: list[str] = []
    for name in _workflow_names():
        try:
            text = (REPO_ROOT / ".github" / "workflows" / name).read_text(
                encoding="utf-8", errors="ignore"
            )
        except OSError:
            continue
        lowered = text.lower()
        if any(hint in lowered for hint in DEPLOY_WORKFLOW_HINTS):
            matches.append(name)
    return matches


def mcp_runtime_deploy_verify() -> dict:
    """Verify the MCP runtime deployment for the target commit.

    Read-only. Confirms the six required fields of ``get_task_result`` are
    returned, whether the target commit is present on the current history,
    whether any deployable Worker asset exists, and whether a deploy pipeline
    workflow is configured. Never fabricates a PASS.
    """
    result = get_task_result(DEPLOY_VERIFY_TASK_ID)
    result_fields = {name: name in result for name in REQUIRED_RESULT_FIELDS}
    fields_complete = all(result_fields.values())

    head = _git("rev-parse", "HEAD")
    target_committed = _git_ok("cat-file", "-e", DEPLOY_VERIFY_COMMIT + "^{commit}")
    target_on_history = target_committed and _git_ok(
        "merge-base", "--is-ancestor", DEPLOY_VERIFY_COMMIT, "HEAD"
    )

    worker = _first_present(WORKER_EVIDENCE)
    deploy_workflows = _deploy_pipeline_workflows()

    checks = [
        {
            "check": "get_task_result required fields",
            "status": PASS if fields_complete else FAIL,
            "detail": (
                "all required fields returned: " + ", ".join(REQUIRED_RESULT_FIELDS)
                if fields_complete
                else "missing fields: "
                + ", ".join(n for n, ok in result_fields.items() if not ok)
            ),
        },
        {
            "check": "target commit present",
            "status": PASS if target_on_history else FAIL,
            "detail": (
                f"commit {DEPLOY_VERIFY_COMMIT[:12]} is on current history (HEAD={head[:12]})"
                if target_on_history
                else f"commit {DEPLOY_VERIFY_COMMIT[:12]} not found on current history"
            ),
        },
        {
            "check": "MCP runtime Worker asset",
            "status": PASS if worker else BLOCKED,
            "detail": (
                f"worker configuration present: {worker}"
                if worker
                else "no Cloudflare Worker configuration or entrypoint found; nothing deployable"
            ),
        },
        {
            "check": "deploy pipeline workflow",
            "status": PASS if deploy_workflows else BLOCKED,
            "detail": (
                "deploy workflow(s): " + ", ".join(deploy_workflows)
                if deploy_workflows
                else "no deploy workflow (deploy|wrangler|cloudflare|mcp) configured"
            ),
        },
        {
            "check": "online /mcp version",
            "status": BLOCKED,
            "detail": "offline verification environment: live /mcp endpoint not reachable from here",
        },
    ]

    if any(c["status"] == FAIL for c in checks):
        final_status = FAIL
    elif any(c["status"] == BLOCKED for c in checks):
        final_status = PARTIAL
    else:
        final_status = PASS

    markdown = _final_return_markdown(
        result=result,
        result_fields=result_fields,
        head=head,
        target_on_history=target_on_history,
        worker=worker,
        deploy_workflows=deploy_workflows,
        checks=checks,
        final_status=final_status,
    )

    return {
        "task_id": DEPLOY_VERIFY_TASK_ID,
        "goal": "PERSONAL_AI_EXECUTION_MCP_RUNTIME_DEPLOY_VERIFY_01",
        "target_commit": DEPLOY_VERIFY_COMMIT,
        "head_commit": head,
        "result_fields": result_fields,
        "result_fields_complete": fields_complete,
        "target_commit_on_history": target_on_history,
        "worker_asset": worker,
        "deploy_workflows": deploy_workflows,
        "online_mcp_version": "unavailable (offline verification environment)",
        "checks": checks,
        "final_status": final_status,
        "final_return_markdown": markdown,
    }


def _final_return_markdown(
    *,
    result: dict,
    result_fields: dict,
    head: str,
    target_on_history: bool,
    worker: str | None,
    deploy_workflows: list[str],
    checks: list[dict],
    final_status: str,
) -> str:
    summary = result.get("execution_summary", {})
    evidence = result.get("evidence", {})
    lines = [
        "# FINAL_RETURN_PERSONAL_AI_EXECUTION_MCP_RUNTIME_DEPLOY_VERIFY_01",
        "",
        f"- task_id: {DEPLOY_VERIFY_TASK_ID}",
        f"- target_commit: {DEPLOY_VERIFY_COMMIT}",
        f"- head_commit: {head}",
        f"- target_commit_on_history: {target_on_history}",
        f"- worker_asset: {worker or 'absent'}",
        f"- deploy_workflows: {', '.join(deploy_workflows) or 'absent'}",
        f"- online_mcp_version: unavailable (offline verification environment)",
        f"- get_task_result status: {summary.get('status')}",
        f"- get_task_result commit: {result.get('commit')}",
        "",
        "## Required return fields",
    ]
    for name, present in result_fields.items():
        lines.append(f"- {name}: {'returned' if present else 'MISSING'}")
    lines += [
        "",
        "## Checks",
    ]
    for check in checks:
        lines.append(f"- [{check['status']}] {check['check']}: {check['detail']}")
    lines += [
        "",
        f"## Final status: {final_status}",
        "",
        f"evidence.decision.status: {evidence.get('decision', {}).get('status')}",
    ]
    return "\n".join(lines)
