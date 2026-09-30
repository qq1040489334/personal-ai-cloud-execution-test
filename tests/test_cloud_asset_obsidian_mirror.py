from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.cloud_asset_obsidian_mirror import (  # noqa: E402
    MIRROR_DIRECTORY,
    render_asset_markdown,
    sync_assets,
)


def sample_asset(*, version="1.0", canonical_version=1, content_hash="hash-v1", summary="Original summary"):
    return {
        "asset_id": "knowledge-architecture-local-execution-shared-intelligence",
        "asset_type": "KNOWLEDGE",
        "version": version,
        "content_hash": content_hash,
        "provenance": {
            "source": {"identity": "reviewed-video", "location": "https://example.invalid/source"},
            "source_version": "candidate-v1",
            "content_version": version,
            "canonical_version": canonical_version,
            "verification": {"verified_at": "2026-09-30T11:26:00+08:00", "content_hash_matches": True},
            "promotion": {"decision": "PROMOTE"},
        },
        "content": {
            "category": "architecture_pattern",
            "summary": summary,
            "principles": ["Keep canonical knowledge separate.", "Use the executor with the required environment."],
            "source_assessment": "Retained as a general architecture pattern.",
            "confidence": "medium-high",
            "review_policy": "Re-review if primary documentation changes.",
        },
    }


def test_renderer_is_deterministic_and_contains_required_fields():
    asset = sample_asset()
    first = render_asset_markdown(asset)
    assert first == render_asset_markdown(asset)
    assert 'authority: "cloudflare_canonical"' in first
    assert f'asset_id: "{asset["asset_id"]}"' in first
    assert 'content_version: "1.0"' in first
    assert "canonical_version: 1" in first
    assert 'content_hash: "hash-v1"' in first
    assert "Cloudflare Canonical is authoritative." in first
    assert "## Review policy" in first
    assert "Re-review if primary documentation changes." in first


def test_sync_creates_note_and_reads_back_metadata_and_content(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    asset = sample_asset()
    result = sync_assets([asset], vault)
    note = vault / MIRROR_DIRECTORY / f'{asset["asset_id"]}.md'

    assert result["status"] == "PASS"
    assert note.is_file()
    assert result["assets"][0]["action"] == "CREATED"
    assert all(result["assets"][0]["readback"].values())


def test_repeating_same_version_and_hash_is_idempotent(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    asset = sample_asset()
    sync_assets([asset], vault)
    note = vault / MIRROR_DIRECTORY / f'{asset["asset_id"]}.md'
    original, original_mtime = note.read_bytes(), note.stat().st_mtime_ns

    result = sync_assets([asset], vault)

    assert result["assets"][0]["action"] == "UNCHANGED"
    assert note.read_bytes() == original
    assert note.stat().st_mtime_ns == original_mtime
    assert len(list((vault / MIRROR_DIRECTORY).glob("*.md"))) == 1


def test_new_canonical_version_updates_same_note(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    old = sample_asset()
    new = sample_asset(
        version="2.0",
        canonical_version=2,
        content_hash="hash-v2",
        summary="Updated canonical summary",
    )
    sync_assets([old], vault)
    result = sync_assets([new], vault)
    notes = list((vault / MIRROR_DIRECTORY).glob("*.md"))
    note = notes[0].read_text(encoding="utf-8")

    assert result["assets"][0]["action"] == "UPDATED"
    assert len(notes) == 1
    assert 'content_version: "2.0"' in note
    assert "canonical_version: 2" in note
    assert 'content_hash: "hash-v2"' in note
    assert "Updated canonical summary" in note


def test_accepts_cloud_asset_read_mcp_wrapper(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    result = sync_assets({"structuredContent": sample_asset()}, vault)
    assert result["assets"][0]["readback"]["content_match"]


def test_rejects_conflicting_duplicates_before_any_write(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    with pytest.raises(ValueError, match="conflicting duplicate"):
        sync_assets([sample_asset(), sample_asset(content_hash="other")], vault)
    assert not (vault / MIRROR_DIRECTORY).exists()


def test_does_not_overwrite_unmanaged_note(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    target_dir = vault / MIRROR_DIRECTORY
    target_dir.mkdir()
    target = target_dir / f'{sample_asset()["asset_id"]}.md'
    target.write_text("# User note\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not this mirror"):
        sync_assets([sample_asset()], vault)
    assert target.read_text(encoding="utf-8") == "# User note\n"


def test_rejects_unsafe_asset_id(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    asset = sample_asset()
    asset["asset_id"] = "../outside"
    with pytest.raises(ValueError, match="safe, stable filename"):
        sync_assets([asset], vault)


def test_task_contract_lists_all_implementation_files():
    contract = json.loads((ROOT / "task_contract_cloudflare_obsidian_mirror_v1.json").read_text(encoding="utf-8"))
    assert set(contract["expected_files"]) == {
        "docs/cloudflare-obsidian-mirror.md",
        "scripts/cloud_asset_obsidian_mirror.py",
        "task_contract_cloudflare_obsidian_mirror_v1.json",
        "tests/test_cloud_asset_obsidian_mirror.py",
    }
