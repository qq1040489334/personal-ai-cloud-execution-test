"""KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_REPAIR_V1 regression tests.

These tests exercise the independent Candidate staging -> review PASS ->
candidate-bound KNOWLEDGE_PROMOTION approval -> ``validate_candidate_gate`` ->
existing Golden writer (``writeKnowledgeCandidate``) -> authoritative Canonical
read-back pipeline.

The five requested acceptance tests are implemented here:

1. ``test_1_draft_direct_write_rejected_zero_writes``
2. ``test_2_forged_promotion_decision_without_approval_rejected``
3. ``test_3_wrong_hash_rejected``
4. ``test_4_valid_full_flow_reaches_authoritative_readback``
5. ``test_5_repeat_promotion_creates_no_duplicate_golden``

They are asserted against the Python pipeline in ``hello.py`` (the same
state/gate semantics used in production reporting) *and* against the real
Worker source executed under Node for the gate and the full D1-backed promotion.
Additive ledger backward-compatibility and existing Knowledge preservation
checks are included as well.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import hello as hello_module

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"
MIGRATIONS_DIR = REPO_ROOT / "worker" / "migrations"
REPORT_PATH = REPO_ROOT / "KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_REPORT_V1.md"

NODE = shutil.which("node")


def worker_source() -> str:
    return WORKER_PATH.read_text(encoding="utf-8")


def future_iso(minutes: int = 60) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def numbered_statuses(statuses: list[str]) -> list[str]:
    ordered: list[str] = []
    for status in statuses:
        if not ordered or ordered[-1] != status:
            ordered.append(status)
    return ordered


def _approved_candidate(content=None, candidate_id="cand-1", version=1):
    content = content if content is not None else {"type": "note", "text": "hello"}
    store = hello_module.new_knowledge_candidate_store()
    staged = hello_module.stage_knowledge_candidate(
        store,
        candidate_id,
        content,
        asset_id="knowledge:" + candidate_id,
        title="candidate " + candidate_id,
        version=version,
    )
    candidate = staged["candidate"]
    transitions = [candidate["status"]]
    hello_module.submit_knowledge_candidate_for_review(store, candidate_id)
    transitions.append(candidate["status"])
    hello_module.record_knowledge_candidate_review(store, candidate_id, "PASS")
    transitions.append(candidate["status"])
    ledger = hello_module.knowledge_candidate_promotion_ledger()
    receipt = "receipt:" + candidate_id
    hello_module.register_knowledge_promotion_approval(
        ledger,
        receipt,
        candidate_id=candidate_id,
        candidate_version=candidate["version"],
        content_hash=candidate["content_hash"],
        review_result="PASS",
        approved_by="human-operator",
        expires_at=future_iso(),
    )
    return store, ledger, candidate, receipt, transitions


# ---------------------------------------------------------------------------
# 1. DRAFT direct write rejects with zero Canonical write attempts
# ---------------------------------------------------------------------------


def test_1_draft_direct_write_rejected_zero_writes() -> None:
    content = {"type": "note", "text": "draft"}
    store = hello_module.new_knowledge_candidate_store()
    staged = hello_module.stage_knowledge_candidate(
        store, "cand-draft", content, asset_id="knowledge:cand-draft", title="draft"
    )
    candidate = staged["candidate"]
    ledger = hello_module.knowledge_candidate_promotion_ledger()
    golden: dict = {}

    report = hello_module.promote_knowledge_candidate(
        store,
        "cand-draft",
        candidate_version=candidate["version"],
        content_hash=candidate["content_hash"],
        review_result="PASS",
        approval_receipt="receipt:never-registered",
        ledger=ledger,
        golden_store=golden,
        promotion_decision="PROMOTE",
    )

    assert report["status"] == hello_module.KNOWLEDGE_PROMOTION_REJECTED
    assert report["reason"] == hello_module.KNOWLEDGE_PROMOTION_REJECT_CANDIDATE_STATE
    assert report["canonical_write_attempts"] == 0
    assert report["write_calls"] == 0
    assert golden == {}
    assert candidate["status"] == hello_module.KNOWLEDGE_CANDIDATE_DRAFT


# ---------------------------------------------------------------------------
# 2. Forged promotion_decision without approval rejects
# ---------------------------------------------------------------------------


def test_2_forged_promotion_decision_without_approval_rejected() -> None:
    store, ledger, candidate, _receipt, _ = _approved_candidate(
        candidate_id="cand-forged"
    )
    golden: dict = {}

    report = hello_module.promote_knowledge_candidate(
        store,
        "cand-forged",
        candidate_version=candidate["version"],
        content_hash=candidate["content_hash"],
        review_result="PASS",
        approval_receipt="receipt:never-registered",
        ledger=ledger,
        golden_store=golden,
        promotion_decision="PROMOTE",
    )

    assert report["status"] == hello_module.KNOWLEDGE_PROMOTION_REJECTED
    assert report["reason"] == hello_module.KNOWLEDGE_PROMOTION_REJECT_APPROVAL
    assert report["promotion_decision_ignored"] is True
    assert report["canonical_write_attempts"] == 0
    assert report["write_calls"] == 0
    assert golden == {}


# ---------------------------------------------------------------------------
# 3. Wrong hash rejects
# ---------------------------------------------------------------------------


def test_3_wrong_hash_rejected() -> None:
    store, ledger, candidate, receipt, _ = _approved_candidate(candidate_id="cand-hash")
    golden: dict = {}

    report = hello_module.promote_knowledge_candidate(
        store,
        "cand-hash",
        candidate_version=candidate["version"],
        content_hash="0" * 64,
        review_result="PASS",
        approval_receipt=receipt,
        ledger=ledger,
        golden_store=golden,
    )

    assert report["status"] == hello_module.KNOWLEDGE_PROMOTION_REJECTED
    assert report["reason"] == hello_module.KNOWLEDGE_PROMOTION_REJECT_HASH
    assert report["canonical_write_attempts"] == 0
    assert report["write_calls"] == 0
    assert golden == {}
    assert ledger["approvals"][receipt]["consumed"] is False


# ---------------------------------------------------------------------------
# 4. Valid full flow reaches authoritative read-back PASS
# ---------------------------------------------------------------------------


def test_4_valid_full_flow_reaches_authoritative_readback() -> None:
    store, ledger, candidate, receipt, transitions = _approved_candidate(
        candidate_id="cand-full"
    )
    golden: dict = {}

    report = hello_module.promote_knowledge_candidate(
        store,
        "cand-full",
        candidate_version=candidate["version"],
        content_hash=candidate["content_hash"],
        review_result="PASS",
        approval_receipt=receipt,
        ledger=ledger,
        golden_store=golden,
    )

    assert report["status"] == hello_module.KNOWLEDGE_PROMOTION_WRITTEN
    assert report["candidate_status"] == (
        hello_module.KNOWLEDGE_CANDIDATE_CANONICAL_READBACK_VERIFIED
    )
    assert report["read_back_verified"] is True
    assert report["write_calls"] == 1
    assert report["canonical_write_attempts"] == 1

    # Candidate advanced through the required lifecycle states.
    full = numbered_statuses(
        transitions + [hello_module.KNOWLEDGE_CANDIDATE_PROMOTED, candidate["status"]]
    )
    assert full == [
        "DRAFT",
        "PENDING_REVIEW",
        "APPROVED_FOR_PROMOTION",
        "PROMOTED",
        "CANONICAL_READBACK_VERIFIED",
    ]

    # Exactly one Golden asset/version, read back authoritatively.
    assert list(golden.keys()) == ["knowledge:cand-full"]
    record = golden["knowledge:cand-full"]
    assert record["version"] == 1
    assert record["content_hash"] == candidate["content_hash"]
    read_back = report["read_back"]
    assert read_back["tool"] == "get_asset"
    assert read_back["found"] is True
    assert read_back["version"] == record["version"]
    assert read_back["content_hash"] == record["content_hash"]
    assert read_back["content"] == record["content"]
    assert candidate["status"] == (
        hello_module.KNOWLEDGE_CANDIDATE_CANONICAL_READBACK_VERIFIED
    )


# ---------------------------------------------------------------------------
# 5. Repeat promotion creates no duplicate Golden
# ---------------------------------------------------------------------------


def test_5_repeat_promotion_creates_no_duplicate_golden() -> None:
    store, ledger, candidate, receipt, _ = _approved_candidate(
        candidate_id="cand-repeat"
    )
    golden: dict = {}

    first = hello_module.promote_knowledge_candidate(
        store,
        "cand-repeat",
        candidate_version=candidate["version"],
        content_hash=candidate["content_hash"],
        review_result="PASS",
        approval_receipt=receipt,
        ledger=ledger,
        golden_store=golden,
    )
    assert first["status"] == hello_module.KNOWLEDGE_PROMOTION_WRITTEN
    assert len(golden) == 1

    second = hello_module.promote_knowledge_candidate(
        store,
        "cand-repeat",
        candidate_version=candidate["version"],
        content_hash=candidate["content_hash"],
        review_result="PASS",
        approval_receipt=receipt,
        ledger=ledger,
        golden_store=golden,
    )

    assert second["status"] == hello_module.KNOWLEDGE_PROMOTION_IDEMPOTENT
    assert second["idempotent"] is True
    assert second["created"] is False
    assert second["write_calls"] == 0
    assert len(golden) == 1
    assert golden["knowledge:cand-repeat"]["version"] == 1


# ---------------------------------------------------------------------------
# Ledger backward compatibility (additive KNOWLEDGE_PROMOTION only)
# ---------------------------------------------------------------------------


def test_ledger_additive_and_backward_compatible() -> None:
    base = hello_module.production_approval_ledger_schema()
    assert base["supported_operations"] == ["decision_write"]

    adapted = hello_module.production_approval_ledger_schema(
        include_knowledge_write=True
    )
    assert adapted["supported_operations"] == ["decision_write", "knowledge_write"]
    # The pre-existing adapter stays byte-for-byte unchanged.
    assert adapted["operation_definitions"]["decision_write"] == (
        base["operation_definitions"]["decision_write"]
    )

    promotion = hello_module.production_approval_ledger_schema(
        include_knowledge_write=True, include_knowledge_promotion=True
    )
    assert hello_module.KNOWLEDGE_PROMOTION_OPERATION in promotion[
        "supported_operations"
    ]
    assert promotion["operation_definitions"]["decision_write"] == (
        base["operation_definitions"]["decision_write"]
    )
    assert promotion["operation_definitions"]["knowledge_write"] == (
        adapted["operation_definitions"]["knowledge_write"]
    )

    ledger = hello_module.production_approval_ledger_store(promotion)
    # Existing single-use / replay semantics are preserved for legacy ops.
    hello_module.register_production_approval(ledger, "a:decision", "decision_write")
    first = hello_module.consume_production_approval(ledger, "a:decision")
    replay = hello_module.consume_production_approval(ledger, "a:decision")
    assert first["result"] == hello_module.LEDGER_CONSUME_ACCEPTED
    assert replay["result"] == hello_module.LEDGER_CONSUME_REPLAY_REJECTED
    # Unknown operations are still rejected.
    unknown = hello_module.register_production_approval(ledger, "a:bad", "not_an_op")
    assert unknown["registered"] is False
    assert unknown["reason"] == hello_module.LEDGER_REJECT_UNSUPPORTED_OPERATION


def test_existing_knowledge_golden_writer_unchanged() -> None:
    """Existing Knowledge Golden write fixture/version/provenance preserved."""
    report = hello_module.knowledge_golden_write_execution_01()
    assert report["execution_status"] == "WRITTEN"
    assert report["knowledge_written"] is True
    assert report["canonical_version"] == 1
    assert report["provenance_status"] == "VERIFIED"
    for flag in hello_module.KNOWLEDGE_GOLDEN_WRITE_MUTATION_FLAGS:
        assert report[flag] is False, flag
    # Existing assets/asset_versions schema is not referenced by the new
    # candidate staging tables (which live in their own D1 tables).
    db = hello_module.KNOWLEDGE_GOLDEN_WRITE_STORE
    assert "assets" in db and "asset_versions" in db


# ---------------------------------------------------------------------------
# Worker source contract
# ---------------------------------------------------------------------------


def test_worker_source_encodes_candidate_gate_and_pipeline() -> None:
    source = worker_source()
    for token in (
        "PERSONAL_AI_KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_V1",
        "KNOWLEDGE_PROMOTION",
        "validateCandidateGate",
        "promoteKnowledgeCandidate",
        "stageKnowledgeCandidate",
        "createKnowledgeCandidate",
        "readKnowledgeCandidate",
        "submitKnowledgeCandidateForReview",
        "knowledge_candidates",
        # P0-A: the single trusted approval authority is reused, not duplicated.
        "personal_ai_approval_ledger",
        "APPROVAL_LEDGER_CONSUME",
        "KNOWLEDGE_CANDIDATE_DRAFT",
        "KNOWLEDGE_CANDIDATE_PENDING_REVIEW",
        "KNOWLEDGE_CANDIDATE_APPROVED_FOR_PROMOTION",
        "KNOWLEDGE_CANDIDATE_PROMOTED",
        "KNOWLEDGE_CANDIDATE_CANONICAL_READBACK_VERIFIED",
        "missing_or_expired_approval",
        "content_hash_mismatch",
    ):
        assert token in source, f"worker is missing pipeline token {token}"
    # P0-A: there must be NO second approval authority and NO agent-callable
    # approval minting path.
    assert "knowledge_promotion_approvals" not in source
    assert "registerKnowledgePromotionApproval" not in source
    assert "KNOWLEDGE_PROMOTION_APPROVAL_INSERT" not in source
    # The gate never reads a caller-supplied promotion_decision.
    gate_block = source.split("function validateCandidateGate(", 1)[1]
    gate_block = gate_block.split("async function stageKnowledgeCandidate", 1)[0]
    assert "promotion_decision" not in gate_block


def test_no_new_migration_artifact_added_and_plan_documented() -> None:
    """Migration 0003 is committed, additive-only and does not touch Golden.

    KNOWLEDGE_GATE_RELEASE_CANDIDATE_FINALIZE_V1 (cf-00bcf790b680) approved this
    additive migration. The independent candidate staging and the single trusted
    approval ledger are now real, committed DDL verified in an isolated database
    (see ``test_isolated_sqlite_migration_*`` and the finalize report) rather
    than an unexecuted plan.
    """
    names = {path.name for path in MIGRATIONS_DIR.glob("*.sql")}
    assert names == {
        "0001_asset_provenance_v0_2.sql",
        "0002_dispatch_idempotency.sql",
        "0003_knowledge_candidate_golden_pipeline.sql",
    }
    sql = (
        MIGRATIONS_DIR / "0003_knowledge_candidate_golden_pipeline.sql"
    ).read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "knowledge_candidates" in lowered
    assert "personal_ai_approval_ledger" in lowered
    assert "approval_ledger_operations" in lowered
    assert "knowledge_promotion_approvals" not in lowered
    for forbidden in ("drop table", "alter table", "delete from", "update assets", "update asset_versions"):
        assert forbidden not in lowered
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "personal_ai_approval_ledger" in report
    assert "rollback" in report.lower()


# ---------------------------------------------------------------------------
# Real Worker execution under Node (gate + full D1-backed promotion)
# ---------------------------------------------------------------------------

GATED_FAKE_D1 = r"""
const assetRows = new Map();
const versionRows = new Map();
const candidateRows = new Map();
const approvalRows = new Map();
let ALLOW_BATCH = true;
let FAIL_BATCH = false;
let VERIFY_READS = 0;
let FAIL_VERIFY_AFTER = -1;
function vkey(a, v) { return a + ":" + v; }
const ASSET_STATUSES = new Set(["staging", "accepted", "superseded", "retired"]);
const KNOWN_HASH_RE = /^[0-9a-f]{64}$/;
function assertAsset(row) {
  if (!ASSET_STATUSES.has(String(row.status))) throw new Error("CHECK constraint failed: assets.status");
  if (row.content_hash !== null && row.content_hash !== undefined && !KNOWN_HASH_RE.test(String(row.content_hash))) throw new Error("CHECK constraint failed: assets.content_hash");
}
function assertVersion(row) {
  if (row.content_hash === null || row.content_hash === undefined) throw new Error("NOT NULL: asset_versions.content_hash");
  if (!KNOWN_HASH_RE.test(String(row.content_hash))) throw new Error("CHECK: asset_versions.content_hash");
  if (row.created_by === null || row.created_by === undefined || String(row.created_by).trim() === "") throw new Error("NOT NULL: asset_versions.created_by");
  if (row.content === null || row.content === undefined) throw new Error("NOT NULL: asset_versions.content");
}
function runStatement(sql, args) {
  if (sql.indexOf("INSERT INTO assets") === 0) {
    const [asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at] = args;
    const row = { asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at };
    assertAsset(row); assetRows.set(asset_id, row);
    return { success: true, meta: { changes: 1 } };
  }
  if (sql.indexOf("UPDATE assets") === 0) {
    const [schema_version, title, status, current_version, content_hash, updated_at, asset_id] = args;
    const current = assetRows.get(asset_id);
    if (!current) return { success: true, meta: { changes: 0 } };
    const row = { ...current, schema_version, title, status, current_version, content_hash, updated_at };
    assertAsset(row); assetRows.set(asset_id, row);
    return { success: true, meta: { changes: 1 } };
  }
  if (sql.indexOf("INSERT INTO asset_versions") === 0) {
    const [asset_id, version, content, content_hash, provenance, verification, created_by, created_at] = args;
    const key = vkey(asset_id, version);
    if (versionRows.has(key)) throw new Error("UNIQUE constraint failed: asset_versions");
    const row = { asset_id, version, content, content_hash, provenance, verification, created_by, created_at };
    assertVersion(row); versionRows.set(key, row);
    return { success: true, meta: { changes: 1 } };
  }
  if (sql.indexOf("INSERT INTO knowledge_candidates") === 0) {
    if (candidateRows.has(args[0])) throw new Error("UNIQUE constraint failed: knowledge_candidates");
    candidateRows.set(args[0], { candidate_id: args[0], asset_id: args[1], title: args[2], status: args[3], content: args[4], content_hash: args[5], version: args[6], provenance: args[7], created_at: args[8], review_state: args[9], review_result: null });
    return { success: true, meta: { changes: 1 } };
  }
  if (sql.indexOf("UPDATE knowledge_candidates SET status = ?, review_state = ?") === 0) {
    const row = candidateRows.get(args[2]);
    if (!row) return { success: true, meta: { changes: 0 } };
    row.status = args[0]; row.review_state = args[1];
    return { success: true, meta: { changes: 1 } };
  }
  if (sql.indexOf("UPDATE knowledge_candidates SET status = ?") === 0) {
    const row = candidateRows.get(args[1]);
    if (!row) return { success: true, meta: { changes: 0 } };
    row.status = args[0];
    return { success: true, meta: { changes: 1 } };
  }
  if (sql.indexOf("INSERT INTO personal_ai_approval_ledger") === 0) {
    const [approval_id, operation, asset_type, candidate_id, candidate_version, content_hash, review_result, approved_by, expires_at, created_at] = args;
    if (approvalRows.has(approval_id)) throw new Error("UNIQUE constraint failed: personal_ai_approval_ledger");
    approvalRows.set(approval_id, { approval_id, operation, asset_type, candidate_id, candidate_version, content_hash, review_result, approved_by, expires_at, state: "REGISTERED", consumed: 0, consume_count: 0, created_at });
    return { success: true, meta: { changes: 1 } };
  }
  if (sql.indexOf("UPDATE personal_ai_approval_ledger SET consumed = 1") === 0) {
    const consumed_at = args[0], approval_id = args[1], operation = args[2];
    const row = approvalRows.get(approval_id);
    if (!row || row.operation !== operation || Number(row.consumed) === 1) return { success: true, meta: { changes: 0 } };
    row.consumed = 1; row.state = "CONSUMED"; row.consume_count = Number(row.consume_count) + 1; row.consumed_at = consumed_at;
    return { success: true, meta: { changes: 1 } };
  }
  throw new Error("unsupported SQL: " + sql);
}
function queryFirst(sql, args) {
  if (sql.indexOf("SELECT candidate_id, asset_id, title, status") === 0) {
    return candidateRows.get(args[0]) || null;
  }
  if (sql.indexOf("SELECT approval_id, operation, asset_type") === 0) {
    let best = null;
    for (const row of approvalRows.values()) {
      if (row.operation === args[0] && row.candidate_id === args[1] && Number(row.candidate_version) === Number(args[2]) && row.content_hash === args[3]) {
        if (!best || String(row.expires_at) > String(best.expires_at)) best = row;
      }
    }
    return best || null;
  }
  if (sql.indexOf("SELECT asset_id, current_version, content_hash, updated_at FROM assets") === 0) {
    return assetRows.get(args[0]) || null;
  }
  if (sql.indexOf("SELECT a.current_version AS asset_version") === 0) {
    VERIFY_READS++;
    if (FAIL_VERIFY_AFTER >= 0 && VERIFY_READS > FAIL_VERIFY_AFTER) return null;
    const asset = assetRows.get(args[0]);
    if (!asset) return null;
    const version = versionRows.get(vkey(asset.asset_id, asset.current_version));
    if (!version) return null;
    return { asset_version: asset.current_version, asset_content_hash: asset.content_hash, asset_status: asset.status, version_version: version.version, version_content: version.content, version_content_hash: version.content_hash, version_created_by: version.created_by, version_provenance: version.provenance, version_verification: version.verification };
  }
  return null;
}
function makeD1() {
  const db = {
    prepare: function(sql) {
      return { bind: function(...args) {
        return { _sql: sql, _args: args,
          run: async function() { return runStatement(sql, args); },
          first: async function() { return queryFirst(sql, args); },
          all: async function() { return { results: [] }; } };
      } };
    }
  };
  if (ALLOW_BATCH) {
    db.batch = async function(statements) {
      if (FAIL_BATCH) throw new Error("batch failed");
      const as = new Map(assetRows), vs = new Map(versionRows);
      const results = [];
      try { for (const s of statements) results.push(runStatement(s._sql, s._args)); }
      catch (err) { assetRows.clear(); versionRows.clear(); for (const [k, v] of as) assetRows.set(k, v); for (const [k, v] of vs) versionRows.set(k, v); throw err; }
      return results;
    };
  }
  return db;
}
"""


def run_gated_probe(script: str) -> dict:
    if NODE is None:
        pytest.skip("node is not available to execute the worker bundle")
    source = re.sub(r"export\s*\{[^}]*\};?\s*$", "", worker_source())
    probe = source + "\n" + GATED_FAKE_D1 + "\n" + script
    handle, path = tempfile.mkstemp(suffix=".mjs", prefix="gated_pipeline_probe_")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(probe)
        out = subprocess.run([NODE, path], capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(path)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def _worker_env_setup(candidate_id: str, content: dict, *, review: bool) -> str:
    payload = json.dumps({"candidate_id": candidate_id, "asset_id": "knowledge:" + candidate_id, "title": "t", "content": content})
    review_call = (
        f"await recordKnowledgeCandidateReview(env, {{candidate_id: {json.dumps(candidate_id)}, review_result: 'PASS'}});"
        if review
        else ""
    )
    return (
        "const env = { ASSET_DB: makeD1() };\n"
        f"await stageKnowledgeCandidate(env, {payload});\n"
        f"{review_call}\n"
    )


def _approve_worker(candidate_id: str, expires="2999-01-01T00:00:00.000Z") -> str:
    # Seeds the trusted single-use approval ledger directly. This models the
    # out-of-band Human Gate registration; the worker itself has no mint path.
    receipt = "receipt:" + candidate_id
    return (
        "const cand = await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_SELECT).bind("
        + json.dumps(candidate_id)
        + ").first();\n"
        + "await env.ASSET_DB.prepare('INSERT INTO personal_ai_approval_ledger (approval_id, operation, asset_type, candidate_id, candidate_version, content_hash, review_result, approved_by, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)').bind("
        + json.dumps(receipt)
        + ", 'KNOWLEDGE_PROMOTION', 'KNOWLEDGE', cand.candidate_id, cand.version, cand.content_hash, 'PASS', 'human-operator', "
        + json.dumps(expires)
        + ", new Date().toISOString()).run();\n"
        + "const approval = await env.ASSET_DB.prepare(APPROVAL_LEDGER_SELECT).bind('KNOWLEDGE_PROMOTION', cand.candidate_id, cand.version, cand.content_hash).first();\n"
    )


def test_worker_1_draft_rejected_zero_writes() -> None:
    script = (
        "\nconst env = { ASSET_DB: makeD1() };\n"
        + "await stageKnowledgeCandidate(env, "
        + json.dumps({"candidate_id": "cand-w1", "asset_id": "knowledge:cand-w1", "title": "t", "content": {"text": "draft"}})
        + ");\n"
        + "const out = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-w1', candidate_version: 1, content_hash: 'deadbeef', review_result: 'PASS', approval_receipt: 'receipt:x'});\n"
        + "console.log(JSON.stringify({ out: out.structuredContent, "
        + "assets: Array.from(assetRows.values()), "
        + "candidate: candidateRows.get('cand-w1') }));\n"
    )
    report = run_gated_probe(script)
    assert report["out"]["status"] == "REJECTED"
    assert report["out"]["reason"] == "candidate_state"
    assert report["out"]["write_calls"] == 0
    assert report["assets"] == []
    assert report["candidate"]["status"] == "DRAFT"


# ---------------------------------------------------------------------------
# Public Knowledge write route is fail-closed (direct tool + MCP tools/call)
#
# The public route must not drive a Canonical write from an asset_id-only
# request: it carries no independently staged candidate, no review state, and
# no bound single-use approval. Both entry points below must return
# REJECTED/candidate_missing with zero DB reads, zero DB mutations, and zero
# Canonical writer calls, and a caller-supplied promotion_decision=PROMOTE must
# not authorise the write.
# ---------------------------------------------------------------------------

PUBLIC_ROUTE_INSTRUMENT = r"""
let dbReads = 0;
let dbMutations = 0;
let writerCalls = 0;
const _origMakeD1 = makeD1;
makeD1 = function() {
  const db = _origMakeD1();
  const origPrepare = db.prepare;
  db.prepare = function(sql) {
    const stmt = origPrepare.call(db, sql);
    const origBind = stmt.bind;
    stmt.bind = function(...args) {
      const bound = origBind.apply(stmt, args);
      const origRun = bound.run;
      const origFirst = bound.first;
      const origAll = bound.all;
      bound.run = async function(...a) { dbMutations++; return origRun.apply(bound, a); };
      bound.first = async function(...a) { dbReads++; return origFirst.apply(bound, a); };
      bound.all = async function(...a) { dbReads++; return origAll.apply(bound, a); };
      return bound;
    };
    return stmt;
  };
  if (db.batch) {
    const origBatch = db.batch;
    db.batch = async function(...a) { dbMutations++; return origBatch.apply(db, a); };
  }
  return db;
};
const _origWriteKnowledgeCandidate = writeKnowledgeCandidate;
writeKnowledgeCandidate = async function(...a) {
  writerCalls++;
  return _origWriteKnowledgeCandidate.apply(null, a);
};
"""

ASSET_ID_ONLY_ARGS = {
    "asset_id": "knowledge:inbox:1",
    "title": "Panama DIY notes",
    "content": {"type": "note", "text": "deepseek v4.1"},
    "promotion_decision": "PROMOTE",
}


def _assert_public_route_rejected(report: dict, structured: dict) -> None:
    assert structured["contract"] == "PERSONAL_AI_KNOWLEDGE_CANDIDATE_GOLDEN_PIPELINE_V1"
    assert structured["status"] == "REJECTED"
    assert structured["reason"] == "candidate_missing"
    assert structured["write_calls"] == 0
    assert report["dbReads"] == 0
    assert report["dbMutations"] == 0
    assert report["writerCalls"] == 0
    assert report["assets"] == []
    assert report["versions"] == []


def test_public_direct_tool_asset_id_only_is_rejected_zero_io() -> None:
    script = (
        "\n"
        + PUBLIC_ROUTE_INSTRUMENT
        + "\nconst env = { ASSET_DB: makeD1() };\n"
        + "const outcome = await toolWriteKnowledgeCandidate(env, "
        + json.dumps(ASSET_ID_ONLY_ARGS)
        + ");\n"
        + "console.log(JSON.stringify({ outcome, dbReads, dbMutations, writerCalls, "
        + "assets: Array.from(assetRows.values()), "
        + "versions: Array.from(versionRows.values()) }));\n"
    )
    report = run_gated_probe(script)
    _assert_public_route_rejected(report, report["outcome"]["structuredContent"])


def test_public_mcp_tools_call_asset_id_only_is_rejected_zero_io() -> None:
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "write_knowledge_candidate",
            "arguments": ASSET_ID_ONLY_ARGS,
        },
    }
    script = (
        "\n"
        + PUBLIC_ROUTE_INSTRUMENT
        + "\nconst env = { ASSET_DB: makeD1() };\n"
        + "const auth = { scopes: ['mcp'] };\n"
        + "const req = new Request('https://worker.example/mcp', { method: 'POST', "
        + "headers: { 'Content-Type': 'application/json' }, body: JSON.stringify("
        + json.dumps(message)
        + ") });\n"
        + "const res = await handleMcp(req, env, {}, auth);\n"
        + "const body = await res.json();\n"
        + "console.log(JSON.stringify({ body, dbReads, dbMutations, writerCalls, "
        + "assets: Array.from(assetRows.values()), "
        + "versions: Array.from(versionRows.values()) }));\n"
    )
    report = run_gated_probe(script)
    result = report["body"]["result"]
    _assert_public_route_rejected(report, result["structuredContent"])


def test_worker_2_forged_decision_without_approval_rejected() -> None:
    script = (
        "\n"
        + _worker_env_setup("cand-w2", {"text": "forged"}, review=True)
        + "const cand = await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_SELECT).bind('cand-w2').first();\n"
        + "const out = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-w2', candidate_version: cand.version, content_hash: cand.content_hash, review_result: 'PASS', approval_receipt: 'receipt:missing', promotion_decision: 'PROMOTE'});\n"
        + "const candAfter = await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_SELECT).bind('cand-w2').first();\n"
        + "console.log(JSON.stringify({ out: out.structuredContent, assets: Array.from(assetRows.values()), candidate: candAfter }));\n"
    )
    report = run_gated_probe(script)
    assert report["out"]["status"] == "REJECTED"
    assert report["out"]["reason"] == "missing_or_expired_approval"
    assert report["out"]["write_calls"] == 0
    assert report["assets"] == []
    assert report["candidate"]["status"] == "APPROVED_FOR_PROMOTION"


def test_worker_3_wrong_hash_rejected() -> None:
    script = (
        "\n"
        + _worker_env_setup("cand-w3", {"text": "wrong-hash"}, review=True)
        + _approve_worker("cand-w3")
        + "const out = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-w3', candidate_version: cand.version, content_hash: '0'.repeat(64), review_result: 'PASS', approval_receipt: approval.approval_receipt});\n"
        + "console.log(JSON.stringify({ out: out.structuredContent, assets: Array.from(assetRows.values()) }));\n"
    )
    report = run_gated_probe(script)
    assert report["out"]["status"] == "REJECTED"
    assert report["out"]["reason"] == "content_hash_mismatch"
    assert report["out"]["write_calls"] == 0
    assert report["assets"] == []


def test_worker_4_valid_full_flow_reads_back() -> None:
    script = (
        "\n"
        + _worker_env_setup("cand-w4", {"text": "full"}, review=True)
        + _approve_worker("cand-w4")
        + "const out = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-w4', candidate_version: cand.version, content_hash: cand.content_hash, review_result: 'PASS', approval_receipt: approval.approval_receipt});\n"
        + "const candAfter = await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_SELECT).bind('cand-w4').first();\n"
        + "console.log(JSON.stringify({ out: out.structuredContent, candidate: candAfter, assets: Array.from(assetRows.values()), versions: Array.from(versionRows.values()) }));\n"
    )
    report = run_gated_probe(script)
    assert report["out"]["status"] == "WRITTEN"
    assert report["out"]["candidate_status"] == "CANONICAL_READBACK_VERIFIED"
    assert report["out"]["read_back_verified"] is True
    assert report["out"]["write_calls"] == 1
    assert report["candidate"]["status"] == "CANONICAL_READBACK_VERIFIED"
    assert len(report["assets"]) == 1
    assert len(report["versions"]) == 1
    assert report["assets"][0]["content_hash"] == report["out"]["content_hash"]


def test_worker_5_repeat_promotion_no_duplicate() -> None:
    script = (
        "\n"
        + _worker_env_setup("cand-w5", {"text": "repeat"}, review=True)
        + _approve_worker("cand-w5")
        + "const first = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-w5', candidate_version: cand.version, content_hash: cand.content_hash, review_result: 'PASS', approval_receipt: approval.approval_receipt});\n"
        + "const second = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-w5', candidate_version: cand.version, content_hash: cand.content_hash, review_result: 'PASS', approval_receipt: approval.approval_receipt});\n"
        + "console.log(JSON.stringify({ first: first.structuredContent, second: second.structuredContent, assets: Array.from(assetRows.values()), versions: Array.from(versionRows.values()) }));\n"
    )
    report = run_gated_probe(script)
    assert report["first"]["status"] == "WRITTEN"
    assert report["second"]["status"] == "IDEMPOTENT"
    assert report["second"]["idempotent"] is True
    assert report["second"]["write_calls"] == 0
    assert len(report["assets"]) == 1
    assert len(report["versions"]) == 1


def test_worker_gate_rejects_expired_and_consumed_approval() -> None:
    script = (
        "\n"
        + _worker_env_setup("cand-w6", {"text": "expired"}, review=True)
        + _approve_worker("cand-w6", expires="2000-01-01T00:00:00.000Z")
        + "const out = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-w6', candidate_version: cand.version, content_hash: cand.content_hash, review_result: 'PASS', approval_receipt: approval.approval_receipt});\n"
        + "console.log(JSON.stringify({ out: out.structuredContent, assets: Array.from(assetRows.values()) }));\n"
    )
    report = run_gated_probe(script)
    assert report["out"]["status"] == "REJECTED"
    assert report["out"]["reason"] == "missing_or_expired_approval"
    assert report["out"]["write_calls"] == 0
    assert report["assets"] == []


# ---------------------------------------------------------------------------
# P0-B: callable candidate entry points through the MCP tool (cross-agent)
# ---------------------------------------------------------------------------

# The public surface keeps the frozen `tools/list` (11 tools); the Knowledge
# tool dispatches the candidate lifecycle sub-operations. This test drives the
# real MCP `tools/call` handler for Agent A (create) and Agent B (independent
# read), then submit -> review, using the independent candidate table.
MCP_LIFECYCLE_SCRIPT = (
    "\nconst env = { ASSET_DB: makeD1() };\n"
    "async function call(name, args, scopes) {\n"
    "  const msg = { jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: args } };\n"
    "  const req = new Request('https://worker.example/mcp', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(msg) });\n"
    "  const res = await handleMcp(req, env, {}, { scopes });\n"
    "  return await res.json();\n"
    "}\n"
    "const create = await call('write_knowledge_candidate', { candidate_operation: 'create', candidate_id: 'cand-mcp', asset_id: 'knowledge:cand-mcp', title: 't', content: { text: 'mcp' } }, ['mcp']);\n"
    "const readByA = await call('write_knowledge_candidate', { candidate_operation: 'read', candidate_id: 'cand-mcp' }, ['asset.read']);\n"
    "const readNoScope = await call('write_knowledge_candidate', { candidate_operation: 'read', candidate_id: 'cand-mcp' }, []);\n"
    "const writeNoScope = await call('write_knowledge_candidate', { candidate_operation: 'submit_review', candidate_id: 'cand-mcp' }, ['asset.read']);\n"
    "const submit = await call('write_knowledge_candidate', { candidate_operation: 'submit_review', candidate_id: 'cand-mcp' }, ['mcp']);\n"
    "const review = await call('write_knowledge_candidate', { candidate_operation: 'review', candidate_id: 'cand-mcp', review_result: 'PASS' }, ['mcp']);\n"
    "const readBack = await call('write_knowledge_candidate', { candidate_operation: 'read', candidate_id: 'cand-mcp' }, ['asset.read']);\n"
    "console.log(JSON.stringify({ create, readByA, readNoScope, writeNoScope, submit, review, readBack, assets: Array.from(assetRows.values()) }));\n"
)


def test_worker_callable_candidate_lifecycle_cross_agent() -> None:
    report = run_gated_probe(MCP_LIFECYCLE_SCRIPT)

    assert report["create"]["result"]["structuredContent"]["staged"] is True
    # Creating a candidate never writes Canonical storage.
    assert report["assets"] == []

    # Agent B reads it independently (separate MCP call, read scope only).
    candidate = report["readByA"]["result"]["structuredContent"]["candidate"]
    assert candidate["candidate_id"] == "cand-mcp"
    assert candidate["status"] == "DRAFT"
    assert candidate["content"] == {"text": "mcp"}

    # Permission isolation: read needs read scope; a mutating sub-operation
    # needs write scope.
    assert "error" in report["readNoScope"]
    assert "error" in report["writeNoScope"]

    assert report["submit"]["result"]["structuredContent"]["status"] == "PENDING_REVIEW"
    assert report["review"]["result"]["structuredContent"]["status"] == "APPROVED_FOR_PROMOTION"
    final = report["readBack"]["result"]["structuredContent"]["candidate"]
    assert final["status"] == "APPROVED_FOR_PROMOTION"
    assert final["review_state"] == "PASS"


# ---------------------------------------------------------------------------
# P0-A: approval is candidate-bound, single-use, and never self-mintable
# ---------------------------------------------------------------------------


def test_worker_approval_is_candidate_bound_and_single_use() -> None:
    script = (
        "\nconst env = { ASSET_DB: makeD1() };\n"
        "await stageKnowledgeCandidate(env, { candidate_id: 'cand-7a', asset_id: 'knowledge:cand-7a', title: 't', content: { text: 'bound' } });\n"
        "await recordKnowledgeCandidateReview(env, { candidate_id: 'cand-7a', review_result: 'PASS' });\n"
        "await stageKnowledgeCandidate(env, { candidate_id: 'cand-7b', asset_id: 'knowledge:cand-7b', title: 't', content: { text: 'other' } });\n"
        "await recordKnowledgeCandidateReview(env, { candidate_id: 'cand-7b', review_result: 'PASS' });\n"
        + _approve_worker("cand-7a")
        + "const first = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-7a', candidate_version: 1, content_hash: cand.content_hash, review_result: 'PASS'});\n"
        + "const replay = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-7a', candidate_version: 1, content_hash: cand.content_hash, review_result: 'PASS', approved_by: 'agent-self', approval_receipt: 'forged'});\n"
        + "const b = await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_SELECT).bind('cand-7b').first();\n"
        + "const cross = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-7b', candidate_version: 1, content_hash: b.content_hash, review_result: 'PASS', approval_receipt: 'receipt:cand-7a'});\n"
        + "const approvals = Array.from(approvalRows.values());\n"
        + "console.log(JSON.stringify({ first: first.structuredContent, replay: replay.structuredContent, cross: cross.structuredContent, approvals, assets: Array.from(assetRows.values()) }));\n"
    )
    report = run_gated_probe(script)
    assert report["first"]["status"] == "WRITTEN"
    # Replay / forged receipt: candidate already verified -> idempotent, no
    # second Golden, and the caller-supplied approved_by/'forged' receipt is
    # ignored.
    assert report["replay"]["status"] == "IDEMPOTENT"
    assert report["replay"]["write_calls"] == 0
    # Cross-candidate reuse (approval bound to 7a offered for 7b) is rejected.
    assert report["cross"]["status"] == "REJECTED"
    assert report["cross"]["reason"] == "missing_or_expired_approval"
    assert report["cross"]["write_calls"] == 0
    assert len(report["assets"]) == 1
    # Exactly one approval exists and it is consumed once.
    assert len(report["approvals"]) == 1
    assert report["approvals"][0]["consumed"] == 1
    assert report["approvals"][0]["consume_count"] == 1
    assert report["approvals"][0]["operation"] == "KNOWLEDGE_PROMOTION"


def test_worker_readback_failure_is_never_reported_verified() -> None:
    script = (
        "\n"
        + _worker_env_setup("cand-8", {"text": "readback"}, review=True)
        + _approve_worker("cand-8")
        # The first verify (inside the canonical write) passes; the second
        # (authoritative read-back) returns null.
        + "FAIL_VERIFY_AFTER = 1;\n"
        + "const out = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-8', candidate_version: 1, content_hash: cand.content_hash, review_result: 'PASS'});\n"
        + "const candAfter = await env.ASSET_DB.prepare(KNOWLEDGE_CANDIDATE_SELECT).bind('cand-8').first();\n"
        + "console.log(JSON.stringify({ out: out.structuredContent, candidate: candAfter, assets: Array.from(assetRows.values()) }));\n"
    )
    report = run_gated_probe(script)
    assert report["out"]["status"] == "REJECTED"
    assert report["out"]["reason"] == "readback_failed"
    assert report["out"]["read_back_verified"] is False
    assert report["out"]["recovery_required"] is True
    # Never claims VERIFIED/canonical read-back success.
    assert report["out"].get("candidate_status") == "PROMOTED"
    assert report["candidate"]["status"] == "PROMOTED"


def test_worker_canonical_write_failure_consumes_once_and_stays_recoverable() -> None:
    script = (
        "\n"
        + _worker_env_setup("cand-9", {"text": "batch-fail"}, review=True)
        + _approve_worker("cand-9")
        # Cloudflare D1 always has batch; force the write batch to fail to model
        # an unavailable canonical sink (e.g. a 429).
        + "FAIL_BATCH = true;\n"
        + "const out = await promoteKnowledgeCandidate(env, {candidate_id: 'cand-9', candidate_version: 1, content_hash: cand.content_hash, review_result: 'PASS'});\n"
        + "console.log(JSON.stringify({ out: out.structuredContent, assets: Array.from(assetRows.values()), approvals: Array.from(approvalRows.values()) }));\n"
    )
    report = run_gated_probe(script)
    assert report["out"]["status"] == "REJECTED"
    assert report["out"]["reason"] == "ASSET_WRITE_FAILED"
    assert report["out"]["approval_consumed"] is True
    assert report["out"]["recovery_required"] is True
    # No Golden row and no false success; the consumed approval cannot replay.
    assert report["assets"] == []
    assert report["approvals"][0]["consumed"] == 1


# ---------------------------------------------------------------------------
# Worker source guarantee: other writers and legacy Knowledge read path intact
# ---------------------------------------------------------------------------


def test_other_writers_and_legacy_reads_unaffected() -> None:
    source = worker_source()
    # SKILL / DECISION / REALITY writers are untouched by the candidate change.
    for token in (
        'name: "write_skill_candidate"',
        'name: "write_decision_record"',
        "writeDecisionRecord",
        "writeSkillCandidate",
        "toolGetAsset",
        "toolSearchAssets",
        'new Set(["KNOWLEDGE", "SKILL", "REALITY", "DECISION"])',
    ):
        assert token in source, f"worker lost {token}"
    # The trusted ledger is the ONLY approval authority (no second table).
    assert "knowledge_promotion_approvals" not in source
    assert "personal_ai_approval_ledger" in source


# ---------------------------------------------------------------------------
# P0-C: isolated-database migration verification (NOT production D1)
# ---------------------------------------------------------------------------


def test_isolated_sqlite_migration_is_idempotent_and_preserves_history(tmp_path) -> None:
    import sqlite3

    db_path = tmp_path / "isolated_migration.db"
    conn = sqlite3.connect(str(db_path))
    # Model the pre-existing canonical tables (must not be touched).
    conn.executescript(
        "CREATE TABLE assets (asset_id TEXT PRIMARY KEY, content_hash TEXT);"
        "CREATE TABLE asset_versions (asset_id TEXT, version INTEGER, content TEXT);"
        "INSERT INTO assets VALUES ('knowledge:old', 'oldhash');"
        "INSERT INTO asset_versions VALUES ('knowledge:old', 1, 'legacy body');"
    )
    conn.commit()
    migration = (
        MIGRATIONS_DIR / "0003_knowledge_candidate_golden_pipeline.sql"
    ).read_text(encoding="utf-8")
    # Apply twice: the second application must be a no-op.
    conn.executescript(migration)
    conn.executescript(migration)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"knowledge_candidates", "personal_ai_approval_ledger", "approval_ledger_operations"} <= tables
    # Existing canonical rows are byte-identical (no mutation / no rewrite).
    assert conn.execute(
        "SELECT content_hash FROM assets WHERE asset_id = 'knowledge:old'"
    ).fetchone()[0] == "oldhash"
    assert conn.execute(
        "SELECT content FROM asset_versions WHERE asset_id = 'knowledge:old'"
    ).fetchone()[0] == "legacy body"
    operations = {
        row[0] for row in conn.execute("SELECT operation FROM approval_ledger_operations")
    }
    assert "KNOWLEDGE_PROMOTION" in operations
    assert "decision_write" in operations
    # No second approval authority.
    assert "knowledge_promotion_approvals" not in tables
    conn.close()


def test_isolated_sqlite_cross_agent_candidate_persistence(tmp_path) -> None:
    # Genuine cross-connection (cross-session) persistence against an isolated
    # database initialised from the real committed migration -- not a shared
    # in-process object.
    db_path = tmp_path / "isolated_candidates.db"
    # Model the pre-existing canonical tables so we can prove candidate
    # operations never touch them.
    _seed = sqlite3.connect(str(db_path))
    _seed.executescript(
        "CREATE TABLE assets (asset_id TEXT PRIMARY KEY, content_hash TEXT);"
        "CREATE TABLE asset_versions (asset_id TEXT, version INTEGER, content TEXT);"
    )
    _seed.commit()
    _seed.close()

    agent_a = hello_module.knowledge_candidate_sqlite_connect(db_path)
    staged = hello_module.sqlite_stage_knowledge_candidate(
        agent_a, "cand-iso", {"text": "persisted"}, asset_id="knowledge:cand-iso", title="iso"
    )
    assert staged["staged"] is True
    agent_a.close()

    agent_b = hello_module.knowledge_candidate_sqlite_connect(db_path)
    read = hello_module.sqlite_read_knowledge_candidate(agent_b, "cand-iso")
    assert read["ok"] is True
    assert read["candidate"]["candidate_id"] == "cand-iso"
    assert read["candidate"]["status"] == "DRAFT"
    assert read["candidate"]["asset_id"] == "knowledge:cand-iso"

    assert hello_module.sqlite_submit_knowledge_candidate_for_review(agent_b, "cand-iso")["ok"] is True
    assert hello_module.sqlite_record_knowledge_candidate_review(agent_b, "cand-iso", "PASS")["ok"] is True
    agent_b.close()

    agent_c = hello_module.knowledge_candidate_sqlite_connect(db_path)
    read_c = hello_module.sqlite_read_knowledge_candidate(agent_c, "cand-iso")
    assert read_c["candidate"]["status"] == "APPROVED_FOR_PROMOTION"
    assert read_c["candidate"]["review_state"] == "PASS"
    # Creating / reviewing a candidate never creates a Canonical asset row.
    assert agent_c.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0
    agent_c.close()


def test_isolated_sqlite_atomic_approval_consume_is_single_use(tmp_path) -> None:
    # Models the Worker's conditional consume against an isolated database using
    # two independent connections. SQLite's single UPDATE ... WHERE consumed = 0
    # is a compare-and-swap: at most one consumer transitions the row.
    db_path = tmp_path / "isolated_ledger.db"
    admin = hello_module.knowledge_candidate_sqlite_connect(db_path)
    registered = hello_module.sqlite_register_knowledge_promotion_approval(
        admin,
        "ap:iso",
        candidate_id="cand-iso",
        candidate_version=1,
        content_hash="a" * 64,
        review_result="PASS",
        approved_by="human-operator",
        expires_at="2999-01-01T00:00:00+00:00",
    )
    assert registered["registered"] is True
    admin.close()

    consumer_a = hello_module.knowledge_candidate_sqlite_connect(db_path)
    consumer_b = hello_module.knowledge_candidate_sqlite_connect(db_path)
    result_a = hello_module.sqlite_consume_promotion_approval(consumer_a, "ap:iso")
    result_b = hello_module.sqlite_consume_promotion_approval(consumer_b, "ap:iso")
    accepted = [result_a["accepted"], result_b["accepted"]]
    assert accepted.count(True) == 1
    assert accepted.count(False) == 1
    replay = hello_module.sqlite_consume_promotion_approval(consumer_a, "ap:iso")
    assert replay["accepted"] is False
    consumer_a.close()
    consumer_b.close()

    admin2 = hello_module.knowledge_candidate_sqlite_connect(db_path)
    consumed, consume_count = admin2.execute(
        "SELECT consumed, consume_count FROM personal_ai_approval_ledger WHERE approval_id = 'ap:iso'"
    ).fetchone()
    assert consumed == 1
    assert consume_count == 1
    # An operation absent from the trusted registry is rejected (foreign key).
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        admin2.execute(
            "INSERT INTO personal_ai_approval_ledger (approval_id, operation, asset_type, "
            "approved_by, expires_at, created_at) VALUES ('ap:bad', 'bogus', 'X', 'h', '2999', 'now')"
        )
    admin2.rollback()
    admin2.close()
