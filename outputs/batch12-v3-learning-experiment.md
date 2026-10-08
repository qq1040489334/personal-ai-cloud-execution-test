# batch12-v3-learning-experiment — KNOWLEDGE_BATCH_12_V3

- Task: `cf-090cdd6bc39c` (parent `cf-2a25d30bcd65`); Project: `personal-ai-knowledge-triage`;
  Risk: `LOW`; Mode: **READONLY / RESEARCH ONLY**.
- Purpose: a **reproducible** experiment to test the two surviving new-domain candidates
  **N2** (structured learning & transfer loop; `T08`+`T11`) and, as a secondary arm, **N1**
  (behavior-change design; `T05`). It is a *study protocol only*: no participant is recruited,
  no data is collected, and no system is changed by this task.
- Hard constraint: **all learner answers are produced by real humans.** No AI-generated or
  model-simulated responses may be used as learner data; doing so would remove the active-recall
  and Feynman effects the method claims (`T08-X1`). Automated scoring is permitted only *after*
  human answers exist, and must be reported as automated.

## 0. Why this experiment exists (traceable motivation)

- N2 is retained at grade B because the workflow is a single author's design (`T08-C1`,`T08-C2`)
  with **no measured outcomes** (`T08-X2`); the transfer literature independently supports **near**
  transfer and explicitly bounds **far** transfer (`T11-C4`,`T11-I1`).
- The single protocol below therefore tests both: (a) whether the structured loop beats plain
  reading, and (b) whether any gain survives delay and crosses to far transfer.
- N1 is tested with the same participant pool in a separate, pre-registered secondary arm because
  its increment (identity layer, `T05-C1`) also lacks an independent outcome study.

## 1. Pre-registration block (fill before data collection; do not edit afterward)

| Field | Value |
|---|---|
| Study ID | `BATCH12-N2-N1-v1` |
| Primary hypothesis (N2) | The structured loop (Arm A) yields higher **delayed retention** than plain reading (Arm B). |
| Secondary H1 (N2) | Arm A yields higher **near-transfer** scores than Arm B. |
| Secondary H2 (N2) | Arm A yields higher **immediate post-test** scores than Arm B. |
| Exploratory (N2) | Arm A shows a **far-transfer** advantage. (Declared exploratory; not a success criterion.) |
| Primary hypothesis (N1) | An identity-statement + tiny-win framing produces higher 4-week adherence than a willpower-only reminder. |
| Primary outcome (N2) | Proportion/score on the delayed-recall instrument (see §4.2). |
| Primary outcome (N1) | 28-day adherence rate on the chosen habit. |
| Design | Two-arm randomized, single-blind scoring, parallel groups. |
| Randomization | 1:1 by computer-generated permuted blocks (block size 4); allocation concealed until consent. |
| Sample size | 48 analysable per N2 arm (96 total) for ~0.5 SD effect at 80% power, α=0.05 two-sided; inflate 15% for attrition → recruit ~112. |
| Falsification (N2) | **N2 is falsified** if there is no statistically significant Arm A > Arm B difference on delayed retention **and** no significant gain on near transfer. Immediate-only gains (that decay) do not rescue N2. |
| Falsification (N1) | **N1 is falsified** if 28-day adherence in the identity arm is not > the willpower arm at α=0.05. |
| Stopping rule | No interim analysis; bounded by calendar (see §6). |
| Ethics | Written informed consent; no sensitive personal data; IRB/local review where required. |

## 2. Variables and controls

- **Independent variable (N2)**: study method — Arm A (structured loop) vs Arm B (plain reading
  + rereading). Both arms receive the **same source material** and the **same total study time**
  (90 minutes) to remove time-on-task as a confound.
- **Independent variable (N1)**: framing — identity+tiny-win vs willpower reminder, same target
  behavior and same reminder cadence.
- **Controls**: prior-knowledge pre-test; language proficiency; self-reported sleep on test day;
  device/time-of-day; rater blinding; identical test instruments across arms; no internet during
  testing.
- **Blinding**: scorers see de-identified answer sheets with arm labels removed; the experimenter
  who administers the tests does not score them.

## 3. Participants and materials

- **Participants**: human adults (age ≥18), fluent in the material language, no prior formal study
  of the target topic; excluded if they have read the priming books/sources.
- **Target topic (N2)**: choose **one** self-contained topic with a crisp deep structure, e.g.
  "cognitive biases in forecasting" or "supply/demand equilibrium". The topic text is frozen,
  hashed (SHA-256), and shipped with the protocol so runs are comparable.
- **Near-transfer material**: same deep structure, new surface (e.g., a different market/context
  using the same equilibrium principle).
- **Far-transfer material**: a structurally analogous problem in an unrelated domain (e.g., applying
  the abstraction to a scheduling or biology problem).
- **N1 habit**: a small daily behavior (e.g., 5-minute evening review) measured by a stamped,
  human-entered log; no app telemetry required.

## 4. Measures and instruments (reproducible)

### 4.1 Pre-test (prior knowledge)
10 short-answer items; scored 0–2 each by two blind raters; used as a covariate.

### 4.2 Instrument I — Immediate declarative post-test (after study, ≤30 min)
- 12 items: 6 free-recall prompts (human-written sentences) + 6 short-answer items.
- Primary delayed metric is the free-recall richness score (0–3 per prompt) judged against a
  published rubric anchored to the frozen source text.

### 4.3 Instrument II — Delayed retention (day 12–14, no study in between)
- Re-administer a parallel form of Instrument I; parallel forms are piloted for equal difficulty.
- **Human answers only.** Learners write answers in their own words; copy-paste/LLM use voids the
  session and the reason is recorded.

### 4.4 Instrument III — Near transfer (day 12–14)
- 4 novel problems reusing the **same** deep structure with new surface features.
- Answers require applying the abstraction, not recalling the source text.

### 4.5 Instrument IV — Far transfer (day 12–14, exploratory)
- 3 problems in an unrelated domain that share only the deep structure.
- Reported separately; a null result is expected if `T11-C4` is correct and does **not** falsify N2
  (far transfer is explicitly bounded).

### 4.6 Instrument V — Feynman explanation (day 12–14)
- Learner explains the topic to a novice in ≤200 words. Scored for causal completeness and jargon
  avoidance. This is the active-recall step the method claims (`T08-C1`, step 10).

### 4.7 Instrument VI — N1 adherence log
- 28 daily entries (done/not done + 1-line note), human-entered, timestamped; plus a 2-item
  identity-strength self-report at baseline and day 28.

## 5. Procedure (exact, so a third party can replicate)

1. **Screening & consent** → collect demographics and N2 pre-test (10 min).
2. **Randomize** to Arm A or Arm B (N2); independently randomize the N1 sub-study.
3. **Study session (90 min, proctored)**:
   - Arm A (structured loop, `T08-C1`): (1) generate ≥4 perspectives; (2) contradiction map;
     (3) synthesis brief; (4) select ≤5 curated resources; (5) difficulty ladder; (6) active
     self-test; (7) Feynman one-pager. All learner-generated.
   - Arm B (plain reading): read the identical source text and reread; may take free notes.
4. **Instrument I** immediately (≤30 min after study).
5. **Days 1–11**: no re-study; the N1 arm keeps its daily log.
6. **Days 12–14**: Instruments II, III, IV, V (without looking anything up).
7. **Day 28**: N1 adherence endpoint + identity-strength self-report.
8. **Scoring**: two blind raters independently score; disagreements >1 point adjudicated by a third
   blind rater. Report inter-rater reliability (ICC(2,1)).
9. **Analysis**: intention-to-treat; ANCOVA on delayed retention with pre-test covariate; Mann-Whitney
   for ordinal scales; Holm correction across the 3 confirmatory tests; report effect sizes and 95% CIs.
10. **Reproducibility package**: frozen topic text + SHA-256, instruments, rubrics, answer-sheet
    templates, randomization seed, and analysis code. Raw human answer sheets retained (consented).

## 6. Timeline, cost, risk

| Phase | Duration | Notes |
|---|---|---|
| Build + pilot instruments | 1–2 weeks | parallel-form difficulty pilot |
| Recruit + study + immediate test | 1–2 weeks | proctored sessions |
| Delay + delayed/transfer tests | 2 weeks | day 12–14 |
| N1 endpoint | 4 weeks from baseline | overlaps |
| Analysis + write-up | 1 week | pre-registered plan only |

- **Cost**: low–medium (participant time/compensation); no paid infrastructure.
- **Risk**: low. The protocol touches no production system, no Canonical store, no credentials.
- **Falsifiability summary**: N2 survives only if delayed retention **and** near transfer improve;
  N1 survives only if adherence improves. A far-transfer-only or immediate-only result is
  insufficient by pre-registration.

## 7. Honest limitations (kept open, not hidden)

- The pre-registered protocol above has **not been executed** in this task; there are **no results**,
  and none is fabricated.
- The topic choice, participant pool, and rubric anchoring are design decisions that a future run
  must instantiate; the frozen topic hash will differ per run.
- Even a successful run tests **near** transfer well and **far** transfer only weakly
  (`T11-C4`,`T11-C5`); no claim of general "触类旁通" is licensed.
- The N1 arm is behavioral and self-report based (`T05-X1`); placebo/expectancy is a known confound.
- Because the user's original 12 breakdown texts are unavailable (see
  `batch12-v3-unresolved-evidence.md`), this protocol is *source-grounded from public sources*,
  not from the user's originals.

## 8. Read-only guarantees

- No participant is enrolled, no data generated, no production/Canonical write, no install,
  deploy, or permission change. This file is a design artifact only.
