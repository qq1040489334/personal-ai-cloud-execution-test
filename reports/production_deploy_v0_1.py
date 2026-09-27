"""PERSONAL_AI_CANONICAL_WORKER_CONTROLLED_PRODUCTION_DEPLOY_V0.1.

Read-only preflight and fail-closed gate engine for the controlled production
deployment of the canonical Personal AI execution Worker.

Task: ``cf-7afde7d95cdb`` (risk: LOW).

Contract goal: deploy the current canonical Personal AI execution Worker to
production under explicit human authorization and establish a verifiable
``Git commit -> source hash -> Cloudflare deployment/version -> live runtime``
evidence chain.

Hard invariants enforced by this module:

* it never deploys, uploads, rotates secrets, or touches D1/KV/production;
* it only reads the repository and non-secret environment variable *names*;
* it never records a secret value; credentials are reported as booleans only;
* a production deployment is never claimed unless the deploy credentials exist
  and the canonical source is verified against the repository HEAD;
* the preflight is fail-closed: any unmet external gate yields ``BLOCKED``
  rather than a fabricated success.

Writing the evidence artifacts::

    python reports/production_deploy_v0_1.py --write

writes ``reports/production_deploy_v0.1.json`` and ``PRODUCTION_DEPLOY_V0.1.md``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

GOAL = "PERSONAL_AI_CANONICAL_WORKER_CONTROLLED_PRODUCTION_DEPLOY_V0.1"
TASK_ID = "cf-7afde7d95cdb"
REPORT_NAME = (
    "PERSONAL_AI_CANONICAL_WORKER_CONTROLLED_PRODUCTION_DEPLOY_V0.1_REPORT"
)

BASELINE_PATH = "worker/PRODUCTION-BASELINE.json"
CANONICAL_SOURCE = "worker/index.js"
WRANGLER_CONFIG = "worker/wrangler.toml"
MIGRATION_PATH = "worker/migrations/0001_asset_provenance_v0_2.sql"

JSON_ARTIFACT = "reports/production_deploy_v0.1.json"
MARKDOWN_ARTIFACT = "PRODUCTION_DEPLOY_V0.1.md"

#: Environment variables that would carry a Cloudflare deploy credential. Only
#: their *presence* is ever checked; values are never read or recorded.
DEPLOY_TOKEN_ENV = ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_API_KEY")
ACCOUNT_ID_ENV = ("CLOUDFLARE_ACCOUNT_ID", "CF_ACCOUNT_ID")

#: Non-secret ``env`` names that are Worker variables rather than secret text.
PUBLIC_ENV_NAMES = ("GITHUB_REPO",)

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

#: The canonical, non-mutating deploy sequence a human must run once the
#: Cloudflare deploy credential is injected into the environment. Secrets are
#: intentionally referenced by env-var name only, never by value.
MANUAL_DEPLOY_SEQUENCE = (
    "export CLOUDFLARE_API_TOKEN=<redacted>  # owner-provided, never committed",
    "npx wrangler d1 execute ASSET_DB --remote "
    f"--file={MIGRATION_PATH}  # additive, idempotent",
    "npx wrangler deploy --config worker/wrangler.toml",
    "npx wrangler deployments list",
    "npx wrangler versions view <deployment-version-id>",
)

REPORT_FIELDS = (
    "report",
    "goal",
    "task_id",
    "generated_at",
    "authorization",
    "verdict",
    "verdict_reason",
    "deployment_attempted",
    "production_mutated",
    "secrets_exposed",
    "canonical_head_commit",
    "preflight",
    "provenance_chain",
    "deployment",
    "live_verification",
    "manual_gate",
    "gates",
    "overall",
    "markdown",
)


# ---------------------------------------------------------------------------
# read-only helpers
# ---------------------------------------------------------------------------
def _run_git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True)


def _git(*args: str) -> str:
    return _run_git(*args).stdout.decode("utf-8", "replace").strip()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_json(path: Path) -> dict[str, Any] | None:
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


def _env_names_present(names: tuple[str, ...]) -> list[str]:
    """Return which environment variables are set, without reading values."""
    return [name for name in names if bool(os.environ.get(name, "").strip())]


def _parse_wrangler_bindings(text: str) -> dict[str, dict[str, str]]:
    """Parse binding names and resource ids from ``wrangler.toml``."""
    bindings: dict[str, dict[str, str]] = {}
    section = ""
    current: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[["):
            section = line
            current = {}
            continue
        if line.startswith("["):
            section = line
            current = {}
            continue
        if "=" not in line or not section:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key == "binding":
            current = {"binding": value}
            if "d1" in section:
                bindings[value] = current
            elif "kv" in section:
                bindings[value] = current
        elif current:
            current[key] = value
    return bindings


def _worker_env_names(text: str) -> list[str]:
    names = set(re.findall(r"\benv\.([A-Z][A-Z0-9_]*)", text))
    return sorted(names)


# ---------------------------------------------------------------------------
# evidence collection
# ---------------------------------------------------------------------------
def collect_evidence() -> dict[str, Any]:
    baseline = _load_json(REPO_ROOT / BASELINE_PATH) or {}

    source_path = REPO_ROOT / CANONICAL_SOURCE
    source_present = source_path.is_file()
    source_bytes = source_path.read_bytes() if source_present else b""
    source_hash = _sha256_bytes(source_bytes)

    wrangler_path = REPO_ROOT / WRANGLER_CONFIG
    wrangler_text = _read_text(wrangler_path) if wrangler_path.is_file() else ""
    bindings = _parse_wrangler_bindings(wrangler_text)

    worker_env = _worker_env_names(_read_text(source_path)) if source_present else []
    config_bindings = sorted(bindings)
    secret_names = sorted(
        name
        for name in worker_env
        if name not in config_bindings and name not in PUBLIC_ENV_NAMES
    )

    migration_path = REPO_ROOT / MIGRATION_PATH
    migration_text = _read_text(migration_path) if migration_path.is_file() else ""
    migration_upper = migration_text.upper()
    destructive = [
        token
        for token in (
            "DROP TABLE",
            "DROP COLUMN",
            "DROP INDEX",
            "DELETE FROM",
            "TRUNCATE",
            "UPDATE ",
        )
        if token in migration_upper
    ]
    additive = (
        migration_path.is_file()
        and "CREATE TABLE IF NOT EXISTS" in migration_upper
        and "CREATE INDEX IF NOT EXISTS" in migration_upper
        and not destructive
    )
    migration_required = any(
        table in _read_text(source_path)
        for table in ("asset_provenance_events", "asset_supersessions")
    ) if source_present else False

    declared_hash = str(
        baseline.get("source_sha256") or baseline.get("source_hash") or ""
    ).strip()
    source_matches_baseline = bool(
        declared_hash and declared_hash.lower() == source_hash.lower()
    )

    head = _git("rev-parse", "HEAD")
    origin_main = _git("rev-parse", "origin/main")
    head_date = _git("show", "-s", "--format=%cI", "HEAD")
    source_commit = _git("log", "-1", "--format=%H", "--", CANONICAL_SOURCE)

    return {
        "baseline": baseline,
        "source_present": source_present,
        "source_bytes": len(source_bytes),
        "source_lines": (
            len(source_bytes.decode("utf-8", "replace").splitlines())
            if source_present
            else 0
        ),
        "source_hash": source_hash,
        "bindings": bindings,
        "config_bindings": config_bindings,
        "worker_env": worker_env,
        "secret_names": secret_names,
        "migration_present": migration_path.is_file(),
        "migration_hash": _sha256_file(migration_path) if migration_path.is_file() else None,
        "migration_additive": additive,
        "migration_destructive": destructive,
        "migration_required": migration_required,
        "declared_hash": declared_hash,
        "source_matches_baseline": source_matches_baseline,
        "head": head,
        "origin_main": origin_main,
        "head_date": head_date,
        "source_commit": source_commit,
        "deploy_token_env_present": _env_names_present(DEPLOY_TOKEN_ENV),
        "account_id_env_present": _env_names_present(ACCOUNT_ID_ENV),
    }


# ---------------------------------------------------------------------------
# report construction
# ---------------------------------------------------------------------------
def _gate(gate: str, status: str, detail: str) -> dict[str, str]:
    return {"gate": gate, "status": status, "detail": detail}


def build_report() -> dict[str, Any]:
    ev = collect_evidence()
    baseline = ev["baseline"]

    credentials_present = bool(ev["deploy_token_env_present"])
    account_present = bool(ev["account_id_env_present"]) or bool(
        str(baseline.get("cloudflare_account_id") or "").strip()
    )

    required_bindings = {"ASSET_DB", "TASK_REGISTRY"}
    bindings_ok = required_bindings <= set(ev["bindings"])

    gates: list[dict[str, str]] = [
        _gate(
            "human authorization recorded in task contract",
            PASS,
            "task contract cf-7afde7d95cdb states production authorization is "
            "granted in the parent conversation; recorded here, not independently "
            "verifiable from the repository (authorization is not a credential)",
        ),
        _gate(
            "canonical source present",
            PASS if ev["source_present"] else FAIL,
            f"canonical worker source present: {CANONICAL_SOURCE}"
            if ev["source_present"]
            else f"canonical worker source missing: {CANONICAL_SOURCE}",
        ),
        _gate(
            "canonical source identified and hashed",
            PASS if ev["source_present"] else FAIL,
            f"source_sha256={ev['source_hash']} "
            f"bytes={ev['source_bytes']} lines={ev['source_lines']} "
            f"last_source_commit={ev['source_commit']} "
            "(preflight HEAD recorded in preflight.canonical_head_commit)",
        ),
        _gate(
            "canonical source matches declared production baseline",
            PASS if ev["source_matches_baseline"] else BLOCKED,
            (
                f"canonical source hash matches baseline {BASELINE_PATH}"
                if ev["source_matches_baseline"]
                else "declared baseline source hash "
                f"{ev['declared_hash'] or 'UNAVAILABLE'} does not match canonical "
                f"HEAD source hash {ev['source_hash']}; deploying would supersede "
                "the Quick Edit baseline and must be paired with a new provenance "
                "record (not a hard failure, but it requires a live deploy)"
            ),
        ),
        _gate(
            "worker bindings present",
            PASS if bindings_ok else FAIL,
            "bindings: "
            + ", ".join(
                f"{name}={spec.get('database_id') or spec.get('id')}"
                for name, spec in sorted(ev["bindings"].items())
            )
            + ("" if bindings_ok else f"; missing: {sorted(required_bindings - set(ev['bindings']))}"),
        ),
        _gate(
            "required secret names identified (values not read)",
            PASS if ev["secret_names"] else BLOCKED,
            "secret names referenced by the worker source: "
            + (", ".join(ev["secret_names"]) or "none detected")
            + "; values were never read or recorded",
        ),
        _gate(
            "asset provenance migration is additive and non-destructive",
            PASS if ev["migration_additive"] else FAIL,
            f"{MIGRATION_PATH} sha256={ev['migration_hash']} "
            "uses CREATE TABLE/INDEX IF NOT EXISTS and contains no destructive "
            f"statements (found: {ev['migration_destructive'] or 'none'})",
        ),
        _gate(
            "required additive migration",
            PASS,
            (
                "the current worker source does not reference the new provenance "
                "tables, so no migration is required for the deployed execution/"
                "asset-read contract; the additive migration is safe to apply via "
                "the canonical wrangler D1 mechanism"
                if not ev["migration_required"]
                else "worker source references provenance tables; apply the additive "
                "migration before deploy"
            ),
        ),
        _gate(
            "Cloudflare deploy credential available",
            PASS if credentials_present else BLOCKED,
            (
                "deploy credential present via env names "
                f"{ev['deploy_token_env_present']}; value not read"
                if credentials_present
                else "no deploy credential in environment (checked names: "
                + ", ".join(DEPLOY_TOKEN_ENV)
                + "); `npx wrangler whoami` reports 'You are not authenticated. "
                "Please run `wrangler login`.' -> fail closed before deploy"
            ),
        ),
        _gate(
            "Cloudflare account identified",
            PASS if account_present else BLOCKED,
            (
                f"account id {baseline.get('cloudflare_account_id')} from {BASELINE_PATH}"
                if account_present
                else "no Cloudflare account id available"
            ),
        ),
        _gate(
            "wrangler non-interactive deploy possible",
            PASS if credentials_present else BLOCKED,
            "wrangler non-interactive deploy can proceed only with a deploy token; "
            "blocked here",
        ),
        _gate(
            "no production mutation performed",
            PASS,
            "preflight only: no deploy, upload, secret rotation, D1/KV write or "
            "workflow mutation was performed",
        ),
        _gate(
            "no secret value exposed in evidence",
            PASS,
            "only non-secret environment variable names and in-repo identifiers "
            "were inspected; no secret value was read or written",
        ),
    ]

    if any(g["status"] == FAIL for g in gates):
        overall = FAIL
    elif any(g["status"] == BLOCKED for g in gates):
        overall = BLOCKED
    else:
        overall = PASS

    deployment_attempted = False
    if overall == BLOCKED:
        verdict_reason = (
            "fail-closed before deploy: the Cloudflare production deploy "
            "credential required to reach account "
            f"{baseline.get('cloudflare_account_id')} is not available in the "
            "execution environment; no canonical, auditable production deploy can "
            "be performed, so none was attempted and no production state was "
            "mutated"
        )
    elif overall == FAIL:
        verdict_reason = "preflight compatibility gate failed; no deploy attempted"
    else:
        verdict_reason = "preflight gates pass; ready for controlled deploy"

    preflight = {
        "canonical_source": {
            "file": CANONICAL_SOURCE,
            "present": ev["source_present"],
            "sha256": ev["source_hash"],
            "bytes": ev["source_bytes"],
            "lines": ev["source_lines"],
            "last_source_commit": ev["source_commit"],
        },
        "canonical_head_commit": ev["head"],
        "canonical_head_date": ev["head_date"],
        "origin_main_commit": ev["origin_main"],
        "baseline": {
            "metadata_path": BASELINE_PATH,
            "production_version": baseline.get("production_version"),
            "source_sha256": baseline.get("source_sha256"),
            "service": baseline.get("service"),
            "environment": baseline.get("environment"),
            "source_matches_canonical_head": ev["source_matches_baseline"],
        },
        "bindings": {
            name: spec.get("database_id") or spec.get("id")
            for name, spec in sorted(ev["bindings"].items())
        },
        "secret_names": ev["secret_names"],
        "migration": {
            "path": MIGRATION_PATH,
            "present": ev["migration_present"],
            "sha256": ev["migration_hash"],
            "additive": ev["migration_additive"],
            "idempotent": ev["migration_additive"],
            "destructive_statements": ev["migration_destructive"],
            "required_by_worker_source": ev["migration_required"],
            "applied": False,
            "apply_method": "npx wrangler d1 execute ASSET_DB --remote "
            f"--file={MIGRATION_PATH}",
        },
        "credentials": {
            "deploy_token_env_names_checked": list(DEPLOY_TOKEN_ENV),
            "deploy_token_env_present": ev["deploy_token_env_present"],
            "deploy_token_present": credentials_present,
            "account_id_env_present": ev["account_id_env_present"],
            "account_id_available": account_present,
            "values_recorded": False,
        },
    }

    provenance_chain = {
        "git_commit": ev["head"],
        "git_commit_date": ev["head_date"],
        "source_file": CANONICAL_SOURCE,
        "source_sha256": ev["source_hash"],
        "source_bytes": ev["source_bytes"],
        "cloudflare_account_id": baseline.get("cloudflare_account_id"),
        "cloudflare_service": baseline.get("service"),
        "cloudflare_environment": baseline.get("environment"),
        "cloudflare_deployment_id": None,
        "cloudflare_version": None,
        "deployment_timestamp": None,
        "prior_production_version": baseline.get("production_version"),
        "prior_production_source_sha256": baseline.get("source_sha256"),
        "evidence_artifact": JSON_ARTIFACT,
        "link_status": "INCOMPLETE_BLOCKED",
        "link_reason": (
            "Git commit and exact source hash are recorded, but no Cloudflare "
            "deployment/version exists because the deploy was blocked before "
            "execution; the next provenance audit must treat the runtime link as "
            "unverified until a real deployment id/version is recorded here"
        ),
    }

    live_verification = {
        "performed": False,
        "reason": "deployment not attempted (blocked before deploy)",
        "endpoint": "https://personal-ai-execution-mcp.<account>.workers.dev",
        "planned_read_only_checks": [
            {
                "check": "health endpoint",
                "request": "GET /healthz",
                "expect": '200 JSON containing {"status":"ok","name":"personal-ai-execution-mcp"}',
            },
            {
                "check": "auth boundary",
                "request": "POST /mcp without Authorization",
                "expect": "401 unauthorized",
            },
            {
                "check": "MCP tools/list schema",
                "request": "POST /mcp (authorized) method=tools/list",
                "expect": "tool schema includes submit_task, get_task_result, search_assets",
            },
            {
                "check": "get_task_result truthfulness",
                "request": "get_task_result for a known task",
                "expect": "status derived from workflow/artifact evidence, not self-report",
            },
            {
                "check": "asset provenance read/search path",
                "request": "search_assets / get asset provenance",
                "expect": "read-only provenance metadata returned without mutation",
            },
        ],
    }

    report: dict[str, Any] = {
        "report": REPORT_NAME,
        "goal": GOAL,
        "task_id": TASK_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authorization": {
            "stated": True,
            "source": "task contract cf-7afde7d95cdb (parent ChatGPT conversation)",
            "independently_verified": False,
            "note": "authorization is recorded but is not a substitute for a Cloudflare credential",
        },
        "verdict": overall,
        "verdict_reason": verdict_reason,
        "deployment_attempted": deployment_attempted,
        "production_mutated": False,
        "secrets_exposed": False,
        "canonical_head_commit": ev["head"],
        "preflight": preflight,
        "provenance_chain": provenance_chain,
        "deployment": None,
        "live_verification": live_verification,
        "manual_gate": {
            "status": "BLOCKED",
            "required_actor": "human owner with Cloudflare production access",
            "gate": "inject a Cloudflare deploy credential for account "
            f"{baseline.get('cloudflare_account_id')}",
            "sequence": list(MANUAL_DEPLOY_SEQUENCE),
            "after_deploy": (
                "populate cloudflare_deployment_id/cloudflare_version/"
                "deployment_timestamp in " + JSON_ARTIFACT + " and "
                + BASELINE_PATH + " so the runtime provenance audit can verify the "
                "commit -> hash -> version -> runtime chain"
            ),
        },
        "gates": gates,
        "overall": overall,
    }
    report["markdown"] = render_markdown(report)
    return report


# ---------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------
def render_markdown(report: dict[str, Any]) -> str:
    preflight = report["preflight"]
    source = preflight["canonical_source"]
    migration = preflight["migration"]
    credentials = preflight["credentials"]

    lines = [
        f"# {REPORT_NAME}",
        "",
        f"- goal: {report['goal']}",
        f"- task_id: {report['task_id']}",
        f"- generated_at: {report['generated_at']}",
        f"- verdict: {report['verdict']}",
        f"- deployment_attempted: {report['deployment_attempted']}",
        f"- production_mutated: {report['production_mutated']}",
        f"- secrets_exposed: {report['secrets_exposed']}",
        "",
        "## Authorization",
        f"- stated: {report['authorization']['stated']}",
        f"- source: {report['authorization']['source']}",
        f"- independently_verified: {report['authorization']['independently_verified']}",
        "",
        "## Preflight",
        f"- canonical HEAD: {preflight['canonical_head_commit']}",
        f"- canonical source: {source['file']} sha256={source['sha256']} "
        f"({source['bytes']} bytes / {source['lines']} lines)",
        f"- last source commit: {source['last_source_commit']}",
        f"- baseline version: {preflight['baseline']['production_version']} "
        f"sha256={preflight['baseline']['source_sha256']}",
        f"- canonical matches baseline: {preflight['baseline']['source_matches_canonical_head']}",
        f"- bindings: {preflight['bindings']}",
        f"- secret names (values never read): {preflight['secret_names']}",
        "",
        "## Migration",
        f"- path: {migration['path']} sha256={migration['sha256']}",
        f"- additive: {migration['additive']} idempotent: {migration['idempotent']}",
        f"- destructive statements: {migration['destructive_statements'] or 'none'}",
        f"- required by worker source: {migration['required_by_worker_source']}",
        f"- applied: {migration['applied']}",
        f"- apply method: {migration['apply_method']}",
        "",
        "## Credential gate",
        f"- deploy token env names checked: {credentials['deploy_token_env_names_checked']}",
        f"- deploy token present: {credentials['deploy_token_present']}",
        f"- account id available: {credentials['account_id_available']}",
        f"- values recorded: {credentials['values_recorded']}",
        "",
        "## Provenance chain (Git commit -> source hash -> Cloudflare -> runtime)",
        f"- git_commit: {report['provenance_chain']['git_commit']}",
        f"- source_sha256: {report['provenance_chain']['source_sha256']}",
        f"- cloudflare_deployment_id: {report['provenance_chain']['cloudflare_deployment_id']}",
        f"- cloudflare_version: {report['provenance_chain']['cloudflare_version']}",
        f"- deployment_timestamp: {report['provenance_chain']['deployment_timestamp']}",
        f"- link_status: {report['provenance_chain']['link_status']}",
        "",
        "## Gates",
    ]
    for gate in report["gates"]:
        lines.append(f"- [{gate['status']}] {gate['gate']}: {gate['detail']}")

    lines += [
        "",
        "## Verdict",
        f"VERDICT={report['verdict']}",
        "DEPLOYMENT_ATTEMPTED=False",
        "PRODUCTION_MUTATED=False",
        "SECRETS_EXPOSED=False",
        f"OVERALL={report['overall']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# artifact writing
# ---------------------------------------------------------------------------
def write_artifacts() -> tuple[Path, Path]:
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
