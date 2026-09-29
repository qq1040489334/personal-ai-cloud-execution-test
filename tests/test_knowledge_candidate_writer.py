"""P0 Knowledge Candidate -> Cloud Canonical KNOWLEDGE writer regression tests.

The controlled writer ``writeKnowledgeCandidate`` in ``worker/index.js`` is the
only entry point that turns a Knowledge Inbox candidate into a canonical Cloud
Asset. It is intentionally narrow:

* it only ever writes ``asset_type = KNOWLEDGE``;
* it validates every input (asset id, title, content) and fails closed;
* it derives the canonical ``content_hash`` from the canonicalized content and
  stores the raw 64-character lowercase SHA-256 hex (no ``sha256:`` prefix) in
  both ``assets.content_hash`` and ``asset_versions.content_hash``;
* it writes the audited production status ``accepted`` (never ``ACTIVE``),
  which is the only promotion value the ``assets.status`` CHECK permits;
* it supplies the NOT NULL ``asset_versions.content_hash`` and
  ``asset_versions.created_by`` columns on every version INSERT;
* it versions against the existing ``assets`` / ``asset_versions`` rows and
  records a ``supersedes`` lineage when a new version is created;
* it is idempotent for identical content (no duplicate version, no rewrite);
* it fails closed: it never returns ``WRITTEN`` / ``IDEMPOTENT`` unless the
  canonical ``asset_versions`` row is present and matches the current
  version/content/hash;
* it keeps the ``assets`` pointer and the version row consistent by writing
  them in a single D1 batch when the binding supports it;
* it records provenance that satisfies the existing
  ``evaluateAssetProvenance`` / ``get_asset`` / ``search_assets`` read semantics;
* it is exposed as an MCP tool that requires the write scope.

The production Worker source is executed directly under Node with a mocked D1
``ASSET_DB`` binding. The mock *enforces* the audited production constraints
(status CHECK, 64-character lowercase hash, NOT NULL version hash/created_by)
so the tests fail if the writer relies on a permissive mock.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from personal_ai_execution import evaluate_provenance

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"

NODE = shutil.which("node")


def worker_source() -> str:
    return WORKER_PATH.read_text(encoding="utf-8")


def run_worker_probe(script: str) -> dict:
    if NODE is None:
        pytest.skip("node is not available to execute the worker bundle")
    source = re.sub(r"export\s*\{[^}]*\};?\s*$", "", worker_source())
    probe = source + "\n" + script
    out = subprocess.run(
        [NODE, "--input-type=module", "-e", probe],
        capture_output=True,
        text=True,
        timeout=60,
    )
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
  if (sql.indexOf("SELECT a.current_version AS asset_version") === 0) {
    const asset = assetRows.get(args[0]);
    if (!asset) return null;
    const version = versionRows.get(vkey(asset.asset_id, asset.current_version));
    if (!version) return null;
    return {
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


def writer_probe(calls: list[dict], asset_id: str | None = None, setup: str = "") -> dict:
    ops = "\n".join(
        f"results.push(await writeKnowledgeCandidate(env, {json.dumps(call)}));"
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


def candidate(**overrides) -> dict:
    base = {
        "asset_id": "knowledge:inbox:1",
        "title": "Panama DIY notes",
        "content": {"type": "note", "text": "deepseek v4.1"},
    }
    base.update(overrides)
    return base


def structured(entry: dict) -> dict:
    return entry.get("structuredContent", json.loads(entry["text"]))


def canonical_json(content) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, separators=(",", ":"), ensure_ascii=False)


def sha256_of(content) -> str:
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def knowledge_provenance(
    content, *, asset_id: str = "knowledge:inbox:1", version: int = 1
) -> dict:
    digest = sha256_of(content)
    return {
        "source": {
            "identity": f"knowledge-candidate:{asset_id}",
            "location": "cloud://knowledge-inbox",
        },
        "source_version": "v1",
        "content_version": "v1",
        "canonical_version": version,
        "content_hash": digest,
        "verification": {
            "method": "recompute_content_hash",
            "evidence": {
                "checked_by": "knowledge_candidate_writer",
                "recomputed": digest,
            },
            "expected_content_hash": digest,
            "content_hash_matches": True,
        },
        "promotion": {
            "decision": "PROMOTE",
            "event_id": f"promote:{asset_id}:{version}",
            "actor": "cloud-agent",
        },
        "captured_at": "2026-01-01T00:00:00.000Z",
        "promoted_at": "2026-01-01T00:00:00.000Z",
    }


def seed_matching_asset(
    content,
    *,
    asset_id: str = "knowledge:inbox:1",
    version: int = 1,
    status: str = "accepted",
    created_by: str = "cloud-agent",
    provenance=None,
    verification=None,
) -> str:
    """Seed an existing asset + current version row that matches ``content``.

    The writer's idempotent fast path triggers on a matching ``content_hash``,
    so this lets tests vary the persisted status / creator / provenance and
    assert the fast path fails closed when the stored version is not a genuine
    verified, accepted version row.
    """
    digest = sha256_of(content)
    if provenance is None:
        provenance = knowledge_provenance(content, asset_id=asset_id, version=version)
    if verification is None:
        verification = provenance.get("verification", {})
    asset = {
        "asset_id": asset_id,
        "asset_type": "KNOWLEDGE",
        "schema_version": "v0.1",
        "title": "t",
        "status": status,
        "current_version": version,
        "content_hash": digest,
        "created_at": "2026-01-01T00:00:00.000Z",
        "updated_at": "2026-01-01T00:00:00.000Z",
    }
    version_row = {
        "asset_id": asset_id,
        "version": version,
        "content": canonical_json(content),
        "content_hash": digest,
        "provenance": json.dumps(provenance),
        "verification": json.dumps(verification),
        "created_by": created_by,
        "created_at": "2026-01-01T00:00:00.000Z",
    }
    return (
        f"assetRows.set({json.dumps(asset_id)}, {json.dumps(asset)});\n"
        f"versionRows.set(vkey({json.dumps(asset_id)}, {version}), "
        f"{json.dumps(version_row)});"
    )



# -- Source contract --------------------------------------------------------


def test_worker_source_encodes_the_knowledge_writer() -> None:
    source = worker_source()
    for token in (
        "PERSONAL_AI_KNOWLEDGE_CANDIDATE_WRITER_V0.1",
        "writeKnowledgeCandidate",
        "toolWriteKnowledgeCandidate",
        '"write_knowledge_candidate"',
        "INSERT INTO asset_versions",
        "INSERT INTO assets",
        "UPDATE assets",
        "ASSET_WRITE_UNAVAILABLE",
        "INVALID_ASSET_TYPE",
        "INVALID_ASSET_ID",
        "INVALID_TITLE",
        "INVALID_CONTENT",
        "ASSET_WRITE_FAILED",
        "canonicalKnowledgeContent",
        "sha256Hex",
        "verifyKnowledgeVersion",
        "KNOWLEDGE_WRITE_STATUS",
        "KNOWLEDGE_HASH_RE",
        "created_by",
    ):
        assert token in source, f"worker is missing knowledge writer token {token}"
    # The audited schema stores raw 64-hex, never a prefixed digest, and only
    # the promotion statuses the CHECK permits.
    assert "sha256:${await sha256Hex" not in source
    assert 'KNOWLEDGE_WRITE_STATUS = "accepted"' in source
    assert '"ACTIVE"' not in source


def test_write_tool_is_registered_and_scoped_to_write() -> None:
    source = worker_source()
    assert 'name: "write_knowledge_candidate"' in source
    assert 'name === "write_knowledge_candidate"' in source
    block = source.split('name === "write_knowledge_candidate"', 1)[1][:200]
    assert "hasWriteScope(auth)" in block
    # Non-KNOWLEDGE assets are never advertised through the writer schema.
    tool_block = source.split('name: "write_knowledge_candidate"', 1)[1].split(
        "},\n  {", 1
    )[0]
    assert "KNOWLEDGE" in tool_block


# -- Validation / fail-closed ----------------------------------------------


def test_missing_asset_db_fails_closed() -> None:
    report = run_worker_probe(
        FakeD1
        + "\nconst env = {};\n"
        + f"const outcome = await writeKnowledgeCandidate(env, {json.dumps(candidate())});\n"
        + "console.log(JSON.stringify(outcome));\n"
    )
    assert report["isError"] is True
    assert report["text"] == "ASSET_WRITE_UNAVAILABLE"


@pytest.mark.parametrize(
    "bad,expected",
    [
        (candidate(asset_type="SKILL"), "INVALID_ASSET_TYPE"),
        (candidate(asset_id=""), "INVALID_ASSET_ID"),
        (candidate(asset_id="../escape"), "INVALID_ASSET_ID"),
        (candidate(asset_id="/etc/passwd"), "INVALID_ASSET_ID"),
        (candidate(title="   "), "INVALID_TITLE"),
        (candidate(content=None), "INVALID_CONTENT"),
        (candidate(content="   "), "INVALID_CONTENT"),
    ],
)
def test_invalid_inputs_fail_closed_and_write_nothing(bad, expected) -> None:
    report = writer_probe([bad])
    entry = report["results"][0]
    assert entry["isError"] is True
    assert entry["text"] == expected
    assert report["assets"] == []
    assert report["versions"] == []


def test_rejects_non_object_args() -> None:
    report = writer_probe([])
    assert report["results"] == []
    outcome = run_worker_probe(
        FakeD1
        + "\nconst env = { ASSET_DB: makeD1() };\n"
        + "const outcome = await writeKnowledgeCandidate(env, null);\n"
        + "console.log(JSON.stringify(outcome));\n"
    )
    assert outcome["isError"] is True
    assert outcome["text"] == "INVALID_ASSET_ID"


# -- Canonical persistence / hash ------------------------------------------


def test_write_persists_canonical_knowledge_with_content_hash() -> None:
    content = {"type": "note", "text": "deepseek v4.1"}
    report = writer_probe([candidate(content=content)])
    result = structured(report["results"][0])

    assert result["asset_type"] == "KNOWLEDGE"
    assert result["status"] == "WRITTEN"
    assert result["created"] is True
    assert result["version"] == 1
    assert result["idempotent"] is False
    assert result["provenance_status"] == "VERIFIED"
    assert result["provenance_verified"] is True
    assert result["content_hash"] == sha256_of(content)
    assert HASH_RE.match(result["content_hash"])

    assert len(report["assets"]) == 1
    asset = report["assets"][0]
    assert asset["asset_id"] == "knowledge:inbox:1"
    assert asset["asset_type"] == "KNOWLEDGE"
    assert asset["current_version"] == 1
    assert asset["content_hash"] == sha256_of(content)

    assert len(report["versions"]) == 1
    version = report["versions"][0]
    assert version["version"] == 1
    assert json.loads(version["content"]) == content


def test_persisted_rows_satisfy_audited_production_constraints() -> None:
    content = {"type": "note", "text": "constraint check"}
    report = writer_probe([candidate(content=content)])
    result = structured(report["results"][0])

    # assets.status CHECK permits only the four canonical values; the promotion
    # writer must use "accepted" rather than the legacy "ACTIVE".
    asset = report["assets"][0]
    assert asset["status"] == "accepted"
    assert asset["status"] in {"staging", "accepted", "superseded", "retired"}

    # Both D1 hash columns carry the raw 64-character lowercase hex digest.
    assert HASH_RE.match(asset["content_hash"])
    assert asset["content_hash"] == result["content_hash"]
    assert "sha256:" not in asset["content_hash"]

    # asset_versions.content_hash and created_by are NOT NULL.
    version = report["versions"][0]
    assert HASH_RE.match(version["content_hash"])
    assert version["content_hash"] == result["content_hash"]
    assert version["created_by"] not in (None, "")


def test_written_provenance_satisfies_canonical_verification() -> None:
    content = "plain knowledge text"
    report = writer_probe([candidate(content=content)])
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

    # The separate verification column is also persisted for the read path.
    verification = json.loads(version["verification"])
    assert verification["expected_content_hash"] == result["content_hash"]


# -- Versioning / supersession ---------------------------------------------


def test_new_content_creates_a_new_version_and_supersedes_lineage() -> None:
    report = writer_probe(
        [
            candidate(content={"text": "v1"}),
            candidate(content={"text": "v2"}),
        ],
        asset_id="knowledge:inbox:1",
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


# -- Idempotency ------------------------------------------------------------


def test_identical_content_is_idempotent_and_writes_no_new_version() -> None:
    content = {"type": "note", "text": "same"}
    report = writer_probe(
        [candidate(content=content), candidate(content=content)],
        asset_id="knowledge:inbox:1",
    )
    first = structured(report["results"][0])
    second = structured(report["results"][1])

    assert first["status"] == "WRITTEN"
    assert first["idempotent"] is False
    assert second["status"] == "IDEMPOTENT"
    assert second["idempotent"] is True
    assert second["created"] is False
    assert second["version"] == first["version"]

    assert len(report["assets"]) == 1
    assert report["assets"][0]["current_version"] == 1
    assert len(report["versions"]) == 1


def test_idempotent_replay_matches_on_normalized_hash() -> None:
    report = writer_probe(
        [
            candidate(content={"text": "same"}),
            candidate(content={"text": "same"}),
        ],
        asset_id="knowledge:inbox:1",
    )
    replay = structured(report["results"][1])
    assert replay["idempotent"] is True
    assert replay["content_hash"] == sha256_of({"text": "same"})


# -- Fail-closed persistence ------------------------------------------------


def test_failed_version_insertion_rolls_back_and_fails_closed() -> None:
    # A conflicting version row makes the atomic batch fail; the writer must not
    # leave a half-written assets pointer behind or claim success.
    setup = 'seedVersion("knowledge:inbox:1", 1, "conflict", "deadbeef", "other");'
    report = writer_probe([candidate()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert report["assets"] == []
    assert len(report["versions"]) == 1


def test_ignored_version_insertion_fails_closed_without_false_success() -> None:
    # An ignored version INSERT (reported success, nothing persisted) must still
    # be detected by the mandatory read-back and reported as a failure, never
    # WRITTEN.
    setup = "IGNORE_VERSION_INSERT = true;"
    report = writer_probe([candidate()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert report["versions"] == []


def test_batch_unavailable_fails_closed_before_writing_either_row() -> None:
    # Cloudflare D1 always supports batch; without it the writer must fail
    # closed *before* writing, never fall back to a non-atomic sequential write.
    setup = "ALLOW_BATCH = false;"
    report = writer_probe([candidate()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert report["assets"] == []
    assert report["versions"] == []


def test_idempotent_path_fails_closed_on_incomplete_provenance() -> None:
    content = {"text": "same"}
    setup = seed_matching_asset(
        content, provenance={"content_hash": sha256_of(content)}
    )
    report = writer_probe([candidate(content=content)], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    # The incomplete stored version is never treated as verified and no new
    # version is appended.
    assert len(report["versions"]) == 1


def test_idempotent_path_fails_closed_on_hash_mismatch_provenance() -> None:
    content = {"text": "same"}
    provenance = knowledge_provenance(content)
    provenance["verification"]["content_hash_matches"] = False
    setup = seed_matching_asset(content, provenance=provenance)
    report = writer_probe([candidate(content=content)], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert len(report["versions"]) == 1


def test_idempotent_path_fails_closed_on_non_accepted_status() -> None:
    content = {"text": "same"}
    setup = seed_matching_asset(content, status="staging")
    report = writer_probe([candidate(content=content)], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert len(report["versions"]) == 1


def test_idempotent_path_fails_closed_on_missing_created_by() -> None:
    content = {"text": "same"}
    setup = seed_matching_asset(content, created_by="")
    report = writer_probe([candidate(content=content)], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert len(report["versions"]) == 1


def test_idempotent_path_accepts_a_genuine_verified_version() -> None:
    # Sanity: a fully valid stored version still short-circuits idempotently.
    content = {"text": "same"}
    setup = seed_matching_asset(content)
    report = writer_probe([candidate(content=content)], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is False
    result = structured(entry)
    assert result["status"] == "IDEMPOTENT"
    assert result["idempotent"] is True
    assert len(report["versions"]) == 1



def test_idempotent_path_fails_closed_when_version_row_is_missing() -> None:
    content = {"text": "same"}
    digest = sha256_of(content)
    setup = (
        "assetRows.set("
        + json.dumps("knowledge:inbox:1")
        + ", { asset_id: "
        + json.dumps("knowledge:inbox:1")
        + ", asset_type: "
        + json.dumps("KNOWLEDGE")
        + ", schema_version: "
        + json.dumps("v0.1")
        + ", title: "
        + json.dumps("t")
        + ", status: "
        + json.dumps("accepted")
        + ", current_version: 1, content_hash: "
        + json.dumps(digest)
        + ", created_at: "
        + json.dumps("2026-01-01T00:00:00.000Z")
        + ", updated_at: "
        + json.dumps("2026-01-01T00:00:00.000Z")
        + " });"
    )
    report = writer_probe([candidate(content=content)], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"


def test_mock_enforces_the_audited_constraints() -> None:
    hash64 = "a" * 64
    bad_hash = "sha256:" + hash64
    script = (
        FakeD1
        + "\nconst db = makeD1();\nconst out = {};\n"
        + "try { await db.prepare(\"INSERT INTO assets (asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\").bind(\"a1\", \"KNOWLEDGE\", \"v0.1\", \"t\", \"ACTIVE\", 1, "
        + json.dumps(hash64)
        + ", \"n\", \"n\").run(); out.bad_status_accepted = true; } catch (e) { out.bad_status_accepted = false; }\n"
        + "try { await db.prepare(\"INSERT INTO assets (asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\").bind(\"a2\", \"KNOWLEDGE\", \"v0.1\", \"t\", \"accepted\", 1, "
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


# -- Read compatibility -----------------------------------------------------


def test_written_asset_reads_back_through_get_asset() -> None:
    content = {"type": "note", "text": "read me back"}
    report = writer_probe([candidate(content=content)], asset_id="knowledge:inbox:1")

    read = report["read"]
    assert read is not None
    assert read["asset_id"] == "knowledge:inbox:1"
    assert read["asset_type"] == "KNOWLEDGE"
    assert read["version"] == 1
    assert read["content"] == content
    assert read["content_hash"] == sha256_of(content)
    assert read["provenance_status"] == "VERIFIED"
    assert read["provenance_verified"] is True
    assert read["historical_provenance_incomplete"] is False


def test_written_asset_is_searchable_through_search_assets() -> None:
    content = {"text": "searchable"}
    script = (
        FakeD1
        + "\nconst env = { ASSET_DB: makeD1() };\n"
        + f"await writeKnowledgeCandidate(env, {json.dumps(candidate(content=content))});\n"
        + "const search = await toolSearchAssets(env, { asset_type: 'KNOWLEDGE', limit: 10 });\n"
        + "console.log(JSON.stringify(search.structuredContent));\n"
    )
    report = run_worker_probe(script)
    assert len(report["assets"]) == 1
    asset = report["assets"][0]
    assert asset["asset_id"] == "knowledge:inbox:1"
    assert asset["provenance_status"] == "VERIFIED"
    assert asset["provenance_verified"] is True


def test_read_back_rejects_non_knowledge_never_written() -> None:
    report = writer_probe([candidate(asset_id="knowledge:inbox:second")], asset_id="missing")
    assert report["read"] is not None
    assert report["read"]["isError"] is True
    assert report["read"]["text"] == "ASSET_NOT_FOUND"
