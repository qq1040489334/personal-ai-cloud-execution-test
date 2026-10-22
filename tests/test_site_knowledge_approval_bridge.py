"""Run actual Site/Worker/D1-binding contracts on isolated local SQLite only."""
import shutil
import subprocess
from pathlib import Path

def test_site_worker_knowledge_approval_contracts():
    node = shutil.which("node")
    assert node, "Node >=22.13 is required for the isolated SQLite contract suite"
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([node, "--test", "site/tests/knowledge-approval-bridge.mjs"],
                            cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
