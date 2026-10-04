# HERMES_REALITY_DAILY_SYNC_BINDING_V0.1

Read-only architecture / integration-boundary audit that connects the **existing
local Hermes runtime** to the **Reality daily WeChat snapshot pipeline**. It
verifies the existing Hermes orchestration contracts and determines the smallest
binding required for:

```
Hermes scheduler/runtime -> WeChatRead -> Snapshot -> Reality ingestion
```

This artifact is an **audit + binding definition only**. It performs **no
production write, no Reality / Canonical write, no deploy, no credential /
permission / binding / schema change, and creates no second state store**.

- Task id: `cf-73da09b0ce57`
- Project: `cloud-assets-activation`
- Risk level: `LOW`
- Mode: **READ-ONLY AUDIT / BINDING DESIGN**
- Builds on:
  - `REALITY_DAILY_WECHAT_SNAPSHOT_PIPELINE_V0.1.md` (pipeline design)
  - `src/personal_ai_execution/reality_daily_snapshot.py` (L2 daily adapter, exists)
  - `src/personal_ai_execution/reality_capture.py` (L2 normalizer, exists)
  - `src/personal_ai_execution/reality_canonical_writer.py` (L3 promotion, exists)
  - `src/personal_ai_execution/hermes_orchestration.py`
    (`WINDOWS_HERMES_TRANSPORT_CONTRACT_V1`, `HERMES_RESULT_ADAPTER_MINIMAL_PATCH_V1`)
  - `REALITY_AUTO_SYNC_CURRENT_STATE_AUDIT_REPORT.md` (L1-L6 gap model)
- Binding status: `DEFINED`
- End-to-end daily ingestion: `BLOCKED_PENDING_HUMAN_GATE`
- Evidence discipline: **OBSERVED / STATED / INFERRED / UNKNOWN** (Section 2)

---

## 1. Scope, intent and non-goals

**Intent.** Determine, from first-party code in this checkout, whether the
**existing** Hermes runtime can serve as the local producer/scheduler boundary
for the daily WeChat snapshot flow, and define the **smallest binding** that
connects it to the already-materialized Reality ingestion boundary — without
touching a device, a relay, a credential or Canonical state.

**In scope.**

- The exact existing Hermes contracts that are reusable as the local
  runtime/transport boundary.
- A verdict on the words *producer* and *scheduler* for Hermes, with evidence.
- The smallest binding between a Hermes-produced daily bundle and the existing
  cloud-side L2/L3 boundary.
- The explicit local-acquisition vs cloud-consumption separation and the exact
  Human Gates that remain.

**Non-goals / deliberately not done.**

- No local WeChat acquisition implementation, no decryption, no DB/file/endpoint
  access. No real WeChat data is accessed.
- No Hermes relay deployment, no endpoint/secret binding, no permission change.
- No production or Canonical write; no Reality asset is created.
- No new state store, no second registry, no schema/Worker/`.github/workflows/`
  change.
- No scheduler/cron/queue is added anywhere.
- No assumption that any live Windows host, WeChat store, Hermes gateway, relay
  or D1 instance exists (all such claims are `UNKNOWN`, Section 2).

---

## 2. Evidence discipline

Every claim carries one tag:

| Tag | Meaning |
| --- | --- |
| `OBSERVED` | read directly from first-party code / tests in this checkout during this run |
| `STATED` | a first-party document or code comment asserts it, not independently re-verified |
| `INFERRED` | derived from `OBSERVED` facts |
| `UNKNOWN` | no evidence; not guessed |

`OBSERVED` means observed **in the checkout at this task's base commit**, not
observed live in production. A historical PASS or self-declared baseline is never
promoted to live `VERIFIED`.

---

## 3. The chain, link by link (evidence)

| # | Link | Status (this run) | Evidence |
| --- | --- | --- | --- |
| 1 | Local scheduler / trigger | `UNKNOWN` / local-owned | `REALITY_DAILY_WECHAT_SNAPSHOT_PIPELINE_V0.1.md:274-296` (scheduling ownership local); `worker/index.js` exports only `fetch` (`:3503`), `worker/wrangler.toml` has no `[triggers]` (`OBSERVED`) |
| 2 | Hermes local runtime/executor | Contracts + probe exist; live runtime `UNKNOWN` | `hermes_orchestration.py:83` `RUNTIME_EXECUTABLES`, `:245` `probe_hermes_runtime`, `:314` `runtime_present` (`OBSERVED`) |
| 3 | WeChatRead local acquisition | Local-only, no bridge in repo | `hello.py:25426` `WECHAT_READER_CAPABILITY_ID = "wechat-reader-v1"`; `:25447-25454` schema fields; `:25550` metadata-only probe; `hello.py:21184-21209` `wechat_snapshot_to_reality` `BLOCKED`, `requires_local_device=True` (`OBSERVED`) |
| 4 | Daily snapshot producer/bundle | Implemented (cloud package, pure) | `reality_daily_snapshot.py:47` `BUNDLE_CONTRACT`; `:296` `assemble_daily_bundle`; `:343` `bundle_fingerprint`; `:350` `bundle_idempotency_key`; `:384` `validate_bundle` (`OBSERVED`) |
| 5 | Transport (local -> cloud, outbound only) | Contract + tests; relay not deployed | `hermes_orchestration.py:776` `TRANSPORT_CONTRACT_VERSION`, `:806` `TRANSPORT_DIRECTION = "windows_outbound_poll"`, `:781-792` endpoints, `:862-887` `MINIMAL_RELAY_GAP` `production_deployed: False` (`OBSERVED`) |
| 6 | Cloud Reality normalization (L2) | Implemented, read-only | `reality_capture.py:249` `normalize_reality_capture`, `:418` `build_capture_envelope`, `:66` `REQUIRED_CAPTURE_FIELDS` (`OBSERVED`) |
| 7 | Cloud Reality promotion (L3) | Implemented, gated, no self-write | `reality_canonical_writer.py:46` `HUMAN_GATE`, `:300` `prepare_promotion`, `:400` `promote_reality_candidate` (`OBSERVED`) |

`STATED`: `REALITY_AUTO_SYNC_CURRENT_STATE_AUDIT_REPORT.md:91-96` says the
Windows transport currently carries **Hermes orchestration task results**, not
WeChat records. This is the central constraint for the binding (Section 5).

---

## 4. Verdict: can Hermes act as the local producer / scheduler boundary?

The answer is **split**, and the two words must not be conflated.

### 4.1 Producer / executor boundary — **YES** (STATED + INFERRED)

- `OBSERVED` the daily bundle producer already defaults its executor to Hermes:
  `reality_daily_snapshot.py:303` `assemble_daily_bundle(..., executor: str =
  "hermes", ...)` and `:328-333` records `producer.runtime = "windows_local"`,
  `producer.executor`, `producer.reader_capability = "wechat-reader-v1"`.
- `OBSERVED` the Hermes runtime is the positively-identified local orchestrator
  (`hermes_orchestration.py:83,245,314`) and the Windows worker is the
  **outbound** side of the transport (`:806`).
- `OBSERVED` the module already names the exact inputs a Windows local agent
  needs and states `cloud_deploys_second_hermes: False`
  (`hermes_orchestration.py:1430-1477`).
- `INFERRED`: Hermes is a viable **local producer/executor**: it can run the
  daily job, invoke `wechat-reader-v1`, assemble the bundle
  (`assemble_daily_bundle`) and drive the outbound transport. No cloud-side
  second Hermes is created.

### 4.2 Scheduler boundary — **NOT CONFIRMED / UNKNOWN**

- `OBSERVED` there is **no scheduling construct** in the Hermes contracts: no
  cron/timer/queue symbol exists; the only time-related constant is the
  transport lease lease/poll (`hermes_orchestration.py:808-810`).
- `OBSERVED` the cloud cannot own the timer: `worker/index.js` exposes only
  `fetch` and `worker/wrangler.toml` declares no `[triggers]`.
- `STATED` the pipeline design assigns scheduling to the **local** host
  (`REALITY_DAILY_WECHAT_SNAPSHOT_PIPELINE_V0.1.md:274-296`) and marks the
  concrete local scheduler product/config `UNKNOWN`.

**Verdict.** Hermes can be the **local runtime/producer + outbound transport
driver**. Whether Hermes itself is the **timer** is `UNKNOWN`: nothing in the
repo shows Hermes owning a schedule, and the design deliberately keeps scheduling
local and unspecified. The binding defined below therefore treats the timer as an
**external local trigger** that starts the Hermes-hosted daily job; it does not
require, claim or deploy any Hermes scheduler.

### 4.3 Binding constraint — the transport is results-shaped

`OBSERVED` the existing transport envelope is a **Hermes task result**:
`TRANSPORT_RESULT_REQUIRED_FIELDS` (`hermes_orchestration.py:847-855`) and
`build_hermes_result_envelope` (`:1775`) carry `task_state`, `status`,
`executor_identity`, `tests`, `artifacts`, `evidence_hash` — **not** a capture
envelope. Cloud ingestion today accepts it into the **existing** Task Registry
via `ingest_hermes_result` (`:1887`), which rejects unregistered tasks and never
creates a second store.

`INFERRED`: a daily snapshot bundle therefore cannot ride the transport verbatim;
it needs a **thin, pure binding** that (a) attaches the bundle to the existing
result envelope as **advisory artifact evidence**, and (b) extracts + validates
it on the cloud side before handing it to the existing L2 boundary. This is the
smallest binding, and it is cloud-only (Section 7).

---

## 5. Local acquisition vs cloud consumption (explicit separation)

This distinction is the reason the binding must stay thin.

| Concern | Where it lives | What crosses the boundary |
| --- | --- | --- |
| WeChat acquisition (`wechat-reader-v1`) | **Local device only** | Nothing; the reader never leaves the device. The cloud cannot read a WeChat DB (`hello.py:25406-25421`, `OBSERVED`) |
| Hermes runtime / daily job / timer | **Local** | Outbound transport calls only; the cloud never dials the device (`hermes_orchestration.py:806`, `OBSERVED`) |
| Snapshot bundle (L2 envelopes) | Assembled locally (pure `assemble_daily_bundle`) | The bundle as advisory artifact evidence |
| Reality normalization (L2) | **Cloud** | Read-only candidate; `write_performed` always `False` (`reality_capture.py:413`, `OBSERVED`) |
| Reality promotion (L3) | **Cloud, Human Gate** | Existing canonical writer only; REALITY is source, never a target (`reality_canonical_writer.py:15-21,52`, `OBSERVED`) |

**Reality remains the shared source layer, never an agent-specific memory.** The
pipeline is executor-agnostic: Hermes is one possible local executor; the cloud
consumes only the L2 envelope/bundle contract. No per-agent store is created.

`UNKNOWN`: the concrete WeChat store layout, DB format, decryption/key handling
and the local timer product are not evidenced and are not assumed.

---

## 6. Smallest binding — chain contracts

The binding adds **no** new cloud interface, writer, table or store. It connects
two already-existing contracts:

```
[local]  external local trigger
            -> Hermes runtime (producer/executor)
            -> wechat-reader-v1            (acquisition, local only)
            -> assemble_daily_bundle(...)  (existing: reality_daily_snapshot.py:296)
            -> attach bundle to Hermes result envelope
               (existing: build_hermes_result_envelope, :1775)
            -> outbound transport (existing contract, UNDEPLOYED relay)
[cloud]     -> extract bundle from result envelope
            -> validate_bundle(...)        (existing: :384)
            -> dry_run_bundle(...)         (existing: :441)
            -> normalize_reality_capture   (existing: reality_capture.py:249)
            -> prepare_promotion (Human Gate; existing: reality_canonical_writer.py:300)
```

Design consequences:

- **Reuse, not redesign.** `reality_capture.py`, `reality_daily_snapshot.py`,
  `reality_canonical_writer.py` and `hermes_orchestration.py` are all reused
  unchanged.
- **No new schema.** The bundle is
  `PERSONAL_AI_REALITY_DAILY_WECHAT_SNAPSHOT_V0.1`; each snapshot is the existing
  L2 envelope.
- **No new store.** The result envelope lives in the existing Task Registry
  only if a caller already ingests it; the dry-run binding persists nothing.
- **One new pure mapping concern.** Bundle <-> Hermes result envelope.

---

## 7. Binding interface (proposed, dry-run, cloud-only)

Contract id: **`HERMES_REALITY_DAILY_SYNC_BINDING_V0.1`**.

Proposed pure functions (no network, no write, no credential):

| Function | Behavior | Reuses |
| --- | --- | --- |
| `attach_bundle_to_result_envelope(bundle, *, task_id, worker_id, lease_id, executor_identity="hermes-native-hand")` | Validate the bundle, then return a Hermes result envelope carrying the bundle in `artifacts` as `{"kind": "reality_daily_bundle", "bundle_contract", "bundle_fingerprint", "bundle"}` and stamp the evidence hash | `validate_bundle` (`reality_daily_snapshot.py:384`), `build_hermes_result_envelope` (`hermes_orchestration.py:1775`), `compute_evidence_hash` (`:931`) |
| `extract_bundle_from_result_envelope(envelope)` | Fail-closed extraction: require a terminal task state, locate the `reality_daily_bundle` artifact, re-validate the bundle; return `(bundle, errors)` with no fabrication | `TERMINAL_TASK_STATES` (`:96`), `validate_bundle` |
| `dry_run_bundle_from_transport(envelope, *, target_asset_type=None)` | Run the extracted bundle through the existing L2 dry-run and return the report; every output states `write_performed=False`, `second_state_store_created=False` | `dry_run_bundle` (`reality_daily_snapshot.py:441`) |

Properties fixed by the binding:

- **Fail-closed.** A missing/non-terminal/malformed result, or a bundle that
  fails `validate_bundle`, yields an explicit error — never a verified candidate.
- **Read-only.** No canonical write, no production write, no second store; the
  binding never calls `promote_reality_candidate` with a live write surface.
- **Idempotent.** Bundle fingerprint (<code>sha256:</code> over canonical JSON,
  `reality_daily_snapshot.py:343`) and envelope `evidence_hash`
  (`hermes_orchestration.py:931`) make re-delivery converge.
- **Epistemic honesty preserved.** Fields the binding derives remain `INFERRED`
  by default (`reality_daily_snapshot.py:193-293`); only an explicit producer
  `OBSERVED` attestation can become promotion-eligible, and the cloud never
  upgrades a tag.

`INFERRED`: placing the bundle in `artifacts` is the minimal fit because
`artifacts` is already `list[Any]` advisory evidence
(`hermes_orchestration.py:1784,1843`) and does not alter
`TRANSPORT_RESULT_REQUIRED_FIELDS` or any schema.

---

## 8. Idempotency, provenance and failure handling (reused)

| Concern | Key / behavior | Source |
| --- | --- | --- |
| Snapshot identity | `target:candidate_id:content_hash` | `reality_canonical_writer.py:345`; `reality_daily_snapshot.py:360` |
| Daily bundle | `bundle_id` + deterministic fingerprint | `reality_daily_snapshot.py:343,350` |
| Transport redelivery | `hermes-result:<task_id>:<evidence_hash>` and Task Registry dedupe | `hermes_orchestration.py:926,1887` |
| Provenance | `PERSONAL_AI_ASSET_PROVENANCE_V0.2` end to end; `source_identity = wechat:conversation:<chat_id>` | `provenance_contract.py:182,300`; `ASSET_PROVENANCE_CONTRACT_V0.2.md:23` |
| Failures | `INCOMPLETE` / `HASH_MISMATCH` never verified; unresolvable target never promoted | `reality_capture.py:305-339`; `reality_canonical_writer.py:400` |

No dedupe table and no second store are introduced; all suppression happens in
the existing writer/registry.

---

## 9. Human Gates (only the ones actually required)

The binding itself is a pure cloud-side mapping and requires **no new gate**. The
three gates already declared by the underlying layers remain, in dependency
order:

| # | Gate | Why human | Evidence of current state |
| --- | --- | --- | --- |
| HG-1 | Local WeChat daily acquisition consent (read the user's real store once per day on the device) | Privacy; the cloud cannot and must not reach the device | `hello.py:21184-21209` `requires_local_device=True`, `requires_human_gate=True` (`OBSERVED`) |
| HG-2 | Hermes relay deployment + bind `HERMES_TRANSPORT_TOKEN` / `HERMES_TRANSPORT_URL` (names only) | Production endpoints + secrets; `hermes.transport` scope | `hermes_orchestration.py:862-887`, `:1576-1602` `production_deployed: False` (`OBSERVED`) |
| HG-3 | Reality canonical promotion of verified candidates | Writes personal canonical state | `reality_canonical_writer.py:46` `HUMAN_GATE_REALITY_CANONICAL_WRITE_V0.1` (`OBSERVED`) |

No gate is invented for the binding itself, and **no gate is granted here**. Until
HG-1..HG-3 are authorized the end-to-end daily sync is
`BLOCKED_PENDING_HUMAN_GATE`; only dry-run validation over synthetic/absent
inputs is possible.

---

## 10. What is deliberately not changed

- No production write and no Canonical/Reality write.
- No deploy; no relay; no Worker change; no `[triggers]`/cron/queue anywhere.
- No credential, secret, token, permission, binding or schema change.
- No `.github/workflows/` change.
- No second state store (reuses the existing Task Registry and
  `ASSET_DB:assets/asset_versions`).
- No real WeChat data is accessed, and no WeChat storage layout is assumed.
- No repository path other than this report is modified.

---

## 11. Acceptance mapping

| Acceptance criterion | Evidence |
| --- | --- |
| No production changes or Canonical writes | Sections 1, 7, 10; `dry_run_bundle` `write_performed=False` (`reality_daily_snapshot.py:542-545`) |
| No second state store | Sections 6, 7, 10; existing Task Registry / `ASSET_DB` reused; `second_state_store_created=False` |
| Confirms whether Hermes can act as local producer/scheduler boundary | Section 4: producer/executor **YES**; scheduler **NOT CONFIRMED/UNKNOWN** |
| Defines smallest next implementation step | Section 12 |
| Maintains local WeChat acquisition vs cloud Reality consumption distinction | Sections 3, 5 |
| OBSERVED/STATED/INFERRED/UNKNOWN reported separately | Section 2 + inline tags throughout |
| Human Gates only where actually required | Section 9 (HG-1..HG-3, no new gate) |

---

## 12. Status and smallest next implementation step

**Status.** Binding `DEFINED`; end-to-end daily sync `BLOCKED_PENDING_HUMAN_GATE`.

**Smallest next implementation step (cloud-only, LOW risk, no gate,
reversible):** materialize the **binding module** described in Section 7:

- `src/personal_ai_execution/reality_hermes_daily_sync.py` — pure functions that
  attach a validated daily bundle to the existing Hermes result envelope, extract
  and re-validate it, and dry-run it through the existing
  `validate_bundle` / `dry_run_bundle` **with no write**;
- `tests/test_reality_hermes_daily_sync.py` — focused tests for the
  complete / non-terminal / malformed-artifact / hash-mismatch / idempotent
  enveloped bundle / no-second-store cases.

This advances the declared dependency `reality_ingestion_contract`
(`hello.py:21340-21346`) by closing the last in-repo seam between the **existing**
Hermes transport contract and the **existing** L2 snapshot adapter, while touching
neither the local device, the relay, any secret, nor any Human Gate.

**Deferred (Human Gate / local device, explicitly out of this step):** the local
`wechat-reader-v1` daily producer (HG-1), the relay deploy + secret bindings
(HG-2), and Reality canonical promotion (HG-3).

---

## Appendix A: Evidence index

- `src/personal_ai_execution/reality_daily_snapshot.py:47,296,303,343,350,360,384,441,542`
- `src/personal_ai_execution/reality_capture.py:66,249,413,418`
- `src/personal_ai_execution/reality_canonical_writer.py:15-21,46,52,300,345,400`
- `src/personal_ai_execution/provenance_contract.py:182,300`
- `src/personal_ai_execution/hermes_orchestration.py:83,96,245,314,776,781-792,806,847-855,862-887,931,926,1430-1477,1480,1528-1533,1576-1602,1775,1843,1887`
- `hello.py:21184-21209,21340-21362,25426,25447-25454,25550`
- `REALITY_DAILY_WECHAT_SNAPSHOT_PIPELINE_V0.1.md:13-25,76-125,274-296,387-400`
- `REALITY_AUTO_SYNC_CURRENT_STATE_AUDIT_REPORT.md:80-99,159-171`
- `worker/index.js:3503` (exports `fetch` only); `worker/wrangler.toml` (no `[triggers]`)
- `tests/test_reality_daily_snapshot.py` (existing dry-run coverage);
  `tests/test_hermes_golden_poc.py` (existing transport coverage)

## Verdict: BINDING DEFINED (end-to-end sync BLOCKED_PENDING_HUMAN_GATE)

The existing Hermes runtime can act as the **local producer/executor and outbound
transport driver** of the daily WeChat snapshot flow; it cannot be confirmed as
the **scheduler**, which stays a local, externally-triggered, product-agnostic
concern. The smallest binding is a **pure, cloud-only, no-gate** mapping between
the already-materialized daily bundle (`reality_daily_snapshot.py`) and the
already-defined Hermes result transport envelope (`hermes_orchestration.py`),
consumed by the existing read-only L2 normalizer. Local WeChat acquisition and
cloud Reality consumption remain strictly separated, no production or Canonical
state is written, no second store is created, and the only remaining blockers are
the pre-existing Human Gates HG-1, HG-2 and HG-3.
