# Cloudflare Canonical to Obsidian mirror

Cloud Asset KNOWLEDGE in Cloudflare remains the only canonical source. Obsidian
is a one-way, human-readable derived mirror. Notes live in the Vault's
Cloudflare Canonical Mirror folder and are keyed by stable asset_id.

## Standard flow

1. Read each approved asset with the existing read-only Cloud Asset Read
   connector, using cloud_asset_read_get_asset(asset_id).
2. Pass the exact returned asset record or its structuredContent to
   scripts/cloud_asset_obsidian_mirror.py. The exporter holds no Cloudflare
   credentials and has no Cloudflare write path.
3. The exporter creates or updates one Markdown note per asset_id. Repeating
   the same version and hash leaves the note untouched; a new canonical version
   deterministically updates that asset's note.
4. The exporter reads every note back from the Vault and checks asset ID,
   content version, canonical version, content hash, managed metadata, and
   rendered canonical content before returning PASS.

When orchestrated from ChatGPT/Work, pass the exact Cloud Asset Read
response directly to the command's stdin; the user does not need to copy or
move an asset file:

    python scripts/cloud_asset_obsidian_mirror.py --input - --vault "$env:OBSIDIAN_VAULT_PATH"

A standalone local run can instead use --input with a JSON file.

The Vault path must already exist. The command writes only to Cloudflare
Canonical Mirror. It refuses to overwrite unmanaged notes and refuses a mirror
directory or note that is a symbolic link.

## Authority and review boundary

The note frontmatter and body state that Cloudflare Canonical is authoritative
and Markdown is a derived mirror. Editing, deleting, or renaming a note never
changes or deletes Cloudflare Canonical. Canonical changes go through the
approved Candidate review, fact and conflict checks, Cloud Asset write/read-
back, then a fresh Cloud Asset Read and local mirror read-back. Do not create a
second source of truth or bidirectional sync.
