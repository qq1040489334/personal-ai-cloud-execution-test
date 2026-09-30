from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.cloud_asset_obsidian_mirror import (  # noqa: E402
    HOME_NOTE,
    INDEX_NOTE,
    MIRROR_DIRECTORY,
    TRANSLATIONS,
    _frontmatter,
    _read_managed,
    render_asset_markdown,
    sync_assets,
)

PRODUCTION_HASHES = {
    "knowledge-architecture-local-execution-shared-intelligence":
        "11be28739a7d4a24dc80af494fb38e7e94f9be01d35d7a04c3d7fce9ad002e64",
    "knowledge-architecture-scoped-knowledge-layers":
        "34f5c9fb08b4006fee5d63c676c9bd611452e0bb17045bef95343102dd315bc0",
    "knowledge-workflow-auditable-task-contract":
        "8d3360d886b4970e675f070f16169fa6aeb8550a17da59d37300967503ff2078",
}

PRODUCTION_CONTENT = {
    "knowledge-architecture-local-execution-shared-intelligence": {
        "category": "architecture_pattern",
        "title": "Local Execution and Shared Intelligence Architecture",
        "summary": "Run intelligence locally and share only reviewed knowledge.",
        "principles": ["Keep execution local.", "Publish only reviewed knowledge."],
        "source_assessment": "Retained as a general architecture pattern.",
        "confidence": "medium-high",
        "review_policy": "Re-review if the architecture document changes.",
    },
    "knowledge-architecture-scoped-knowledge-layers": {
        "category": "architecture_pattern",
        "title": "Scoped Knowledge Layers",
        "summary": "Isolate knowledge by scope and keep explicit boundaries.",
        "principles": ["Define scope per layer.", "Review cross-layer references."],
        "source_assessment": "Retained as a general architecture pattern.",
        "confidence": "medium",
        "review_policy": "Re-review if the scope model changes.",
    },
    "knowledge-workflow-auditable-task-contract": {
        "category": "workflow",
        "title": "Auditable Task Contract",
        "summary": "Use a structured task contract with acceptance criteria.",
        "principles": ["Declare scope and acceptance.", "Keep test evidence."],
        "source_assessment": "Retained as a general workflow pattern.",
        "confidence": "high",
        "review_policy": "Re-review if the contract format changes.",
    },
}

EXPECTED_PATHS = {
    "knowledge-architecture-local-execution-shared-intelligence": "AI 架构/本地执行与共享智能架构.md",
    "knowledge-architecture-scoped-knowledge-layers": "AI 架构/按范围隔离的知识分层模型.md",
    "knowledge-workflow-auditable-task-contract": "工作流/可审计的 AI 任务契约.md",
}


def make_asset(asset_id: str, *, content_hash: str | None = None, version: str = "1.0",
               canonical_version=1, content_overrides: dict | None = None) -> dict:
    content = dict(PRODUCTION_CONTENT[asset_id])
    if content_overrides:
        content.update(content_overrides)
    return {
        "asset_id": asset_id,
        "asset_type": "KNOWLEDGE",
        "version": version,
        "content_hash": content_hash or PRODUCTION_HASHES[asset_id],
        "provenance": {
            "source": {"identity": "reviewed-source", "location": "https://example.invalid/source"},
            "source_version": "candidate-v1",
            "content_version": version,
            "canonical_version": canonical_version,
            "verification": {"verified_at": "2026-09-30T11:26:00+08:00", "content_hash_matches": True},
            "promotion": {"decision": "PROMOTE"},
        },
        "content": content,
    }


def production_assets() -> list[dict]:
    return [make_asset(asset_id) for asset_id in PRODUCTION_HASHES]


def note_paths(mirror: Path) -> list[Path]:
    return [p for p in mirror.rglob("*.md") if p.name not in {HOME_NOTE, Path(INDEX_NOTE).name}]


def managed_notes(mirror: Path, asset_id: str) -> list[Path]:
    found = []
    for path in note_paths(mirror):
        fields = _read_managed(path)
        if fields and fields.get("asset_id") == asset_id:
            found.append(path)
    return found


def wikilinks(note: str) -> list[str]:
    return re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", note)


def legacy_note(asset_id: str) -> str:
    return (
        "---\n"
        'mirror_managed: true\n'
        'authority: "cloudflare_canonical"\n'
        f'asset_id: "{asset_id}"\n'
        "---\n\n"
        "# legacy note\n"
    )


def test_translation_table_pins_exact_reviewed_hashes():
    assert set(TRANSLATIONS) == set(PRODUCTION_HASHES)
    for asset_id, entry in TRANSLATIONS.items():
        assert entry["reviewed_hash"] == PRODUCTION_HASHES[asset_id]


def test_renderer_is_deterministic_for_production_asset():
    asset = make_asset("knowledge-architecture-local-execution-shared-intelligence")
    first = render_asset_markdown(asset)
    assert first == render_asset_markdown(asset)
    assert "# 本地执行与共享智能架构" in first
    assert "## 核心结论" in first
    assert "## 实践要点" in first
    assert "## 来源与置信度" in first
    assert "## 复核条件" in first
    assert "## 相关笔记" in first


def test_three_production_assets_render_into_chinese_layout(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    result = sync_assets(production_assets(), vault)
    mirror = vault / MIRROR_DIRECTORY

    assert result["status"] == "PASS"
    for asset_id, relative in EXPECTED_PATHS.items():
        note = mirror / relative
        assert note.is_file(), relative
        text = note.read_text(encoding="utf-8")
        assert "本笔记由 Cloudflare Canonical 单向派生" in text
        for heading in ("## 核心结论", "## 实践要点", "## 来源与置信度", "## 复核条件"):
            assert heading in text
    assert (mirror / HOME_NOTE).is_file()
    assert (mirror / INDEX_NOTE).is_file()


def test_notes_preserve_machine_metadata_out_of_rendered_body(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    sync_assets(production_assets(), vault)
    mirror = vault / MIRROR_DIRECTORY

    for asset_id, relative in EXPECTED_PATHS.items():
        fields, body = _frontmatter((mirror / relative).read_text(encoding="utf-8"))
        source = PRODUCTION_CONTENT[asset_id]
        assert fields["mirror_managed"] is True
        assert fields["authority"] == "cloudflare_canonical"
        assert fields["asset_id"] == asset_id
        assert fields["version"] == "1.0"
        assert fields["content_version"] == "1.0"
        assert fields["canonical_version"] == 1
        assert fields["content_hash"] == PRODUCTION_HASHES[asset_id]
        assert fields["category"] == source["category"]
        assert fields["confidence"] == source["confidence"]
        assert fields["review_policy"] == source["review_policy"]
        assert fields["provenance"]["canonical_version"] == 1
        assert fields["localization_applied"] is True
        for machine_key in ("mirror_managed:", "authority:", "content_hash:", "provenance:"):
            assert machine_key not in body


def test_chinese_tags_links_home_and_index(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    sync_assets(production_assets(), vault)
    mirror = vault / MIRROR_DIRECTORY
    home = (mirror / HOME_NOTE).read_text(encoding="utf-8")
    index = (mirror / INDEX_NOTE).read_text(encoding="utf-8")

    for asset_id, relative in EXPECTED_PATHS.items():
        target = relative[:-3]
        assert f"[[{target}|" in home
        assert f"| {asset_id} | {relative} |" in index
        fields, _ = _frontmatter((mirror / relative).read_text(encoding="utf-8"))
        assert fields["note_title"] in home
        assert any(tag in {"AI 架构", "工作流"} for tag in fields["tags"])

    first, second, third = (
        (mirror / EXPECTED_PATHS["knowledge-architecture-local-execution-shared-intelligence"]).read_text(encoding="utf-8"),
        (mirror / EXPECTED_PATHS["knowledge-architecture-scoped-knowledge-layers"]).read_text(encoding="utf-8"),
        (mirror / EXPECTED_PATHS["knowledge-workflow-auditable-task-contract"]).read_text(encoding="utf-8"),
    )
    assert "[[AI 架构/按范围隔离的知识分层模型]]" in first
    assert "[[工作流/可审计的 AI 任务契约]]" in first
    assert "[[AI 架构/本地执行与共享智能架构]]" in second
    assert "[[工作流/可审计的 AI 任务契约]]" in second
    assert "[[AI 架构/本地执行与共享智能架构]]" in third
    assert "[[AI 架构/按范围隔离的知识分层模型]]" in third

    for source in (home, first, second, third):
        for link in wikilinks(source):
            assert (mirror / f"{link}.md").is_file(), link


def test_stale_hash_invalidates_localized_override(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    asset_id = "knowledge-architecture-local-execution-shared-intelligence"
    sync_assets([make_asset(asset_id)], vault)
    mirror = vault / MIRROR_DIRECTORY
    localized = mirror / EXPECTED_PATHS[asset_id]
    assert localized.is_file()

    stale = make_asset(
        asset_id,
        content_hash="0" * 64,
        version="2.0",
        canonical_version=2,
        content_overrides={
            "title": "Changed Canonical Title",
            "summary": "Changed canonical summary that must render instead of the stale translation.",
        },
    )
    result = sync_assets([stale], vault)
    assert result["assets"][0]["localization_applied"] is False

    notes = managed_notes(mirror, asset_id)
    assert len(notes) == 1
    assert not localized.exists()
    text = notes[0].read_text(encoding="utf-8")
    assert "本地执行与共享智能架构" not in text
    assert "Changed canonical summary" in text
    fields, _ = _frontmatter(text)
    assert fields["localization_applied"] is False
    assert fields["content_hash"] == "0" * 64


def test_partial_sync_preserves_index_and_other_notes(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    sync_assets(production_assets(), vault)
    mirror = vault / MIRROR_DIRECTORY
    untouched = mirror / EXPECTED_PATHS["knowledge-workflow-auditable-task-contract"]
    original = untouched.read_bytes()

    result = sync_assets(
        [make_asset("knowledge-architecture-local-execution-shared-intelligence")], vault
    )

    entries = result["index_entries"]
    for asset_id, relative in EXPECTED_PATHS.items():
        assert entries[asset_id] == relative
    index = (mirror / INDEX_NOTE).read_text(encoding="utf-8")
    for asset_id, relative in EXPECTED_PATHS.items():
        assert f"| {asset_id} | {relative} |" in index
    home = (mirror / HOME_NOTE).read_text(encoding="utf-8")
    assert "[[工作流/可审计的 AI 任务契约|" in home
    assert untouched.read_bytes() == original


def test_repeat_sync_leaves_notes_home_and_index_unchanged(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    sync_assets(production_assets(), vault)
    mirror = vault / MIRROR_DIRECTORY
    managed = [mirror / relative for relative in EXPECTED_PATHS.values()]
    managed += [mirror / HOME_NOTE, mirror / INDEX_NOTE]
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in managed}

    result = sync_assets(production_assets(), vault)

    assert all(entry["action"] == "UNCHANGED" for entry in result["assets"])
    for path, (data, mtime) in before.items():
        assert path.read_bytes() == data, path
        assert path.stat().st_mtime_ns == mtime, path


def test_legacy_flat_note_is_migrated_after_successful_readback(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    mirror = vault / MIRROR_DIRECTORY
    mirror.mkdir()
    asset_id = "knowledge-architecture-local-execution-shared-intelligence"
    legacy = mirror / f"{asset_id}.md"
    legacy.write_text(legacy_note(asset_id), encoding="utf-8")

    result = sync_assets([make_asset(asset_id)], vault)

    friendly = mirror / EXPECTED_PATHS[asset_id]
    assert friendly.is_file()
    assert not legacy.exists()
    assert result["assets"][0]["migrated_from"] == [f"{asset_id}.md"]


def test_unmanaged_flat_note_is_left_untouched(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    mirror = vault / MIRROR_DIRECTORY
    mirror.mkdir()
    asset_id = "knowledge-architecture-local-execution-shared-intelligence"
    legacy = mirror / f"{asset_id}.md"
    legacy.write_text("# User flat note\n", encoding="utf-8")

    result = sync_assets([make_asset(asset_id)], vault)

    assert legacy.read_text(encoding="utf-8") == "# User flat note\n"
    assert (mirror / EXPECTED_PATHS[asset_id]).is_file()
    assert result["assets"][0]["migrated_from"] == []


def test_refuses_collision_with_unmanaged_friendly_target(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    mirror = vault / MIRROR_DIRECTORY
    target = mirror / EXPECTED_PATHS["knowledge-architecture-local-execution-shared-intelligence"]
    target.parent.mkdir(parents=True)
    target.write_text("# User note\n", encoding="utf-8")

    with pytest.raises(ValueError, match="refusing collision"):
        sync_assets([make_asset("knowledge-architecture-local-execution-shared-intelligence")], vault)
    assert target.read_text(encoding="utf-8") == "# User note\n"


def test_sync_does_not_mutate_canonical_input(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    asset = make_asset("knowledge-workflow-auditable-task-contract")
    snapshot = copy.deepcopy(asset)
    sync_assets([asset], vault)
    assert asset == snapshot


def test_accepts_cloud_asset_read_mcp_wrapper(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    asset = make_asset("knowledge-workflow-auditable-task-contract")
    result = sync_assets({"structuredContent": asset}, vault)
    assert result["assets"][0]["readback"]["content_match"]


def test_rejects_conflicting_duplicates_before_any_write(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    asset_id = "knowledge-architecture-local-execution-shared-intelligence"
    with pytest.raises(ValueError, match="conflicting duplicate"):
        sync_assets([make_asset(asset_id), make_asset(asset_id, content_hash="other")], vault)
    assert not (vault / MIRROR_DIRECTORY).exists()


def test_rejects_unsafe_asset_id(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    asset = make_asset("knowledge-workflow-auditable-task-contract")
    asset["asset_id"] = "../outside"
    with pytest.raises(ValueError, match="safe, stable filename"):
        sync_assets([asset], vault)


def test_rejects_symlinked_mirror_directory(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (vault / MIRROR_DIRECTORY).symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic link"):
        sync_assets([make_asset("knowledge-workflow-auditable-task-contract")], vault)


def test_task_contract_lists_all_implementation_files():
    contract = json.loads(
        (ROOT / "task_contract_cloudflare_obsidian_mirror_v1.json").read_text(encoding="utf-8")
    )
    assert set(contract["expected_files"]) == {
        "docs/cloudflare-obsidian-mirror.md",
        "scripts/cloud_asset_obsidian_mirror.py",
        "task_contract_cloudflare_obsidian_mirror_v1.json",
        "tests/test_cloud_asset_obsidian_mirror.py",
    }
