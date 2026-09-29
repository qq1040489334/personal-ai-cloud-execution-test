"""P0 Knowledge Candidate -> Cloud Canonical KNOWLEDGE writer regression tests.

The controlled writer ``write_knowledge_candidate`` in ``worker/index.js`` is the
only entry point that turns a Knowledge Inbox candidate into a canonical Cloud
Asset. It is intentionally narrow:

* it only ever writes ``asset_type = KNOWLEDGE``;
* it validates every input (asset id, title, content) and fails closed;
* it derives the canonical ``content_hash`` from the canonicalized content;
* it versions against the existing ``assets`` / ``asset_versions`` rows and
  records a ``supersedes`` lineage when a new version is created;
* it is idempotent for identical content (no duplicate version, no rewrite);
* it records provenance that satisfies the existing
  ``evaluateAssetProvenance`` / ``get_asset`` / ``search_assets`` read semantics;
* it is exposed as an MCP tool that requires the write scope.

The production Worker source is executed directly under Node with a mocked D1
``ASSET_DB`` binding, exactly like the other Worker regression suites.
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


FakeD1 = r"""
const assetRows = new Map();
const versionRows = new Map();
function vkey(a, v) { return a + ":" + v; }
function makeD1() {
  return {
    prepare: function(sql) {
      return {
        bind: function(...args) {
          return {
            run: async function() {
              if (sql.indexOf("INSERT INTO assets") === 0) {
                const [asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at] = args;
                assetRows.set(asset_id, { asset_id, asset_type, schema_version, title, status, current_version, content_hash, created_at, updated_at });
                return { success: true, meta: { changes: 1 } };
              }
              if (sql.indexOf("UPDATE assets") === 0) {
                const [schema_version, title, status, current_version, content_hash, updated_at, asset_id] = args;
                const row = assetRows.get(asset_id);
                if (!row) return { success: true, meta: { changes: 0 } };
                row.schema_version = schema_version; row.title = title; row.status = status;
                row.current_version = current_version; row.content_hash = content_hash;
                row.updated_at = updated_at;
                return { success: true, meta: { changes: 1 } };
              }
              if (sql.indexOf("INSERT OR IGNORE INTO asset_versions") === 0) {
                const [asset_id, version, content, provenance, verification, created_at] = args;
                const key = vkey(asset_id, version);
                if (versionRows.has(key)) return { success: true, meta: { changes: 0 } };
                versionRows.set(key, { asset_id, version, content, provenance, verification, created_at });
                return { success: true, meta: { changes: 1 } };
              }
              return { success: true, meta: { changes: 0 } };
            },
            first: async function() {
              if (sql.indexOf("SELECT asset_id, current_version, content_hash, updated_at FROM assets") === 0) {
                return assetRows.get(args[0]) || null;
              }
              if (sql.indexOf("SELECT a.asset_id") === 0) {
                const asset = assetRows.get(args[0]);
                if (!asset) return null;
                const version = versionRows.get(vkey(asset.asset_id, asset.current_version));
                return { ...asset, content: version ? version.content : null, provenance: version ? version.provenance : null, verification: version ? version.verification : null };
              }
              return null;
            },
            all: async function() {
              const results = [];
              for (const asset of assetRows.values()) {
                const version = versionRows.get(vkey(asset.asset_id, asset.current_version));
                results.push({ ...asset, content: version ? version.content : null, provenance: version ? version.provenance : null, verification: version ? version.verification : null });
              }
              return { results };
            }
          };
        }
      };
    }
  };
}
"""


def writer_probe(calls: list[dict], asset_id: str | None = None) -> dict:
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


def sha256_of(content) -> str:
    if isinstance(content, str):
        text = content
    else:
        text = json.dumps(content, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# -- Source contract --------------------------------------------------------


def test_worker_source_encodes_the_knowledge_writer() -> None:
    source = worker_source()
    for token in (
        "PERSONAL_AI_KNOWLEDGE_CANDIDATE_WRITER_V0.1",
        "writeKnowledgeCandidate",
        "toolWriteKnowledgeCandidate",
        '"write_knowledge_candidate"',
        "INSERT OR IGNORE INTO asset_versions",
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
    ):
        assert token in source, f"worker is missing knowledge writer token {token}"


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
