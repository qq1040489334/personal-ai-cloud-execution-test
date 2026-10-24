"""Focused synthetic redirect regression; no outbound requests."""
from pathlib import Path
import subprocess

def test_observation_redirect_regression():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(["node", "tests/observation_redirect_regression.mjs"], cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
