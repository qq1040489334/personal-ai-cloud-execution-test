"""Regression for document-only contracts: tests never expand the allowlist."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocumentScopeRegression(unittest.TestCase):
    def test_agent_instruction_conditions_test_writes_on_explicit_paths(self):
        workflow = (ROOT / ".github/workflows/agent-dispatch.yml").read_text()
        self.assertIn("add or update pytest tests only when their exact paths are explicitly listed in task.expected_files", workflow)
        self.assertIn("otherwise run existing tests and perform task-specific validation", workflow)
        self.assertIn("modify only paths explicitly listed in task.expected_files", workflow)
        self.assertIn("scripts/scope_guard.py", workflow)
        self.assertIn("python -m pytest -q", workflow)

    def test_document_only_passes_but_unlisted_test_still_fails(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            def git(*args):
                return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout
            git("init", "-q")
            git("config", "user.name", "regression")
            git("config", "user.email", "regression@example.com")
            (repo / "base.md").write_text("base")
            git("add", ".")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD").strip()
            contract = {"task_id": "regression-only", "expected_files": ["KNOWLEDGE_TRIAGE_LAYER_V1.md"]}
            # Put the contract outside the git worktree, as the workflow does.
            with tempfile.TemporaryDirectory() as ct:
                cp = Path(ct) / "task.json"
                cp.write_text(json.dumps(contract))
                def guard():
                    return subprocess.run([sys.executable, str(ROOT / "scripts/scope_guard.py"), base, str(cp)], cwd=repo, capture_output=True, text=True)
                (repo / "KNOWLEDGE_TRIAGE_LAYER_V1.md").write_text("# Triage")
                self.assertEqual(guard().returncode, 0)
                (repo / "tests").mkdir()
                (repo / "tests/test_knowledge_triage_layer_v1.py").write_text("def test_doc(): pass")
                failed = guard()
                self.assertEqual(failed.returncode, 1)
                self.assertIn("outside task allowlist: tests/test_knowledge_triage_layer_v1.py", failed.stdout)
                contract["expected_files"].append("tests/test_knowledge_triage_layer_v1.py")
                cp.write_text(json.dumps(contract))
                self.assertEqual(guard().returncode, 0)


if __name__ == "__main__":
    unittest.main()
