"""Run the actual observation and production scope regressions in normal CI."""
import subprocess
from pathlib import Path

def test_observation_and_scope_regressions():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(['node', '--test', 'tests/test_task_execution_status.cjs',
        'tests/test_early_task_run.cjs', 'tests/test_production_compat.cjs'],
        cwd=root, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
