"""Minimal module for the cloud execution golden test."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

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
