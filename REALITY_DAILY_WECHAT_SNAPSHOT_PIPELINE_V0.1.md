# REALITY_DAILY_WECHAT_SNAPSHOT_PIPELINE_V0.1

Design of a **daily** WeChat snapshot ingestion pipeline that flows a
Windows-local snapshot through the **existing** Personal AI REALITY layers into
Reality ingestion. This artifact is a **design/specification only**: it performs
**no production write, no Canonical write, no deploy, no credential / permission
/ binding / schema change, and creates no second state store**.

- Task id: `cf-1d4242a79ea8`
- Project: `cloud-assets-activation`
- Risk level: `LOW`
- Mode: **DESIGN / READ-ONLY**
- Builds on:
  - `REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1` (L2,
    `src/personal_ai_execution/reality_capture.py`)
  - `PERSONAL_AI_REALITY_CANONICAL_WRITER_V0.1` (L3,
    `src/personal_ai_execution/reality_canonical_writer.py`)
  - `PERSONAL_AI_ASSET_PROVENANCE_V0.2`
    (`src/personal_ai_execution/provenance_contract.py`)
  - `WINDOWS_HERMES_TRANSPORT_CONTRACT_V1`
    (`src/personal_ai_execution/hermes_orchestration.py`)
  - `REALITY_AUTO_SYNC_CURRENT_STATE_AUDIT_REPORT.md` (L1-L6 gap model)
- Design status: `DESIGNED`
- Daily ingestion status: `BLOCKED_PENDING_HUMAN_GATE` (Section 13)
- Evidence discipline: **OBSERVED / STATED / INFERRED / UNKNOWN** (Section 2)

---

## 1. Scope, intent and non-goals

**Intent.** Define the smallest, reuse-first pipeline that turns a
**once-per-day local WeChat snapshot** into Reality candidates through the
existing L2/L3 boundary, with explicit scheduling, envelope, provenance,
idempotency, retention and failure semantics.

**In scope.**

- The daily snapshot **flow** from the local runtime to Reality ingestion.
- The **snapshot/bundle envelope** the local runtime hands to the cloud.
- The **smallest integration boundary** (reuse existing normalizer/writer).
- Scheduling ownership, idempotency, retention and fail-closed handling.
- The exact **Human Gates** required before real daily ingestion.

**Non-goals / deliberately not done.**

- No local WeChat acquisition implementation, no decryption, no DB access.
- No production or Canonical write, no deploy, no scheduler/cron/queue added.
- No new state store, no schema/binding/credential/permission change.
- No `.github/workflows/` change and no Worker change.
- No claim that any live Windows host, WeChat store, relay or D1 instance exists
  (all such claims are `UNKNOWN`, Section 2).

This mirrors the repository's established contract pattern
(`REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1.md`, Section 7): a spec/report is
the only repository artifact; any reference adapter is validated out-of-tree.

---

## 2. Evidence discipline

Every claim carries one tag:

| Tag | Meaning |
| --- | --- |
| `OBSERVED` | read directly from first-party code / tests in this checkout during this run |
| `STATED` | a first-party document or code comment asserts it, not independently re-verified |
| `INFERRED` | derived from `OBSERVED` facts |
| `UNKNOWN` | no evidence; not guessed |

`OBSERVED` in this report means observed **in the checkout at this task's base
commit**, not observed live in production. A historical PASS or self-declared
baseline is never promoted to live `VERIFIED`.

---

## 3. Architecture alignment: Reality is the shared source layer

**Design principle (explicit):** WeChat ingestion feeds **Reality as the shared
source/provenance layer**, never an agent-specific memory. The pipeline is
**executor-agnostic**: any local runtime that can produce the envelope (Hermes or
another local executor) feeds the *same* Reality ingestion contract. There is no
per-agent store and no parallel source of truth.

**WeChatRead is a local runtime acquisition capability only.**

- `OBSERVED` `hello.py:25426` declares `WECHAT_READER_CAPABILITY_ID =
  "wechat-reader-v1"`; `hello.py:25550` defines the read-only, metadata-only
  probe `wechatread_real_source_probe_v0_1`.
- `OBSERVED` `hello.py:25447-25454` declares the reader output schema fields
  (`chat_id`, `message_id`, `sender_id`, `create_time_iso`,
  `content_available`, `source_db`).
- `OBSERVED` `hello.py:25406-25421` states the probe "never reads, decodes,
  prints, hashes or returns message bodies" and assumes nothing about the source.
- The reader itself is **not a dependency of the cloud**: acquisition happens on
  the local device; the cloud only normalizes a caller-supplied envelope
  (`REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1.md:41-50`).

**Cloud Agent must never access WeChat databases.** The L2 normalizer does not
read a WeChat store, database, file or network endpoint
(`REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1.md:41-44`, `OBSERVED`). Nothing in
this design widens that boundary.

Role separation (unchanged from `WINDOWS_HERMES_TRANSPORT_CONTRACT_V1:771-774`):

```
local device (Windows)                      cloud (Cloudflare)
+---------------------------+               +---------------------------------+
| WeChatRead wechat-reader  |  outbound     | Hermes relay (Human Gate)       |
| -v1 (acquisition only)    |  poll only    |        |                        |
| daily snapshot producer   | ------------> |        v                        |
| local outbound spool      |               | L2 normalize_reality_capture    |
+---------------------------+               |        |  (read-only candidate)  |
                                            |        v                        |
                                            | L3 promote_reality_candidate    |
                                            |    (Human Gate; existing writer)|
                                            |        v                        |
                                            | Personal AI Canonical (ASSET_DB)|
                                            +---------------------------------+
```

`REALITY` is **source/provenance, never a target** (`OBSERVED`
`reality_canonical_writer.py:17-21,48-52`; promotion routes to `KNOWLEDGE` /
`SKILL` / `DECISION`). A daily WeChat snapshot therefore *supplies* Reality; it
does not create a WeChat-shaped canonical asset and does not become an agent's
private memory.

---

## 4. Existing components reused (evidence)

| Link | Status (this run) | Evidence |
| --- | --- | --- |
| L1 local WeChat acquisition | `UNKNOWN` / local-only | `hello.py:21184-21209` `wechat_snapshot_to_reality` is `BLOCKED`, `requires_local_device=True`; `hello.py:25550` reader probe. No bridge in repo (`OBSERVED`). |
| L2 normalization | Implemented, read-only | `src/personal_ai_execution/reality_capture.py:249` `normalize_reality_capture`, `:418` `build_capture_envelope` (`OBSERVED`). |
| L3 canonical promotion | Implemented, fail-closed | `reality_canonical_writer.py:300` `prepare_promotion`, `:400` `promote_reality_candidate`, `:46` `HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1` (`OBSERVED`). |
| L4 Windows transport | Contract + tests; not deployed | `hermes_orchestration.py:776` `WINDOWS_HERMES_TRANSPORT_CONTRACT_V1`, `:806` `windows_outbound_poll`, `:864-865` `production_deployed: False` (`OBSERVED`). |
| L5 scheduler/trigger | Absent | `worker/index.js` exports only `fetch`; `worker/wrangler.toml` has no `[triggers]`/cron/queue (`OBSERVED`). |
| L6 canonical read | Contract PASS / live `UNKNOWN` | `REALITY_AUTO_SYNC_CURRENT_STATE_AUDIT_REPORT.md:42-56` (`STATED`, based on observed read tools). |
| Provenance | Implemented | `ASSET_PROVENANCE_CONTRACT_V0.2.md:23` canonical origin `wechat:conversation:42`; `provenance_contract.py` (`OBSERVED`). |

---

## 5. Smallest integration boundary

**The integration boundary is the existing L2 capture envelope.** The daily
pipeline adds *no* new cloud interface, writer, table or store. It is:

```
local daily producer  -->  capture envelope (L2 contract, already defined)
                      -->  normalize_reality_capture(envelope)   [L2, read-only]
                      -->  promote_reality_candidate(normalized)  [L3, Human Gate]
```

Design consequences:

- **Reuse, not redesign.** The daily pipeline is a *producer side* concern plus a
  thin local-to-L2 adapter; the cloud side already exists and is tested.
- **No new schema.** The envelope fields and aliases are those of
  `REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1.md` Section 2.
- **No new store.** The candidate is not persisted at L2; only a gated L3
  promotion writes to the existing `ASSET_DB: assets / asset_versions`.
- **One boundary to test.** A daily bundle is an ordered list of L2 envelopes;
  ingestion is `for snapshot in bundle.snapshots: normalize_reality_capture(...)`.

The **only genuinely new artifact** required is the *local* daily snapshot
producer/adapter and its bundle envelope (Section 6/7). It is deferred to the
minimum next step (Section 16) and is bounded by a Human Gate (Section 13).

---

## 6. Daily snapshot flow (local runtime -> Reality ingestion)

End-to-end, once per day:

1. **Trigger (local).** The local scheduler on the Windows host starts the daily
   job (Section 8). The cloud is never the timer; it remains passive.
2. **Acquire (local, L1).** `wechat-reader-v1` produces metadata-only output for
   the day window (`chat_id`, `message_id`, `sender_id`, `create_time_iso`,
   `content_available`, `source_db`) plus the observed content when available.
3. **Adapt (local).** The local producer maps each reader item to an L2 capture
   envelope via the existing shape (`build_capture_envelope` semantics) and
   assembles the **daily bundle** (Section 7). It attests per-field epistemic
   status (Section 7.3).
4. **Spool (local).** The bundle is written to a bounded, append-only **local
   outbound spool** (not a cloud store). This is the only durable queue at rest,
   and it is local; the cloud creates no store.
5. **Transport (outbound only, L4).** The bundle is delivered over the existing
   `windows_outbound_poll` transport (`hermes_orchestration.py:806`) through the
   relay endpoints `/hermes/transport/v1/...` — **specified but not deployed**
   (`hermes_orchestration.py:781-792, 864-865`). The cloud never dials Windows.
6. **Normalize (cloud, L2).** For each snapshot envelope, call
   `normalize_reality_capture`. Output is one read-only `REALITY` candidate with
   explicit status `VERIFIED` / `INCOMPLETE` / `HASH_MISMATCH` and a recomputed
   content hash. `write_performed` is always `false`.
7. **Promote (cloud, L3, Human Gate).** Only when a candidate is `VERIFIED` and
   `promotion_eligible` **and** `HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1` is
   authorized **and** an existing write surface is injected, `prepare_promotion`
   / `promote_reality_candidate` routes it to an existing canonical target. This
   step is out of scope for this design and remains `BLOCKED` without the gate.

```
local:   [daily timer] -> wechat-reader-v1 -> adapter -> local spool
                                                              |
cloud:                          (outbound poll relay, Human Gate)
                                                              v
        normalize_reality_capture -> candidate (read-only)
                                                              v
        promote_reality_candidate (Human Gate + write surface) -> ASSET_DB
```

---

## 7. Snapshot envelope

### 7.1 Two-level envelope

The pipeline has a **bundle** (one per day per chat) containing **snapshot
envelopes** (one per L2 capture).

**Daily bundle (new, producer-side, local):**

```jsonc
{
  "bundle_contract": "PERSONAL_AI_REALITY_DAILY_WECHAT_SNAPSHOT_V0.1",
  "bundle_id": "wechat-daily:<chat_id>:<window_start>:<window_end>",
  "producer": {
    "runtime": "windows_local",
    "executor": "hermes|other-local-executor",
    "reader_capability": "wechat-reader-v1",
    "reader_version": "<declared>"
  },
  "window": {"start": "<iso8601>", "end": "<iso8601>", "timezone": "<tz>"},
  "watermark": {
    "previous_source_version": "<iso8601|null>",
    "this_source_version": "<iso8601>"
  },
  "snapshots": [ /* one L2 capture envelope per message (Section 7.2) */ ]
}
```

**Snapshot envelope** is exactly the existing L2 envelope, so the cloud boundary
is unchanged (`REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1.md:58-79`). Required
fields: `source_identity`, `source_location`, `source_version`,
`content_version`, `captured_at`, `content`, `verification_evidence`.

### 7.2 Reader output -> L2 envelope mapping

| `wechat-reader-v1` output | L2 envelope field | Rule |
| --- | --- | --- |
| `chat_id` | `source_identity` | `wechat:conversation:<chat_id>` (canonical origin form; `ASSET_PROVENANCE_CONTRACT_V0.2.md:23`) |
| `source_db` + `chat_id` | `source_location` | opaque `wechat://local-snapshot/<source_db>/<chat_id>`; local paths are redacted on read |
| reader DB revision / watermark | `source_version` | observed source revision |
| `message_id` / content revision | `content_version` | revision of the captured content |
| `create_time_iso` | `captured_at` | ISO-8601 UTC |
| `content_available=true` + body | `content` | opaque payload passed through; hashed, never parsed/decrypted by cloud |
| reader run metadata | `verification_evidence` | explicit evidence object: capability, version, `source_db`, `sender_id`, `message_id`, window, `content_available`, observed-at |
| `message_id` | `message_id` / `candidate_id` | stable fallback `candidate_id` |

`content_available=false` is a **first-class** case: the snapshot carries no
`content`, so L2 reports `INCOMPLETE` and it is never verified (Section 12).

### 7.3 Epistemic attestation

Cloud cannot observe the local store, so the producer must supply the per-field
epistemic block (`OBSERVED` / `STATED` / `INFERRED` / `UNKNOWN`). A field present
without an explicit status defaults to `STATED` (never `OBSERVED`), and
`promotion_eligible` is `true` only when the candidate is `VERIFIED` **and** every
required field is explicitly `OBSERVED`
(`REALITY_CAPTURE_NORMALIZATION_CONTRACT_V0.1.md:85-113`). The producer must not
upgrade an inference to an observation.

---

## 8. Scheduling

- **Ownership: local.** `OBSERVED` the Worker exports only `fetch` and
  `wrangler.toml` declares no `[triggers]`/cron/queue; therefore the cloud cannot
  and must not own the timer in V0.1. Adding a cloud scheduler would be a deploy
  + binding change and is explicitly out of scope.
- **Cadence.** Once per day at a fixed local time (default: a low-activity hour).
  A configurable **window** `[start, end)` defines the messages included.
- **Direction.** Pull/outbound only: the local job polls/delivers; the cloud never
  initiates a connection to the device (`hermes_orchestration.py:806`).
- **Watermark.** The bundle carries `watermark.previous_source_version` and
  `watermark.this_source_version` so successive days are gap-free and a
  re-run is detectable. The next window starts at the previous watermark.
- **Overlap for at-least-once.** Each daily window re-reads a small overlap
  (e.g. the tail of the previous window); duplicates are suppressed by
  idempotency at L2/L3 (Section 10), never by cloud-side scheduling.
- **Missed run / catch-up.** If a day is skipped, the local job runs the missed
  windows on next start (bounded catch-up, oldest first). The cloud is stateless
  with respect to scheduling; it just normalizes whatever arrives.
- **Jitter.** Local jitter avoids thundering-herd on the relay.

`UNKNOWN`: any concrete local scheduler product/version, local spool path, or
Windows Task Scheduler configuration. Not guessed here.

---

## 9. Provenance

Provenance reuses `PERSONAL_AI_ASSET_PROVENANCE_V0.2` end to end; no new
provenance vocabulary is introduced.

- `source_identity` = `wechat:conversation:<chat_id>` (canonical WeChat origin,
  `ASSET_PROVENANCE_CONTRACT_V0.2.md:23`).
- `source_location` = opaque `wechat://local-snapshot/...` URI.
- `source_version` / `content_version` come from the daily watermark and message
  revision, so each promoted version is traceable to a day window.
- `verification_evidence` is **explicit** (reader capability/version/source_db/
  sender/window); a lone hash flag is never accepted as evidence
  (`ASSET_PROVENANCE_CONTRACT_V0.2.md:64-65`).
- `content_hash` is recomputed by the cloud over the opaque content; a
  caller-declared hash that disagrees yields `HASH_MISMATCH`.
- Promotion fields (`canonical_version`, `promotion_decision`, `promotion_event`,
  `promoted_at`) are intentionally unset at capture and filled only by the L3
  gate (`reality_canonical_writer.py:252-297`).
- Supersession lineage is preserved via the existing provenance V0.2 model; no
  history is rewritten.

`INFERRED`: `chat_id` -> conversation identity mapping is the intended canonical
form; the reader output field names are `OBSERVED`, the mapping choice is a
design decision.

---

## 10. Idempotency

Idempotency is **reuse-first** and layered:

| Level | Key | Behavior |
| --- | --- | --- |
| Message/snapshot | `target:candidate_id:content_hash` (existing L3 scheme, `reality_canonical_writer.py:345`) | Same content -> same key; L3 returns `IDEMPOTENT` and writes no new version. |
| Candidate identity | `candidate_id` falls back `message_id` then `capture_id` (`reality_capture.py:265-270`) | Stable identity even when the producer omits `candidate_id`. |
| Content integrity | cloud-recomputed `content_hash` | A changed body under the same id is a different hash (updates as a new version); a tampered declared hash is `HASH_MISMATCH`. |
| Existing canonical pointer | `existing_asset.content_hash` equal to candidate hash | L3 reports `IDEMPOTENT` / replay, no new version (`reality_canonical_writer.py:349-358`). |
| Daily bundle | deterministic `bundle_id` + bundle fingerprint | Re-running the same window is detectable; the same envelopes converge to the same L3 idempotency keys. |

Consequences: daily re-runs, retries after transport failure, and overlapped
windows are all safe. Duplicate suppression happens in the existing writer, not
in the scheduler. **No dedupe table and no second store are created.**

---

## 11. Retention

- **Local outbound spool (local-only).** Bounded retention (design default:
  delete after acknowledged delivery, with a short safety window). This is a
  local runtime concern and is **not** a cloud store. No WeChat message body is
  retained by the cloud beyond what a gated promotion stores.
- **Cloud candidates (L2).** Not persisted: `normalize_reality_capture` is pure
  and read-only (`write_performed: false`). Nothing accumulates unless promoted.
- **Canonical (L3).** Append-only and versioned; promotion never deletes
  history. Supersession uses existing provenance V0.2 lineage
  (`ASSET_PROVENANCE_CONTRACT_V0.2.md:85-94`). **No canonical row is deleted.**
- **Provenance events.** Append-only capture/verification/promotion evidence
  (`ASSET_PROVENANCE_CONTRACT_V0.2.md:85`), keyed by asset/version.
- **Content minimisation.** Only `content_available=true` payloads enter the
  envelope; unavailable content is represented as absence, never fabricated.

`UNKNOWN`: exact retention durations are a policy parameter to be fixed at the
Human Gate; this design defines the mechanism, not the final duration.

---

## 12. Failure handling (fail-closed)

| Failure | Detected by | Result | Recovery |
| --- | --- | --- | --- |
| Local acquisition fails | local producer | no bundle emitted; cloud sees nothing | local retry/backoff; human alert |
| Reader schema incompatible | `wechatread_real_source_probe_v0_1` -> `INCOMPATIBLE` (`hello.py:25711`) | do not emit | fix/declare reader schema, re-probe |
| `content_available=false` | L2 missing `content` | `INCOMPLETE`, never verified | re-capture when available |
| Missing explicit evidence | L2 `verification_evidence` absent | `INCOMPLETE` (`reality_capture.py:305-312`) | add explicit evidence |
| Invalid epistemic token | L2 `invalid` | `INCOMPLETE` (`reality_capture.py:557-559`) | correct the attestation |
| Declared hash disagrees | L2 hash check | `HASH_MISMATCH`, never verified (`reality_capture.py:320-325`) | re-capture / quarantine |
| Transport fails mid-batch | relay/transport | local spool retains; at-least-once + idempotency | retry same envelope |
| Promotion not authorized | L3 | `BLOCKED` + gate id (`reality_canonical_writer.py:466-472`) | obtain Human Gate |
| No write surface/credential | L3 | `BLOCKED` + exact dependency (`reality_canonical_writer.py:474-482`) | bind existing write surface at gate |
| Partial day | bundle/window report | per-snapshot statuses; no silent success | catch-up run |

Rules: an `INCOMPLETE` or `HASH_MISMATCH` candidate is **never** verified and
never promoted; a `BLOCKED` promotion writes nothing. Every outcome is explicit
and auditable. No failure is allowed to fabricate evidence or a success status.

---

## 13. Human Gate required for real daily ingestion

Real daily ingestion **cannot** begin without explicit human authorization. The
required gates, in dependency order:

| # | Gate | Scope | Why it is human | Evidence of current state |
| --- | --- | --- | --- | --- |
| HG-1 | Local WeChat daily acquisition consent | Read the user's real WeChat store once per day on the local device | Privacy: reading personal messages requires the device owner's consent; cloud cannot and must not reach the device | `hello.py:21184-21197` `requires_local_device=True`, `requires_human_gate=True` (`OBSERVED`) |
| HG-2 | Hermes relay deployment | Deploy relay endpoints + bind `HERMES_TRANSPORT_TOKEN` / `HERMES_TRANSPORT_URL` (names only) | Production endpoints + secrets; `hermes.transport` scope | `hermes_orchestration.py:862-887`, `:1576-1602` `production_deployed: False` (`OBSERVED`) |
| HG-3 | REALITY canonical promotion | Enable promotion of verified daily candidates into existing canonical targets | Writes personal canonical state | `reality_canonical_writer.py:46` `HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1` (`OBSERVED`) |

Until all three are granted, the pipeline is `BLOCKED_PENDING_HUMAN_GATE`: the
design and dry-run validation exist, but **no real daily ingestion occurs**.
This design itself grants no gate and changes no credential/binding/permission.

---

## 14. What is deliberately not changed

- No production write and no Canonical write (L2 is read-only; L3 is dry-run/gated).
- No deploy; no Worker change; no `[triggers]`/cron/queue.
- No credential, secret, permission, binding or schema change.
- No `.github/workflows/` change.
- No second state store (reuses `ASSET_DB: assets / asset_versions` and the
  existing `EventSyncRegistry`).
- No assumption about WeChat storage layout, DB format, decryption or keys
  (`UNKNOWN`, supplied opaquely by the local caller).
- No repository path other than this report is modified; the reference adapter
  used for validation lives out-of-tree (Appendix B).

---

## 15. Acceptance mapping

| Acceptance criterion | Evidence |
| --- | --- |
| Report distinguishes OBSERVED/STATED/INFERRED/UNKNOWN | Section 2 + inline tags throughout; `UNKNOWN` items called out (Sections 8, 11, 14) |
| No production changes or Canonical writes | Sections 1, 14; L2 `write_performed: false`; L3 `prepare_promotion` only (Appendix B) |
| Architecture aligns with Reality as shared source layer, not agent-specific memory | Section 3 (executor-agnostic; `REALITY` source/provenance, never a target) |
| Defines minimum next implementation step | Section 16 |
| Explicitly identifies any Human Gate required for real daily ingestion | Section 13 (HG-1, HG-2, HG-3) |

---

## 16. Status and minimum next implementation step

**Status.** `DESIGNED`; daily ingestion `BLOCKED_PENDING_HUMAN_GATE`.

**Minimum next implementation step (cloud-only, LOW risk, no gate, reversible):**
materialize the **daily snapshot adapter/validator** in the cloud package:

- `src/personal_ai_execution/reality_daily_snapshot.py` — pure functions that
  (a) map `wechat-reader-v1` output to `build_capture_envelope`, (b) assemble and
  fingerprint the daily bundle, and (c) dry-run the bundle through the existing
  `normalize_reality_capture` and `prepare_promotion` **with no write**;
- `tests/test_reality_daily_snapshot.py` — focused tests for the complete /
  `content_available=false` / hash-mismatch / idempotent-bundle / REALITY-never-
  target cases.

This advances the pipeline along the declared dependency
`reality_ingestion_contract` (`hello.py:21340-21346`) while touching neither the
local device nor any Human Gate. It is the same out-of-tree adapter validated in
Appendix B, materialized under a separate task scope.

**Deferred (Human Gate / local device, explicitly out of this step):** the local
`wechat-reader-v1` daily producer (HG-1), the relay deploy + secret bindings
(HG-2), and REALITY canonical promotion (HG-3).

---

## Appendix A: Normative interface shapes

**A.1 Bundle contract id.** `PERSONAL_AI_REALITY_DAILY_WECHAT_SNAPSHOT_V0.1`.

**A.2 Bundle id.**
`bundle_id = "wechat-daily:" + chat_id + ":" + window_start + ":" + window_end`.

**A.3 Snapshot envelope.** The existing L2 envelope (required fields
`source_identity`, `source_location`, `source_version`, `content_version`,
`captured_at`, `content`, `verification_evidence`), produced by the local adapter
using `build_capture_envelope` semantics.

**A.4 Bundle ingestion (cloud, no write).** For each snapshot:
`normalize_reality_capture(snapshot)`; aggregate statuses and verify
`write_performed is False` for every result. Promotion, if ever authorized,
delegates to `prepare_promotion` / `promote_reality_candidate`.

**A.5 Idempotency.** Message key `target:candidate_id:content_hash`; daily key
`bundle_id` + deterministic bundle fingerprint (canonical JSON SHA-256).

## Appendix B: Out-of-tree validation evidence

The Appendix A adapter was executed **outside the repository** (in
`/tmp/opencode/`) against the *existing materialized* `reality_capture` and
`reality_canonical_writer` modules. No repository path other than this report was
modified by this task.

```
$ python -m pytest -q test_reality_daily_snapshot_ref.py
5 passed in 0.01s
```

Worked example (daily bundle -> L2 -> dry-run L3):

```
BUNDLE_ID wechat-daily:conv-42:2026-10-01T00:00:00+00:00:2026-10-02T00:00:00+00:00
FINGERPRINT sha256:b6ae71cd1d5be3092217bee2f6ed90e5b6c734bc45f92e2ea2997adf90a5e347
STATUS ['VERIFIED'] promotion_eligible 1 write_performed False
PLAN PREPARED gate HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1 write False second_store False
INCOMPLETE ['INCOMPLETE'] missing ['content']
```

Covered cases: complete bundle -> `VERIFIED` + `promotion_eligible` with no write;
`content_available=false` -> `INCOMPLETE` (missing `content`), never verified;
`prepare_promotion` returns `PREPARED` with `requires_human_gate=true`,
`production_write_performed=false`, `second_state_store_created=false`; target
`REALITY` -> `QUARANTINED` (REALITY is never a target); bundle fingerprint is
deterministic.

Full repository regression at the end of this task (no production path changed by
this artifact): see the task's `python -m pytest -q` run recorded in the
execution result.

## Verdict: DESIGNED (daily ingestion BLOCKED_PENDING_HUMAN_GATE)

A daily WeChat snapshot pipeline is defined on top of the **existing** Reality
layers with no production change: WeChatRead is a local acquisition capability
only; a per-day bundle of existing L2 capture envelopes flows outbound through
the (undeployed) Hermes transport into `normalize_reality_capture`, and a
verified candidate can only reach the existing canonical writer behind
`HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1`. Scheduling, envelope, provenance,
idempotency, retention and fail-closed handling are specified, and Reality
remains the shared source layer rather than any agent-specific memory.
