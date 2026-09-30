"""Deterministic one-way mirror from read-only Cloud Asset KNOWLEDGE to Obsidian.

The presentation layer (Chinese titles, folder layout, human-readable sections,
home page, and index) is purely derived. Cloudflare Canonical stays the single
authoritative source; this exporter never writes to Cloudflare.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

MIRROR_DIRECTORY = "Cloudflare Canonical Mirror"
HOME_NOTE = "00 知识首页.md"
INDEX_NOTE = "_System/Mirror Index.md"
MIRROR_MARKER = "<!-- mirror-managed: cloudflare-canonical -->"
MIRROR_TAG = "cloudflare-canonical-mirror"
DEFAULT_FOLDER = "其他"
NOTICE = (
    "本笔记由 Cloudflare Canonical 单向派生，仅供人读。Cloudflare Canonical 是唯一权威来源；"
    "编辑、重命名或删除本笔记都不会改变 Canonical。"
)
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}\Z")
BAD_COMPONENT = re.compile(r"[/\\\x00-\x1f]")

CATEGORY_FOLDERS = {
    "architecture": "AI 架构",
    "architecture_pattern": "AI 架构",
    "ai_architecture": "AI 架构",
    "knowledge_architecture": "AI 架构",
    "workflow": "工作流",
    "workflow_pattern": "工作流",
    "process": "工作流",
}

CONTENT_LABELS = {
    "summary": "核心结论",
    "principles": "实践要点",
    "source_assessment": "来源评估",
    "confidence": "置信度",
    "review_policy": "复核条件",
    "title": "标题",
    "category": "分类",
}
EXTRA_ORDER = ("source_assessment",)

# Reviewed Chinese presentation overrides. Each entry applies only while the
# asset content_hash still matches the reviewed hash, so a Canonical change
# invalidates the translation and forces the safe canonical fallback.
TRANSLATIONS: dict[str, dict[str, Any]] = {
    "knowledge-architecture-local-execution-shared-intelligence": {
        "reviewed_hash": "11be28739a7d4a24dc80af494fb38e7e94f9be01d35d7a04c3d7fce9ad002e64",
        "title": "本地执行与共享智能架构",
        "folder": "AI 架构",
        "tags": ["AI 架构", "本地执行", "共享智能", "架构模式"],
        "core_conclusion": (
            "把智能能力的主要执行放在本地环境，可以保留对数据与运行时环境的控制；"
            "同时通过一个受控的共享层，把经过审阅的规范化知识沉淀下来，供不同场景复用。"
        ),
        "practice_points": [
            "默认在本地完成推理与数据处理，避免把未审阅的数据直接送出。",
            "共享层只接收经过来源核对与冲突检查的规范化知识。",
            "Cloudflare Canonical 保持为唯一权威来源，派生镜像只读且不得反向写入。",
        ],
        "review_condition": "当主要架构文档、执行环境假设或共享边界发生变化时重新审阅。",
        "links": [
            "knowledge-architecture-scoped-knowledge-layers",
            "knowledge-workflow-auditable-task-contract",
        ],
    },
    "knowledge-architecture-scoped-knowledge-layers": {
        "reviewed_hash": "34f5c9fb08b4006fee5d63c676c9bd611452e0bb17045bef95343102dd315bc0",
        "title": "按范围隔离的知识分层模型",
        "folder": "AI 架构",
        "tags": ["AI 架构", "知识分层", "范围隔离", "边界"],
        "core_conclusion": "知识按作用范围分层，并在每一层维护独立的边界与可见性，减少跨范围污染和越权引用。",
        "practice_points": [
            "为每一层知识明确适用范围、责任方与生命周期。",
            "跨层引用必须显式声明，并经过审阅后再进入上层知识。",
            "保持单一权威来源，派生层只读，避免出现第二份事实来源。",
        ],
        "review_condition": "当分层边界、范围定义或可见性规则调整时重新审阅。",
        "links": [
            "knowledge-architecture-local-execution-shared-intelligence",
            "knowledge-workflow-auditable-task-contract",
        ],
    },
    "knowledge-workflow-auditable-task-contract": {
        "reviewed_hash": "8d3360d886b4970e675f070f16169fa6aeb8550a17da59d37300967503ff2078",
        "title": "可审计的 AI 任务契约",
        "folder": "工作流",
        "tags": ["工作流", "任务契约", "可审计", "验收标准"],
        "core_conclusion": (
            "以结构化任务契约为入口，显式声明目标、验收标准与允许改动范围，"
            "使 AI 执行过程可验证、可追溯、可审计。"
        ),
        "practice_points": [
            "每个任务都写清目标、验收条件和允许修改的文件范围。",
            "执行后保留测试结果与证据，并区分代码层验证与真实系统操作。",
            "只在授权范围内改动，遇到阻塞时如实报告而不是绕过约束。",
        ],
        "review_condition": "当任务契约格式、验收方式或审计要求变化时重新审阅。",
        "links": [
            "knowledge-architecture-local-execution-shared-intelligence",
            "knowledge-architecture-scoped-knowledge-layers",
        ],
    },
}


def _assets(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [asset for item in value for asset in _assets(item)]
    if not isinstance(value, dict):
        raise ValueError("Cloud Asset Read input must contain an asset object")
    if "asset_id" in value:
        return [value]
    for key in ("structuredContent", "result", "data"):
        if key in value:
            return _assets(value[key])
    if isinstance(value.get("assets"), list):
        return _assets(value["assets"])
    for block in value.get("content", []):
        if isinstance(block, dict) and isinstance(block.get("text"), str):
            try:
                return _assets(json.loads(block["text"]))
            except json.JSONDecodeError:
                pass
    raise ValueError("input does not contain a Cloud Asset Read record")


def _validate(asset: dict[str, Any]) -> tuple[str, Any, str]:
    asset_id = asset.get("asset_id")
    if not isinstance(asset_id, str) or not SAFE_ID.fullmatch(asset_id):
        raise ValueError("asset_id must be a safe, stable filename identifier")
    if str(asset.get("asset_type", "")).upper() != "KNOWLEDGE":
        raise ValueError(f"{asset_id}: only KNOWLEDGE assets can be mirrored")
    if not isinstance(asset.get("content_hash"), str) or not asset["content_hash"].strip():
        raise ValueError(f"{asset_id}: canonical content_hash is required")
    provenance = asset.get("provenance") or {}
    if not isinstance(provenance, dict):
        raise ValueError(f"{asset_id}: provenance must be an object")
    version = asset.get("version") or provenance.get("content_version")
    if version is None or not str(version).strip():
        raise ValueError(f"{asset_id}: canonical content version is required")
    if not isinstance(asset.get("content"), (dict, list, str)):
        raise ValueError(f"{asset_id}: canonical content is required")
    return asset_id, version, asset["content_hash"]


def _content(asset: dict[str, Any]) -> dict[str, Any]:
    value = asset.get("content")
    return value if isinstance(value, dict) else {}


def _category(asset: dict[str, Any]) -> Any:
    category = _content(asset).get("category")
    return category if category is not None else asset.get("subtype")


def _category_folder(category: Any) -> str:
    if category is None:
        return DEFAULT_FOLDER
    return CATEGORY_FOLDERS.get(str(category), DEFAULT_FOLDER)


def _fallback_tags(category: Any) -> list[str]:
    tags = [MIRROR_TAG]
    if category:
        tags.insert(0, str(category))
    return tags


def _title(asset: dict[str, Any]) -> str:
    content = _content(asset)
    if isinstance(content.get("title"), str) and content["title"].strip():
        return content["title"]
    acronyms = {"ai", "api", "mcp", "url", "id"}
    return " ".join(
        word.upper() if word.lower() in acronyms else word.capitalize()
        for word in asset["asset_id"].replace("_", "-").split("-")
    )


def _extra_sections(content: dict[str, Any]) -> list[tuple[str, Any]]:
    if not isinstance(content, dict):
        return []
    handled = {"summary", "principles", "review_policy", "title", "category", "confidence"}
    keys = [key for key in EXTRA_ORDER if key in content]
    keys += sorted(key for key in content if key not in handled and key not in EXTRA_ORDER)
    return [(CONTENT_LABELS.get(key, key.replace("_", " ").capitalize()), content[key]) for key in keys]


def _presentation(asset: dict[str, Any]) -> dict[str, Any]:
    asset_id = asset["asset_id"]
    content = _content(asset)
    translation = TRANSLATIONS.get(asset_id)
    localized = bool(translation) and translation.get("reviewed_hash") == asset.get("content_hash")
    if localized:
        links = []
        for target_id in translation.get("links", []):
            target = TRANSLATIONS.get(target_id)
            if target:
                links.append(f"{target['folder']}/{target['title']}")
        return {
            "title": translation["title"],
            "folder": translation["folder"],
            "tags": list(translation["tags"]),
            "core": translation.get("core_conclusion"),
            "points": list(translation.get("practice_points", [])),
            "review": translation.get("review_condition") or content.get("review_policy"),
            "extra": _extra_sections(content),
            "links": links,
            "localized": True,
            "reviewed_hash": translation["reviewed_hash"],
        }
    category = _category(asset)
    return {
        "title": _title(asset),
        "folder": _category_folder(category),
        "tags": _fallback_tags(category),
        "core": content.get("summary"),
        "points": content.get("principles") or [],
        "review": content.get("review_policy"),
        "extra": _extra_sections(content),
        "links": [],
        "localized": False,
        "reviewed_hash": None,
    }


def _metadata(asset: dict[str, Any], presentation: dict[str, Any]) -> dict[str, Any]:
    asset_id, version, content_hash = _validate(asset)
    provenance = asset.get("provenance") or {}
    content = _content(asset)
    return {
        "mirror_schema_version": 2,
        "mirror_managed": True,
        "mirror_direction": "cloudflare_to_obsidian",
        "authority": "cloudflare_canonical",
        "asset_id": asset_id,
        "asset_type": "KNOWLEDGE",
        "version": str(version),
        "content_version": str(version),
        "canonical_version": provenance.get("canonical_version", asset.get("canonical_version")),
        "content_hash": content_hash,
        "category": _category(asset),
        "folder": presentation["folder"],
        "note_title": presentation["title"],
        "tags": presentation["tags"],
        "provenance": provenance,
        "confidence": content.get("confidence"),
        "review_policy": content.get("review_policy"),
        "localization_applied": presentation["localized"],
        "localization_reviewed_hash": presentation["reviewed_hash"],
    }


def _value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join("- " + _value(item).replace("\n", "\n  ") for item in value)
    if isinstance(value, dict):
        return "\n".join(
            f"- **{key}:** " + _value(value[key]).replace("\n", "\n  ")
            for key in sorted(value)
        )
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _source_rows(asset: dict[str, Any]) -> list[str]:
    provenance = asset.get("provenance") or {}
    source = provenance.get("source") if isinstance(provenance.get("source"), dict) else {}
    promotion = provenance.get("promotion") if isinstance(provenance.get("promotion"), dict) else {}
    verification = provenance.get("verification") if isinstance(provenance.get("verification"), dict) else {}
    rows = []
    for label, value in (
        ("来源标识", source.get("identity")),
        ("来源位置", source.get("location")),
        ("来源版本", provenance.get("source_version")),
        ("提升决定", promotion.get("decision")),
        ("核对时间", verification.get("verified_at")),
    ):
        if value is not None and value != "":
            rows.append(f"- **{label}：** {value}")
    confidence = _content(asset).get("confidence")
    if confidence is not None and confidence != "":
        rows.append(f"- **置信度：** {confidence}")
    return rows


def _body(asset: dict[str, Any], presentation: dict[str, Any]) -> str:
    sections = [f"# {presentation['title']}", f"> {NOTICE}"]
    if presentation["core"] not in (None, "", []):
        sections.append("## 核心结论\n\n" + _value(presentation["core"]))
    if presentation["points"]:
        sections.append("## 实践要点\n\n" + _value(presentation["points"]))
    source_rows = _source_rows(asset)
    if source_rows:
        sections.append("## 来源与置信度\n\n" + "\n".join(source_rows))
    for label, value in presentation["extra"]:
        if value not in (None, "", []):
            sections.append(f"## {label}\n\n{_value(value)}")
    if presentation["review"] not in (None, "", []):
        sections.append("## 复核条件\n\n" + _value(presentation["review"]))
    if presentation["links"]:
        sections.append("## 相关笔记\n\n" + "\n".join(f"- [[{link}]]" for link in presentation["links"]))
    return "\n\n".join(sections) + "\n"


def _render(asset: dict[str, Any]) -> tuple[dict[str, Any], str]:
    presentation = _presentation(asset)
    metadata = _metadata(asset, presentation)
    yaml = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)}"
        for key, value in metadata.items()
    )
    return presentation, f"---\n{yaml}\n---\n\n{_body(asset, presentation)}"


def render_asset_markdown(asset: dict[str, Any]) -> str:
    return _render(asset)[1]


def _frontmatter(note: str) -> tuple[dict[str, Any], str]:
    if not note.startswith("---\n"):
        raise ValueError("mirror note is missing YAML frontmatter")
    end = note.find("\n---\n", 4)
    if end < 0:
        raise ValueError("mirror note has unterminated YAML frontmatter")
    fields = {}
    for row in note[4:end].splitlines():
        key, separator, raw = row.partition(":")
        if not separator:
            raise ValueError("mirror note has malformed YAML frontmatter")
        fields[key.strip()] = json.loads(raw.strip())
    return fields, note[end + 5 :].lstrip("\n")


def _read_managed(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    try:
        fields, _ = _frontmatter(text)
    except ValueError:
        return None
    if (
        fields.get("mirror_managed") is not True
        or fields.get("authority") != "cloudflare_canonical"
        or not isinstance(fields.get("asset_id"), str)
    ):
        return None
    return fields


def _safe_component(name: Any) -> str:
    cleaned = BAD_COMPONENT.sub("-", str(name)).strip().strip(".")
    if not cleaned or cleaned in (".", ".."):
        return "未命名"
    return cleaned


def _note_relative_path(asset_id: str, presentation: dict[str, Any]) -> str:
    folder = _safe_component(presentation["folder"])
    title = _safe_component(presentation["title"])
    return f"{folder}/{title}.md"


def _assert_no_symlink(mirror: Path, relative: str) -> None:
    current = mirror
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise ValueError(f"refusing to write through a symbolic link: {relative}")


def _prepare_parent(mirror: Path, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved = path.parent.resolve(strict=True)
    if not resolved.is_relative_to(mirror):
        raise ValueError(f"note parent escapes the mirror directory: {path.name}")


def _write_atomic(path: Path, note: str) -> None:
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(note)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _vault_paths(vault_directory: str | Path) -> tuple[Path, Path]:
    vault = Path(vault_directory).expanduser().resolve(strict=True)
    if not vault.is_dir():
        raise ValueError(f"Vault path is not a directory: {vault}")
    mirror = vault / MIRROR_DIRECTORY
    if mirror.is_symlink():
        raise ValueError("mirror directory must not be a symbolic link")
    mirror.mkdir(parents=True, exist_ok=True)
    mirror = mirror.resolve(strict=True)
    if not mirror.is_relative_to(vault):
        raise ValueError("mirror directory resolves outside the Obsidian Vault")
    return vault, mirror


def _reconcile(mirror: Path, asset_id: str, keep: Path) -> list[str]:
    removed = []
    keep_resolved = keep.resolve()
    for candidate in sorted(mirror.rglob("*.md"), key=lambda item: item.as_posix()):
        try:
            if candidate.resolve() == keep_resolved:
                continue
        except OSError:
            continue
        fields = _read_managed(candidate)
        if fields is not None and fields.get("asset_id") == asset_id:
            candidate.unlink()
            removed.append(candidate.relative_to(mirror).as_posix())
    return removed


def _load_index(mirror: Path) -> dict[str, str]:
    path = mirror / INDEX_NOTE
    entries: dict[str, str] = {}
    if not path.exists():
        return entries
    text = path.read_text(encoding="utf-8")
    if MIRROR_MARKER not in text and text.strip():
        raise ValueError(f"{INDEX_NOTE} exists but is not this mirror's managed index")
    for line in text.splitlines():
        match = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", line)
        if not match:
            continue
        asset_id, relative = match.group(1), match.group(2)
        if asset_id == "asset_id" or set(asset_id) <= set("-: "):
            continue
        entries[asset_id] = relative
    return entries


def _render_index(entries: dict[str, str]) -> str:
    lines = [
        "# 镜像索引 Mirror Index",
        "",
        MIRROR_MARKER,
        "",
        "本索引由 Cloudflare Canonical → Obsidian 镜像自动维护，"
        "将每个资产 asset_id 映射到其派生笔记路径。",
        "",
        "| asset_id | path |",
        "| --- | --- |",
    ]
    lines += [f"| {asset_id} | {entries[asset_id]} |" for asset_id in sorted(entries)]
    return "\n".join(lines) + "\n"


def _entry_title(mirror: Path, relative: str) -> str:
    path = mirror / relative
    if path.is_file():
        fields = _read_managed(path)
        if fields and isinstance(fields.get("note_title"), str) and fields["note_title"]:
            return fields["note_title"]
    return Path(relative).stem


def _render_home(entries: dict[str, str], mirror: Path) -> str:
    lines = [
        "# 知识首页",
        "",
        MIRROR_MARKER,
        "",
        "> Cloudflare Canonical 是唯一权威来源；本页及其链接的笔记均为单向派生，仅供人读。",
        "",
        f"本知识库当前收录 {len(entries)} 篇笔记。",
        "",
        "## 知识笔记",
        "",
    ]
    for asset_id in sorted(entries):
        relative = entries[asset_id]
        target = relative[:-3] if relative.endswith(".md") else relative
        lines.append(f"- [[{target}|{_entry_title(mirror, relative)}]]")
    lines += ["", "## 系统", "", f"- [[{INDEX_NOTE[:-3]}|镜像索引]]"]
    return "\n".join(lines) + "\n"


def _update_index(mirror: Path, updates: dict[str, str]) -> tuple[dict[str, str], str]:
    path = mirror / INDEX_NOTE
    _assert_no_symlink(mirror, INDEX_NOTE)
    entries = _load_index(mirror)
    entries.update(updates)
    content = _render_index(entries)
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing != content:
        _write_atomic(path, content)
    readback = path.read_text(encoding="utf-8")
    if readback != content:
        raise ValueError("mirror index read-back verification failed")
    return entries, INDEX_NOTE


def _update_home(mirror: Path, entries: dict[str, str]) -> str:
    path = mirror / HOME_NOTE
    _assert_no_symlink(mirror, HOME_NOTE)
    content = _render_home(entries, mirror)
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing != content:
        _write_atomic(path, content)
    readback = path.read_text(encoding="utf-8")
    if readback != content:
        raise ValueError("mirror home read-back verification failed")
    return HOME_NOTE


def sync_assets(payload: Any, vault_directory: str | Path) -> dict[str, Any]:
    assets = _assets(payload)
    if not assets:
        raise ValueError("no Cloud Asset Read records were supplied")
    by_id: dict[str, dict[str, Any]] = {}
    for asset in assets:
        _validate(asset)
        key = asset["asset_id"].casefold()
        if key in by_id and by_id[key] != asset:
            raise ValueError(f"conflicting duplicate asset_id in one batch: {asset['asset_id']}")
        by_id[key] = asset

    vault, mirror = _vault_paths(vault_directory)

    plans = []
    seen_targets: dict[str, str] = {}
    for asset in sorted(by_id.values(), key=lambda item: item["asset_id"].casefold()):
        presentation = _presentation(asset)
        relative = _note_relative_path(asset["asset_id"], presentation)
        if relative in seen_targets:
            raise ValueError(f"multiple assets resolve to the same mirror note: {relative}")
        seen_targets[relative] = asset["asset_id"]
        plans.append((asset, presentation, relative))

    results = []
    index_updates: dict[str, str] = {}
    for asset, presentation, relative in plans:
        asset_id = asset["asset_id"]
        target = mirror / relative
        _assert_no_symlink(mirror, relative)
        _prepare_parent(mirror, target)

        expected = _render(asset)[1]
        action = "CREATED"
        if target.exists():
            fields = _read_managed(target)
            if fields is None or fields.get("asset_id") != asset_id:
                raise ValueError(
                    f"{asset_id}: refusing collision with unmanaged or different note at {relative}"
                )
            existing = target.read_text(encoding="utf-8")
            action = "UNCHANGED" if existing == expected else "UPDATED"
        if action != "UNCHANGED":
            _write_atomic(target, expected)

        readback = target.read_text(encoding="utf-8")
        fields, body = _frontmatter(readback)
        expected_fields = _metadata(asset, presentation)
        checks = {
            "asset_id_match": fields.get("asset_id") == asset_id,
            "content_version_match": fields.get("content_version") == expected_fields["content_version"],
            "canonical_version_match": fields.get("canonical_version") == expected_fields["canonical_version"],
            "content_hash_match": fields.get("content_hash") == asset["content_hash"],
            "category_match": fields.get("category") == expected_fields["category"],
            "provenance_match": fields.get("provenance") == expected_fields["provenance"],
            "confidence_match": fields.get("confidence") == expected_fields["confidence"],
            "review_policy_match": fields.get("review_policy") == expected_fields["review_policy"],
            "content_match": body == _body(asset, presentation),
            "managed_mirror_match": fields == expected_fields,
            "rendered_note_match": readback == expected,
        }
        if not all(checks.values()):
            raise ValueError(f"{asset_id}: Vault read-back verification failed")
        migrated = _reconcile(mirror, asset_id, target)
        index_updates[asset_id] = relative
        results.append({
            "asset_id": asset_id,
            "content_version": expected_fields["content_version"],
            "canonical_version": expected_fields["canonical_version"],
            "content_hash": asset["content_hash"],
            "category": expected_fields["category"],
            "localization_applied": expected_fields["localization_applied"],
            "action": action,
            "note_path": relative,
            "absolute_path": str(target),
            "migrated_from": migrated,
            "readback": checks,
        })

    entries, index_relative = _update_index(mirror, index_updates)
    home_relative = _update_home(mirror, entries)
    return {
        "status": "PASS",
        "authority": "cloudflare_canonical",
        "mirror_direction": "cloudflare_to_obsidian",
        "vault_path": str(vault),
        "mirror_directory": MIRROR_DIRECTORY,
        "home_note": home_relative,
        "index_note": index_relative,
        "index_entries": entries,
        "assets": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Cloud Asset Read JSON file, or '-' for stdin")
    parser.add_argument("--vault", default=os.environ.get("OBSIDIAN_VAULT_PATH"))
    args = parser.parse_args(argv)
    if not args.vault:
        parser.error("--vault or OBSIDIAN_VAULT_PATH is required")
    try:
        stream = sys.stdin if args.input == "-" else Path(args.input).expanduser().open(encoding="utf-8")
        try:
            payload = json.load(stream)
        finally:
            if stream is not sys.stdin:
                stream.close()
        print(json.dumps(sync_assets(payload, args.vault), ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
