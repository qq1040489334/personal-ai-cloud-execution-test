"""DECISION_INGESTION_WRITER_V0.2 regression tests.

The controlled writer ``writeDecisionRecord`` in ``worker/index.js`` is the only
entry point that turns a normalized, ``VERIFIED`` DECISION record into a
canonical Cloud Asset version (``asset_type = DECISION``). It is intentionally
narrow:

* it validates the decision evidence (review verdict, dispatch outcome,
  promotion, agent recommendation, user choice, override reason, outcome and
  evidence reference) and fails closed;
* it derives ``user_override`` / ``supersedes`` and never trusts the caller;
* it computes the canonical ``content_hash`` and stores the raw 64-character
  lowercase SHA-256 hex in both ``assets.content_hash`` and
  ``asset_versions.content_hash``;
* it writes the audited production status ``accepted`` (never ``ACTIVE``);
* it supplies the NOT NULL ``asset_versions.content_hash`` / ``created_by``;
* it is idempotent for identical content and records verified
  ASSET_PROVENANCE_V0.2 provenance;
* it fails closed: it never returns ``WRITTEN`` / ``IDEMPOTENT`` unless the
  canonical ``asset_versions`` row is present and matches the current
  version/content/hash/status/creator/provenance;
* it reuses the existing ``assets`` / ``asset_versions`` storage, the
  ``normalize_decision`` ingestion vocabulary and the existing read path;
* it is exposed as an MCP tool that requires the write scope.

The production Worker source is executed directly under Node with a mocked D1
``ASSET_DB`` binding that *enforces* the audited production constraints (status
CHECK, 64-character lowercase hash, NOT NULL version hash/created_by) so the
tests fail if the writer relies on a permissive mock.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from personal_ai_execution.decision_contract import normalize_decision
from personal_ai_execution.provenance_contract import (
    PROVENANCE_CONTRACT_VERSION,
    evaluate_provenance,
)
from personal_ai_execution.status_contract import REVIEW_VERDICTS

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
MIGRATIONS_DIR = REPO_ROOT / "worker" / "migrations"
SPEC_PATH = REPO_ROOT / "DECISION_INGESTION_WRITER_SPEC_V0.1.md"

NODE = shutil.which("node")


def worker_source() -> str:
    return WORKER_PATH.read_text(encoding="utf-8")


def run_worker_probe(script: str) -> dict:
    if NODE is None:
        pytest.skip("node is not available to execute the worker bundle")
    source = re.sub(r"export\s*\{[^}]*\};?\s*$", "", worker_source())
    probe = source + "\n" + script
    # The worker bundle is larger than the per-argument ``-e`` limit once the
    # DECISION writer is present, so the probe is executed from a temp module.
    with tempfile.NamedTemporaryFile(
        "w", suffix=".mjs", encoding="utf-8", delete=False
    ) as handle:
        handle.write(probe)
        probe_path = handle.name
    try:
        out = subprocess.run(
            [NODE, probe_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        Path(probe_path).unlink(missing_ok=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


# The mock models the audited production D1 schema:
#   * assets.status CHECK in (staging, accepted, superseded, retired)
#   * assets.content_hash is exactly 64 lowercase hex
#   * asset_versions.content_hash NOT NULL and 64 lowercase hex
#   * asset_versions.created_by NOT NULL
# ``ALLOW_BATCH`` toggles D1 batch support; ``IGNORE_VERSION_INSERT`` models an
# ignored/duplicate version INSERT that reports success without persisting.
FakeD1 = r"""
const assetRows = new Map();
const versionRows = new Map();
let ALLOW_BATCH = true;
let IGNORE_VERSION_INSERT = false;
function vkey(a, v) { return a + ":" + v; }
const ASSET_STATUSES = new Set(["staging", "accepted", "superseded", "retired"]);
const KNOWN_HASH_RE = /^[0-9a-f]{64}$/;
function assertAsset(row) {
  if (!ASSET_STATUSES.has(String(row.status))) throw new Error("CHECK constraint failed: assets.status");
  if (row.content_hash !== null && row.content_hash !== undefined && !KNOWN_HASH_RE.test(String(row.content_hash))) {
    throw new Error("CHECK constraint failed: assets.content_hash");
  }
}
function assertVersion(row) {
  if (row.content_hash === null || row.content_hash === undefined) throw new Error("NOT NULL constraint failed: asset_versions.content_hash");
  if (!KNOWN_HASH_RE.test(String(row.content_hash))) throw new Error("CHECK constraint failed: asset_versions.content_hash");
  if (row.created_by === null || row.created_by === undefined || String(row.created_by).trim() === "") throw new Error("NOT NULL constraint failed: asset_versions.created_by");
  if (row.content === null || row.content === undefined) throw new Error("NOT NULL constraint failed: asset_versions.content");
}
function seedVersion(asset_id, version, content, content_hash, created_by) {
  versionRows.set(vkey(asset_id, version), { asset_id, version, content, content_hash, provenance: "{}", verification: "{}", created_by, created_at: "2026-01-01T00:00:00.000Z" });
}
function runStatement(sql, args) {
  if (sql.indexOf("INSERT INTO assets") === 0) {
    const [asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at] = args;
    const row = { asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at };
    assertAsset(row);
    assetRows.set(asset_id, row);
    return { success: true, meta: { changes: 1 } };
  }
  if (sql.indexOf("UPDATE assets") === 0) {
    const [schema_version, title, status, current_version, content_hash, updated_at, asset_id] = args;
    const current = assetRows.get(asset_id);
    if (!current) return { success: true, meta: { changes: 0 } };
    const row = { ...current, schema_version, title, status, current_version, content_hash, updated_at };
    assertAsset(row);
    assetRows.set(asset_id, row);
    return { success: true, meta: { changes: 1 } };
  }
  if (sql.indexOf("INSERT INTO asset_versions") === 0) {
    const [asset_id, version, content, content_hash, provenance, verification, created_by, created_at] = args;
    if (IGNORE_VERSION_INSERT) return { success: true, meta: { changes: 0 } };
    const key = vkey(asset_id, version);
    if (versionRows.has(key)) throw new Error("UNIQUE constraint failed: asset_versions.asset_id, asset_versions.version");
    const row = { asset_id, version, content, content_hash, provenance, verification, created_by, created_at };
    assertVersion(row);
    versionRows.set(key, row);
    return { success: true, meta: { changes: 1 } };
  }
  throw new Error("unsupported SQL: " + sql);
}
function queryFirst(sql, args) {
  if (sql.indexOf("SELECT asset_id, current_version, content_hash, updated_at FROM assets") === 0) {
    return assetRows.get(args[0]) || null;
  }
  if (sql.indexOf("SELECT a.asset_id AS asset_id, a.asset_type AS asset_type") === 0) {
    const asset = assetRows.get(args[0]);
    if (!asset) return null;
    const version = versionRows.get(vkey(asset.asset_id, asset.current_version));
    if (!version) return null;
    return {
      asset_id: asset.asset_id,
      asset_type: asset.asset_type,
      asset_version: asset.current_version,
      asset_content_hash: asset.content_hash,
      asset_status: asset.status,
      version_version: version.version,
      version_content: version.content,
      version_content_hash: version.content_hash,
      version_created_by: version.created_by,
      version_provenance: version.provenance,
      version_verification: version.verification
    };
  }
  if (sql.indexOf("SELECT a.asset_id") === 0) {
    const asset = assetRows.get(args[0]);
    if (!asset) return null;
    const version = versionRows.get(vkey(asset.asset_id, asset.current_version));
    return { ...asset, content: version ? version.content : null, provenance: version ? version.provenance : null, verification: version ? version.verification : null };
  }
  return null;
}
function queryAll() {
  const results = [];
  for (const asset of assetRows.values()) {
    const version = versionRows.get(vkey(asset.asset_id, asset.current_version));
    results.push({ ...asset, content: version ? version.content : null, provenance: version ? version.provenance : null, verification: version ? version.verification : null });
  }
  return { results };
}
function makeD1() {
  const db = {
    prepare: function(sql) {
      return {
        bind: function(...args) {
          return {
            _sql: sql,
            _args: args,
            run: async function() { return runStatement(sql, args); },
            first: async function() { return queryFirst(sql, args); },
            all: async function() { return queryAll(sql, args); }
          };
        }
      };
    }
  };
  if (ALLOW_BATCH) {
    db.batch = async function(statements) {
      const assetSnapshot = new Map(assetRows);
      const versionSnapshot = new Map(versionRows);
      const results = [];
      try {
        for (const statement of statements) results.push(runStatement(statement._sql, statement._args));
      } catch (err) {
        assetRows.clear();
        versionRows.clear();
        for (const [k, v] of assetSnapshot) assetRows.set(k, v);
        for (const [k, v] of versionSnapshot) versionRows.set(k, v);
        throw err;
      }
      return results;
    };
  }
  return db;
}
"""


def decision_probe(calls: list[dict], asset_id: str | None = None, setup: str = "") -> dict:
    ops = "\n".join(
        f"results.push(await writeDecisionRecord(env, {json.dumps(call)}));"
        for call in calls
    )
    read = ""
    if asset_id is not None:
        read = (
            "const readOutcome = await toolGetAsset(env, "
            f"{json.dumps({'asset_id': asset_id})});\n"
            "read = readOutcome.structuredContent || "
            "{ isError: readOutcome.isError, text: readOutcome.text };"
        )
    script = (
        FakeD1
        + "\n"
        + setup
        + "\nconst env = { ASSET_DB: makeD1() };\n"
        + "const results = [];\nlet read = null;\n"
        + ops
        + "\n"
        + read
        + "\nconsole.log(JSON.stringify({ results, read, "
        + "assets: Array.from(assetRows.values()), "
        + "versions: Array.from(versionRows.values()) }));\n"
    )
    return run_worker_probe(script)


def decision(**overrides) -> dict:
    base = {
        "decision_id": "cf-decision-1",
        "task_id": "cf-decision-1",
        "review_verdict": "PASS",
        "dispatch_outcome": "DISPATCHED",
        "promotion_decision": "PROMOTE",
        "promotion_event": "promote:cf-decision-1:1",
        "agent_recommendation": "approve",
        "user_choice": "approve",
        "user_outcome": "accepted",
        "decided_at": "2026-09-02T00:00:00+00:00",
        "evidence_ref": "decision-event:1",
    }
    base.update(overrides)
    return base


def persisted_content(**overrides) -> dict:
    base = {
        "decision_id": "cf-decision-1",
        "task_id": "cf-decision-1",
        "review_verdict": "PASS",
        "dispatch_outcome": "DISPATCHED",
        "promotion_decision": "PROMOTE",
        "promotion_event": "promote:cf-decision-1:1",
        "agent_recommendation": "approve",
        "user_choice": "approve",
        "user_outcome": "accepted",
        "user_override": False,
        "override_reason": None,
        "outcome_feedback": None,
        "evidence_ref": "decision-event:1",
        "decided_at": "2026-09-02T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def structured(entry: dict) -> dict:
    return entry.get("structuredContent", json.loads(entry["text"]))


def canonical_decision_json(content: dict) -> str:
    return json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_of_content(content: dict) -> str:
    return sha256_hex(canonical_decision_json(content))


HASH_RE = re.compile(r"^[0-9a-f]{64}$")

DECISION_WRITE_TOKENS = (
    "PERSONAL_AI_DECISION_WRITER_V0.1",
    "writeDecisionRecord",
    "toolWriteDecisionRecord",
    '"write_decision_record"',
    "INSERT INTO asset_versions",
    "INSERT INTO assets",
    "UPDATE assets",
    "ASSET_WRITE_UNAVAILABLE",
    "INVALID_INPUT",
    "INVALID_ASSET_TYPE",
    "INVALID_ASSET_ID",
    "INVALID_TASK_ID",
    "INVALID_REVIEW_VERDICT",
    "INVALID_DISPATCH_OUTCOME",
    "INVALID_PROMOTION",
    "INVALID_AGENT_RECOMMENDATION",
    "INVALID_USER_CHOICE",
    "INVALID_USER_OUTCOME",
    "INVALID_OVERRIDE_REASON",
    "INVALID_OVERRIDE",
    "INVALID_DECIDED_AT",
    "INVALID_EVIDENCE_REF",
    "INCOMPLETE_DECISION",
    "ASSET_WRITE_FAILED",
    "canonicalDecisionContent",
    "sha256Hex",
    "verifyDecisionVersion",
    "DECISION_WRITE_STATUS",
    "created_by",
)


def decision_provenance(content: dict, *, version: int = 1) -> dict:
    digest = sha256_of_content(content)
    stamp = "2026-09-02T00:00:00.000Z"
    return {
        "source": {
            "identity": content["evidence_ref"],
            "location": "cloud://decision-registry",
        },
        "source_version": "v1",
        "content_version": "v1",
        "canonical_version": version,
        "content_hash": digest,
        "verification": {
            "method": "recompute_content_hash",
            "evidence": {
                "checked_by": "decision_ingestion_writer",
                "recomputed": digest,
                "verified_at": stamp,
            },
            "verified_at": stamp,
            "expected_content_hash": digest,
            "content_hash_matches": True,
        },
        "promotion": {
            "decision": content["promotion_decision"],
            "event_id": content["promotion_event"],
            "decided_at": stamp,
            "actor": "cloud-agent",
        },
        "captured_at": stamp,
        "promoted_at": stamp,
        "supersedes": [],
        "superseded_by": None,
    }


def seed_matching_decision(
    content: dict | None = None,
    *,
    version: int = 1,
    status: str = "accepted",
    created_by: str = "cloud-agent",
    provenance=None,
    verification=None,
) -> str:
    if content is None:
        content = persisted_content()
    canon = canonical_decision_json(content)
    digest = sha256_hex(canon)
    if provenance is None:
        provenance = decision_provenance(content, version=version)
    if verification is None:
        verification = provenance.get("verification", {})
    asset = {
        "asset_id": "decision:cf-decision-1",
        "asset_type": "DECISION",
        "schema_version": "v0.1",
        "title": "t",
        "status": status,
        "current_version": version,
        "content_hash": digest,
        "created_at": "2026-01-01T00:00:00.000Z",
        "updated_at": "2026-01-01T00:00:00.000Z",
    }
    version_row = {
        "asset_id": "decision:cf-decision-1",
        "version": version,
        "content": canon,
        "content_hash": digest,
        "provenance": json.dumps(provenance),
        "verification": json.dumps(verification),
        "created_by": created_by,
        "created_at": "2026-01-01T00:00:00.000Z",
    }
    return (
        "assetRows.set("
        + json.dumps("decision:cf-decision-1")
        + ", "
        + json.dumps(asset)
        + ");\n"
        + "versionRows.set(vkey("
        + json.dumps("decision:cf-decision-1")
        + ", "
        + str(version)
        + "), "
        + json.dumps(version_row)
        + ");"
    )


# -- Source contract --------------------------------------------------------


def test_worker_source_encodes_the_decision_writer() -> None:
    source = worker_source()
    for token in DECISION_WRITE_TOKENS:
        assert token in source, f"worker is missing decision writer token {token}"
    assert "sha256:${await sha256Hex" not in source
    assert 'DECISION_WRITE_STATUS = "accepted"' in source
    assert '"ACTIVE"' not in source


def test_write_decision_tool_is_registered_and_scoped_to_write() -> None:
    source = worker_source()
    assert 'name: "write_decision_record"' in source
    assert 'name === "write_decision_record"' in source
    block = source.split('name === "write_decision_record"', 1)[1][:200]
    assert "hasWriteScope(auth)" in block
    tool_block = source.split('name: "write_decision_record"', 1)[1][:600]
    assert "DECISION" in tool_block
    assert "REVIEW_VERDICTS" in tool_block


# -- Validation / fail-closed ----------------------------------------------


def test_missing_asset_db_fails_closed() -> None:
    report = run_worker_probe(
        FakeD1
        + "\nconst env = {};\n"
        + f"const outcome = await writeDecisionRecord(env, {json.dumps(decision())});\n"
        + "console.log(JSON.stringify(outcome));\n"
    )
    assert report["isError"] is True
    assert report["text"] == "ASSET_WRITE_UNAVAILABLE"


def test_rejects_non_object_args() -> None:
    for bad in ("null", "[1,2,3]", '"decision"'):
        report = run_worker_probe(
            FakeD1
            + "\nconst env = { ASSET_DB: makeD1() };\n"
            + f"const outcome = await writeDecisionRecord(env, {bad});\n"
            + "console.log(JSON.stringify(outcome));\n"
        )
        assert report["isError"] is True
        assert report["text"] == "INVALID_INPUT"


def _without(key: str) -> dict:
    payload = decision()
    payload.pop(key, None)
    return payload


@pytest.mark.parametrize(
    "bad,expected",
    [
        (decision(asset_type="KNOWLEDGE"), "INVALID_ASSET_TYPE"),
        (decision(decision_id="../escape"), "INVALID_ASSET_ID"),
        (decision(asset_id="knowledge:foo"), "INVALID_ASSET_ID"),
        (decision(asset_id="/etc/passwd"), "INVALID_ASSET_ID"),
        (decision(task_id=""), "INVALID_TASK_ID"),
        (decision(review_verdict="MAYBE"), "INVALID_REVIEW_VERDICT"),
        (decision(dispatch_outcome="MAYBE"), "INVALID_DISPATCH_OUTCOME"),
        (decision(promotion_decision=""), "INVALID_PROMOTION"),
        (decision(promotion_event=""), "INVALID_PROMOTION"),
        (decision(agent_recommendation="   "), "INVALID_AGENT_RECOMMENDATION"),
        (decision(user_choice=""), "INVALID_USER_CHOICE"),
        (decision(user_outcome=""), "INVALID_USER_OUTCOME"),
        (
            decision(agent_recommendation="approve", user_choice="reject", override_reason=""),
            "INVALID_OVERRIDE_REASON",
        ),
        (decision(user_override=True), "INVALID_OVERRIDE"),
        (decision(decided_at=""), "INVALID_DECIDED_AT"),
        (decision(decided_at="not-a-date"), "INVALID_DECIDED_AT"),
        (decision(evidence_ref=""), "INVALID_EVIDENCE_REF"),
        (_without("review_verdict"), "INCOMPLETE_DECISION"),
        (_without("dispatch_outcome"), "INCOMPLETE_DECISION"),
    ],
)
def test_invalid_inputs_fail_closed_and_write_nothing(bad, expected) -> None:
    report = decision_probe([bad])
    entry = report["results"][0]
    assert entry["isError"] is True
    assert entry["text"] == expected
    assert report["assets"] == []
    assert report["versions"] == []


def test_normalization_contract_agrees_with_writer_rejection() -> None:
    incomplete = _without("review_verdict")
    normalized = normalize_decision(incomplete)
    assert normalized["status"] != "VERIFIED"
    assert "review_verdict" in normalized["missing"]
    report = decision_probe([incomplete])
    assert report["results"][0]["text"] == "INCOMPLETE_DECISION"
    assert report["assets"] == []
    assert report["versions"] == []


# -- Canonical persistence / hash / provenance ------------------------------


def test_write_persists_canonical_decision_with_content_hash() -> None:
    report = decision_probe([decision()])
    result = structured(report["results"][0])

    assert result["contract"] == "PERSONAL_AI_DECISION_WRITER_V0.1"
    assert result["asset_id"] == "decision:cf-decision-1"
    assert result["asset_type"] == "DECISION"
    assert result["status"] == "WRITTEN"
    assert result["created"] is True
    assert result["version"] == 1
    assert result["idempotent"] is False
    assert result["provenance_status"] == "VERIFIED"
    assert result["provenance_verified"] is True
    assert HASH_RE.match(result["content_hash"])

    assert len(report["assets"]) == 1
    asset = report["assets"][0]
    assert asset["asset_id"] == "decision:cf-decision-1"
    assert asset["asset_type"] == "DECISION"
    assert asset["current_version"] == 1
    assert asset["content_hash"] == result["content_hash"]

    assert len(report["versions"]) == 1
    version = report["versions"][0]
    assert version["version"] == 1
    assert result["content_hash"] == sha256_hex(version["content"])
    assert json.loads(version["content"]) == persisted_content()


def test_persisted_rows_satisfy_audited_production_constraints() -> None:
    report = decision_probe([decision()])
    result = structured(report["results"][0])

    asset = report["assets"][0]
    assert asset["status"] == "accepted"
    assert asset["status"] in {"staging", "accepted", "superseded", "retired"}
    assert HASH_RE.match(asset["content_hash"])
    assert asset["content_hash"] == result["content_hash"]
    assert "sha256:" not in asset["content_hash"]

    version = report["versions"][0]
    assert HASH_RE.match(version["content_hash"])
    assert version["content_hash"] == result["content_hash"]
    assert version["created_by"] not in (None, "")


def test_written_provenance_satisfies_canonical_verification() -> None:
    report = decision_probe([decision()])
    result = structured(report["results"][0])
    version = report["versions"][0]
    provenance = json.loads(version["provenance"])

    assert provenance["content_hash"] == result["content_hash"]
    assert provenance["canonical_version"] == 1
    assert provenance["promotion"]["decision"] == "PROMOTE"
    assert provenance["verification"]["content_hash_matches"] is True

    evaluation = evaluate_provenance(
        provenance, content_hash=result["content_hash"], canonical_version=1
    )
    assert evaluation["status"] == "VERIFIED"
    assert evaluation["verified"] is True
    assert evaluation["missing"] == []
    assert evaluation["hash_match"] is True

    verification = json.loads(version["verification"])
    assert verification["expected_content_hash"] == result["content_hash"]


def test_written_provenance_reuses_asset_provenance_v0_2_contract() -> None:
    report = decision_probe([decision()])
    result = structured(report["results"][0])
    provenance = json.loads(report["versions"][0]["provenance"])

    evaluation = evaluate_provenance(
        provenance, content_hash=result["content_hash"], canonical_version=1
    )
    assert evaluation["contract"] == PROVENANCE_CONTRACT_VERSION
    assert PROVENANCE_CONTRACT_VERSION in worker_source()
    assert "evaluateAssetProvenance" in worker_source()
    for key in (
        "source",
        "source_version",
        "content_version",
        "canonical_version",
        "content_hash",
        "verification",
        "promotion",
        "captured_at",
        "promoted_at",
    ):
        assert key in provenance


# -- Idempotency / dedup ----------------------------------------------------


def test_identical_decision_is_idempotent_and_writes_no_new_version() -> None:
    report = decision_probe([decision(), decision()])
    first = structured(report["results"][0])
    second = structured(report["results"][1])

    assert first["status"] == "WRITTEN"
    assert second["status"] == "IDEMPOTENT"
    assert second["idempotent"] is True
    assert second["created"] is False
    assert second["version"] == first["version"] == 1

    assert len(report["assets"]) == 1
    assert report["assets"][0]["current_version"] == 1
    assert len(report["versions"]) == 1


def test_idempotent_replay_matches_on_normalized_hash() -> None:
    report = decision_probe([decision(), decision()])
    first = structured(report["results"][0])
    replay = structured(report["results"][1])
    assert replay["idempotent"] is True
    assert replay["content_hash"] == first["content_hash"]
    assert replay["content_hash"] == sha256_of_content(persisted_content())


def test_new_decision_creates_a_new_version_and_supersedes_lineage() -> None:
    report = decision_probe(
        [
            decision(),
            decision(promotion_event="promote:cf-decision-1:2", user_outcome="completed"),
        ]
    )
    first = structured(report["results"][0])
    second = structured(report["results"][1])

    assert first["version"] == 1
    assert second["version"] == 2
    assert second["created"] is False
    assert second["previous_version"] == 1
    assert second["supersedes"] == ["1"]

    asset = report["assets"][0]
    assert asset["current_version"] == 2
    assert asset["content_hash"] == second["content_hash"]
    assert asset["status"] == "accepted"
    assert len(report["versions"]) == 2

    latest = [v for v in report["versions"] if v["version"] == 2][0]
    provenance = json.loads(latest["provenance"])
    assert provenance["supersedes"] == ["1"]
    assert provenance["canonical_version"] == 2


def test_stable_promotion_event_is_not_duplicated_on_replay() -> None:
    report = decision_probe([decision(), decision()])
    first = structured(report["results"][0])
    replay = structured(report["results"][1])

    assert replay["idempotent"] is True
    assert replay["promotion_event"] == first["promotion_event"]
    assert len(report["versions"]) == 1


# -- Provenance / auditability + user choice / override ---------------------


def test_agent_recommendation_and_user_choice_are_both_persisted() -> None:
    report = decision_probe(
        [
            decision(
                agent_recommendation="approve",
                user_choice="reject",
                override_reason="unsafe",
                user_outcome="rolled_back",
            )
        ]
    )
    result = structured(report["results"][0])
    content = json.loads(report["versions"][0]["content"])

    assert result["agent_recommendation"] == "approve"
    assert result["user_choice"] == "reject"
    assert content["agent_recommendation"] == "approve"
    assert content["user_choice"] == "reject"
    assert content["user_override"] is True
    assert content["override_reason"] == "unsafe"
    assert content["user_outcome"] == "rolled_back"


def test_user_override_sets_flag_and_requires_reason() -> None:
    report = decision_probe(
        [decision(user_choice="reject", override_reason="human veto", user_outcome="rejected")]
    )
    result = structured(report["results"][0])
    content = json.loads(report["versions"][0]["content"])
    assert result["user_override"] is True
    assert content["user_override"] is True
    assert content["override_reason"] == "human veto"


def test_user_override_rejects_contradicting_caller_flag() -> None:
    report = decision_probe(
        [
            decision(
                user_choice="reject",
                override_reason="human veto",
                user_override=False,
            )
        ]
    )
    entry = report["results"][0]
    assert entry["isError"] is True
    assert entry["text"] == "INVALID_OVERRIDE"
    assert report["assets"] == []
    assert report["versions"] == []


def test_missing_override_reason_is_rejected() -> None:
    report = decision_probe([decision(user_choice="reject")])
    entry = report["results"][0]
    assert entry["isError"] is True
    assert entry["text"] == "INVALID_OVERRIDE_REASON"
    assert report["versions"] == []


def test_later_outcome_feedback_appends_new_version_without_mutating_history() -> None:
    report = decision_probe(
        [
            decision(),
            decision(
                promotion_event="promote:cf-decision-1:2",
                outcome_feedback={"result": "worked"},
            ),
        ]
    )
    structured(report["results"][0])
    second = structured(report["results"][1])

    assert second["version"] == 2
    assert len(report["versions"]) == 2
    v1 = [v for v in report["versions"] if v["version"] == 1][0]
    v2 = [v for v in report["versions"] if v["version"] == 2][0]
    assert json.loads(v1["content"]) == persisted_content()
    assert json.loads(v2["content"])["outcome_feedback"] == {"result": "worked"}


# -- Fail-closed persistence ------------------------------------------------


def test_failed_version_insertion_rolls_back_and_fails_closed() -> None:
    setup = 'seedVersion("decision:cf-decision-1", 1, "conflict", "deadbeef", "other");'
    report = decision_probe([decision()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert report["assets"] == []
    assert len(report["versions"]) == 1


def test_ignored_version_insertion_fails_closed_without_false_success() -> None:
    setup = "IGNORE_VERSION_INSERT = true;"
    report = decision_probe([decision()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert report["versions"] == []


def test_batch_unavailable_fails_closed_before_writing_either_row() -> None:
    setup = "ALLOW_BATCH = false;"
    report = decision_probe([decision()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert report["assets"] == []
    assert report["versions"] == []


def test_idempotent_path_fails_closed_on_incomplete_provenance() -> None:
    content = persisted_content()
    setup = seed_matching_decision(
        content, provenance={"content_hash": sha256_of_content(content)}
    )
    report = decision_probe([decision()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert len(report["versions"]) == 1


def test_idempotent_path_fails_closed_on_hash_mismatch_provenance() -> None:
    content = persisted_content()
    provenance = decision_provenance(content)
    provenance["verification"]["content_hash_matches"] = False
    setup = seed_matching_decision(content, provenance=provenance)
    report = decision_probe([decision()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert len(report["versions"]) == 1


def test_idempotent_path_fails_closed_on_non_accepted_status() -> None:
    setup = seed_matching_decision(persisted_content(), status="staging")
    report = decision_probe([decision()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert len(report["versions"]) == 1


def test_idempotent_path_fails_closed_on_missing_created_by() -> None:
    setup = seed_matching_decision(persisted_content(), created_by="")
    report = decision_probe([decision()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert len(report["versions"]) == 1


def test_idempotent_path_accepts_a_genuine_verified_version() -> None:
    content = persisted_content()
    setup = seed_matching_decision(content)
    report = decision_probe([decision()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is False
    result = structured(entry)
    assert result["status"] == "IDEMPOTENT"
    assert result["idempotent"] is True
    assert len(report["versions"]) == 1


def test_idempotent_path_fails_closed_when_version_row_is_missing() -> None:
    content = persisted_content()
    digest = sha256_of_content(content)
    asset = {
        "asset_id": "decision:cf-decision-1",
        "asset_type": "DECISION",
        "schema_version": "v0.1",
        "title": "t",
        "status": "accepted",
        "current_version": 1,
        "content_hash": digest,
        "created_at": "2026-01-01T00:00:00.000Z",
        "updated_at": "2026-01-01T00:00:00.000Z",
    }
    setup = "assetRows.set(" + json.dumps("decision:cf-decision-1") + ", " + json.dumps(asset) + ");"
    report = decision_probe([decision()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"


def test_mock_enforces_the_audited_constraints() -> None:
    hash64 = "a" * 64
    bad_hash = "sha256:" + hash64
    script = (
        FakeD1
        + "\nconst db = makeD1();\nconst out = {};\n"
        + "try { await db.prepare(\"INSERT INTO assets (asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\").bind(\"a1\", \"DECISION\", \"v0.1\", \"t\", \"ACTIVE\", 1, "
        + json.dumps(hash64)
        + ", \"n\", \"n\").run(); out.bad_status_accepted = true; } catch (e) { out.bad_status_accepted = false; }\n"
        + "try { await db.prepare(\"INSERT INTO assets (asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\").bind(\"a2\", \"DECISION\", \"v0.1\", \"t\", \"accepted\", 1, "
        + json.dumps(bad_hash)
        + ", \"n\", \"n\").run(); out.bad_hash_accepted = true; } catch (e) { out.bad_hash_accepted = false; }\n"
        + "try { await db.prepare(\"INSERT INTO asset_versions (asset_id, version, content, content_hash, provenance, verification, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)\").bind(\"a3\", 1, \"c\", "
        + json.dumps(hash64)
        + ", \"p\", \"v\", null, \"n\").run(); out.null_created_by_accepted = true; } catch (e) { out.null_created_by_accepted = false; }\n"
        + "console.log(JSON.stringify(out));\n"
    )
    report = run_worker_probe(script)
    assert report["bad_status_accepted"] is False
    assert report["bad_hash_accepted"] is False
    assert report["null_created_by_accepted"] is False


# -- Read-back / error semantics -------------------------------------------


def test_written_decision_reads_back_through_get_asset() -> None:
    report = decision_probe([decision()], asset_id="decision:cf-decision-1")

    read = report["read"]
    assert read is not None
    assert read["asset_id"] == "decision:cf-decision-1"
    assert read["asset_type"] == "DECISION"
    assert read["version"] == 1
    assert read["content"] == persisted_content()
    assert HASH_RE.match(read["content_hash"])
    assert read["provenance_status"] == "VERIFIED"
    assert read["provenance_verified"] is True
    assert read["historical_provenance_incomplete"] is False


def test_written_decision_is_searchable_through_search_assets() -> None:
    script = (
        FakeD1
        + "\nconst env = { ASSET_DB: makeD1() };\n"
        + f"await writeDecisionRecord(env, {json.dumps(decision())});\n"
        + "const search = await toolSearchAssets(env, { asset_type: 'DECISION', limit: 10 });\n"
        + "console.log(JSON.stringify(search.structuredContent));\n"
    )
    report = run_worker_probe(script)
    assert len(report["assets"]) == 1
    asset = report["assets"][0]
    assert asset["asset_id"] == "decision:cf-decision-1"
    assert asset["provenance_status"] == "VERIFIED"
    assert asset["provenance_verified"] is True


def test_read_back_reports_verified_provenance_and_audit_fields() -> None:
    report = decision_probe(
        [
            decision(
                agent_recommendation="approve",
                user_choice="reject",
                override_reason="unsafe",
                user_outcome="rolled_back",
            )
        ],
        asset_id="decision:cf-decision-1",
    )
    read = report["read"]
    content = read["content"]
    assert content["agent_recommendation"] == "approve"
    assert content["user_choice"] == "reject"
    assert content["user_override"] is True
    assert content["override_reason"] == "unsafe"
    assert content["user_outcome"] == "rolled_back"
    assert content["evidence_ref"] == "decision-event:1"
    assert read["provenance_verified"] is True


def test_read_back_rejects_missing_decision_asset() -> None:
    report = decision_probe([decision(decision_id="cf-decision-other")], asset_id="decision:missing")
    assert report["read"] is not None
    assert report["read"]["isError"] is True
    assert report["read"]["text"] == "ASSET_NOT_FOUND"


# -- Reuse guards (no architecture expansion) -------------------------------


def test_decision_asset_type_is_already_canonical() -> None:
    source = worker_source()
    assert 'new Set(["KNOWLEDGE", "SKILL", "REALITY", "DECISION"])' in source
    assert 'var DECISION_ASSET_TYPE = "DECISION"' in source


def test_migration_set_is_additive_only_and_immutable_history() -> None:
    """Migration history is additive-only; 0001/0002 are frozen.

    KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_V1 (cf-00bcf790b680) authorised a
    single additive migration ``0003_knowledge_candidate_golden_pipeline.sql``.
    This replaces the earlier "exactly two migrations" freeze while preserving
    its real intent: the historical 0001/0002 artifacts must never change, and
    every new migration must be additive schema only (no mutation of ``assets``
    / ``asset_versions`` / existing Knowledge rows and no new ungated write
    path).
    """
    migrations = {path.name: path for path in MIGRATIONS_DIR.glob("*.sql")}
    # The original two migrations remain present and byte-stable in name.
    assert "0001_asset_provenance_v0_2.sql" in migrations
    assert "0002_dispatch_idempotency.sql" in migrations
    assert "0003_knowledge_candidate_golden_pipeline.sql" in migrations

    new_sql = migrations["0003_knowledge_candidate_golden_pipeline.sql"].read_text(
        encoding="utf-8"
    )
    lowered = new_sql.lower()
    # Additive/idempotent only.
    assert "create table if not exists" in lowered
    assert "create index if not exists" in lowered
    # It never rewrites existing canonical storage or history.
    assert "alter table" not in lowered
    assert "drop table" not in lowered
    assert "drop index" not in lowered
    assert "delete from" not in lowered
    assert "insert into assets" not in lowered
    assert "insert into asset_versions" not in lowered
    assert "update assets" not in lowered
    assert "update asset_versions" not in lowered
    # It creates the candidate staging + the single trusted approval ledger
    # (no second approval authority).
    assert "knowledge_candidates" in lowered
    assert "personal_ai_approval_ledger" in lowered
    assert "knowledge_promotion_approvals" not in lowered


def test_decision_ingestion_contract_is_reused() -> None:
    source = worker_source()
    # The writer reuses the existing review verdict vocabulary and ingestion
    # contract version rather than re-declaring a second one.
    assert list(REVIEW_VERDICTS) == ["PASS", "FAIL", "BLOCKED"]
    assert source.count("var REVIEW_VERDICTS = ") == 1
    assert "PERSONAL_AI_DECISION_INGESTION_V0.1" in source
    assert "normalizeDecision" in source
    normalized = normalize_decision(decision())
    assert normalized["status"] == "VERIFIED"


def test_no_personos_or_curator_symbols_introduced() -> None:
    source = worker_source()
    for token in ("PersonOS", "Curator", '"Inbox"', "'Inbox'"):
        assert token not in source


# -- This specification -----------------------------------------------------


def test_spec_exists_and_documents_the_writer_contract() -> None:
    assert SPEC_PATH.exists()
    spec = SPEC_PATH.read_text(encoding="utf-8")
    for invariant in (
        "writeDecisionRecord",
        "toolWriteDecisionRecord",
        "PERSONAL_AI_DECISION_WRITER_V0.1",
        "ASSET_WRITE_UNAVAILABLE",
        "INCOMPLETE_DECISION",
        "ASSET_WRITE_FAILED",
        "verifyDecisionVersion",
        "IDEMPOTENT",
        "ASSET_PROVENANCE_V0.2",
        "Human Gate",
    ):
        assert invariant in spec
