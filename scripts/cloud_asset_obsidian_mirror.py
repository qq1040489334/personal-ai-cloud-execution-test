"""Deterministic one-way mirror from read-only Cloud Asset KNOWLEDGE to Obsidian."""
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
NOTICE = (
    "Cloudflare Canonical is authoritative. This file is a derived, one-way "
    "human-readable mirror; editing it does not update Canonical."
)
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}\Z")
ORDER = ("summary", "principles", "source_assessment", "confidence", "review_policy", "category", "title")
LABELS = {
    "summary": "Summary",
    "principles": "Principles",
    "source_assessment": "Source assessment",
    "confidence": "Confidence",
    "review_policy": "Review policy",
    "category": "Category",
    "title": "Title",
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


def _metadata(asset: dict[str, Any]) -> dict[str, Any]:
    asset_id, version, content_hash = _validate(asset)
    provenance = asset.get("provenance") or {}
    source = provenance.get("source") or {}
    promotion = provenance.get("promotion") or {}
    verification = provenance.get("verification") or {}
    content = asset["content"]
    category = content.get("category") if isinstance(content, dict) else None
    metadata = {
        "mirror_schema_version": 1,
        "mirror_managed": True,
        "mirror_direction": "cloudflare_to_obsidian",
        "authority": "cloudflare_canonical",
        "asset_id": asset_id,
        "asset_type": "KNOWLEDGE",
        "content_version": str(version),
        "canonical_version": provenance.get("canonical_version", asset.get("canonical_version")),
        "content_hash": content_hash,
        "category": category if category is not None else asset.get("subtype"),
        "provenance_source_identity": source.get("identity"),
        "provenance_source_location": source.get("location"),
        "provenance_source_version": provenance.get("source_version"),
        "provenance_promotion_decision": promotion.get("decision"),
        "provenance_verified_at": verification.get("verified_at"),
        "canonical_hash_verified": verification.get("content_hash_matches"),
    }
    if isinstance(content, dict):
        for key in ("confidence", "review_policy"):
            if key in content:
                metadata[key] = content[key]
    return metadata


def _title(asset: dict[str, Any]) -> str:
    content = asset["content"]
    if isinstance(content, dict) and isinstance(content.get("title"), str):
        return content["title"]
    acronyms = {"ai", "api", "mcp", "url", "id"}
    return " ".join(
        word.upper() if word.lower() in acronyms else word.capitalize()
        for word in asset["asset_id"].replace("_", "-").split("-")
    )


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


def _body(asset: dict[str, Any]) -> str:
    sections = [f"# {_title(asset)}", f"> {NOTICE}"]
    content = asset["content"]
    if isinstance(content, dict):
        keys = [key for key in ORDER if key in content]
        keys += sorted(key for key in content if key not in ORDER)
        for key in keys:
            sections.append(f"## {LABELS.get(key, key.replace('_', ' ').capitalize())}\n\n{_value(content[key])}")
    else:
        sections.append(f"## Content\n\n{_value(content)}")

    provenance = asset.get("provenance") or {}
    source = provenance.get("source") or {}
    promotion = provenance.get("promotion") or {}
    verification = provenance.get("verification") or {}
    rows = []
    for label, value in (
        ("Source identity", source.get("identity")),
        ("Source location", source.get("location")),
        ("Source version", provenance.get("source_version")),
        ("Promotion decision", promotion.get("decision")),
        ("Verified at", verification.get("verified_at")),
    ):
        if value is not None and value != "":
            rows.append(f"- **{label}:** {value}")
    if rows:
        sections.append("## Provenance\n\n" + "\n".join(rows))
    return "\n\n".join(sections) + "\n"


def render_asset_markdown(asset: dict[str, Any]) -> str:
    metadata = _metadata(asset)
    yaml = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)}"
        for key, value in metadata.items()
    )
    return f"---\n{yaml}\n---\n\n{_body(asset)}"


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


def _write_atomic(path: Path, note: str) -> None:
    temporary = None
    try:
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


def sync_assets(payload: Any, vault_directory: str | Path) -> dict[str, Any]:
    assets = _assets(payload)
    if not assets:
        raise ValueError("no Cloud Asset Read records were supplied")
    by_id = {}
    for asset in assets:
        _validate(asset)
        key = asset["asset_id"].casefold()
        if key in by_id and by_id[key] != asset:
            raise ValueError(f"conflicting duplicate asset_id in one batch: {asset['asset_id']}")
        by_id[key] = asset

    vault, mirror = _vault_paths(vault_directory)
    results = []
    for asset in sorted(by_id.values(), key=lambda item: item["asset_id"].casefold()):
        asset_id = asset["asset_id"]
        path = mirror / f"{asset_id}.md"
        if path.is_symlink():
            raise ValueError(f"{asset_id}: refusing to write through a symbolic link")
        expected = render_asset_markdown(asset)
        action = "CREATED"
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            try:
                fields, _ = _frontmatter(existing)
            except ValueError as exc:
                raise ValueError(f"{asset_id}: target exists but is not this mirror's managed note") from exc
            if (
                fields.get("mirror_managed") is not True
                or fields.get("authority") != "cloudflare_canonical"
                or fields.get("asset_id") != asset_id
            ):
                raise ValueError(f"{asset_id}: target exists but is not this mirror's managed note")
            action = "UNCHANGED" if existing == expected else "UPDATED"
        if action != "UNCHANGED":
            _write_atomic(path, expected)

        readback = path.read_text(encoding="utf-8")
        fields, body = _frontmatter(readback)
        expected_fields = _metadata(asset)
        checks = {
            "asset_id_match": fields.get("asset_id") == asset_id,
            "content_version_match": fields.get("content_version") == expected_fields["content_version"],
            "canonical_version_match": fields.get("canonical_version") == expected_fields["canonical_version"],
            "content_hash_match": fields.get("content_hash") == asset["content_hash"],
            "content_match": body == _body(asset),
            "managed_mirror_match": fields == expected_fields,
            "rendered_note_match": readback == expected,
        }
        if not all(checks.values()):
            raise ValueError(f"{asset_id}: Vault read-back verification failed")
        results.append({
            "asset_id": asset_id,
            "content_version": expected_fields["content_version"],
            "canonical_version": expected_fields["canonical_version"],
            "content_hash": asset["content_hash"],
            "action": action,
            "note_path": path.relative_to(vault).as_posix(),
            "absolute_path": str(path),
            "readback": checks,
        })
    return {
        "status": "PASS",
        "authority": "cloudflare_canonical",
        "mirror_direction": "cloudflare_to_obsidian",
        "vault_path": str(vault),
        "mirror_directory": MIRROR_DIRECTORY,
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
