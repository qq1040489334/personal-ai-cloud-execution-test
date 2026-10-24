"""Run the focused, synthetic workflow-read diagnostics checks in normal CI."""
from pathlib import Path
import subprocess


def test_observation_diagnostics():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["node", "--test", "tests/diagnostics.test.mjs"],
        cwd=root, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
