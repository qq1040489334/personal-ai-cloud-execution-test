"""Gate 2 (``scripts/scope_guard.py``) mode-aware scope-enforcement tests.

Proves the readonly half of the dual-mode contract: an explicitly readonly
contract with ``expected_files = []`` passes the contract load and then **fails
closed** the moment any file changes, while write mode (and a missing mode,
which defaults to write) still requires a non-empty allowlist and still enforces
the changed-files allowlist.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCOPE_GUARD_PATH = REPO_ROOT / "scripts" / "scope_guard.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("scope_guard_under_test", SCOPE_GUARD_PATH)
    assert spec and spec.loader, "cannot load scripts/scope_guard.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scope_guard = _load_module()


# --- pure mode/allowlist resolution ---------------------------------------


def test_task_mode_defaults_to_write() -> None:
    assert scope_guard.task_mode({}) == "write"
    assert scope_guard.task_mode({"mode": None}) == "write"


@pytest.mark.parametrize("mode", ["readonly", "read_only", "read-only", "READONLY"])
def test_task_mode_recognizes_readonly(mode: str) -> None:
    assert scope_guard.task_mode({"mode": mode}) == "readonly"


def test_task_mode_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        scope_guard.task_mode({"mode": "wildcard"})


def test_resolve_allowlist_readonly_empty_is_allowed() -> None:
    assert scope_guard.resolve_allowlist({"mode": "readonly", "expected_files": []}) == set()


def test_resolve_allowlist_write_empty_is_rejected() -> None:
    with pytest.raises(ValueError):
        scope_guard.resolve_allowlist({"mode": "write", "expected_files": []})


def test_resolve_allowlist_missing_mode_empty_is_rejected() -> None:
    with pytest.raises(ValueError):
        scope_guard.resolve_allowlist({"expected_files": []})


def test_resolve_allowlist_preserves_write_allowlist() -> None:
    allow = scope_guard.resolve_allowlist(
        {"mode": "write", "expected_files": ["scripts/scope_guard.py"]}
    )
    assert allow == {"scripts/scope_guard.py"}


# --- end-to-end guard execution in a scratch git repo ----------------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _run_guard(repo: Path, contract: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCOPE_GUARD_PATH), "HEAD", str(contract_path)],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_readonly_empty_allowlist_passes_with_no_changes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    proc = _run_guard(repo, {"mode": "readonly", "expected_files": []}, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS" in proc.stdout


def test_readonly_empty_allowlist_blocks_any_changed_file(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    proc = _run_guard(repo, {"mode": "readonly", "expected_files": []}, tmp_path)
    assert proc.returncode == 1
    assert "modification outside task allowlist: tracked.txt" in proc.stdout


def test_readonly_empty_allowlist_blocks_any_new_file(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    proc = _run_guard(repo, {"mode": "readonly", "expected_files": []}, tmp_path)
    assert proc.returncode == 1
    assert "new file outside task allowlist: new.txt" in proc.stdout


def test_write_empty_allowlist_is_rejected(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    proc = _run_guard(repo, {"mode": "write", "expected_files": []}, tmp_path)
    assert proc.returncode == 1
    assert "non-empty" in proc.stdout


def test_missing_mode_empty_allowlist_is_rejected(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    proc = _run_guard(repo, {"expected_files": []}, tmp_path)
    assert proc.returncode == 1
    assert "non-empty" in proc.stdout


def test_write_allowlist_blocks_change_outside_it(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "allowed.txt").write_text("allowed\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    proc = _run_guard(
        repo, {"mode": "write", "expected_files": ["allowed.txt"]}, tmp_path
    )
    assert proc.returncode == 1
    assert "modification outside task allowlist: tracked.txt" in proc.stdout


def test_write_allowlist_permits_listed_change(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    proc = _run_guard(
        repo, {"mode": "write", "expected_files": ["tracked.txt"]}, tmp_path
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS" in proc.stdout
