"""Regression suite for PERSONAL_AI_KNOWLEDGE_TRIAGE_LAYER_V1.

The triage layer is analysis/classification only. These tests pin the
machine-readable contract in ``KNOWLEDGE_TRIAGE_LAYER_V1.md``:

* the embedded JSON Schema (Draft 2020-12) is parseable and carries the exact
  enums and required fields;
* the four synthetic example records (PROMOTE_GOLDEN / KEEP / ARCHIVE / REJECT)
  validate against it and carry the four-section review output;
* the promotion guardrails (non-LOW quality, non-DUPLICATE, evidence A/B,
  verified source fact, Human Review gate, unavailable-corpus block, STALE
  exception) hold;
* the adversarial cases are rejected;
* the layer performs no canonical/DECISION/SKILL/Cloudflare/registry write or
  deployment.

``jsonschema`` is optional. When it is importable it is used directly; otherwise
an explicit, documented stdlib validator covers the subset of Draft 2020-12 the
document actually uses (``type``, ``required``, ``enum``, ``const``,
``properties``, ``additionalProperties``, ``minLength``, ``minItems``, ``items``,
``anyOf``, ``allOf``, ``if``/``then``/``not`` and local ``$ref``). ``format`` is
intentionally not enforced by the stdlib path -- an honest coverage limitation
recorded by ``stdlib_validator_covers``.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "KNOWLEDGE_TRIAGE_LAYER_V1.md"

try:  # optional dependency; the layer must not require it
    import jsonschema  # type: ignore

    HAS_JSONSCHEMA = True
except Exception:  # pragma: no cover - exercised on hosts without jsonschema
    jsonschema = None  # type: ignore
    HAS_JSONSCHEMA = False

STDLIB_VALIDATOR_COVERS = (
    "type",
    "required",
    "enum",
    "const",
    "properties",
    "additionalProperties",
    "minLength",
    "minItems",
    "items",
    "anyOf",
    "allOf",
    "if/then",
    "not",
    "$ref",
)

VALUE_ENUM = ["HIGH", "MEDIUM", "LOW"]
SOURCE_QUALITY_ENUM = ["HIGH", "MEDIUM", "LOW"]
EVIDENCE_ENUM = ["A", "B", "C", "UNKNOWN"]
FRESHNESS_ENUM = ["CURRENT", "AGING", "STALE"]
DUP_ENUM = ["NEW", "SIMILAR", "DUPLICATE"]
PROMOTION_ENUM = ["KEEP", "PROMOTE_GOLDEN", "ARCHIVE", "REJECT"]
CATEGORY_ENUM = [
    "AI_TECHNOLOGY",
    "PERSONAL_AI",
    "FINANCE",
    "BUSINESS",
    "LIFE_DECISION",
    "SKILL",
    "TOOL",
    "OTHER",
]
SOURCE_TYPE_ENUM = ["VIDEO", "ARTICLE", "BOOK", "GITHUB", "OTHER"]
REQUIRED_FIELDS = {
    "id",
    "source",
    "source_type",
    "category",
    "value_assessment",
    "quality_check",
    "duplication_check",
    "promotion_decision",
}


# ---------------------------------------------------------------------------
# Markdown / JSON extraction
# ---------------------------------------------------------------------------


def read_doc() -> str:
    assert DOC_PATH.is_file(), "KNOWLEDGE_TRIAGE_LAYER_V1.md must exist"
    return DOC_PATH.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    """Collapse hard line wraps so phrase checks are not layout-sensitive."""
    return re.sub(r"\s+", " ", text)


def sections(text: str) -> dict[str, str]:
    """Split the document into top-level ``## `` sections."""
    out: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                out[current] = "\n".join(buf)
            current = line[3:].strip()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf)
    return out


def json_blocks(section_text: str) -> list:
    raw = re.findall(r"```json\n(.*?)\n```", section_text, re.S)
    return [json.loads(block) for block in raw]


def load_schema() -> dict:
    return json_blocks(sections(read_doc())["Schema"])[0]


def load_examples() -> list[dict]:
    return json_blocks(sections(read_doc())["Examples"])


def load_adversarial() -> list[dict]:
    return json_blocks(sections(read_doc())["Adversarial Cases"])


# ---------------------------------------------------------------------------
# Minimal stdlib validator (Draft 2020-12 subset used by the document)
# ---------------------------------------------------------------------------


def _resolve_ref(root: dict, ref: str) -> dict:
    assert ref.startswith("#/")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _type_ok(expected, value) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        if name == "object" and isinstance(value, dict):
            return True
        if name == "array" and isinstance(value, list):
            return True
        if name == "string" and isinstance(value, str):
            return True
        if name == "boolean" and isinstance(value, bool):
            return True
        if name == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if name == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if name == "null" and value is None:
            return True
    return False


def validate(schema: dict, instance, path: str = "$", root: dict | None = None) -> list[str]:
    """Return a list of human-readable errors (empty means valid)."""
    if root is None:
        root = schema
    errors: list[str] = []

    if "$ref" in schema:
        return validate(_resolve_ref(root, schema["$ref"]), instance, path, root)

    if "type" in schema and not _type_ok(schema["type"], instance):
        errors.append(f"{path}: expected type {schema['type']}, got {type(instance).__name__}")
        return errors

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in enum {schema['enum']}")

    if isinstance(instance, str) and "minLength" in schema and len(instance) < schema["minLength"]:
        errors.append(f"{path}: string shorter than minLength {schema['minLength']}")

    if isinstance(instance, list) and "minItems" in schema and len(instance) < schema["minItems"]:
        errors.append(f"{path}: array shorter than minItems {schema['minItems']}")

    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(f"{path}: missing required field {name!r}")
        props = schema.get("properties", {})
        for name, subschema in props.items():
            if name in instance:
                errors.extend(validate(subschema, instance[name], f"{path}.{name}", root))
        additional = schema.get("additionalProperties", True)
        if additional is False:
            for name in instance:
                if name not in props:
                    errors.append(f"{path}: additional property {name!r} is not allowed")
        elif isinstance(additional, dict):
            for name in instance:
                if name not in props:
                    errors.extend(validate(additional, instance[name], f"{path}.{name}", root))

    if isinstance(instance, list) and "items" in schema:
        for index, item in enumerate(instance):
            errors.extend(validate(schema["items"], item, f"{path}[{index}]", root))

    if "anyOf" in schema:
        if not any(not validate(sub, instance, path, root) for sub in schema["anyOf"]):
            errors.append(f"{path}: does not match any anyOf branch")

    if "allOf" in schema:
        for sub in schema["allOf"]:
            errors.extend(validate(sub, instance, path, root))

    if "not" in schema:
        if not validate(schema["not"], instance, path, root):
            errors.append(f"{path}: matched a forbidden 'not' schema")

    if "if" in schema:
        if not validate(schema["if"], instance, path, root):
            if "then" in schema:
                errors.extend(validate(schema["then"], instance, path, root))
            elif "else" in schema:
                errors.extend(validate(schema["else"], instance, path, root))

    return errors


def schema_errors(schema: dict, record: dict) -> list[str]:
    """Validate using jsonschema when available, else the stdlib validator."""
    if HAS_JSONSCHEMA:
        validator = jsonschema.Draft202012Validator(schema)
        return [f"{list(e.path)}: {e.message}" for e in validator.iter_errors(record)]
    return validate(schema, record)


# ---------------------------------------------------------------------------
# Semantic policy checks (what JSON Schema cannot prove)
# ---------------------------------------------------------------------------


def semantic_violations(record: dict) -> list[str]:
    """Check the truth/provenance/gate conditions schema cannot verify."""
    violations: list[str] = []
    decision = record.get("promotion_decision")
    golden = decision == "PROMOTE_GOLDEN"

    if golden:
        if not record.get("golden_reason"):
            violations.append("golden requires a non-empty golden_reason")
        quality = record.get("quality_check", {})
        if quality.get("source_quality") == "LOW":
            violations.append("LOW source quality must never be Golden")
        if quality.get("evidence_level") not in ("A", "B"):
            violations.append("Golden requires evidence level A or B")
        dup = record.get("duplication_check", {})
        if dup.get("result") == "DUPLICATE":
            violations.append("DUPLICATE material must never be Golden")
        if dup.get("comparison_complete") is not True or dup.get("corpus_available") is not True:
            violations.append("unavailable/incomplete dedup corpus blocks promotion")
        if quality.get("freshness") == "STALE":
            exception = record.get("historical_value_exception")
            if not exception or exception.get("used") is not True:
                violations.append("STALE Golden requires an explicit historical_value_exception")
        review = record.get("human_review", {})
        if review.get("required") is not True:
            violations.append("promotion requires human_review.required == true")
        if review.get("status") != "PENDING":
            violations.append("promotion requires human_review.status == PENDING")
        facts = record.get("claims", {}).get("source_facts", [])
        verified = [f for f in facts if f.get("verification_status") == "VERIFIED"]
        if not verified:
            violations.append("Golden requires at least one VERIFIED source_fact")
        for fact in verified:
            if "locator" not in fact and "verified_external_evidence" not in fact:
                violations.append("a VERIFIED source_fact needs a locator or verified external evidence")
        eligibility = record.get("golden_eligibility", {})
        for criterion in (
            "long_term_value",
            "evidence_quality",
            "verifiability",
            "nonduplication",
            "personal_ai_utility",
            "traceable_provenance",
        ):
            if eligibility.get(criterion, {}).get("met") is not True:
                violations.append(f"Golden criterion not met: {criterion}")
        if eligibility.get("verified_source_fact_present") is not True:
            violations.append("Golden requires verified_source_fact_present == true")
    else:
        if "golden_reason" in record:
            violations.append("golden_reason must be absent for non-Golden decisions")

    for candidate in record.get("claims", {}).get("decision_candidates", []):
        if candidate.get("auto_executed") is not False:
            violations.append("decision candidates must never auto-execute a DECISION write")

    return violations


def accepted_by_schema_and_policy(schema: dict, record: dict) -> bool:
    return not schema_errors(schema, record) and not semantic_violations(record)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def schema() -> dict:
    return load_schema()


@pytest.fixture(scope="module")
def examples() -> list[dict]:
    return load_examples()


@pytest.fixture(scope="module")
def adversarial() -> list[dict]:
    return load_adversarial()


def golden_fixture() -> dict:
    """A deep copy of the valid PROMOTE_GOLDEN example."""
    for record in load_examples():
        if record.get("promotion_decision") == "PROMOTE_GOLDEN":
            return copy.deepcopy(record)
    raise AssertionError("no PROMOTE_GOLDEN example found")


# ---------------------------------------------------------------------------
# Schema contract
# ---------------------------------------------------------------------------


def test_schema_block_present_and_is_draft_2020_12(schema: dict) -> None:
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "KNOWLEDGE_TRIAGE_RECORD_V1"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False


def test_schema_requires_the_named_fields(schema: dict) -> None:
    assert REQUIRED_FIELDS.issubset(set(schema["required"]))


def test_schema_enum_values_are_exact(schema: dict) -> None:
    props = schema["properties"]
    assert props["source_type"]["enum"] == SOURCE_TYPE_ENUM
    assert props["category"]["enum"] == CATEGORY_ENUM
    assert props["value_assessment"]["properties"]["value"]["enum"] == VALUE_ENUM
    quality = props["quality_check"]["properties"]
    assert quality["source_quality"]["enum"] == SOURCE_QUALITY_ENUM
    assert quality["evidence_level"]["enum"] == EVIDENCE_ENUM
    assert quality["freshness"]["enum"] == FRESHNESS_ENUM
    assert props["duplication_check"]["properties"]["result"]["enum"] == DUP_ENUM
    assert props["promotion_decision"]["enum"] == PROMOTION_ENUM


def test_claim_arrays_are_separate_and_discriminated(schema: dict) -> None:
    claim_props = schema["properties"]["claims"]["properties"]
    assert set(claim_props) == {"source_facts", "ai_abstractions", "decision_candidates"}
    fact_item = claim_props["source_facts"]["items"]
    abstraction_item = claim_props["ai_abstractions"]["items"]
    candidate_item = claim_props["decision_candidates"]["items"]
    assert fact_item["properties"]["claim_type"]["const"] == "SOURCE_FACT"
    assert abstraction_item["properties"]["claim_type"]["const"] == "AI_ABSTRACTION"
    assert candidate_item["properties"]["claim_type"]["const"] == "DECISION_CANDIDATE"
    assert "anyOf" in fact_item
    assert "evidence_level" not in abstraction_item["properties"]
    assert candidate_item["properties"]["auto_executed"]["const"] is False


def test_doc_documents_required_governance_sections() -> None:
    text = read_doc()
    for token in (
        "KNOWLEDGE_TRIAGE_RECORD_V1",
        "SOURCE_FACT",
        "AI_ABSTRACTION",
        "DECISION_CANDIDATE",
        "PROMOTE_GOLDEN",
        "Human Review",
        "historical_value_exception",
        "deduplication",
        "freshness",
        "evidence",
    ):
        assert token in text


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------


def test_four_examples_with_all_decisions(examples: list[dict]) -> None:
    assert len(examples) == 4
    decisions = {record["promotion_decision"] for record in examples}
    assert decisions == set(PROMOTION_ENUM)


def test_all_examples_validate_against_schema(schema: dict, examples: list[dict]) -> None:
    for record in examples:
        assert schema_errors(schema, record) == [], f"{record['id']} failed schema"


def test_all_examples_have_no_semantic_violations(examples: list[dict]) -> None:
    for record in examples:
        assert semantic_violations(record) == [], f"{record['id']} failed policy"


def test_examples_are_labelled_synthetic() -> None:
    text = read_doc()
    assert "synthetic fixtures" in text.lower()
    assert "not claims of live external verification" in text


def test_each_example_has_four_part_review_output(examples: list[dict]) -> None:
    for record in examples:
        output = record["review_output"]
        assert set(output) == {"triage_summary", "decision", "evidence", "next_action"}
        for value in output.values():
            assert value.strip()


def test_golden_example_carries_human_review_gate(examples: list[dict]) -> None:
    golden = [r for r in examples if r["promotion_decision"] == "PROMOTE_GOLDEN"]
    assert golden, "a PROMOTE_GOLDEN example is required"
    review = golden[0]["human_review"]
    assert review["required"] is True
    assert review["status"] == "PENDING"
    assert review["gate_id"]


def test_non_golden_examples_omit_golden_reason(examples: list[dict]) -> None:
    for record in examples:
        if record["promotion_decision"] != "PROMOTE_GOLDEN":
            assert "golden_reason" not in record


# ---------------------------------------------------------------------------
# Adversarial / policy cases
# ---------------------------------------------------------------------------


def test_adversarial_cases_cover_required_scenarios(adversarial: list[dict]) -> None:
    cases = {entry["case"] for entry in adversarial}
    assert {
        "pure_ai_inference_only",
        "low_source_quality",
        "duplicate_material",
        "stale_without_historical_exception",
        "unavailable_dedup_corpus",
        "unverifiable_major_fact",
    }.issubset(cases)


@pytest.mark.parametrize(
    "case_name",
    [
        "pure_ai_inference_only",
        "low_source_quality",
        "duplicate_material",
        "stale_without_historical_exception",
        "unavailable_dedup_corpus",
        "unverifiable_major_fact",
    ],
)
def test_each_adversarial_case_is_rejected(schema: dict, adversarial: list[dict], case_name: str) -> None:
    entry = next(c for c in adversarial if c["case"] == case_name)
    record = entry["record"]
    assert not accepted_by_schema_and_policy(schema, record), case_name


def test_ai_only_inference_cannot_golden(schema: dict, adversarial: list[dict]) -> None:
    record = next(c for c in adversarial if c["case"] == "pure_ai_inference_only")["record"]
    assert record["claims"]["source_facts"] == []
    assert schema_errors(schema, record)  # minItems 1 violations
    assert any("VERIFIED source_fact" in v for v in semantic_violations(record))


def test_low_quality_cannot_golden(schema: dict, adversarial: list[dict]) -> None:
    record = next(c for c in adversarial if c["case"] == "low_source_quality")["record"]
    assert record["quality_check"]["source_quality"] == "LOW"
    assert schema_errors(schema, record)
    assert any("LOW source quality" in v for v in semantic_violations(record))


def test_duplicate_cannot_golden(schema: dict, adversarial: list[dict]) -> None:
    record = next(c for c in adversarial if c["case"] == "duplicate_material")["record"]
    assert record["duplication_check"]["result"] == "DUPLICATE"
    assert schema_errors(schema, record)
    assert any("DUPLICATE" in v for v in semantic_violations(record))


def test_stale_without_exception_cannot_golden(schema: dict, adversarial: list[dict]) -> None:
    record = next(
        c for c in adversarial if c["case"] == "stale_without_historical_exception"
    )["record"]
    assert record["quality_check"]["freshness"] == "STALE"
    assert schema_errors(schema, record)
    assert any("historical_value_exception" in v for v in semantic_violations(record))


def test_unavailable_corpus_blocks_promotion(schema: dict, adversarial: list[dict]) -> None:
    record = next(c for c in adversarial if c["case"] == "unavailable_dedup_corpus")["record"]
    assert record["duplication_check"]["comparison_complete"] is False
    assert record["duplication_check"]["corpus_available"] is False
    assert schema_errors(schema, record)
    assert any("corpus" in v for v in semantic_violations(record))


def test_unverifiable_major_fact_cannot_golden(schema: dict, adversarial: list[dict]) -> None:
    record = next(c for c in adversarial if c["case"] == "unverifiable_major_fact")["record"]
    assert record["golden_eligibility"]["verifiability"]["met"] is False
    assert schema_errors(schema, record)
    assert any("verifiability" in v for v in semantic_violations(record))


# ---------------------------------------------------------------------------
# Structural guardrails exercised on mutations
# ---------------------------------------------------------------------------


def test_promote_golden_requires_golden_reason(schema: dict) -> None:
    record = golden_fixture()
    del record["golden_reason"]
    assert schema_errors(schema, record)


def test_non_golden_forbids_golden_reason(schema: dict) -> None:
    record = golden_fixture()
    record["promotion_decision"] = "KEEP"
    assert schema_errors(schema, record)


def test_golden_requires_evidence_a_or_b(schema: dict) -> None:
    record = golden_fixture()
    record["quality_check"]["evidence_level"] = "C"
    assert schema_errors(schema, record)


def test_golden_requires_medium_or_better_quality(schema: dict) -> None:
    record = golden_fixture()
    record["quality_check"]["source_quality"] = "LOW"
    assert schema_errors(schema, record)


def test_golden_requires_verified_source_fact(schema: dict) -> None:
    record = golden_fixture()
    record["claims"]["source_facts"] = []
    assert schema_errors(schema, record)


def test_golden_requires_verified_source_fact_flag(schema: dict) -> None:
    record = golden_fixture()
    record["golden_eligibility"]["verified_source_fact_present"] = False
    assert schema_errors(schema, record)


def test_golden_requires_all_eligibility_criteria_met(schema: dict) -> None:
    record = golden_fixture()
    record["golden_eligibility"]["verifiability"]["met"] = False
    assert schema_errors(schema, record)


def test_golden_requires_complete_comparison(schema: dict) -> None:
    record = golden_fixture()
    record["duplication_check"]["comparison_complete"] = False
    assert schema_errors(schema, record)


def test_golden_requires_corpus_available(schema: dict) -> None:
    record = golden_fixture()
    record["duplication_check"]["corpus_available"] = False
    assert schema_errors(schema, record)


def test_stale_golden_requires_exception(schema: dict) -> None:
    record = golden_fixture()
    record["quality_check"]["freshness"] = "STALE"
    record.pop("historical_value_exception", None)
    assert schema_errors(schema, record)


def test_stale_golden_with_exception_is_structurally_allowed(schema: dict) -> None:
    record = golden_fixture()
    record["quality_check"]["freshness"] = "STALE"
    record["historical_value_exception"] = {
        "used": True,
        "historical_scope": "synthetic fixture: period-accurate reference",
        "evidence": "synthetic fixture: verified archive copy",
        "review_required": True,
    }
    assert schema_errors(schema, record) == []


def test_similar_golden_requires_net_new_claims(schema: dict) -> None:
    record = golden_fixture()
    record["duplication_check"]["result"] = "SIMILAR"
    record["duplication_check"].pop("net_new_claims", None)
    assert schema_errors(schema, record)

    record["duplication_check"]["net_new_claims"] = ["synthetic net-new claim"]
    assert schema_errors(schema, record) == []


def test_golden_requires_human_review_required_true(schema: dict) -> None:
    record = golden_fixture()
    record["human_review"]["required"] = False
    assert schema_errors(schema, record)


def test_golden_requires_pending_human_review_status(schema: dict) -> None:
    record = golden_fixture()
    record["human_review"]["status"] = "APPROVED"
    assert schema_errors(schema, record)


def test_source_fact_needs_locator_or_verified_external_evidence(schema: dict) -> None:
    record = golden_fixture()
    fact = record["claims"]["source_facts"][0]
    fact.pop("locator", None)
    fact.pop("verified_external_evidence", None)
    assert schema_errors(schema, record)


def test_ai_abstraction_cannot_carry_an_evidence_level(schema: dict) -> None:
    record = golden_fixture()
    record["claims"]["ai_abstractions"][0]["evidence_level"] = "A"
    assert schema_errors(schema, record)


def test_source_fact_cannot_be_claim_type_abstraction(schema: dict) -> None:
    record = golden_fixture()
    record["claims"]["source_facts"][0]["claim_type"] = "AI_ABSTRACTION"
    assert schema_errors(schema, record)


def test_decision_candidate_must_not_auto_execute(schema: dict) -> None:
    record = golden_fixture()
    record["claims"]["decision_candidates"][0]["auto_executed"] = True
    assert schema_errors(schema, record)
    assert any("auto-execute" in v for v in semantic_violations(record))


def test_golden_reason_must_be_nonempty(schema: dict) -> None:
    record = golden_fixture()
    record["golden_reason"] = ""
    assert schema_errors(schema, record)


def test_missing_required_top_level_field_is_invalid(schema: dict) -> None:
    for field in REQUIRED_FIELDS:
        record = golden_fixture()
        del record[field]
        assert schema_errors(schema, record), field


# ---------------------------------------------------------------------------
# Scope / advisory guarantees
# ---------------------------------------------------------------------------


def test_promotion_is_advisory_with_human_review_gate() -> None:
    text = read_doc()
    lowered = text.lower()
    assert "advisory" in lowered
    assert "human review gate" in lowered
    assert "never" in lowered
    assert "pending" in lowered


def test_doc_declares_no_canonical_or_production_writes() -> None:
    text = read_doc()
    for token in (
        "Canonical KNOWLEDGE",
        "DECISION",
        "SKILL",
        "Cloudflare Canonical",
        "Skill Registry",
        "production deployment",
    ):
        assert token in text
    assert "Never" in text
    assert "no canonical/decision/skill/cloudflare" in normalized(text).lower()


def test_doc_lists_semantic_checks_schema_cannot_prove() -> None:
    text = normalized(read_doc())
    assert "Semantic checks" in text
    assert "cannot verify truth" in text


def test_stdlib_validator_coverage_is_documented_and_works(schema: dict) -> None:
    if HAS_JSONSCHEMA:
        assert schema_errors(schema, golden_fixture()) == []
    else:
        assert set(STDLIB_VALIDATOR_COVERS)  # documented subset
        assert validate(schema, golden_fixture()) == []
        bad = golden_fixture()
        del bad["promotion_decision"]
        assert validate(schema, bad)


def test_adversarial_cases_are_labelled_synthetic() -> None:
    text = read_doc()
    assert "Adversarial Cases" in text
    assert "synthetic fixtures" in text.lower()
