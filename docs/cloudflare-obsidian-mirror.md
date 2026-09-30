# Cloudflare Canonical to Obsidian mirror

Cloud Asset KNOWLEDGE in Cloudflare remains the only canonical source. Obsidian
is a one-way, human-readable derived mirror. The exporter writes a Chinese,
human-readable knowledge library under the Vault folder
`Cloudflare Canonical Mirror`; Cloudflare Canonical is never written to.

## Human folder layout

    Cloudflare Canonical Mirror/
      00 知识首页.md
      AI 架构/
        本地执行与共享智能架构.md
        按范围隔离的知识分层模型.md
      工作流/
        可审计的 AI 任务契约.md
      _System/
        Mirror Index.md

Notes are grouped into category-derived folders and named with deterministic
Chinese titles. `00 知识首页.md` links to every mirrored note, and
`_System/Mirror Index.md` maps each `asset_id` to its note path.

## What each note contains

- Chinese sections for the core conclusion, practice points, source and
  confidence, and review condition.
- Deterministic wikilinks between related notes.
- YAML frontmatter used only for machine verification: `mirror_managed`,
  `authority`, `asset_id`, `version`, `content_version`, `canonical_version`,
  `content_hash`, `category`, `provenance`, `confidence`, and `review_policy`.
  These fields stay out of the rendered body.

The Chinese presentation text is a source-faithful, hash-pinned translation of
the Canonical summary, principles, source assessment, confidence, and review
policy. It translates only what the Canonical record already says: every
Canonical principle is preserved exactly, with nothing summarized, omitted, or
added, so the presentation never introduces recommendations, assumptions, or
broader claims that are not in that record. For example, the local-execution
note is presented as an architecture pattern: local execution is appropriate
when an environment requires it, but it is not universally mandatory; the
scoped-knowledge note keeps indexes as access mechanisms rather than additional
sources of truth and keeps review before promotion; and the task-contract note
keeps that completion is not inferred from an Agent narrative alone and that
outputs or read-back are verified when applicable.

Each override is keyed by the reviewed `content_hash` and applies only while the
Canonical `content_hash` still matches that reviewed hash. When Canonical
changes, the override is invalidated and the exporter falls back to a safe
rendering of the current Canonical content, so stale translations cannot survive
a Canonical update. The translated `confidence` is shown only in the human body;
the YAML `confidence`, `provenance`, and `review_policy` fields keep the exact
Canonical values for machine verification.

## Standard flow

1. Read each approved asset with the existing read-only Cloud Asset Read
   connector, using cloud_asset_read_get_asset(asset_id).
2. Pass the exact returned asset record or its structuredContent to
   scripts/cloud_asset_obsidian_mirror.py. The exporter holds no Cloudflare
   credentials and has no Cloudflare write path.
3. The exporter creates or updates one Markdown note per asset_id. Repeating
   the same version and hash leaves the notes, home page, and index untouched.
4. The exporter reads every note, the home page, and the index back from the
   Vault and checks asset ID, versions, hash, category, provenance, confidence,
   review policy, tags, and rendered content before returning PASS.

When orchestrated from ChatGPT/Work, pass the exact Cloud Asset Read
response directly to the command's stdin; the user does not need to copy or
move an asset file:

    python scripts/cloud_asset_obsidian_mirror.py --input - --vault "$env:OBSIDIAN_VAULT_PATH"

A standalone local run can instead use --input with a JSON file.

The Vault path must already exist. The command writes only to Cloudflare
Canonical Mirror. It refuses to overwrite unmanaged notes, refuses a mirror
directory or note path that is a symbolic link, refuses note-path collisions,
and only migrates a legacy flat `asset_id.md` note after its frontmatter proves
this mirror owns it and the new friendly note has been written and verified.

## Index, partial sync, and idempotency

The mirror index merges the current sync into the existing index, so entries
for assets that are not part of a partial sync are preserved. Re-syncing
identical Canonical content produces no file changes.

## Authority and review boundary

The note frontmatter and body state that Cloudflare Canonical is authoritative
and Markdown is a derived mirror. Editing, deleting, or renaming a note never
changes or deletes Cloudflare Canonical. Canonical changes go through the
approved Candidate review, fact and conflict checks, Cloud Asset write/read-
back, then a fresh Cloud Asset Read and local mirror read-back. Do not create a
second source of truth or bidirectional sync.

A cloud code-only task verifies the exporter with fixture tests. It does not
prove a real Vault write/read-back; live Vault synchronization is only claimed
when a real Vault endpoint is demonstrably available.
