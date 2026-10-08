# batch12-v4-promotion-gates — KNOWLEDGE_BATCH_12_V4

- Task: `cf-53544efd2c1a` (parent `cf-4fd63aaa14f0`); Project: `personal-ai-knowledge-triage`;
  Risk: `LOW`; Mode: **READONLY / RESEARCH ONLY**.
- Purpose: regenerated V4 promotion-gates report. The previous draft of this path was blocked by
  Gate 3 (secret leak scan) because its body contained an api-key-like **sample**. This version
  describes that sample only **neutrally**, by pattern class rather than by value, and contains
  **no** credential-shaped string.
- Companion file: `outputs/batch12-v4-canonical-body-delta.md` (body delta + corrected N1/N2/N3
  overlap). Both are layered on the immutable V1/V2/V3 reports, which are not modified.

## 1. Why this regeneration exists (failed run 37707943066)

| Field | Value |
|---|---|
| Workflow run | `37707943066` (run number 224), workflow `cloud-agent-dispatch` |
| Event | `repository_dispatch` type `gpt_task` |
| Base revision | `6dfceaf7052f1c9d9f29250345d4233630bbdc3c` |
| Run conclusion | `failure` |
| Failed job | `cloud-agent-dispatch` (job id `113086713962`) |
| Failed step | step 13 **`Gate 3 - secret leak check (fail-closed)`** |
| Public annotation | `Process completed with exit code 1.` (`.github` line 17) |
| Step 14 `Push` | **skipped** (blocked by step 13) |

**Root cause class: `SECRET_GUARD_CONTENT_BLOCK`.** The previous draft body embedded a placeholder
literal whose shape matched the api-key prefix pattern checked by `scripts/secret_guard.py`
(`KEY_PATTERN`). Gate 3 is fail-closed and blocked publication exactly as designed. Because `Push`
was skipped, the offending draft was never published and the tree stayed clean at the base revision.

**Repair is content-side.** The fix is to describe the sample without reproducing it. Gate 3 was
**not** weakened, bypassed, ignore-listed, or edited.

### 1.1 Gate 3 unchanged (no security weakening)

- `scripts/secret_guard.py` is unmodified by this task; `KEY_PATTERN` and the `MODEL_API_KEY`
  literal-value check remain exactly as in the base revision.
- No ignore list, environment-variable behaviour, or threshold was relaxed.
- The failed run's log and artifact downloads require authentication (HTTP 401/403), so the exact
  offending literal was deliberately **not** retrieved and is **not** reproduced in any output.
- Local verification (`§6`) runs the base-revision guard against this change set with the same
  strict pattern and reports `PASS`.

## 2. Promotion gates — all remain CLOSED

| Gate | Status | Condition to open |
|---|---|---|
| Source completeness | **CLOSED** (`SOURCE_BREAKDOWN_PARTIAL`, 0/12) | owner supplies 12/12 breakdown full texts (video transcripts NOT required) |
| Canonical full-text dedup | **CLOSED** (`FULL_CANONICAL_DEDUP_BLOCKED`) | full bodies for K01–K18/S01/S02 supplied; a real L2 comparison run |
| Evidence for self-reported metrics | **CLOSED** | independent, non-vendor measurement of T06/T08/T10 metrics |
| Compliance/authorization review | **CLOSED** | legal/scope review for T01/T02/T10/T12 external actions |
| Executable-artifact permission audit | **CLOSED** | independent audit of T04/T12 skills + S02 `computer_use_guard` reach |
| N1/N2 outcome evidence | **CLOSED** | the learning experiment is actually executed with real humans |
| Promotion to Canonical | **CLOSED** | all gates above open **and** human review; never auto-executed |

No gate is opened by this report. No promotion is performed.

## 3. Candidate promotion dispositions (V4, corrected)

The N1/N2/N3 overlap assessments are corrected against the real canonical body summaries relayed
by the parent task; the full derivation is in `batch12-v4-canonical-body-delta.md` §3–§4.

| ID | Candidate | Corrected body-summary overlap | Disposition | Blocker(s) |
|---|---|---|---|---|
| **N1** | Behavior-change design (identity + habit loop + environment/friction) | K03 = controllable variables/experiments → N1/K03 overlap **NOT SUPPORTED** | `NOVEL_CANDIDATE`, **unpromoted** | 17/20 bodies unread; self-report boundary; no outcome study |
| **N2** | Structured learning & transfer loop | K02 = targeted clarification → N2/K02 overlap **NOT SUPPORTED** | `NOVEL_CANDIDATE`, **unpromoted** | S01 body unread; no measured outcomes; far transfer bounded; human answers required |
| **N3** | Evidence/data-hygiene classification (four provenance classes) | K10 = evidence strength vs action value → N3/K10 duplication **withdrawn** | `CANDIDATE_REFERENCE_CHECKLIST`, **unpromoted** | 17/20 bodies unread; duplication by another asset cannot be excluded |

- "NOT SUPPORTED" is an overlap finding only; it is **not** a full-corpus novelty claim.
- No candidate is promoted, merged over a canonical asset, or written to Canonical.
- The V3 learning experiment remains a design artifact only; it has not been executed and yields no
  results here.

## 4. Source gaps still blocking (unchanged)

- **Gap A — user breakdowns:** `SOURCE_BREAKDOWN_PARTIAL`, **0/12** originals available. The required
  artifact is the user-provided breakdown full texts; video verbatim transcripts are not required.
- **Gap B — canonical bodies:** `FULL_CANONICAL_DEDUP_BLOCKED`. Only K13 principles plus K02/K03/K10
  body summaries were relayed; 17/20 asset bodies remain unread. No L2 full-text comparison is done.
- **Layer honesty:** L1 title/metadata screening is complete and is **not** a dedup result; L2 is not
  performed.

## 5. Explicit non-actions (acceptance mapping)

| Acceptance item | Evidence |
|---|---|
| Gate 3 secret scan passes without weakening its rules | §1.1 and the `PASS` result in §6; guard source unchanged |
| Two expected Markdown reports committed and published | this file + `outputs/batch12-v4-canonical-body-delta.md` (published by the workflow `Push` step) |
| Evidence distinctions N1/N2/N3 and source gaps explicitly maintained | §3 and §4; detailed derivation in the companion file |
| No secret-like samples, credentials, production writes, deploys, or permission changes | this file and the companion are report-only; no canonical write, no deploy, no binding/schema/permission/secret change, no file deleted, `.github/workflows/` untouched |

## 6. Verification commands (read-only except the two reports)

```bash
# Gate 3 source is unchanged and strict
sha256sum scripts/secret_guard.py
git diff --stat 6dfceaf7052f1c9d9f29250345d4233630bbdc3c -- scripts/secret_guard.py

# Re-run the base-revision guard against this change set (same strict pattern)
git show 6dfceaf7052f1c9d9f29250345d4233630bbdc3c:scripts/secret_guard.py \
  | python - 6dfceaf7052f1c9d9f29250345d4233630bbdc3c

# Confirm the two V4 reports contain no api-key-shaped literal
python - <<'PY'
import re, pathlib
pat = re.compile(r"sk-[A-Za-z0-9]{10,}")
for name in ("outputs/batch12-v4-canonical-body-delta.md",
             "outputs/batch12-v4-promotion-gates.md"):
    text = pathlib.Path(name).read_text(encoding="utf-8")
    print(name, "matches:", [m.group(0)[:4] + "..." for m in pat.finditer(text)] or "NONE")
PY

# Full suite
python -m pytest -q
```

## 7. Verdict

| Question | Answer |
|---|---|
| Failed run / step | `37707943066` / step 13 `Gate 3 - secret leak check (fail-closed)` |
| Root cause class | `SECRET_GUARD_CONTENT_BLOCK` (api-key-like sample in the unpushed draft) |
| Gate 3 weakened or bypassed? | **No** — unchanged source, strict pattern, still fails closed |
| Credential-shaped strings in the V4 reports? | **None** (verified in §6) |
| N1 / N2 / N3 | distinct decisions maintained; K03/K02/K10 overlaps corrected to `NOT SUPPORTED`; none promoted |
| Source gaps | `SOURCE_BREAKDOWN_PARTIAL` (0/12) and `FULL_CANONICAL_DEDUP_BLOCKED` remain open |
| Canonical writes / deploys / permission changes | **None** |
| final_status | `PARTIAL_SOURCE_GAP` + `FULL_CANONICAL_DEDUP_BLOCKED` (never `PASS`) |
