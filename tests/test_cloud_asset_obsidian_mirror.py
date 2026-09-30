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
    _presentation,
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
        "summary": (
            "For AI collaboration systems, separate shared intelligence and management "
            "capabilities from environment-dependent execution. Shared services can host "
            "reusable knowledge, policy, and model access, while execution that depends on "
            "user files, browser sessions, apps, or credentials is handled by the local or "
            "user executor that actually owns that environment. Treat it as an architecture "
            "pattern; local execution is not universally required."
        ),
        "principles": [
            "Separate long-term shared knowledge and coordination capabilities from replaceable executors.",
            "Route tasks that need a local browser, files, apps, or login state to the executor that actually owns that environment.",
            "A remote Agent's capability depends on the tools, mounts, credentials, and execution environment actually granted; do not treat local execution as universally mandatory.",
        ],
        "source_assessment": (
            "Derived from the supplied video breakdown and normalized against public DeepSeek "
            "Harness documentation. Official docs confirm developer preview and model/tool task "
            "execution, but do not establish the video's full team-server architecture as an "
            "official feature."
        ),
        "confidence": "medium-high",
        "review_policy": (
            "Re-review if the execution architecture or DeepSeek Harness primary documentation "
            "changes significantly."
        ),
    },
    "knowledge-architecture-scoped-knowledge-layers": {
        "category": "architecture_pattern",
        "title": "Scoped Knowledge Layers",
        "summary": (
            "Organize collaborative AI knowledge by scope and lifecycle rather than one "
            "undifferentiated store. Conceptual scopes include canonical/shared operating "
            "knowledge, reusable experience, private/personal context, and a retrieval/index "
            "layer; exact names and permissions follow the system's canonical data model."
        ),
        "principles": [
            "Organize knowledge by scope and lifecycle rather than a single undifferentiated store.",
            "Separate canonical/shared operating knowledge from reusable experience, private/personal context, and the retrieval/index layer.",
            "Exact names, scopes, and permissions follow the system's canonical data model.",
            "Cross-layer references and promotions must be explicit and reviewed, keeping layer boundaries clear.",
        ],
        "source_assessment": (
            "The four-layer scheme was observed in the video. No primary-source evidence "
            "establishes it as native Harness functionality, so it is retained as a reusable "
            "pattern rather than product fact."
        ),
        "confidence": "medium",
        "review_policy": "Merge or revise this model when the canonical knowledge taxonomy changes.",
    },
    "knowledge-workflow-auditable-task-contract": {
        "category": "workflow",
        "title": "Auditable Task Contract",
        "summary": (
            "Use a structured task contract as the entry point, explicitly declaring the "
            "objective, acceptance criteria, and allowed change scope so AI execution is "
            "verifiable, traceable, and auditable."
        ),
        "principles": [
            "Use a persistent task object binding objective, context, and permissions.",
            "Keep logs and evidence so execution remains traceable.",
            "Produce artifacts and a result, and require review.",
            "Capture reusable local/cloud task contracts.",
        ],
        "source_assessment": (
            "Inspired by the video's task-card workflow and not verified as native Harness "
            "functionality, but aligned with the existing Personal AI Execution V2."
        ),
        "confidence": "high",
        "review_policy": "Re-review when the canonical execution contract changes.",
    },
}

EXPECTED_PATHS = {
    "knowledge-architecture-local-execution-shared-intelligence": "AI 架构/本地执行与共享智能架构.md",
    "knowledge-architecture-scoped-knowledge-layers": "AI 架构/按范围隔离的知识分层模型.md",
    "knowledge-workflow-auditable-task-contract": "工作流/可审计的 AI 任务契约.md",
}

# Exact reviewed Chinese presentation text for each pinned hash. These strings are
# the acceptance oracle: the rendered note must contain every one of them and no
# additional core claim or principle beyond this list.
EXPECTED_LOCALIZED = {
    "knowledge-architecture-local-execution-shared-intelligence": {
        "title": "本地执行与共享智能架构",
        "core": (
            "对于 AI 协作系统，应将共享智能/管理能力与依赖具体环境的执行分离。"
            "共享服务可承载可复用知识、策略和模型访问；依赖用户文件、浏览器会话、应用或凭据的执行，"
            "应交给实际拥有相应环境的本地/用户执行器。把它视为一种架构模式，"
            "不表示所有任务都必须在本地执行。"
        ),
        "points": [
            "将长期共享知识和协调能力与可替换执行器分离。",
            "需要本地浏览器、文件、应用或登录状态的任务，路由给实际拥有该环境的执行器。",
            "远程 Agent 的能力取决于实际授予的工具、挂载、凭据和执行环境；不要把本地执行视为普遍必需。",
        ],
        "assessment": (
            "基于提供的抖音视频拆解整理，并对照当前公开的 DeepSeek Harness 文档做了规范化。"
            "官方资料确认 Harness 处于开发者预览阶段，支持模型/工具任务执行；"
            "但未证明视频所述整套团队服务器架构是 Harness 官方功能。"
        ),
        "confidence": "中高",
        "review": "如果执行架构或 DeepSeek Harness 一手文档发生重大变化，重新审查。",
    },
    "knowledge-architecture-scoped-knowledge-layers": {
        "title": "按范围隔离的知识分层模型",
        "core": (
            "按范围和生命周期组织协作式 AI 知识，而不是把所有上下文放在一个未区分的存储中。"
            "可用的概念范围包括规范/共享的操作知识、可复用经验、私有/个人上下文以及检索/索引层。"
            "具体层名称和权限应遵循系统的 Canonical 数据模型。"
        ),
        "points": [
            "将长期规范知识与低置信度经验/候选区分开。",
            "对私有/个人上下文实施访问控制，并与共享组织知识区分。",
            "将检索/索引视为访问机制，而不是额外的事实来源。",
            "信息只有经过来源、价值和冲突审查后才能晋升。",
        ],
        "assessment": (
            "视频拆解中观察到四层组织方式。"
            "没有一手来源证据证明该精确四层方案是 DeepSeek Harness 原生功能，"
            "因此将其保留为可复用的设计模式，而非产品事实。"
        ),
        "confidence": "中",
        "review": "当规范知识分类发生变化时，合并或修订该模型。",
    },
    "knowledge-workflow-auditable-task-contract": {
        "title": "可审计的 AI 任务契约",
        "core": (
            "将重要 AI 工作表示为持久化任务对象，而不只是临时聊天。"
            "一项任务对象绑定目标、上下文、权限、执行证据/日志、产物、结果和复核状态，"
            "以支持交接、追溯和可靠的闭环复核。"
        ),
        "points": [
            "聊天可以发起工作，但持久的执行状态应存放在任务/执行系统中。",
            "将产物和证据关联到生成它的任务。",
            "不能只凭 Agent 的叙述就标记任务完成；适用时核验输出或做回读。",
            "任务执行合同应可在本地和云端执行器之间复用。",
        ],
        "assessment": (
            "受提供的视频中任务卡工作流启发。"
            "没有一手来源证据证明所述团队任务卡系统是 DeepSeek Harness 原生功能。"
            "保留的知识是一般工作流模式，并与现有 Personal AI Execution V2 设计一致。"
        ),
        "confidence": "高",
        "review": "当规范执行合同发生变化时重新审查。",
    },
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


def test_architecture_note_preserves_local_execution_nuance():
    text = render_asset_markdown(
        make_asset("knowledge-architecture-local-execution-shared-intelligence")
    )
    assert "把它视为一种架构模式，不表示所有任务都必须在本地执行" in text
    assert "应交给实际拥有相应环境的本地/用户执行器" in text
    assert "不要把本地执行视为普遍必需" in text
    assert "默认在本地完成推理与数据处理" not in text
    assert "本地是默认" not in text


def test_localized_core_and_principles_exactly_match_reviewed_copy():
    for asset_id, expected in EXPECTED_LOCALIZED.items():
        presentation = _presentation(make_asset(asset_id))
        assert presentation["localized"] is True
        assert presentation["title"] == expected["title"]
        assert presentation["core"] == expected["core"]
        assert presentation["points"] == expected["points"]
        assert len(presentation["points"]) == len(expected["points"])


def test_rendered_notes_contain_exact_copy_without_omission_or_addition():
    for asset_id, expected in EXPECTED_LOCALIZED.items():
        text = render_asset_markdown(make_asset(asset_id))
        assert expected["core"] in text
        assert expected["assessment"] in text
        assert expected["review"] in text
        points_section = text.split("## 实践要点\n\n", 1)[1].split("\n\n", 1)[0]
        rendered_points = [
            line[2:] for line in points_section.splitlines() if line.startswith("- ")
        ]
        assert rendered_points == expected["points"]


def test_user_critical_limitations_are_verbatim():
    scoped = render_asset_markdown(
        make_asset("knowledge-architecture-scoped-knowledge-layers")
    )
    assert "将检索/索引视为访问机制，而不是额外的事实来源。" in scoped
    assert "信息只有经过来源、价值和冲突审查后才能晋升。" in scoped

    contract = render_asset_markdown(
        make_asset("knowledge-workflow-auditable-task-contract")
    )
    assert "不能只凭 Agent 的叙述就标记任务完成；适用时核验输出或做回读。" in contract

    architecture = render_asset_markdown(
        make_asset("knowledge-architecture-local-execution-shared-intelligence")
    )
    assert "不表示所有任务都必须在本地执行。" in architecture
    assert "不要把本地执行视为普遍必需。" in architecture


def test_localized_source_assessment_confidence_and_review_are_chinese(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    sync_assets(production_assets(), vault)
    mirror = vault / MIRROR_DIRECTORY
    for asset_id, checks in EXPECTED_LOCALIZED.items():
        text = (mirror / EXPECTED_PATHS[asset_id]).read_text(encoding="utf-8")
        for needle in (checks["assessment"], checks["review"]):
            assert needle in text, (asset_id, needle)
        assert f"**置信度：** {checks['confidence']}" in text
        assert "Retained as a general" not in text


def test_yaml_keeps_canonical_machine_values_while_body_is_localized(tmp_path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    sync_assets(production_assets(), vault)
    mirror = vault / MIRROR_DIRECTORY
    for asset_id, relative in EXPECTED_PATHS.items():
        fields, body = _frontmatter((mirror / relative).read_text(encoding="utf-8"))
        canonical = PRODUCTION_CONTENT[asset_id]
        assert fields["confidence"] == canonical["confidence"]
        assert fields["review_policy"] == canonical["review_policy"]
        assert fields["provenance"] == make_asset(asset_id)["provenance"]
        assert fields["localization_applied"] is True
        assert f"**置信度：** {canonical['confidence']}" not in body


def test_stale_hash_disables_every_localized_field(tmp_path):
    for asset_id in EXPECTED_PATHS:
        vault = tmp_path / asset_id
        vault.mkdir()
        sync_assets([make_asset(asset_id)], vault)
        mirror = vault / MIRROR_DIRECTORY
        stale = make_asset(
            asset_id,
            content_hash="f" * 64,
            version="9.0",
            canonical_version=9,
            content_overrides={
                "title": "Fresh Canonical Title",
                "summary": "Fresh canonical summary.",
                "source_assessment": "Fresh canonical source assessment.",
                "confidence": "low",
            },
        )
        result = sync_assets([stale], vault)
        assert result["assets"][0]["localization_applied"] is False
        notes = managed_notes(mirror, asset_id)
        assert len(notes) == 1
        text = notes[0].read_text(encoding="utf-8")
        localized = TRANSLATIONS[asset_id]
        assert localized["title"] not in text
        for point in localized["practice_points"]:
            assert point not in text
        assert localized["source_assessment"] not in text
        assert f"**置信度：** {localized['confidence_display']}" not in text
        assert "Fresh canonical summary." in text
        assert "Fresh canonical source assessment." in text
        assert "**置信度：** low" in text
        fields, _ = _frontmatter(text)
        assert fields["confidence"] == "low"
        assert fields["localization_applied"] is False
        assert fields["content_hash"] == "f" * 64


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
