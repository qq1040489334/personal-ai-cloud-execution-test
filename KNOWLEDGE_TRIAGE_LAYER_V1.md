# PERSONAL_AI_KNOWLEDGE_TRIAGE_LAYER_V1

An **analysis and classification only** layer for Personal AI knowledge. It
accepts video, article, book, GitHub and other inputs (and future structured
Agent outputs), classifies them, checks quality/evidence/deduplication/freshness,
and emits an **advisory** promotion decision. It is deliberately inert: it never
writes canonical knowledge and never changes any production system.

- Task id: `cf-e2ef06bb97b1`
- Risk level: `LOW`
- Record schema: `KNOWLEDGE_TRIAGE_RECORD_V1` (JSON Schema Draft 2020-12)
- Focused tests: `tests/test_knowledge_triage_layer_v1.py`

## 1. Purpose and hard scope boundaries

This layer produces a triage **record** and a triage **recommendation**. It does
**not** produce canonical state.

| Boundary | Rule |
| --- | --- |
| Canonical KNOWLEDGE | **Never** created or modified by this layer. |
| DECISION | **Never** created or modified. Decision candidates are inert. |
| SKILL | **Never** created or modified. |
| Cloudflare Canonical / bindings | **Never** touched. |
| D1 schemas / migrations | **Never** touched. |
| secrets / OAuth / permissions | **Never** touched. |
| Skill Registry | **Never** modified. |
| production deployment | **Never** performed. |
| `PROMOTE_GOLDEN` | An **advisory recommendation only**, always gated by a separate, explicit Human Review Gate. |

No ingestion, promotion, write or deployment is executed in this layer. The only
outputs are (a) these rules, (b) machine-readable triage records and (c) review
output for a human. A promotion recommendation carries **no authority on its
own**.

## 2. Input model

An input is captured into a `source` object plus a top-level `source_type`:

| Field | Meaning | Required |
| --- | --- | --- |
| `source_type` | one of `VIDEO`, `ARTICLE`, `BOOK`, `GITHUB`, `OTHER` | yes |
| `source.title` | human-readable title | yes |
| `source.url` | canonical URL where available | no |
| `source.author` / `source.publisher` | author or originating source | no |
| `source.capture_time` | when the material was captured (ISO-8601) | yes |
| `source.publication_date` | when the source was published/updated | no |
| `source.version` | revision/edition/commit when relevant | no |
| `source.content` | raw content **or** AI summary, clearly labelled | yes |
| `source.missing_information` | explicit list of what is missing | no |

Content labelling and missing-information handling:

- `source.content.content_kind` is `RAW`, `AI_SUMMARY` or `MIXED`. An AI summary
  is an **abstraction** unless it has been checked against the original
  material; it must never be stored as if it were a raw source fact.
- When the original cannot be retrieved, the record must say so and list the gap
  in `source.missing_information`; the gap also lowers the achievable evidence
  level.
- A missing/blank required field makes the input **incomplete** for triage; it
  may be recorded, but it can never receive `PROMOTE_GOLDEN`.

## 3. Record and claim model

Claims live in three **separate** arrays under `claims`; they are never merged:

| Array | Meaning | Evidence authority |
| --- | --- | --- |
| `claims.source_facts` | Facts taken from the input material or explicitly verified external evidence. | May carry evidence level `A`/`B`/`C`/`UNKNOWN`. |
| `claims.ai_abstractions` | AI-generated summaries/derivations. | **Never** evidence; cannot upgrade a fact. |
| `claims.decision_candidates` | Candidate decisions proposed for humans. | **Never** auto-writes `DECISION`. |

Boundary rules (encoded in the schema where structurally expressible, and
checked semantically otherwise):

- A `SOURCE_FACT` requires an input-material `locator` **or** explicitly verified
  `verified_external_evidence`, plus `provenance` and `captured_at`. A fact with
  neither is invalid.
- An `AI_ABSTRACTION` may not carry `evidence_level`; it records its `model` and
  `derived_from`. AI judgment can never upgrade the evidence level of a claim.
- A `DECISION_CANDIDATE` has `auto_executed` fixed to `false`; it can never
  automatically write a `DECISION`.
- Every record carries a `source.capture_time` and a top-level `evaluation_time`,
  so capture date and evaluation date are always distinguishable.

## 4. Evidence rules

`quality_check.evidence_level` rates the **evidence**, never model confidence:

| Level | Definition |
| --- | --- |
| `A` | High-credibility primary/official/original research, or independently verifiable evidence. |
| `B` | Credible secondary sources, or multiple mutually supporting sources with independence checked. |
| `C` | Ordinary single source, personal experience, or not sufficiently verified. |
| `UNKNOWN` | Insufficient evidence to rate. |

- Official claims still require scope and verification: an official statement does
  not by itself establish a broader fact.
- Sources with unknown origin, unavailable originals, or unverifiable major claims
  cannot reach Golden.
- AI summary text is not evidence; only source material and verified external
  evidence can raise the level.

## 5. Golden promotion rules

`PROMOTE_GOLDEN` is a recommendation that must consider, together:

1. **Long-term value** (`golden_eligibility.long_term_value`).
2. **Evidence quality** (`golden_eligibility.evidence_quality`).
3. **Verifiability** (`golden_eligibility.verifiability`).
4. **Non-duplication** (`golden_eligibility.nonduplication`).
5. **Actual Personal AI utility** (`golden_eligibility.personal_ai_utility`).
6. **Traceable provenance** (`golden_eligibility.traceable_provenance`).

A record may be recommended for Golden only if **all** hold:

- `promotion_decision == PROMOTE_GOLDEN` and `golden_reason` is non-empty;
- `quality_check.source_quality` is `HIGH` or `MEDIUM` (**never** `LOW`);
- `quality_check.evidence_level` is `A` or `B`;
- `duplication_check.result` is `NEW` or `SIMILAR` (**never** `DUPLICATE`), with
  `comparison_complete == true` and `corpus_available == true`;
- at least one `SOURCE_FACT` is present and at least one is `VERIFIED`;
- `golden_eligibility.verified_source_fact_present == true` and every criterion
  above is `met == true`;
- `human_review.required == true` and `human_review.status == PENDING`
  (the Human Review Gate).

Never Golden: `LOW` source quality, marketing-only material, unverifiable major
facts, `DUPLICATE` material, and pure AI inference.

**Stale:** `STALE` defaults to non-promotion. A `STALE` record may only be
recommended for Golden with an explicit, documented
`historical_value_exception` (historical scope + verified evidence + Human
Review).

A `SIMILAR` record may only be recommended for Golden when it documents
`duplication_check.net_new_claims` (the net-new claims it adds).

Two structural rules keep the vocabulary honest:

- `golden_reason` must be non-empty **only** for `PROMOTE_GOLDEN`; for every other
  decision it must be absent.
- `golden_eligibility` records a boolean `met` plus a `rationale` **per
  criterion**, so the reasoning is structured rather than a single opaque flag.

## 6. Deduplication workflow

Deterministic, read-only comparison:

1. Compute the canonical URL and stable identifiers (version/edition/commit).
2. Compute a content hash of the canonicalized captured content.
3. Compare exact identity (URL/identifier/hash) against the read-only corpus.
4. For near matches, compare **claim semantic similarity** and report the
   matching records.
5. Apply the result: `NEW` (no match), `SIMILAR` (partial overlap), `DUPLICATE`
   (same material).

Comparison scope and limitations are explicit:

- `duplication_check.corpus_available` is `false` when the read-only comparison
  corpus cannot be reached.
- `duplication_check.comparison_complete` is `false` when the comparison could
  not be completed.
- An unknown/unavailable corpus is **not** confirmed `NEW`. It may be recorded as
  *provisional* `NEW` with `comparison_complete: false`, but that **blocks
  promotion** (Golden requires `comparison_complete == true` and
  `corpus_available == true`) pending verification.
- `DUPLICATE` never promotes. `SIMILAR` requires documented net-new claims.

## 7. Freshness rules

Freshness is domain-relative; this layer invents **no universal aging interval**.
It records:

- the source `publication_date`/`version`;
- the triage `review_date`;
- a domain-appropriate `recheck_trigger` (e.g. "a newer official revision is
  published", "the quarterly report is superseded").

`quality_check.freshness` is `CURRENT`, `AGING` or `STALE`, justified by the
recorded `freshness_basis`. Historical facts are distinguished from current
advice: a historical fact may remain accurate for its period, whereas dated
critical claims (prices, versions, availability, policy) require re-verification
and never become Golden on age alone.

## 8. Triage workflow (four sections per material)

Every material receives, in `review_output`:

1. **Triage Summary** — what the material is (source, type, category, value).
2. **Decision** — the advisory `promotion_decision` and its rationale.
3. **Evidence** — evidence level, source quality, freshness, claim provenance.
4. **Next Action** — the concrete next step (e.g. send to Human Review Gate, keep
   for reference, archive, or reject).

The layer classifies and recommends; a human decides.

## 9. Human Review contract

- Human review metadata is required on every record (`human_review`).
- For any promotion (`PROMOTE_GOLDEN`) the contract is:
  `human_review.required == true` and `human_review.status == PENDING`, with a
  `gate_id` identifying the separate Human Review Gate.
- Promotion never executes here. No canonical/DECISION/SKILL/Cloudflare/
  registry write or deployment happens regardless of the recommendation.
- Human decisions are recorded later by the human gate, not by this layer.

## 10. Semantic checks (what schema alone cannot prove)

The schema enforces structure. The following are **semantic** checks that a
regular machine consumer (or test) must apply because JSON Schema cannot verify
truth, provenance, source independence or dedup completeness:

- A `SOURCE_FACT` marked `VERIFIED` must trace to a real locator or verified
  external evidence; the schema only checks that one of the two is present.
- `evidence_level` `A`/`B` requires actual primary/secondary independence; the
  schema cannot detect a single source restated as "multiple".
- `comparison_complete == true` only means the comparison ran; it does not prove
  the corpus was complete.
- Pure AI inference must never be promoted even if it happens to satisfy the
  structural fields; a human/machine reviewer must reject it.
- `historical_value_exception` must document real scope and verified evidence;
  the schema only checks presence when `STALE` + Golden.

## Schema

The single source of truth for the record is the following JSON Schema
(Draft 2020-12). `KNOWLEDGE_TRIAGE_RECORD_V1` is the value of
`schema_version`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://personal-ai.local/schemas/KNOWLEDGE_TRIAGE_RECORD_V1.json",
  "title": "KNOWLEDGE_TRIAGE_RECORD_V1",
  "description": "Advisory knowledge triage record. Analysis/classification only; never writes canonical KNOWLEDGE, DECISION or SKILL.",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "schema_version",
    "source_type",
    "source",
    "category",
    "value_assessment",
    "quality_check",
    "duplication_check",
    "claims",
    "promotion_decision",
    "human_review",
    "review_output",
    "evaluation_time"
  ],
  "properties": {
    "id": {"type": "string", "minLength": 1},
    "schema_version": {"const": "KNOWLEDGE_TRIAGE_RECORD_V1"},
    "source_type": {"enum": ["VIDEO", "ARTICLE", "BOOK", "GITHUB", "OTHER"]},
    "source": {
      "type": "object",
      "additionalProperties": false,
      "required": ["title", "capture_time", "content"],
      "properties": {
        "title": {"type": "string", "minLength": 1},
        "url": {"type": "string"},
        "author": {"type": "string"},
        "publisher": {"type": "string"},
        "capture_time": {"type": "string", "format": "date-time"},
        "publication_date": {"type": "string"},
        "version": {"type": "string"},
        "content": {
          "type": "object",
          "additionalProperties": false,
          "required": ["content_kind"],
          "properties": {
            "content_kind": {"enum": ["RAW", "AI_SUMMARY", "MIXED"]},
            "raw_text": {"type": "string"},
            "ai_summary": {"type": "string"},
            "content_hash": {"type": "string"}
          }
        },
        "missing_information": {"type": "array", "items": {"type": "string"}}
      }
    },
    "category": {
      "enum": [
        "AI_TECHNOLOGY",
        "PERSONAL_AI",
        "FINANCE",
        "BUSINESS",
        "LIFE_DECISION",
        "SKILL",
        "TOOL",
        "OTHER"
      ]
    },
    "value_assessment": {
      "type": "object",
      "additionalProperties": false,
      "required": ["value", "reason"],
      "properties": {
        "value": {"enum": ["HIGH", "MEDIUM", "LOW"]},
        "reason": {"type": "string", "minLength": 1}
      }
    },
    "quality_check": {
      "type": "object",
      "additionalProperties": false,
      "required": ["source_quality", "evidence_level", "freshness"],
      "properties": {
        "source_quality": {"enum": ["HIGH", "MEDIUM", "LOW"]},
        "evidence_level": {"enum": ["A", "B", "C", "UNKNOWN"]},
        "freshness": {"enum": ["CURRENT", "AGING", "STALE"]},
        "freshness_basis": {"type": "string"},
        "review_date": {"type": "string"},
        "recheck_trigger": {"type": "string"}
      }
    },
    "duplication_check": {
      "type": "object",
      "additionalProperties": false,
      "required": ["result", "comparison_complete", "corpus_available"],
      "properties": {
        "result": {"enum": ["NEW", "SIMILAR", "DUPLICATE"]},
        "comparison_complete": {"type": "boolean"},
        "corpus_available": {"type": "boolean"},
        "canonical_url": {"type": "string"},
        "content_hash": {"type": "string"},
        "matched_records": {"type": "array", "items": {"type": "string"}},
        "net_new_claims": {"type": "array", "items": {"type": "string"}},
        "basis": {"type": "string"}
      }
    },
    "claims": {
      "type": "object",
      "additionalProperties": false,
      "required": ["source_facts", "ai_abstractions", "decision_candidates"],
      "properties": {
        "source_facts": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "claim_id",
              "text",
              "claim_type",
              "provenance",
              "verification_status",
              "captured_at"
            ],
            "anyOf": [
              {"required": ["locator"]},
              {"required": ["verified_external_evidence"]}
            ],
            "properties": {
              "claim_id": {"type": "string", "minLength": 1},
              "text": {"type": "string", "minLength": 1},
              "claim_type": {"const": "SOURCE_FACT"},
              "locator": {"type": "string", "minLength": 1},
              "verified_external_evidence": {"type": "string", "minLength": 1},
              "provenance": {"type": "string", "minLength": 1},
              "evidence_level": {"enum": ["A", "B", "C", "UNKNOWN"]},
              "verification_status": {"enum": ["VERIFIED", "PARTIAL", "UNVERIFIED"]},
              "source_date": {"type": "string"},
              "captured_at": {"type": "string", "format": "date-time"}
            }
          }
        },
        "ai_abstractions": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "claim_id",
              "text",
              "claim_type",
              "derived_from",
              "verification_status",
              "captured_at"
            ],
            "properties": {
              "claim_id": {"type": "string", "minLength": 1},
              "text": {"type": "string", "minLength": 1},
              "claim_type": {"const": "AI_ABSTRACTION"},
              "derived_from": {"type": "array", "minItems": 1, "items": {"type": "string"}},
              "model": {"type": "string"},
              "verification_status": {"enum": ["UNVERIFIED", "VERIFIED_AGAINST_SOURCE"]},
              "captured_at": {"type": "string", "format": "date-time"}
            }
          }
        },
        "decision_candidates": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "claim_id",
              "text",
              "claim_type",
              "derived_from",
              "recommended_action",
              "auto_executed",
              "verification_status",
              "captured_at"
            ],
            "properties": {
              "claim_id": {"type": "string", "minLength": 1},
              "text": {"type": "string", "minLength": 1},
              "claim_type": {"const": "DECISION_CANDIDATE"},
              "derived_from": {"type": "array", "minItems": 1, "items": {"type": "string"}},
              "recommended_action": {"type": "string", "minLength": 1},
              "auto_executed": {"const": false},
              "verification_status": {"enum": ["UNVERIFIED", "PENDING_HUMAN_REVIEW"]},
              "captured_at": {"type": "string", "format": "date-time"}
            }
          }
        }
      }
    },
    "promotion_decision": {"enum": ["KEEP", "PROMOTE_GOLDEN", "ARCHIVE", "REJECT"]},
    "promotion_rationale": {"type": "string"},
    "golden_reason": {"type": "string", "minLength": 1},
    "golden_eligibility": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "long_term_value",
        "evidence_quality",
        "verifiability",
        "nonduplication",
        "personal_ai_utility",
        "traceable_provenance",
        "verified_source_fact_present"
      ],
      "properties": {
        "long_term_value": {"$ref": "#/$defs/criterion"},
        "evidence_quality": {"$ref": "#/$defs/criterion"},
        "verifiability": {"$ref": "#/$defs/criterion"},
        "nonduplication": {"$ref": "#/$defs/criterion"},
        "personal_ai_utility": {"$ref": "#/$defs/criterion"},
        "traceable_provenance": {"$ref": "#/$defs/criterion"},
        "verified_source_fact_present": {"type": "boolean"}
      }
    },
    "historical_value_exception": {
      "type": "object",
      "additionalProperties": false,
      "required": ["used", "historical_scope", "evidence", "review_required"],
      "properties": {
        "used": {"type": "boolean"},
        "historical_scope": {"type": "string", "minLength": 1},
        "evidence": {"type": "string", "minLength": 1},
        "review_required": {"const": true},
        "reviewed_by": {"type": "string"}
      }
    },
    "human_review": {
      "type": "object",
      "additionalProperties": false,
      "required": ["required", "status", "gate_id"],
      "properties": {
        "required": {"type": "boolean"},
        "status": {"enum": ["PENDING", "APPROVED", "REJECTED", "NOT_REQUIRED"]},
        "gate_id": {"type": "string", "minLength": 1},
        "reviewer": {"type": ["string", "null"]},
        "reviewed_at": {"type": ["string", "null"]},
        "notes": {"type": "string"}
      }
    },
    "review_output": {
      "type": "object",
      "additionalProperties": false,
      "required": ["triage_summary", "decision", "evidence", "next_action"],
      "properties": {
        "triage_summary": {"type": "string", "minLength": 1},
        "decision": {"type": "string", "minLength": 1},
        "evidence": {"type": "string", "minLength": 1},
        "next_action": {"type": "string", "minLength": 1}
      }
    },
    "evaluation_time": {"type": "string", "format": "date-time"}
  },
  "$defs": {
    "criterion": {
      "type": "object",
      "additionalProperties": false,
      "required": ["met", "rationale"],
      "properties": {
        "met": {"type": "boolean"},
        "rationale": {"type": "string", "minLength": 1}
      }
    }
  },
  "allOf": [
    {
      "if": {
        "properties": {"promotion_decision": {"const": "PROMOTE_GOLDEN"}},
        "required": ["promotion_decision"]
      },
      "then": {
        "required": ["golden_reason", "golden_eligibility"],
        "properties": {
          "golden_reason": {"type": "string", "minLength": 1},
          "quality_check": {
            "required": ["source_quality", "evidence_level", "freshness"],
            "properties": {
              "source_quality": {"enum": ["HIGH", "MEDIUM"]},
              "evidence_level": {"enum": ["A", "B"]}
            }
          },
          "duplication_check": {
            "required": ["result", "comparison_complete", "corpus_available"],
            "properties": {
              "result": {"enum": ["NEW", "SIMILAR"]},
              "comparison_complete": {"const": true},
              "corpus_available": {"const": true}
            }
          },
          "human_review": {
            "required": ["required", "status"],
            "properties": {
              "required": {"const": true},
              "status": {"const": "PENDING"}
            }
          },
          "claims": {
            "required": ["source_facts"],
            "properties": {"source_facts": {"minItems": 1}}
          },
          "golden_eligibility": {
            "required": [
              "long_term_value",
              "evidence_quality",
              "verifiability",
              "nonduplication",
              "personal_ai_utility",
              "traceable_provenance",
              "verified_source_fact_present"
            ],
            "properties": {
              "long_term_value": {
                "required": ["met"],
                "properties": {"met": {"const": true}}
              },
              "evidence_quality": {
                "required": ["met"],
                "properties": {"met": {"const": true}}
              },
              "verifiability": {
                "required": ["met"],
                "properties": {"met": {"const": true}}
              },
              "nonduplication": {
                "required": ["met"],
                "properties": {"met": {"const": true}}
              },
              "personal_ai_utility": {
                "required": ["met"],
                "properties": {"met": {"const": true}}
              },
              "traceable_provenance": {
                "required": ["met"],
                "properties": {"met": {"const": true}}
              },
              "verified_source_fact_present": {"const": true}
            }
          }
        }
      }
    },
    {
      "if": {
        "properties": {"promotion_decision": {"not": {"const": "PROMOTE_GOLDEN"}}},
        "required": ["promotion_decision"]
      },
      "then": {"not": {"required": ["golden_reason"]}}
    },
    {
      "if": {
        "properties": {
          "promotion_decision": {"const": "PROMOTE_GOLDEN"},
          "quality_check": {
            "properties": {"freshness": {"const": "STALE"}},
            "required": ["freshness"]
          }
        },
        "required": ["promotion_decision", "quality_check"]
      },
      "then": {"required": ["historical_value_exception"]}
    },
    {
      "if": {
        "properties": {
          "promotion_decision": {"const": "PROMOTE_GOLDEN"},
          "duplication_check": {
            "properties": {"result": {"const": "SIMILAR"}},
            "required": ["result"]
          }
        },
        "required": ["promotion_decision", "duplication_check"]
      },
      "then": {
        "properties": {
          "duplication_check": {
            "required": ["net_new_claims"],
            "properties": {"net_new_claims": {"minItems": 1}}
          }
        }
      }
    }
  ]
}
```

## Examples

All examples below are **synthetic fixtures**. Their facts are supplied
hypothetical input, not claims of live external verification. Each is a complete
`KNOWLEDGE_TRIAGE_RECORD_V1` record and each includes the four-section review
output.

### Example 1 — PROMOTE_GOLDEN (advisory only, pending Human Review)

```json
{
  "id": "KT-V1-EXAMPLE-PROMOTE-GOLDEN",
  "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
  "source_type": "ARTICLE",
  "source": {
    "title": "Synthetic fixture: versioned protocol specification",
    "url": "https://example.invalid/spec/2025-06-18",
    "author": "Synthetic maintainers",
    "publisher": "Synthetic Standards Body",
    "capture_time": "2026-02-01T08:00:00Z",
    "publication_date": "2025-06-18",
    "version": "2025-06-18",
    "content": {
      "content_kind": "RAW",
      "raw_text": "Synthetic fixture: the specification defines message framing and capability negotiation.",
      "content_hash": "sha256:synthetic-promote-golden"
    },
    "missing_information": []
  },
  "category": "AI_TECHNOLOGY",
  "value_assessment": {
    "value": "HIGH",
    "reason": "Synthetic fixture: canonical, versioned reference with long-term utility."
  },
  "quality_check": {
    "source_quality": "HIGH",
    "evidence_level": "A",
    "freshness": "CURRENT",
    "freshness_basis": "Synthetic fixture: treated current within its documented review window.",
    "review_date": "2026-02-01",
    "recheck_trigger": "A newer official specification revision is published."
  },
  "duplication_check": {
    "result": "NEW",
    "comparison_complete": true,
    "corpus_available": true,
    "canonical_url": "https://example.invalid/spec/2025-06-18",
    "content_hash": "sha256:synthetic-promote-golden",
    "matched_records": [],
    "basis": "Synthetic fixture: canonical URL and content hash are absent from the read-only corpus."
  },
  "claims": {
    "source_facts": [
      {
        "claim_id": "F1",
        "text": "Synthetic fixture: messages are framed as JSON-RPC 2.0 messages.",
        "claim_type": "SOURCE_FACT",
        "locator": "section 'Message Framing', revision 2025-06-18",
        "provenance": "Synthetic fixture: official specification captured 2026-02-01T08:00:00Z",
        "evidence_level": "A",
        "verification_status": "VERIFIED",
        "source_date": "2025-06-18",
        "captured_at": "2026-02-01T08:00:00Z"
      }
    ],
    "ai_abstractions": [
      {
        "claim_id": "A1",
        "text": "Synthetic fixture: the specification implies tools should normalize capability negotiation.",
        "claim_type": "AI_ABSTRACTION",
        "derived_from": ["F1"],
        "model": "synthetic-fixture-model",
        "verification_status": "VERIFIED_AGAINST_SOURCE",
        "captured_at": "2026-02-01T08:05:00Z"
      }
    ],
    "decision_candidates": [
      {
        "claim_id": "D1",
        "text": "Synthetic fixture: adopt the versioned specification revision as the baseline.",
        "claim_type": "DECISION_CANDIDATE",
        "derived_from": ["F1", "A1"],
        "recommended_action": "Adopt the documented revision as the integration baseline.",
        "auto_executed": false,
        "verification_status": "PENDING_HUMAN_REVIEW",
        "captured_at": "2026-02-01T08:06:00Z"
      }
    ]
  },
  "promotion_decision": "PROMOTE_GOLDEN",
  "promotion_rationale": "Synthetic fixture: high evidence, non-duplicate, verified source fact, complete comparison.",
  "golden_reason": "Synthetic fixture: canonical high-evidence reference with durable utility and traceable provenance.",
  "golden_eligibility": {
    "long_term_value": {"met": true, "rationale": "Synthetic fixture: durable reference value."},
    "evidence_quality": {"met": true, "rationale": "Synthetic fixture: primary official evidence."},
    "verifiability": {"met": true, "rationale": "Synthetic fixture: verifiable against the captured revision."},
    "nonduplication": {"met": true, "rationale": "Synthetic fixture: no duplicate in the available corpus."},
    "personal_ai_utility": {"met": true, "rationale": "Synthetic fixture: directly informs integration work."},
    "traceable_provenance": {"met": true, "rationale": "Synthetic fixture: URL, locator and capture time recorded."},
    "verified_source_fact_present": true
  },
  "human_review": {
    "required": true,
    "status": "PENDING",
    "gate_id": "HR-KT-V1-EXAMPLE-PROMOTE-GOLDEN",
    "reviewer": null,
    "reviewed_at": null,
    "notes": "Synthetic fixture: promotion is advisory and awaits the Human Review Gate."
  },
  "review_output": {
    "triage_summary": "Synthetic fixture: a versioned AI-technology specification article.",
    "decision": "PROMOTE_GOLDEN (recommendation only), pending Human Review.",
    "evidence": "Level A primary official evidence with a located, verified source fact.",
    "next_action": "Send to the separate Human Review Gate; do not write canonical state here."
  },
  "evaluation_time": "2026-02-01T08:10:00Z"
}
```

### Example 2 — KEEP (useful, not canonical)

```json
{
  "id": "KT-V1-EXAMPLE-KEEP",
  "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
  "source_type": "VIDEO",
  "source": {
    "title": "Synthetic fixture: practical tooling walkthrough",
    "url": "https://example.invalid/video/tooling",
    "author": "Synthetic creator",
    "publisher": "Synthetic Channel",
    "capture_time": "2026-03-02T10:00:00Z",
    "publication_date": "2026-02-20",
    "content": {
      "content_kind": "AI_SUMMARY",
      "ai_summary": "Synthetic fixture: an AI summary of a tooling walkthrough.",
      "content_hash": "sha256:synthetic-keep"
    },
    "missing_information": ["Original transcript not captured; summary is unchecked against the video."]
  },
  "category": "TOOL",
  "value_assessment": {
    "value": "MEDIUM",
    "reason": "Synthetic fixture: useful practical tips but overlapping with existing notes."
  },
  "quality_check": {
    "source_quality": "MEDIUM",
    "evidence_level": "B",
    "freshness": "CURRENT",
    "freshness_basis": "Synthetic fixture: recent but fast-moving tooling domain.",
    "review_date": "2026-03-02",
    "recheck_trigger": "A tool major version change."
  },
  "duplication_check": {
    "result": "SIMILAR",
    "comparison_complete": true,
    "corpus_available": true,
    "matched_records": ["KT-V1-EXAMPLE-ARCHIVE"],
    "net_new_claims": ["Synthetic fixture: one new keyboard-shortcut workflow."],
    "basis": "Synthetic fixture: overlaps an existing note but adds one net-new claim."
  },
  "claims": {
    "source_facts": [
      {
        "claim_id": "F2",
        "text": "Synthetic fixture: the walkthrough demonstrates a documented shortcut.",
        "claim_type": "SOURCE_FACT",
        "locator": "video 00:03:12",
        "provenance": "Synthetic fixture: AI summary derived from the captured video.",
        "evidence_level": "B",
        "verification_status": "PARTIAL",
        "captured_at": "2026-03-02T10:00:00Z"
      }
    ],
    "ai_abstractions": [
      {
        "claim_id": "A2",
        "text": "Synthetic fixture: the shortcut may speed up daily work.",
        "claim_type": "AI_ABSTRACTION",
        "derived_from": ["F2"],
        "model": "synthetic-fixture-model",
        "verification_status": "UNVERIFIED",
        "captured_at": "2026-03-02T10:05:00Z"
      }
    ],
    "decision_candidates": []
  },
  "promotion_decision": "KEEP",
  "promotion_rationale": "Synthetic fixture: useful but not canonical; keep for reference.",
  "human_review": {
    "required": false,
    "status": "NOT_REQUIRED",
    "gate_id": "HR-KT-V1-EXAMPLE-KEEP",
    "reviewer": null,
    "reviewed_at": null
  },
  "review_output": {
    "triage_summary": "Synthetic fixture: a tooling video summarized by AI.",
    "decision": "KEEP (no promotion).",
    "evidence": "Level B secondary/partial evidence; AI summary is not evidence.",
    "next_action": "Keep in the working notes; re-check on a tool major version change."
  },
  "evaluation_time": "2026-03-02T10:10:00Z"
}
```

### Example 3 — ARCHIVE (stale, defaults to non-promotion)

```json
{
  "id": "KT-V1-EXAMPLE-ARCHIVE",
  "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
  "source_type": "GITHUB",
  "source": {
    "title": "Synthetic fixture: deprecated integration guide",
    "url": "https://example.invalid/repo/deprecated-guide",
    "author": "Synthetic org",
    "capture_time": "2026-01-15T12:00:00Z",
    "publication_date": "2021-05-01",
    "version": "v1.0.0",
    "content": {
      "content_kind": "RAW",
      "raw_text": "Synthetic fixture: setup instructions for a deprecated integration.",
      "content_hash": "sha256:synthetic-archive"
    },
    "missing_information": []
  },
  "category": "TOOL",
  "value_assessment": {
    "value": "LOW",
    "reason": "Synthetic fixture: describes a deprecated integration no longer recommended."
  },
  "quality_check": {
    "source_quality": "MEDIUM",
    "evidence_level": "C",
    "freshness": "STALE",
    "freshness_basis": "Synthetic fixture: superseded by newer versions years ago.",
    "review_date": "2026-01-15",
    "recheck_trigger": "Historical interest only."
  },
  "duplication_check": {
    "result": "NEW",
    "comparison_complete": true,
    "corpus_available": true,
    "matched_records": [],
    "basis": "Synthetic fixture: unique but outdated."
  },
  "claims": {
    "source_facts": [
      {
        "claim_id": "F3",
        "text": "Synthetic fixture: the guide documents a deprecated integration.",
        "claim_type": "SOURCE_FACT",
        "locator": "README section 'Setup'",
        "provenance": "Synthetic fixture: captured repository document.",
        "evidence_level": "C",
        "verification_status": "VERIFIED",
        "source_date": "2021-05-01",
        "captured_at": "2026-01-15T12:00:00Z"
      }
    ],
    "ai_abstractions": [],
    "decision_candidates": []
  },
  "promotion_decision": "ARCHIVE",
  "promotion_rationale": "Synthetic fixture: stale and low current value; archive for historical reference only.",
  "human_review": {
    "required": false,
    "status": "NOT_REQUIRED",
    "gate_id": "HR-KT-V1-EXAMPLE-ARCHIVE",
    "reviewer": null,
    "reviewed_at": null
  },
  "review_output": {
    "triage_summary": "Synthetic fixture: a deprecated tool integration guide.",
    "decision": "ARCHIVE (no promotion).",
    "evidence": "Level C single source; STALE with no historical-value exception.",
    "next_action": "Archive; do not promote."
  },
  "evaluation_time": "2026-01-15T12:10:00Z"
}
```

### Example 4 — REJECT (duplicate, low quality, unverifiable)

```json
{
  "id": "KT-V1-EXAMPLE-REJECT",
  "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
  "source_type": "OTHER",
  "source": {
    "title": "Synthetic fixture: anonymous marketing blast",
    "url": "https://example.invalid/marketing/blast",
    "capture_time": "2026-04-01T09:00:00Z",
    "content": {
      "content_kind": "AI_SUMMARY",
      "ai_summary": "Synthetic fixture: promotional claims with no source.",
      "content_hash": "sha256:synthetic-reject"
    },
    "missing_information": ["No author", "No publication date", "No original evidence"]
  },
  "category": "BUSINESS",
  "value_assessment": {
    "value": "LOW",
    "reason": "Synthetic fixture: marketing-only material duplicating existing records."
  },
  "quality_check": {
    "source_quality": "LOW",
    "evidence_level": "UNKNOWN",
    "freshness": "AGING",
    "freshness_basis": "Synthetic fixture: undated promotional material.",
    "review_date": "2026-04-01",
    "recheck_trigger": "None; rejected."
  },
  "duplication_check": {
    "result": "DUPLICATE",
    "comparison_complete": true,
    "corpus_available": true,
    "matched_records": ["KT-V1-EXAMPLE-KEEP"],
    "basis": "Synthetic fixture: same material already recorded."
  },
  "claims": {
    "source_facts": [],
    "ai_abstractions": [
      {
        "claim_id": "A4",
        "text": "Synthetic fixture: the product is claimed to be the best.",
        "claim_type": "AI_ABSTRACTION",
        "derived_from": ["source.content"],
        "model": "synthetic-fixture-model",
        "verification_status": "UNVERIFIED",
        "captured_at": "2026-04-01T09:00:00Z"
      }
    ],
    "decision_candidates": []
  },
  "promotion_decision": "REJECT",
  "promotion_rationale": "Synthetic fixture: low source quality, duplicate, marketing-only, unverifiable major claims.",
  "human_review": {
    "required": false,
    "status": "NOT_REQUIRED",
    "gate_id": "HR-KT-V1-EXAMPLE-REJECT",
    "reviewer": null,
    "reviewed_at": null
  },
  "review_output": {
    "triage_summary": "Synthetic fixture: anonymous promotional material with no source.",
    "decision": "REJECT (no promotion).",
    "evidence": "Unknown evidence, low source quality, duplicate, marketing-only.",
    "next_action": "Discard; do not ingest or promote."
  },
  "evaluation_time": "2026-04-01T09:05:00Z"
}
```

## Adversarial Cases

Each case is an **attempted Golden promotion** (or invalid claim) that must be
rejected. The `expected` value is the reason it must not promote. These are
synthetic fixtures.

```json
{
  "case": "pure_ai_inference_only",
  "expected": "SCHEMA_INVALID_OR_POLICY_REJECT",
  "record": {
    "id": "KT-V1-ADV-AI-ONLY",
    "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
    "source_type": "ARTICLE",
    "source": {
      "title": "Synthetic fixture: AI-only reasoning",
      "capture_time": "2026-05-01T09:00:00Z",
      "content": {"content_kind": "AI_SUMMARY", "ai_summary": "Synthetic fixture: model musings."}
    },
    "category": "OTHER",
    "value_assessment": {"value": "HIGH", "reason": "Synthetic fixture: model thinks it is valuable."},
    "quality_check": {"source_quality": "HIGH", "evidence_level": "A", "freshness": "CURRENT"},
    "duplication_check": {"result": "NEW", "comparison_complete": true, "corpus_available": true},
    "claims": {
      "source_facts": [],
      "ai_abstractions": [
        {
          "claim_id": "A1",
          "text": "Synthetic fixture: pure model inference presented as fact.",
          "claim_type": "AI_ABSTRACTION",
          "derived_from": ["model"],
          "model": "synthetic-fixture-model",
          "verification_status": "UNVERIFIED",
          "captured_at": "2026-05-01T09:00:00Z"
        }
      ],
      "decision_candidates": []
    },
    "promotion_decision": "PROMOTE_GOLDEN",
    "golden_reason": "Synthetic fixture: invalid Golden attempt.",
    "golden_eligibility": {
      "long_term_value": {"met": true, "rationale": "Synthetic fixture."},
      "evidence_quality": {"met": true, "rationale": "Synthetic fixture."},
      "verifiability": {"met": true, "rationale": "Synthetic fixture."},
      "nonduplication": {"met": true, "rationale": "Synthetic fixture."},
      "personal_ai_utility": {"met": true, "rationale": "Synthetic fixture."},
      "traceable_provenance": {"met": true, "rationale": "Synthetic fixture."},
      "verified_source_fact_present": false
    },
    "human_review": {"required": true, "status": "PENDING", "gate_id": "HR-ADV-AI-ONLY"},
    "review_output": {
      "triage_summary": "Synthetic fixture.",
      "decision": "REJECT.",
      "evidence": "None.",
      "next_action": "Reject."
    },
    "evaluation_time": "2026-05-01T09:05:00Z"
  }
}
```

```json
{
  "case": "low_source_quality",
  "expected": "SCHEMA_INVALID_OR_POLICY_REJECT",
  "record": {
    "id": "KT-V1-ADV-LOW-QUALITY",
    "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
    "source_type": "ARTICLE",
    "source": {
      "title": "Synthetic fixture: low quality source",
      "capture_time": "2026-05-01T09:00:00Z",
      "content": {"content_kind": "RAW", "raw_text": "Synthetic fixture."}
    },
    "category": "OTHER",
    "value_assessment": {"value": "HIGH", "reason": "Synthetic fixture."},
    "quality_check": {"source_quality": "LOW", "evidence_level": "A", "freshness": "CURRENT"},
    "duplication_check": {"result": "NEW", "comparison_complete": true, "corpus_available": true},
    "claims": {
      "source_facts": [
        {
          "claim_id": "F1",
          "text": "Synthetic fixture.",
          "claim_type": "SOURCE_FACT",
          "locator": "synthetic",
          "provenance": "synthetic",
          "evidence_level": "A",
          "verification_status": "VERIFIED",
          "captured_at": "2026-05-01T09:00:00Z"
        }
      ],
      "ai_abstractions": [],
      "decision_candidates": []
    },
    "promotion_decision": "PROMOTE_GOLDEN",
    "golden_reason": "Synthetic fixture: invalid Golden attempt.",
    "golden_eligibility": {
      "long_term_value": {"met": true, "rationale": "Synthetic fixture."},
      "evidence_quality": {"met": true, "rationale": "Synthetic fixture."},
      "verifiability": {"met": true, "rationale": "Synthetic fixture."},
      "nonduplication": {"met": true, "rationale": "Synthetic fixture."},
      "personal_ai_utility": {"met": true, "rationale": "Synthetic fixture."},
      "traceable_provenance": {"met": true, "rationale": "Synthetic fixture."},
      "verified_source_fact_present": true
    },
    "human_review": {"required": true, "status": "PENDING", "gate_id": "HR-ADV-LOW-QUALITY"},
    "review_output": {
      "triage_summary": "Synthetic fixture.",
      "decision": "REJECT.",
      "evidence": "Low quality.",
      "next_action": "Reject."
    },
    "evaluation_time": "2026-05-01T09:05:00Z"
  }
}
```

```json
{
  "case": "duplicate_material",
  "expected": "SCHEMA_INVALID_OR_POLICY_REJECT",
  "record": {
    "id": "KT-V1-ADV-DUPLICATE",
    "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
    "source_type": "ARTICLE",
    "source": {
      "title": "Synthetic fixture: duplicate",
      "capture_time": "2026-05-01T09:00:00Z",
      "content": {"content_kind": "RAW", "raw_text": "Synthetic fixture."}
    },
    "category": "OTHER",
    "value_assessment": {"value": "HIGH", "reason": "Synthetic fixture."},
    "quality_check": {"source_quality": "HIGH", "evidence_level": "A", "freshness": "CURRENT"},
    "duplication_check": {
      "result": "DUPLICATE",
      "comparison_complete": true,
      "corpus_available": true,
      "matched_records": ["KT-V1-EXAMPLE-KEEP"]
    },
    "claims": {
      "source_facts": [
        {
          "claim_id": "F1",
          "text": "Synthetic fixture.",
          "claim_type": "SOURCE_FACT",
          "locator": "synthetic",
          "provenance": "synthetic",
          "evidence_level": "A",
          "verification_status": "VERIFIED",
          "captured_at": "2026-05-01T09:00:00Z"
        }
      ],
      "ai_abstractions": [],
      "decision_candidates": []
    },
    "promotion_decision": "PROMOTE_GOLDEN",
    "golden_reason": "Synthetic fixture: invalid Golden attempt.",
    "golden_eligibility": {
      "long_term_value": {"met": true, "rationale": "Synthetic fixture."},
      "evidence_quality": {"met": true, "rationale": "Synthetic fixture."},
      "verifiability": {"met": true, "rationale": "Synthetic fixture."},
      "nonduplication": {"met": true, "rationale": "Synthetic fixture."},
      "personal_ai_utility": {"met": true, "rationale": "Synthetic fixture."},
      "traceable_provenance": {"met": true, "rationale": "Synthetic fixture."},
      "verified_source_fact_present": true
    },
    "human_review": {"required": true, "status": "PENDING", "gate_id": "HR-ADV-DUPLICATE"},
    "review_output": {
      "triage_summary": "Synthetic fixture.",
      "decision": "REJECT.",
      "evidence": "Duplicate.",
      "next_action": "Reject."
    },
    "evaluation_time": "2026-05-01T09:05:00Z"
  }
}
```

```json
{
  "case": "stale_without_historical_exception",
  "expected": "SCHEMA_INVALID_OR_POLICY_REJECT",
  "record": {
    "id": "KT-V1-ADV-STALE",
    "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
    "source_type": "ARTICLE",
    "source": {
      "title": "Synthetic fixture: stale",
      "capture_time": "2026-05-01T09:00:00Z",
      "content": {"content_kind": "RAW", "raw_text": "Synthetic fixture."}
    },
    "category": "OTHER",
    "value_assessment": {"value": "HIGH", "reason": "Synthetic fixture."},
    "quality_check": {"source_quality": "HIGH", "evidence_level": "A", "freshness": "STALE"},
    "duplication_check": {"result": "NEW", "comparison_complete": true, "corpus_available": true},
    "claims": {
      "source_facts": [
        {
          "claim_id": "F1",
          "text": "Synthetic fixture.",
          "claim_type": "SOURCE_FACT",
          "locator": "synthetic",
          "provenance": "synthetic",
          "evidence_level": "A",
          "verification_status": "VERIFIED",
          "captured_at": "2026-05-01T09:00:00Z"
        }
      ],
      "ai_abstractions": [],
      "decision_candidates": []
    },
    "promotion_decision": "PROMOTE_GOLDEN",
    "golden_reason": "Synthetic fixture: invalid Golden attempt.",
    "golden_eligibility": {
      "long_term_value": {"met": true, "rationale": "Synthetic fixture."},
      "evidence_quality": {"met": true, "rationale": "Synthetic fixture."},
      "verifiability": {"met": true, "rationale": "Synthetic fixture."},
      "nonduplication": {"met": true, "rationale": "Synthetic fixture."},
      "personal_ai_utility": {"met": true, "rationale": "Synthetic fixture."},
      "traceable_provenance": {"met": true, "rationale": "Synthetic fixture."},
      "verified_source_fact_present": true
    },
    "human_review": {"required": true, "status": "PENDING", "gate_id": "HR-ADV-STALE"},
    "review_output": {
      "triage_summary": "Synthetic fixture.",
      "decision": "REJECT.",
      "evidence": "Stale without exception.",
      "next_action": "Reject."
    },
    "evaluation_time": "2026-05-01T09:05:00Z"
  }
}
```

```json
{
  "case": "unavailable_dedup_corpus",
  "expected": "SCHEMA_INVALID_OR_POLICY_REJECT",
  "record": {
    "id": "KT-V1-ADV-NO-CORPUS",
    "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
    "source_type": "ARTICLE",
    "source": {
      "title": "Synthetic fixture: unknown corpus",
      "capture_time": "2026-05-01T09:00:00Z",
      "content": {"content_kind": "RAW", "raw_text": "Synthetic fixture."}
    },
    "category": "OTHER",
    "value_assessment": {"value": "HIGH", "reason": "Synthetic fixture."},
    "quality_check": {"source_quality": "HIGH", "evidence_level": "A", "freshness": "CURRENT"},
    "duplication_check": {
      "result": "NEW",
      "comparison_complete": false,
      "corpus_available": false,
      "basis": "Synthetic fixture: corpus unavailable, provisional NEW only."
    },
    "claims": {
      "source_facts": [
        {
          "claim_id": "F1",
          "text": "Synthetic fixture.",
          "claim_type": "SOURCE_FACT",
          "locator": "synthetic",
          "provenance": "synthetic",
          "evidence_level": "A",
          "verification_status": "VERIFIED",
          "captured_at": "2026-05-01T09:00:00Z"
        }
      ],
      "ai_abstractions": [],
      "decision_candidates": []
    },
    "promotion_decision": "PROMOTE_GOLDEN",
    "golden_reason": "Synthetic fixture: invalid Golden attempt.",
    "golden_eligibility": {
      "long_term_value": {"met": true, "rationale": "Synthetic fixture."},
      "evidence_quality": {"met": true, "rationale": "Synthetic fixture."},
      "verifiability": {"met": true, "rationale": "Synthetic fixture."},
      "nonduplication": {"met": true, "rationale": "Synthetic fixture."},
      "personal_ai_utility": {"met": true, "rationale": "Synthetic fixture."},
      "traceable_provenance": {"met": true, "rationale": "Synthetic fixture."},
      "verified_source_fact_present": true
    },
    "human_review": {"required": true, "status": "PENDING", "gate_id": "HR-ADV-NO-CORPUS"},
    "review_output": {
      "triage_summary": "Synthetic fixture.",
      "decision": "BLOCK promotion.",
      "evidence": "Dedup corpus unavailable.",
      "next_action": "Verify corpus before any promotion."
    },
    "evaluation_time": "2026-05-01T09:05:00Z"
  }
}
```

```json
{
  "case": "unverifiable_major_fact",
  "expected": "SCHEMA_INVALID_OR_POLICY_REJECT",
  "record": {
    "id": "KT-V1-ADV-UNVERIFIABLE",
    "schema_version": "KNOWLEDGE_TRIAGE_RECORD_V1",
    "source_type": "ARTICLE",
    "source": {
      "title": "Synthetic fixture: unverifiable major fact",
      "capture_time": "2026-05-01T09:00:00Z",
      "content": {"content_kind": "AI_SUMMARY", "ai_summary": "Synthetic fixture."}
    },
    "category": "FINANCE",
    "value_assessment": {"value": "HIGH", "reason": "Synthetic fixture."},
    "quality_check": {"source_quality": "HIGH", "evidence_level": "A", "freshness": "CURRENT"},
    "duplication_check": {"result": "NEW", "comparison_complete": true, "corpus_available": true},
    "claims": {
      "source_facts": [
        {
          "claim_id": "F1",
          "text": "Synthetic fixture: an unverifiable major financial claim.",
          "claim_type": "SOURCE_FACT",
          "verified_external_evidence": "",
          "provenance": "synthetic",
          "evidence_level": "A",
          "verification_status": "UNVERIFIED",
          "captured_at": "2026-05-01T09:00:00Z"
        }
      ],
      "ai_abstractions": [],
      "decision_candidates": []
    },
    "promotion_decision": "PROMOTE_GOLDEN",
    "golden_reason": "Synthetic fixture: invalid Golden attempt.",
    "golden_eligibility": {
      "long_term_value": {"met": true, "rationale": "Synthetic fixture."},
      "evidence_quality": {"met": true, "rationale": "Synthetic fixture."},
      "verifiability": {"met": false, "rationale": "Synthetic fixture: major fact unverifiable."},
      "nonduplication": {"met": true, "rationale": "Synthetic fixture."},
      "personal_ai_utility": {"met": true, "rationale": "Synthetic fixture."},
      "traceable_provenance": {"met": true, "rationale": "Synthetic fixture."},
      "verified_source_fact_present": true
    },
    "human_review": {"required": true, "status": "PENDING", "gate_id": "HR-ADV-UNVERIFIABLE"},
    "review_output": {
      "triage_summary": "Synthetic fixture.",
      "decision": "REJECT.",
      "evidence": "Unverifiable major fact.",
      "next_action": "Reject."
    },
    "evaluation_time": "2026-05-01T09:05:00Z"
  }
}
```

## Test and evidence summary

Focused suite: `tests/test_knowledge_triage_layer_v1.py`.

It parses the embedded Draft 2020-12 schema and the four synthetic example
records, validates enum/required fields and the promotion guardrails, and
exercises the adversarial policy cases. If the optional `jsonschema` package is
importable it is used directly; otherwise the suite applies an explicit,
documented stdlib validator and records that honest coverage limitation. The
suite also runs semantic policy checks for the conditions JSON Schema cannot
prove (real provenance, source independence, dedup completeness, pure AI
inference, and the Human Review gate).

No canonical/DECISION/SKILL/Cloudflare/registry write or deployment is performed
by this layer or its tests.
