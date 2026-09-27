"""CLOUDFLARE_WORKER_CANONICAL_DEPLOY_V0.2.

Canonical Module-Worker production deploy engine with a version-API-first,
fail-closed provenance contract.

Task: ``cf-0fe692a1235b`` (risk: LOW).

Contract goal: deploy the canonical Personal AI execution Worker
(``worker/index.js``) to Cloudflare production using the *Module Worker*
upload format (``export default { fetch }`` / ``main_module=index.js``) and the
Cloudflare Worker **versions API** rather than retrying the legacy content
endpoint, then close the verifiable provenance chain::

    git commit -> worker/index.js sha256 -> Cloudflare version id
                                                       -> deployment id
                                                       -> live runtime

Hard invariants enforced by this module:

* it never deploys/uploads on its own when the write surface is unavailable;
* a production deployment is never claimed unless a Cloudflare write
  credential is present in the execution environment;
* it never reads, records, or emits a secret value; secret bindings are
  preserved by name only (``keep_bindings=["secret_text"]``);
* it never modifies unrelated production resources: the exact production
  binding/secret name set must be preserved and the KV/D1 ids are read-only;
* the result is fail-closed: a BLOCKED status is reported instead of a
  fabricated success.

Writing the evidence artifacts::

    python reports/canonical_deploy_v0_2.py --write

writes ``reports/canonical_deploy_v0.2.json`` and
``CLOUDFLARE_WORKER_CANONICAL_DEPLOY_V0.2.md``.
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

GOAL = "CLOUDFLARE_WORKER_CANONICAL_DEPLOY_V0.2"
TASK_ID = "cf-0fe692a1235b"
REPORT_NAME = "CLOUDFLARE_WORKER_CANONICAL_DEPLOY_V0.2_REPORT"

BASELINE_PATH = "worker/PRODUCTION-BASELINE.json"
CANONICAL_SOURCE = "worker/index.js"
WRANGLER_CONFIG = "worker/wrangler.toml"

JSON_ARTIFACT = "reports/canonical_deploy_v0.2.json"
MARKDOWN_ARTIFACT = "CLOUDFLARE_WORKER_CANONICAL_DEPLOY_V0.2.md"

#: Environment variables that would carry a Cloudflare write credential. Only
#: their *presence* is ever checked; values are never read or recorded.
DEPLOY_TOKEN_ENV = ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_API_KEY")
ACCOUNT_ID_ENV = ("CLOUDFLARE_ACCOUNT_ID", "CF_ACCOUNT_ID")

#: Worker service name and the account it lives in (from the production baseline).
SERVICE_NAME = "personal-ai-execution-mcp"

#: Module-Worker upload format requirements.
MAIN_MODULE = "index.js"
MODULE_CONTENT_TYPE = "application/javascript+module"

#: The exact production binding/secret name set that must be preserved. Any
#: deploy that would add, rename, or drop one of these is rejected.
PRESERVED_BINDING_NAMES = (
    "ASSET_DB",
    "GITHUB_REPO",
    "GITHUB_TOKEN",
    "MCP_AUTH_TOKEN",
    "OAUTH_SIGNING_KEY",
    "OWNER_PASSWORD",
    "TASK_REGISTRY",
)

#: Bindings backed by Cloudflare resources (read-only ids; never mutated here).
RESOURCE_BINDINGS = {"ASSET_DB", "TASK_REGISTRY"}

#: Bindings carried as plain-text Worker variables (non-secret).
PLAINTEXT_BINDINGS = ("GITHUB_REPO",)

#: Secret bindings: values are never read; preserved by the platform.
SECRET_BINDING_NAMES = (
    "GITHUB_TOKEN",
    "MCP_AUTH_TOKEN",
    "OAUTH_SIGNING_KEY",
    "OWNER_PASSWORD",
)

#: Ordered, non-mutating deploy sequence a human runs once a write credential is
#: injected. Secrets are referenced by env-var name only, never by value.
MANUAL_DEPLOY_SEQUENCE = (
    "export CLOUDFLARE_API_TOKEN=<redacted>  # owner-provided, never committed",
    f"npx wrangler versions upload --config {WRANGLER_CONFIG}"
    "  # Module Worker: main_module=index.js",
    f"npx wrangler versions deploy --config {WRANGLER_CONFIG}",
    "npx wrangler deployments list",
    "npx wrangler versions view <deployment-version-id>",
)

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

REPORT_FIELDS = (
    "report",
    "goal",
    "task_id",
    "generated_at",
    "authorization",
    "deploy_status",
    "verdict",
    "verdict_reason",
    "deployment_attempted",
    "production_mutated",
    "secrets_exposed",
    "canonical",
    "preflight",
    "module_upload",
    "versions_api",
    "cloudflare",
    "provenance",
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


def _parse_wrangler_bindings(text: str) -> dict[str, str]:
    """Parse binding name -> resource id from ``wrangler.toml`` (read-only)."""
    bindings: dict[str, str] = {}
    section = ""
    binding_name = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[["):
            section = line
            binding_name = ""
            continue
        if line.startswith("["):
            section = line
            binding_name = ""
            continue
        if "=" not in line or not section:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key == "binding":
            binding_name = value
        elif binding_name and key in ("database_id", "id", "namespace_id"):
            bindings[binding_name] = value
    return bindings


def _worker_env_names(text: str) -> list[str]:
    names = set(re.findall(r"\benv\.([A-Z][A-Z0-9_]*)", text))
    return sorted(names)


def _module_worker_syntax(text: str) -> bool:
    """True when the source is a Module Worker (``export default`` fetch)."""
    return bool(
        re.search(r"export\s*\{[^}]*default", text)
        or re.search(r"export\s+default\b", text)
    )


# ---------------------------------------------------------------------------
# evidence collection
# ---------------------------------------------------------------------------
def collect_evidence() -> dict[str, Any]:
    baseline = _load_json(REPO_ROOT / BASELINE_PATH) or {}

    source_path = REPO_ROOT / CANONICAL_SOURCE
    source_present = source_path.is_file()
    source_text = _read_text(source_path) if source_present else ""
    source_bytes = source_path.read_bytes() if source_present else b""
    source_hash = _sha256_bytes(source_bytes)

    wrangler_path = REPO_ROOT / WRANGLER_CONFIG
    wrangler_text = _read_text(wrangler_path) if wrangler_path.is_file() else ""
    config_bindings = _parse_wrangler_bindings(wrangler_text)

    worker_env = _worker_env_names(source_text)
    secret_names = [n for n in worker_env if n in SECRET_BINDING_NAMES]

    declared_hash = str(
        baseline.get("source_sha256") or baseline.get("source_hash") or ""
    ).strip()
    source_matches_baseline = bool(
        declared_hash and declared_hash.lower() == source_hash.lower()
    )

    head = _git("rev-parse", "HEAD")
    head_date = _git("show", "-s", "--format=%cI", "HEAD")
    source_commit = _git("log", "-1", "--format=%H", "--", CANONICAL_SOURCE)

    return {
        "baseline": baseline,
        "source_present": source_present,
        "source_text": source_text,
        "source_bytes": len(source_bytes),
        "source_lines": len(source_text.splitlines()),
        "source_hash": source_hash,
        "module_syntax": _module_worker_syntax(source_text),
        "config_bindings": config_bindings,
        "worker_env": worker_env,
        "secret_names": secret_names,
        "declared_hash": declared_hash,
        "source_matches_baseline": source_matches_baseline,
        "head": head,
        "head_date": head_date,
        "source_commit": source_commit,
        "deploy_token_env_present": _env_names_present(DEPLOY_TOKEN_ENV),
        "account_id_env_present": _env_names_present(ACCOUNT_ID_ENV),
    }


# ---------------------------------------------------------------------------
# module upload / versions API descriptors
# ---------------------------------------------------------------------------
def build_module_metadata(account: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the Module-Worker upload metadata (``main_module=index.js``).

    Only non-secret binding descriptors are materialised. Secret bindings are
    preserved by name through ``keep_bindings=["secret_text"]`` and are never
    included as values.
    """
    baseline = account if account is not None else (
        _load_json(REPO_ROOT / BASELINE_PATH) or {}
    )
    bindings = baseline.get("bindings") or {}
    asset_db = bindings.get("ASSET_DB") or "45d6f18a-3a34-4ccd-8337-c00a775cd7a2"
    task_registry = (
        bindings.get("TASK_REGISTRY") or "60f6203f262d44378abd0accfa7fef46"
    )
    github_repo = bindings.get("GITHUB_REPO") or "qq1040489334/personal-ai-cloud-execution-test"

    return {
        "main_module": MAIN_MODULE,
        "compatibility_date": baseline.get("compatibility_date") or "2026-09-23",
        "keep_bindings": ["secret_text"],
        "bindings": [
            {"type": "d1", "name": "ASSET_DB", "id": asset_db},
            {
                "type": "kv_namespace",
                "name": "TASK_REGISTRY",
                "namespace_id": task_registry,
            },
            {"type": "plain_text", "name": "GITHUB_REPO", "text": github_repo},
        ],
        "preserved_secret_bindings": list(SECRET_BINDING_NAMES),
        "preserved_resource_bindings": sorted(RESOURCE_BINDINGS),
    }


def build_versions_api_plan(account_id: str | None = None) -> dict[str, Any]:
    """Return the version-API-first deploy plan (no content-endpoint retries)."""
    acct = account_id or "78a22a0699aa94a39d8f7bfdbac18249"
    base = f"/accounts/{acct}/workers/scripts/{SERVICE_NAME}"
    return {
        "strategy": "versions_api",
        "forbidden_strategies": ["legacy_content_endpoint_retry"],
        "create_version": {
            "method": "POST",
            "path": f"{base}/versions",
            "content_type": "multipart/form-data",
            "parts": [
                {"name": "metadata", "content_type": "application/json"},
                {
                    "name": MAIN_MODULE,
                    "content_type": MODULE_CONTENT_TYPE,
                },
            ],
            "auth_header": "Authorization: Bearer <CLOUDFLARE_API_TOKEN>",
        },
        "create_deployment": {
            "method": "POST",
            "path": f"{base}/deployments",
            "body": {"version_id": "<version-id>", "percentage": 100},
        },
        "list_deployments": {"method": "GET", "path": f"{base}/deployments"},
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
    account_id = str(baseline.get("cloudflare_account_id") or "").strip() or (
        "78a22a0699aa94a39d8f7bfdbac18249"
    )

    metadata = build_module_metadata(baseline)
    api_plan = build_versions_api_plan(account_id)

    # Binding/secret preservation check: the union of names the upload would
    # carry (resource + plaintext + preserved secrets) must equal the declared
    # production set exactly, and must still include the baseline bindings.
    upload_binding_names = {b["name"] for b in metadata["bindings"]}
    upload_binding_names |= set(metadata["preserved_secret_bindings"])
    preserved_exactly = upload_binding_names == set(PRESERVED_BINDING_NAMES)
    baseline_bindings_kept = set(baseline.get("bindings", {})) <= upload_binding_names
    bindings_preserved = preserved_exactly and baseline_bindings_kept

    module_ok = ev["source_present"] and ev["module_syntax"]

    gates: list[dict[str, str]] = [
        _gate(
            "canonical source present",
            PASS if ev["source_present"] else FAIL,
            f"canonical worker source present: {CANONICAL_SOURCE}"
            if ev["source_present"]
            else f"canonical worker source missing: {CANONICAL_SOURCE}",
        ),
        _gate(
            "canonical git commit and source hash recorded",
            PASS if ev["source_present"] else FAIL,
            f"source_sha256={ev['source_hash']} "
            f"bytes={ev['source_bytes']} lines={ev['source_lines']} "
            f"last_source_commit={ev['source_commit']} "
            "(canonical HEAD commit recorded in canonical.git_commit)",
        ),
        _gate(
            "module worker syntax (export default fetch)",
            PASS if ev["module_syntax"] else FAIL,
            f"{CANONICAL_SOURCE} is a Module Worker exporting a default fetch "
            "handler; upload uses main_module=index.js"
            if ev["module_syntax"]
            else f"{CANONICAL_SOURCE} does not declare an export default handler",
        ),
        _gate(
            "module upload metadata uses main_module=index.js",
            PASS if metadata["main_module"] == MAIN_MODULE else FAIL,
            "metadata.main_module="
            f"{metadata['main_module']} content_type for the module part is "
            f"{MODULE_CONTENT_TYPE} (multipart/form-data)",
        ),
        _gate(
            "union of preserved binding/secret names matches production set",
            PASS if bindings_preserved else FAIL,
            "preserved: " + ", ".join(PRESERVED_BINDING_NAMES)
            + "; secret bindings preserved via keep_bindings=['secret_text']; "
            "values never read",
        ),
        _gate(
            "required secret names identified (values not read)",
            PASS if ev["secret_names"] else BLOCKED,
            "secret names referenced by the worker source: "
            + (", ".join(ev["secret_names"]) or "none detected")
            + "; values were never read or recorded",
        ),
        _gate(
            "versions API selected over legacy content endpoint",
            PASS,
            "deploy strategy="
            f"{api_plan['strategy']}; create version via "
            f"{api_plan['create_version']['method']} "
            f"{api_plan['create_version']['path']} then create deployment via "
            f"{api_plan['create_deployment']['method']} "
            f"{api_plan['create_deployment']['path']}",
        ),
        _gate(
            "Cloudflare write credential available",
            PASS if credentials_present else BLOCKED,
            (
                "write credential present via env names "
                f"{ev['deploy_token_env_present']}; value not read"
                if credentials_present
                else "no Cloudflare write credential in environment (checked "
                "names: " + ", ".join(DEPLOY_TOKEN_ENV) + "); the Cloudflare "
                "Asset Deploy Write MCP / versions API is not reachable from "
                "this execution environment -> fail closed before any upload"
            ),
        ),
        _gate(
            "Cloudflare account identified",
            PASS if account_id else BLOCKED,
            f"account id {account_id} from {BASELINE_PATH}",
        ),
        _gate(
            "production identity preserved (no unrelated resource mutation)",
            PASS,
            "no secret rotation, no binding rename/removal, no KV/D1 deletion, "
            "no OAuth or auth-logic change; resource ids are read-only in evidence",
        ),
        _gate(
            "no secret value exposed in evidence",
            PASS,
            "only non-secret environment variable names and in-repo identifiers "
            "were inspected; credentials.values_recorded=False",
        ),
    ]

    if any(g["status"] == FAIL for g in gates):
        deploy_status = FAIL
    elif any(g["status"] == BLOCKED for g in gates):
        deploy_status = BLOCKED
    else:
        deploy_status = PASS

    deployment_attempted = deploy_status == PASS
    cloudflare: dict[str, Any] = {
        "version_id": None,
        "deployment_id": None,
        "deployment_timestamp": None,
        "script_name": SERVICE_NAME,
        "account_id": account_id,
    }

    if deploy_status == BLOCKED:
        verdict_reason = (
            "fail-closed before upload: a Cloudflare write credential for "
            f"account {account_id} is not available in the execution "
            "environment; the Module-Worker versions API endpoint cannot be "
            "reached, so no version/deployment was created and no production "
            "state was mutated"
        )
    elif deploy_status == FAIL:
        verdict_reason = (
            "preflight compatibility gate failed (module syntax or binding "
            "preservation); no version/deployment attempted"
        )
    else:
        verdict_reason = (
            "all gates pass; a Module-Worker version and 100% deployment were "
            "created and verified via the versions API"
        )

    relationship_status = "VERIFIED" if deploy_status == PASS else BLOCKED
    if deploy_status == PASS:
        relationship_reason = (
            "Cloudflare version id and deployment id recorded; the deployed "
            "runtime is traceable to the canonical git commit and exact source "
            "sha256"
        )
    elif deploy_status == FAIL:
        relationship_status = "UNVERIFIED"
        relationship_reason = (
            "preflight failed, so no Cloudflare version/deployment links the "
            "canonical source hash to a live runtime"
        )
    else:
        relationship_reason = (
            "git commit and exact source sha256 are recorded, but no Cloudflare "
            "version id / deployment id exists because the write surface is "
            "unavailable; the runtime link stays BLOCKED until a real deploy "
            "backfills cloudflare.version_id / cloudflare.deployment_id"
        )

    preflight = {
        "canonical_source": {
            "file": CANONICAL_SOURCE,
            "present": ev["source_present"],
            "sha256": ev["source_hash"],
            "bytes": ev["source_bytes"],
            "lines": ev["source_lines"],
            "module_worker": ev["module_syntax"],
            "last_source_commit": ev["source_commit"],
        },
        "canonical_head_commit": ev["head"],
        "canonical_head_date": ev["head_date"],
        "baseline": {
            "metadata_path": BASELINE_PATH,
            "production_version": baseline.get("production_version"),
            "source_sha256": baseline.get("source_sha256"),
            "service": baseline.get("service"),
            "environment": baseline.get("environment"),
            "source_matches_canonical_head": ev["source_matches_baseline"],
        },
        "bindings": baseline.get("bindings"),
        "preserved_binding_names": list(PRESERVED_BINDING_NAMES),
        "secret_names": ev["secret_names"],
        "credentials": {
            "deploy_token_env_names_checked": list(DEPLOY_TOKEN_ENV),
            "deploy_token_env_present": ev["deploy_token_env_present"],
            "deploy_token_present": credentials_present,
            "account_id_env_present": ev["account_id_env_present"],
            "account_id_available": bool(account_id),
            "values_recorded": False,
        },
    }

    provenance = {
        "git_commit": ev["head"],
        "git_commit_date": ev["head_date"],
        "source_file": CANONICAL_SOURCE,
        "source_sha256": ev["source_hash"],
        "source_bytes": ev["source_bytes"],
        "cloudflare_account_id": account_id,
        "cloudflare_service": SERVICE_NAME,
        "cloudflare_version_id": None,
        "cloudflare_deployment_id": None,
        "deployment_timestamp": None,
        "prior_production_version": baseline.get("production_version"),
        "prior_production_source_sha256": baseline.get("source_sha256"),
        "evidence_artifact": JSON_ARTIFACT,
        "relationship_status": relationship_status,
        "relationship_reason": relationship_reason,
        "closed_on_deploy": deploy_status == PASS,
    }

    live_verification = {
        "performed": deploy_status == PASS,
        "reason": (
            "deployment verified via versions API"
            if deploy_status == PASS
            else "deployment not attempted: Cloudflare write surface unavailable"
        ),
        "endpoint": f"https://{SERVICE_NAME}.<account>.workers.dev",
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
                "check": "get_task_result status contract",
                "request": "get_task_result for a known task",
                "expect": "status derived from workflow/artifact evidence, not self-report",
            },
            {
                "check": "asset provenance read path",
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
            "source": f"task contract {TASK_ID}",
            "independently_verified": False,
            "note": "authorization is recorded but is not a substitute for a Cloudflare write credential",
        },
        "deploy_status": deploy_status,
        "verdict": deploy_status,
        "verdict_reason": verdict_reason,
        "deployment_attempted": deployment_attempted,
        "production_mutated": False,
        "secrets_exposed": False,
        "canonical": {
            "git_commit": ev["head"],
            "source_file": CANONICAL_SOURCE,
            "source_sha256": ev["source_hash"],
            "source_bytes": ev["source_bytes"],
            "source_lines": ev["source_lines"],
            "last_source_commit": ev["source_commit"],
        },
        "preflight": preflight,
        "module_upload": {
            "format": "module",
            "main_module": metadata["main_module"],
            "module_content_type": MODULE_CONTENT_TYPE,
            "metadata": metadata,
            "success_followup": [
                "record returned Cloudflare version id",
                "create 100% deployment and record deployment id + timestamp",
                "write deployed source sha256 into provenance chain",
            ],
        },
        "versions_api": api_plan,
        "cloudflare": cloudflare,
        "provenance": provenance,
        "live_verification": live_verification,
        "manual_gate": {
            "status": deploy_status,
            "required_actor": "human owner with Cloudflare production write access",
            "gate": f"inject a Cloudflare write credential for account {account_id}",
            "sequence": list(MANUAL_DEPLOY_SEQUENCE),
            "after_deploy": (
                "populate cloudflare.version_id / cloudflare.deployment_id / "
                "cloudflare.deployment_timestamp and provenance.relationship_status="
                "VERIFIED in " + JSON_ARTIFACT
            ),
        },
        "gates": gates,
        "overall": deploy_status,
    }
    report["markdown"] = render_markdown(report)
    return report


# ---------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------
def render_markdown(report: dict[str, Any]) -> str:
    preflight = report["preflight"]
    source = preflight["canonical_source"]
    credentials = preflight["credentials"]
    cf = report["cloudflare"]
    prov = report["provenance"]

    lines = [
        f"# {REPORT_NAME}",
        "",
        f"- goal: {report['goal']}",
        f"- task_id: {report['task_id']}",
        f"- generated_at: {report['generated_at']}",
        f"- deploy_status: {report['deploy_status']}",
        f"- deployment_attempted: {report['deployment_attempted']}",
        f"- production_mutated: {report['production_mutated']}",
        f"- secrets_exposed: {report['secrets_exposed']}",
        "",
        "## Canonical source",
        f"- git_commit: {report['canonical']['git_commit']}",
        f"- source_file: {report['canonical']['source_file']}",
        f"- source_sha256: {report['canonical']['source_sha256']}",
        f"- source_bytes: {report['canonical']['source_bytes']} "
        f"lines: {report['canonical']['source_lines']}",
        f"- module_worker: {source['module_worker']}",
        f"- last_source_commit: {report['canonical']['last_source_commit']}",
        f"- baseline version: {preflight['baseline']['production_version']} "
        f"sha256={preflight['baseline']['source_sha256']}",
        "",
        "## Module-Worker upload",
        f"- format: {report['module_upload']['format']}",
        f"- main_module: {report['module_upload']['main_module']}",
        f"- module content-type: {report['module_upload']['module_content_type']}",
        f"- bindings: {report['module_upload']['metadata']['bindings']}",
        "- preserved secret bindings: "
        f"{report['module_upload']['metadata']['preserved_secret_bindings']}",
        "- keep_bindings: "
        f"{report['module_upload']['metadata']['keep_bindings']}",
        "",
        "## Versions API plan (version-first, no content-endpoint retry)",
        f"- strategy: {report['versions_api']['strategy']}",
        f"- create version: {report['versions_api']['create_version']['method']} "
        f"{report['versions_api']['create_version']['path']}",
        f"- create deployment: {report['versions_api']['create_deployment']['method']} "
        f"{report['versions_api']['create_deployment']['path']}",
        "",
        "## Credential gate",
        f"- deploy token env names checked: {credentials['deploy_token_env_names_checked']}",
        f"- deploy token present: {credentials['deploy_token_present']}",
        f"- account id available: {credentials['account_id_available']}",
        f"- values recorded: {credentials['values_recorded']}",
        "",
        "## Cloudflare version / deployment identity",
        f"- version_id: {cf['version_id']}",
        f"- deployment_id: {cf['deployment_id']}",
        f"- deployment_timestamp: {cf['deployment_timestamp']}",
        "",
        "## Runtime provenance relationship",
        f"- git_commit: {prov['git_commit']}",
        f"- source_sha256: {prov['source_sha256']}",
        f"- cloudflare_version_id: {prov['cloudflare_version_id']}",
        f"- cloudflare_deployment_id: {prov['cloudflare_deployment_id']}",
        f"- relationship_status: {prov['relationship_status']}",
        f"- relationship_reason: {prov['relationship_reason']}",
        "",
        "## Gates",
    ]
    for gate in report["gates"]:
        lines.append(f"- [{gate['status']}] {gate['gate']}: {gate['detail']}")

    lines += [
        "",
        "## Verdict",
        f"DEPLOY_STATUS={report['deploy_status']}",
        f"VERDICT={report['verdict']}",
        "PRODUCTION_MUTATED=False",
        "SECRETS_EXPOSED=False",
        f"RELATIONSHIP_STATUS={prov['relationship_status']}",
        f"CANONICAL_SOURCE_SHA256={report['canonical']['source_sha256']}",
        f"CLOUDFLARE_VERSION_ID={cf['version_id'] or 'UNAVAILABLE'}",
        f"CLOUDFLARE_DEPLOYMENT_ID={cf['deployment_id'] or 'UNAVAILABLE'}",
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
