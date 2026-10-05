"""Gate 1 (``scripts/task_contract.py``) mode-aware contract tests.

Pins the readonly/write dual-mode contract:

* an explicit readonly task may declare ``expected_files = []``;
* write mode — and a missing ``mode``, which defaults to write — must declare a
  non-empty ``expected_files`` allowlist;
* forbidden / unsafe entries are still rejected in both modes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_CONTRACT_PATH = REPO_ROOT / "scripts" / "task_contract.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("task_contract_under_test", TASK_CONTRACT_PATH)
    assert spec and spec.loader, "cannot load scripts/task_contract.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


task_contract = _load_module()


def _base_contract(**overrides):
    contract = {
        "task_id": "cf-readonly-test",
        "goal": "exercise the readonly/write gate adaptation",
        "instructions": ["do the thing"],
        "risk_level": "LOW",
        "expected_files": ["scripts/task_contract.py"],
        "acceptance": ["the thing is done"],
    }
    contract.update(overrides)
    return contract


def test_all_required_fields_remain_mandatory() -> None:
    errors = task_contract.evaluate(_base_contract())
    assert errors == []

    incomplete = _base_contract()
    del incomplete["acceptance"]
    assert any("acceptance" in e for e in task_contract.evaluate(incomplete))


def test_rejects_non_low_medium_risk() -> None:
    assert any(
        "risk_level" in e for e in task_contract.evaluate(_base_contract(risk_level="HIGH"))
    )


def test_readonly_with_empty_expected_files_is_accepted() -> None:
    contract = _base_contract(mode="readonly", expected_files=[])
    assert task_contract.evaluate(contract) == []


@pytest.mark.parametrize("mode", ["readonly", "read_only", "read-only", "READONLY"])
def test_readonly_mode_aliases_accept_empty_allowlist(mode: str) -> None:
    contract = _base_contract(mode=mode, expected_files=[])
    assert task_contract.evaluate(contract) == []


def test_write_with_empty_expected_files_is_rejected() -> None:
    errors = task_contract.evaluate(_base_contract(mode="write", expected_files=[]))
    assert any("non-empty" in e for e in errors)


def test_missing_mode_defaults_to_write_and_rejects_empty() -> None:
    contract = _base_contract(expected_files=[])
    contract.pop("mode", None)
    assert task_contract.task_mode(contract) == "write"
    errors = task_contract.evaluate(contract)
    assert any("non-empty" in e for e in errors)


def test_missing_mode_defaults_to_write_with_non_empty_allowlist() -> None:
    contract = _base_contract()
    contract.pop("mode", None)
    assert task_contract.task_mode(contract) == "write"
    assert task_contract.evaluate(contract) == []


def test_unknown_mode_is_rejected() -> None:
    errors = task_contract.evaluate(_base_contract(mode="wildcard", expected_files=[]))
    assert any("mode not acceptable" in e for e in errors)


def test_readonly_still_rejects_forbidden_and_unsafe_entries() -> None:
    forbidden = _base_contract(mode="readonly", expected_files=[".github/workflows/agent.yml"])
    assert any("forbidden" in e for e in task_contract.evaluate(forbidden))

    unsafe = _base_contract(mode="readonly", expected_files=["../escape.py"])
    assert any("unsafe" in e for e in task_contract.evaluate(unsafe))


def test_write_non_empty_allowlist_is_preserved() -> None:
    contract = _base_contract(
        mode="write", expected_files=["scripts/task_contract.py", "tests/test_task_contract.py"]
    )
    assert task_contract.evaluate(contract) == []
