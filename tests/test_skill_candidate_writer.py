"""P0 Skill Candidate -> Cloud Canonical SKILL writer regression tests.

``writeSkillCandidate`` in ``worker/index.js`` reuses the validated KNOWLEDGE
writer core (``writeKnowledgeCandidate``) with a SKILL-only restriction: it
accepts only ``asset_type = SKILL`` and otherwise inherits the audited
persistence semantics (canonical content hash, ``accepted`` status,
NOT NULL version hash/created_by, idempotency, fail-closed read-back and
provenance verification).

The production Worker source is executed directly under Node with the mocked D1
``ASSET_DB`` binding defined by the KNOWLEDGE writer suite, which enforces the
audited production constraints. Probes are written to a temporary module file
rather than passed with ``node -e`` so the suite is not limited by the
per-argument size limit on the Worker bundle.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from personal_ai_execution import evaluate_provenance

from test_knowledge_candidate_writer import (
    FakeD1,
    HASH_RE,
    seed_matching_asset,
    sha256_of,
    structured,
    worker_source,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = REPO_ROOT / "worker" / "index.js"

NODE = shutil.which("node")


def run_probe(script: str) -> dict:
    if NODE is None:
        pytest.skip("node is not available to execute the worker bundle")
    source = re.sub(r"export\s*\{[^}]*\};?\s*$", "", worker_source())
    probe = source + "\n" + script
    handle, path = tempfile.mkstemp(suffix=".mjs", prefix="skill_writer_probe_")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(probe)
        out = subprocess.run(
            [NODE, path], capture_output=True, text=True, timeout=60
        )
    finally:
        os.unlink(path)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def skill_probe(calls: list[dict], asset_id: str | None = None, setup: str = "") -> dict:
    ops = "\n".join(
        f"results.push(await writeSkillCandidate(env, {json.dumps(call)}));"
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
    return run_probe(script)


def candidate(**overrides) -> dict:
    base = {
        "asset_id": "skill:inbox:1",
        "title": "Panama DIY runbook",
        "content": {"type": "skill", "steps": ["open", "close"]},
    }
    base.update(overrides)
    return base


# -- Source contract --------------------------------------------------------


def test_worker_source_encodes_the_skill_writer() -> None:
    source = worker_source()
    for token in (
        "PERSONAL_AI_SKILL_CANDIDATE_WRITER_V0.1",
        "writeSkillCandidate",
        "writeKnowledgeCandidate",
    ):
        assert token in source, f"worker is missing skill writer token {token}"
    # The skill wrapper reuses the KNOWLEDGE core with a SKILL-only restriction.
    block = source.split("async function writeSkillCandidate", 1)[1][:160]
    assert 'writeKnowledgeCandidate(env, args, "SKILL")' in block


def test_skill_restriction_is_bound_to_the_wrapper_not_the_input() -> None:
    source = worker_source()
    # The shared core rejects any asset type that differs from the allowed one,
    # so the KNOWLEDGE entry point still rejects SKILL (see the KNOWLEDGE suite)
    # while the SKILL wrapper rejects everything else.
    assert "assetType !== allowed" in source


# -- Validation / fail-closed ----------------------------------------------


def test_missing_asset_db_fails_closed() -> None:
    report = run_probe(
        FakeD1
        + "\nconst env = {};\n"
        + f"const outcome = await writeSkillCandidate(env, {json.dumps(candidate())});\n"
        + "console.log(JSON.stringify(outcome));\n"
    )
    assert report["isError"] is True
    assert report["text"] == "ASSET_WRITE_UNAVAILABLE"


@pytest.mark.parametrize(
    "bad,expected",
    [
        (candidate(asset_type="KNOWLEDGE"), "INVALID_ASSET_TYPE"),
        (candidate(asset_type="REALITY"), "INVALID_ASSET_TYPE"),
        (candidate(asset_id=""), "INVALID_ASSET_ID"),
        (candidate(asset_id="../escape"), "INVALID_ASSET_ID"),
        (candidate(title="   "), "INVALID_TITLE"),
        (candidate(content=None), "INVALID_CONTENT"),
        (candidate(content="   "), "INVALID_CONTENT"),
    ],
)
def test_invalid_inputs_fail_closed_and_write_nothing(bad, expected) -> None:
    report = skill_probe([bad])
    entry = report["results"][0]
    assert entry["isError"] is True
    assert entry["text"] == expected
    assert report["assets"] == []
    assert report["versions"] == []


# -- Canonical persistence / hash ------------------------------------------


def test_write_persists_canonical_skill_with_content_hash() -> None:
    content = {"type": "skill", "steps": ["a", "b"]}
    report = skill_probe([candidate(content=content)])
    result = structured(report["results"][0])

    assert result["asset_type"] == "SKILL"
    assert result["contract"] == "PERSONAL_AI_SKILL_CANDIDATE_WRITER_V0.1"
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
    assert asset["asset_id"] == "skill:inbox:1"
    assert asset["asset_type"] == "SKILL"
    assert asset["current_version"] == 1
    assert asset["content_hash"] == sha256_of(content)

    assert len(report["versions"]) == 1
    version = report["versions"][0]
    assert version["version"] == 1
    assert json.loads(version["content"]) == content


def test_persisted_rows_satisfy_audited_production_constraints() -> None:
    content = {"type": "skill", "constraint": True}
    report = skill_probe([candidate(content=content)])
    result = structured(report["results"][0])

    asset = report["assets"][0]
    assert asset["asset_type"] == "SKILL"
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
    content = "plain skill text"
    report = skill_probe([candidate(content=content)])
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


# -- Versioning / idempotency ----------------------------------------------


def test_new_content_creates_a_new_version_and_supersedes_lineage() -> None:
    report = skill_probe(
        [
            candidate(content={"steps": ["v1"]}),
            candidate(content={"steps": ["v2"]}),
        ],
        asset_id="skill:inbox:1",
    )
    first = structured(report["results"][0])
    second = structured(report["results"][1])

    assert first["version"] == 1
    assert second["version"] == 2
    assert second["created"] is False
    assert second["previous_version"] == 1
    assert second["supersedes"] == ["1"]

    asset = report["assets"][0]
    assert asset["asset_type"] == "SKILL"
    assert asset["current_version"] == 2
    assert asset["content_hash"] == second["content_hash"]
    assert len(report["versions"]) == 2


def test_identical_content_is_idempotent_and_writes_no_new_version() -> None:
    content = {"type": "skill", "text": "same"}
    report = skill_probe(
        [candidate(content=content), candidate(content=content)],
        asset_id="skill:inbox:1",
    )
    first = structured(report["results"][0])
    second = structured(report["results"][1])

    assert first["status"] == "WRITTEN"
    assert second["status"] == "IDEMPOTENT"
    assert second["idempotent"] is True
    assert second["asset_type"] == "SKILL"
    assert second["contract"] == "PERSONAL_AI_SKILL_CANDIDATE_WRITER_V0.1"
    assert second["version"] == first["version"]

    assert len(report["assets"]) == 1
    assert len(report["versions"]) == 1


# -- Fail-closed persistence ------------------------------------------------


def test_failed_version_insertion_rolls_back_and_fails_closed() -> None:
    setup = 'seedVersion("skill:inbox:1", 1, "conflict", "deadbeef", "other");'
    report = skill_probe([candidate()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert report["assets"] == []
    assert len(report["versions"]) == 1


def test_batch_unavailable_fails_closed_before_writing_either_row() -> None:
    setup = "ALLOW_BATCH = false;"
    report = skill_probe([candidate()], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert report["assets"] == []
    assert report["versions"] == []


def test_idempotent_path_fails_closed_on_non_accepted_status() -> None:
    content = {"text": "same"}
    setup = seed_matching_asset(content, asset_id="skill:inbox:1", status="staging")
    report = skill_probe([candidate(content=content)], setup=setup)
    entry = report["results"][0]

    assert entry["isError"] is True
    assert entry["text"] == "ASSET_WRITE_FAILED"
    assert len(report["versions"]) == 1


# -- Read compatibility -----------------------------------------------------


def test_written_skill_reads_back_through_get_asset() -> None:
    content = {"type": "skill", "read": "me"}
    report = skill_probe([candidate(content=content)], asset_id="skill:inbox:1")

    read = report["read"]
    assert read is not None
    assert read["asset_id"] == "skill:inbox:1"
    assert read["asset_type"] == "SKILL"
    assert read["version"] == 1
    assert read["content"] == content
    assert read["content_hash"] == sha256_of(content)
    assert read["provenance_status"] == "VERIFIED"
    assert read["provenance_verified"] is True
