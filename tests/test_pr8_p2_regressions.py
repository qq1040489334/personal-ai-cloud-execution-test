"""Actual maintained code, synthetic Human Gate and isolated SQLite only."""
import shutil
import subprocess
from pathlib import Path

def test_pr8_p2_security_regressions():
    node = shutil.which('node')
    assert node
    result = subprocess.run([node, '--test', 'site/tests/pr8-p2-regressions.mjs'],
                            cwd=Path(__file__).resolve().parents[1], capture_output=True,
                            text=True, encoding='utf-8', timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
