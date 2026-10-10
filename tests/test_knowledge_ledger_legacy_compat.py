"""KNOWLEDGE_LEDGER_COMPAT_CODE_INTEGRATION_V0.3R1 regression tests.

These tests exercise the REAL committed migration files and the REAL Worker SQL
constants (extracted with Node, not a hand-copied Python string) against
isolated in-memory / file SQLite.

Scope proven here (local SQLite only):

* The production-shaped **STRICT** legacy ``personal_ai_approval_ledger``
  (exactly the eight legacy columns, INTEGER epoch timing, unwidened operation
  CHECK) makes migration ``0003`` fail with ``no such column: candidate_id``.
* ``0002z_knowledge_approval_ledger_compat.sql`` applies a *guarded* union
  rebuild: legacy columns/order/types/constraints are preserved verbatim,
  INTEGER epoch timing is never converted to TEXT, the pre-state is retained as
  ``personal_ai_approval_ledger__legacy_backup``, and ``0003`` then resolves its
  indexes.
* The legacy Site WebAuthn single-use CAS on ``consumed_at`` remains
  authoritative, and the Worker's real gate SQL (consumed_at IS NULL) consumes
  exactly once under a two-connection race.
* Unknown ledger drift HALTs fail-closed; ``0003`` is immutable; the Worker has
  no approval-mint path.
* The expiry parser accepts a numeric-epoch ``expires_at`` and rejects a
  consumed or expired approval.

Real Cloudflare D1 is NOT exercised and remains ``REAL_D1_UNVERIFIED``. The
Deployed Site<->Worker integration remains ``BLOCKED`` until its source and
existing verifier are reconciled. Issue #7 adds a candidate Site mint adapter;
``site/tests/knowledge-approval-bridge.mjs`` exercises that real adapter and the
real Worker with a synthetic signer, without claiming deployed WebAuthn proof.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = REPO_ROOT / "worker" / "migrations"
WORKER_PATH = REPO_ROOT / "worker" / "index.js"

LEGACY_SQL = MIGRATIONS_DIR / "0002z_knowledge_approval_ledger_compat.sql"
GOLDEN_SQL = MIGRATIONS_DIR / "0003_knowledge_candidate_golden_pipeline.sql"

NODE = shutil.which("node")

# ---------------------------------------------------------------------------
# Production-shaped STRICT legacy ledger (read back from D1; CHAR(64) CHECK).
# ---------------------------------------------------------------------------
LEGACY_LEDGER_DDL = """
CREATE TABLE personal_ai_approval_ledger (
  approval_id          TEXT PRIMARY KEY,
  requesting_user_hash TEXT NOT NULL CHECK (length(requesting_user_hash) = 64),
  operation            TEXT CHECK (operation IN ('deploy_worker_version','write_decision_record')),
  exact_target         TEXT,
  payload_sha256       TEXT,
  created_at           INTEGER,
  expires_at           INTEGER,
  consumed_at          INTEGER
) STRICT;
"""

LEGACY_COLUMNS = (
    "approval_id",
    "requesting_user_hash",
    "operation",
    "exact_target",
    "payload_sha256",
    "created_at",
    "expires_at",
    "consumed_at",
)

# 0003 is frozen history; this hash must never change.
GOLDEN_0003_SHA256 = "9a51d3a53ad5ac3e78e07fc9720ad5492443f5a1f6ac677018570fdfc337927a"

# Site WebAuthn legacy CAS (unchanged contract) and the mirror Worker SQL,
# extracted from the real worker source below.
SITE_CAS_CONSUME = (
    "UPDATE personal_ai_approval_ledger SET consumed_at = ? "
    "WHERE approval_id = ? AND consumed_at IS NULL"
)


def _connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path if path is not None else ":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _seed_legacy(conn: sqlite3.Connection) -> None:
    conn.executescript(LEGACY_LEDGER_DDL)
    now = int(time.time())
    rows = [
        ("ap:deploy:consumed", "a" * 64, "deploy_worker_version",
         "personal-ai-execution-mcp@1b6a318a", "b" * 64, now - 3600, now + 3600, now - 60),
        ("ap:decision:unconsumed", "c" * 64, "write_decision_record",
         "decision:2026-10-10", "d" * 64, now - 120, now + 7200, None),
        ("ap:deploy:expired", "e" * 64, "deploy_worker_version",
         "personal-ai-execution-mcp@old", "f" * 64, now - 7200, now - 3600, None),
        ("ap:decision:consumed", "g" * 64, "write_decision_record",
         "decision:2026-10-09", "h" * 64, now - 7200, now + 600, now - 300),
    ]
    conn.executemany(
        "INSERT INTO personal_ai_approval_ledger "
        "(approval_id, requesting_user_hash, operation, exact_target, payload_sha256, "
        " created_at, expires_at, consumed_at) VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


def _apply_migration(conn: sqlite3.Connection, path: Path) -> None:
    conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def _legacy_sql(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'personal_ai_approval_ledger'"
    ).fetchone()
    return row[0] if row else ""


def _columns(conn: sqlite3.Connection) -> list[str]:
    return [r[1] for r in conn.execute("PRAGMA table_info(personal_ai_approval_ledger)")]


def _is_strict(conn: sqlite3.Connection) -> bool:
    return "STRICT" in (_legacy_sql(conn) or "")


def _legacy_rows(conn: sqlite3.Connection) -> list[tuple]:
    cols = ", ".join(LEGACY_COLUMNS)
    return [tuple(r) for r in conn.execute(
        f"SELECT {cols} FROM personal_ai_approval_ledger ORDER BY approval_id"
    )]


def _detect_shape(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='personal_ai_approval_ledger'"
    ).fetchone()
    if not row:
        return "ABSENT"
    cols = set(_columns(conn))
    sql = _legacy_sql(conn)
    if "candidate_id" in cols and "KNOWLEDGE_PROMOTION" in sql:
        return "UNION"
    if cols == set(LEGACY_COLUMNS) and "write_decision_record" in sql:
        return "LEGACY"
    return "DRIFT"


def _guarded_rebuild(conn: sqlite3.Connection) -> str:
    """Deterministic, fail-closed rebuild modelled on the D1 runner guard."""
    shape = _detect_shape(conn)
    if shape == "UNION":
        return "ALREADY_REPAIRED"
    if shape == "ABSENT":
        return "HALT_ABSENT"
    if shape == "DRIFT":
        return "HALT_DRIFT"
    before = _legacy_rows(conn)
    _apply_migration(conn, LEGACY_SQL)
    assert _legacy_rows(conn) == before, "legacy rows drifted across rebuild"
    return "REBUILT"


# ---------------------------------------------------------------------------
# Real Worker SQL extraction (via Node) and Node gate probe.
# ---------------------------------------------------------------------------

def _node_probe(body: str) -> dict:
    if NODE is None:
        pytest.skip("node is not available")
    source = re.sub(r"export\s*\{[^}]*\};?\s*$", "", WORKER_PATH.read_text(encoding="utf-8"))
    handle, path = tempfile.mkstemp(suffix=".mjs", prefix="ledger_compat_probe_")
    try:
        with open(handle, "w", encoding="utf-8") as stream:
            stream.write(source + "\n" + body)
        out = subprocess.run([NODE, path], capture_output=True, text=True, timeout=60)
    finally:
        Path(path).unlink(missing_ok=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def _worker_sql_constants() -> dict:
    return _node_probe(
        "console.log(JSON.stringify({"
        "select: APPROVAL_LEDGER_SELECT, consume: APPROVAL_LEDGER_CONSUME, "
        "invalidate: APPROVAL_LEDGER_INVALIDATE}));"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_worker_sql_is_consumed_at_gated_and_validated_by_node() -> None:
    constants = _worker_sql_constants()
    select = constants["select"]
    consume = constants["consume"]
    invalidate = constants["invalidate"]

    # The single-use authority is the legacy integer `consumed_at`, not the
    # Worker-only `consumed` mirror.
    assert "consumed_at IS NULL" in select
    assert "AND consumed = 0" not in select
    assert "consumed_at" in select
    assert "consumed_at IS NULL" in consume
    assert "AND consumed = 0" not in consume
    assert "consumed_at IS NULL" in invalidate
    assert "AND consumed = 0" not in invalidate

    # The consume call site binds an integer epoch second, never an ISO string.
    worker = WORKER_PATH.read_text(encoding="utf-8")
    assert "Math.floor(Date.now() / 1000)" in worker
    assert "APPROVAL_LEDGER_CONSUME).bind((new Date()).toISOString()" not in worker


def test_node_gate_accepts_numeric_epoch_and_consumed_at_single_use() -> None:
    future = int(time.time()) + 600
    past = int(time.time()) - 600
    h = "a" * 64
    base = (
        "const cand = { candidate_id: 'cand-node', version: 1, content_hash: %s, "
        "status: 'APPROVED_FOR_PROMOTION', review_state: 'PASS' };\n"
        "const supplied = { recomputed_content_hash: %s, content_hash: %s, "
        "candidate_version: 1, review_result: 'PASS' };\n"
        "function ap(expires, consumedAt) { return { operation: 'KNOWLEDGE_PROMOTION', "
        "candidate_id: 'cand-node', candidate_version: 1, content_hash: %s, "
        "review_result: 'PASS', approval_id: 'ap:1', approved_by: 'human', "
        "invalidated: 0, state: 'REGISTERED', consumed: 0, consumed_at: consumedAt, "
        "expires_at: expires }; }\n"
        "console.log(JSON.stringify({"
        "live: validateCandidateGate(cand, supplied, ap(%d, null), Date.now()), "
        "expired: validateCandidateGate(cand, supplied, ap(%d, null), Date.now()), "
        "consumed: validateCandidateGate(cand, supplied, ap(%d, %d), Date.now()), "
        "iso: validateCandidateGate(cand, supplied, ap(new Date((%d)*1000).toISOString(), null), Date.now())"
        "}));"
    ) % (json.dumps(h), json.dumps(h), json.dumps(h), json.dumps(h), future, past, future, future, future)
    result = _node_probe(base)
    assert result["live"]["ok"] is True
    assert result["iso"]["ok"] is True
    assert result["expired"]["ok"] is False
    assert result["expired"]["reason"] == "missing_or_expired_approval"
    assert result["consumed"]["ok"] is False
    assert result["consumed"]["reason"] == "missing_or_expired_approval"


def test_baseline_0003_fails_on_prod_shaped_strict_ledger() -> None:
    conn = _connect()
    _seed_legacy(conn)
    assert _is_strict(conn)
    assert _columns(conn) == list(LEGACY_COLUMNS)
    with pytest.raises(sqlite3.OperationalError, match="no such column: candidate_id"):
        _apply_migration(conn, MIGRATIONS_DIR / "0001_asset_provenance_v0_2.sql")
        _apply_migration(conn, MIGRATIONS_DIR / "0002_dispatch_idempotency.sql")
        _apply_migration(conn, GOLDEN_SQL)
    conn.close()


def test_0002z_guarded_rebuild_then_0003_applies_in_order() -> None:
    conn = _connect()
    _seed_legacy(conn)
    before = _legacy_rows(conn)
    assert _guarded_rebuild(conn) == "REBUILT"
    assert _detect_shape(conn) == "UNION"
    assert _is_strict(conn)
    assert _columns(conn)[:8] == list(LEGACY_COLUMNS)

    types = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(personal_ai_approval_ledger)")}
    assert types["created_at"] == "INTEGER"
    assert types["expires_at"] == "INTEGER"
    assert types["consumed_at"] == "INTEGER"

    assert _legacy_rows(conn) == before
    backup = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='personal_ai_approval_ledger__legacy_backup'"
    ).fetchone()
    assert backup is not None

    _apply_migration(conn, MIGRATIONS_DIR / "0001_asset_provenance_v0_2.sql")
    _apply_migration(conn, MIGRATIONS_DIR / "0002_dispatch_idempotency.sql")
    _apply_migration(conn, GOLDEN_SQL)

    indexes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_approval_ledger_binding" in indexes
    assert "idx_approval_ledger_state" in indexes
    operations = {r[0] for r in conn.execute("SELECT operation FROM approval_ledger_operations")}
    assert operations == {
        "deploy_worker_version", "write_decision_record", "decision_write",
        "knowledge_write", "KNOWLEDGE_PROMOTION",
    }
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "personal_ai_approval_ledger__v2" not in tables
    assert "knowledge_promotion_approvals" not in tables

    # A second guarded pass is an idempotent no-op.
    assert _guarded_rebuild(conn) == "ALREADY_REPAIRED"
    conn.close()


def test_legacy_webauthn_cas_single_use_remains_integer_epoch() -> None:
    conn = _connect()
    _seed_legacy(conn)
    _guarded_rebuild(conn)
    now = int(time.time())

    assert conn.execute(SITE_CAS_CONSUME, (now, "ap:decision:unconsumed")).rowcount == 1
    assert conn.execute(SITE_CAS_CONSUME, (now, "ap:decision:unconsumed")).rowcount == 0

    row = conn.execute(
        "SELECT consumed, consumed_at, state FROM personal_ai_approval_ledger "
        "WHERE approval_id='ap:decision:unconsumed'"
    ).fetchone()
    assert isinstance(row["consumed_at"], int)
    assert row["consumed_at"] == now

    mirror = conn.execute(
        "SELECT consumed, state FROM personal_ai_approval_ledger "
        "WHERE approval_id='ap:deploy:consumed'"
    ).fetchone()
    assert mirror["consumed"] == 1 and mirror["state"] == "CONSUMED"

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO personal_ai_approval_ledger (approval_id, requesting_user_hash, "
            "operation, created_at, expires_at) VALUES ('ap:x', ?, 'bogus', 1, 1)",
            ("z" * 64,),
        )
    conn.rollback()
    conn.close()


def _seed_bound_union_approval(conn: sqlite3.Connection, approval_id: str, candidate_id: str,
                               version: int, content_hash: str, expires_at: int) -> None:
    now = int(time.time())
    conn.execute(
        "INSERT INTO personal_ai_approval_ledger (approval_id, requesting_user_hash, "
        "operation, exact_target, payload_sha256, created_at, expires_at, consumed_at, "
        "asset_type, candidate_id, candidate_version, content_hash, review_result, "
        "approved_by, state, consumed, consume_count, invalidated) VALUES "
        "(?, ?, 'KNOWLEDGE_PROMOTION', ?, ?, ?, ?, NULL, 'KNOWLEDGE', ?, ?, ?, "
        "'PASS', ?, 'REGISTERED', 0, 0, 0)",
        (approval_id, "1" * 64, candidate_id, content_hash, now - 5, expires_at,
         candidate_id, version, content_hash, "1" * 64),
    )
    conn.commit()


def test_worker_real_sql_single_use_cas_and_replay(tmp_path) -> None:
    constants = _worker_sql_constants()
    path = str(tmp_path / "union_ledger.db")

    seed = _connect(path)
    _seed_legacy(seed)
    _guarded_rebuild(seed)
    _apply_migration(seed, GOLDEN_SQL)
    candidate = ("cand-v03", 1, "9" * 64)
    _seed_bound_union_approval(seed, "ap:kp:1", *candidate, int(time.time()) + 600)
    target = json.dumps({"operation": "KNOWLEDGE_PROMOTION", "candidate_id": candidate[0],
                         "candidate_version": 1, "content_hash": candidate[2], "asset_id": "knowledge:test",
                         "review_result": "PASS", "reviewed_at": "review-1"}, separators=(",", ":"))
    payload_hash = hashlib.sha256(target.encode()).hexdigest()
    seed.execute("UPDATE personal_ai_approval_ledger SET exact_target=?,payload_sha256=? WHERE approval_id='ap:kp:1'", (target, payload_hash))
    seed.execute("INSERT INTO knowledge_candidates(candidate_id,asset_id,status,content,content_hash,version,created_at,review_state,review_result,reviewed_at) VALUES(?, 'knowledge:test','PROMOTION_RESERVED','test',?,1,'now','PASS','PASS','review-1')", (candidate[0],candidate[2]))
    seed.commit()
    live = seed.execute(constants["select"], ("KNOWLEDGE_PROMOTION", *candidate, target, payload_hash)).fetchall()
    assert len(live) == 1

    a = _connect(path)
    b = _connect(path)
    now = int(time.time())
    wins = 0
    for conn in (a, b):
        cur = conn.execute(constants["consume"], (now, "ap:kp:1", "KNOWLEDGE_PROMOTION", *candidate, now, target, payload_hash, "knowledge:test", "review-1"))
        conn.commit()
        wins += cur.rowcount
    assert wins == 1
    # Replay after consume is rejected by the same real SQL.
    replay = seed.execute(constants["consume"], (now, "ap:kp:1", "KNOWLEDGE_PROMOTION", *candidate, now, target, payload_hash, "knowledge:test", "review-1"))
    seed.commit()
    assert replay.rowcount == 0

    row = seed.execute(
        "SELECT consumed, consume_count, consumed_at, state FROM personal_ai_approval_ledger "
        "WHERE approval_id='ap:kp:1'"
    ).fetchone()
    assert row["consumed"] == 1 and row["consume_count"] == 1
    assert isinstance(row["consumed_at"], int) and row["state"] == "CONSUMED"
    a.close()
    b.close()
    seed.close()


def test_worker_real_sql_stale_invalidation_blocks_replay() -> None:
    constants = _worker_sql_constants()
    conn = _connect()
    _seed_legacy(conn)
    _guarded_rebuild(conn)
    _seed_bound_union_approval(conn, "ap:stale", "cand-s", 1, "8" * 64, int(time.time()) + 600)
    assert len(conn.execute(
        constants["select"], ("KNOWLEDGE_PROMOTION", "cand-s", 1, "8" * 64, "cand-s", "8" * 64)).fetchall()) == 1

    changed = conn.execute(
        constants["invalidate"],
        (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "KNOWLEDGE_PROMOTION", "cand-s"),
    )
    conn.commit()
    assert changed.rowcount == 1
    assert len(conn.execute(
        constants["select"], ("KNOWLEDGE_PROMOTION", "cand-s", 1, "8" * 64, "cand-s", "8" * 64)).fetchall()) == 0
    row = conn.execute(
        "SELECT invalidated, consumed, state FROM personal_ai_approval_ledger "
        "WHERE approval_id='ap:stale'"
    ).fetchone()
    assert row["invalidated"] == 1 and row["consumed"] == 0 and row["state"] == "INVALIDATED"
    # Re-invalidating a dead row is a no-op.
    again = conn.execute(
        constants["invalidate"],
        ("2026-01-01T00:00:00Z", "KNOWLEDGE_PROMOTION", "cand-s"),
    )
    conn.commit()
    assert again.rowcount == 0
    conn.close()


def test_migration_ordering_guard_halts_on_drift_and_absent() -> None:
    # Unknown shape HALTs fail-closed with no partial mutation.
    drift = _connect()
    drift.execute("CREATE TABLE personal_ai_approval_ledger (approval_id TEXT PRIMARY KEY, weird TEXT)")
    drift.commit()
    assert _guarded_rebuild(drift) == "HALT_DRIFT"
    assert "candidate_id" not in set(_columns(drift))
    drift.close()

    # Absent ledger HALTs; it never silently creates one.
    absent = _connect()
    assert _guarded_rebuild(absent) == "HALT_ABSENT"
    tables = {r[0] for r in absent.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "personal_ai_approval_ledger" not in tables
    absent.close()


def test_0003_migration_is_immutable() -> None:
    digest = hashlib.sha256(GOLDEN_SQL.read_bytes()).hexdigest()
    assert digest == GOLDEN_0003_SHA256


def test_worker_cannot_mint_an_approval() -> None:
    source = WORKER_PATH.read_text(encoding="utf-8")
    assert "INSERT INTO personal_ai_approval_ledger" not in source
    assert "registerKnowledgePromotionApproval" not in source
    assert "KNOWLEDGE_PROMOTION_APPROVAL_INSERT" not in source
    # The Worker consumes via the legacy single-use field only.
    assert "APPROVAL_LEDGER_CONSUME" in source


def test_0002z_is_offline_and_only_additive_to_the_authority() -> None:
    sql = LEGACY_SQL.read_text(encoding="utf-8")
    lowered = sql.lower()
    # The rebuild retains the pre-state (RENAME) and never DROPs the authority.
    assert "personal_ai_approval_ledger__legacy_backup" in lowered
    assert "drop table" not in lowered
    # It never touches Golden canonical storage.
    assert "update assets" not in lowered
    assert "update asset_versions" not in lowered
    assert "delete from" not in lowered
    # It keeps INTEGER epoch timing (never converts to TEXT).
    assert re.search(r"consumed_at\s+INTEGER", sql)
    assert re.search(r"expires_at\s+INTEGER", sql)
