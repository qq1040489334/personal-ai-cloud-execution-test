import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path


REPO = Path(__file__).resolve().parent
GENERATOR = REPO / "scripts" / "build_execution_result.py"


def run_generator(tmp_path, agent_result):
    task_path = tmp_path / "task.json"
    agent_path = tmp_path / "agent_result.json"
    output_path = tmp_path / "execution_result.json"
    task_path.write_text(
        json.dumps({"task_id": "parent-contract-001", "goal": "Preserve Agent evidence"}),
        encoding="utf-8",
    )
    agent_path.write_text(json.dumps(agent_result), encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            str(task_path),
            "HEAD",
            "566 passed",
            str(output_path),
            str(agent_path),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_production_generator_preserves_unknown_agent_result_fields(tmp_path):
    agent_result = {
        "final_status": "BLOCKED_EVIDENCE_MISSING",
        "parent_task_id": "parent-001",
        "child_task_id": None,
        "production_evidence": {"exactly_once": False},
        "audit": {"d1_mutations": 0},
        "future_unknown_field": {"test": True},
    }

    result = run_generator(tmp_path, agent_result)

    for key, value in agent_result.items():
        assert result[key] == value
    assert result["status"] == "success"
    assert result["task_id"] == "parent-contract-001"
    assert result["commit"]
    assert result["tests"] == "566 passed"
    assert isinstance(result["changed_files"], list)
    assert result["summary"] == "Preserve Agent evidence"


def test_compatibility_metadata_wins_agent_field_collisions(tmp_path):
    result = run_generator(
        tmp_path,
        {
            "status": "failure",
            "task_id": "agent-task-id",
            "commit": "agent-commit",
            "tests": "agent test claim",
            "changed_files": ["agent.py"],
            "summary": "agent summary",
            "future_unknown_field": True,
        },
    )

    assert result["status"] == "success"
    assert result["task_id"] == "parent-contract-001"
    assert result["commit"] != "agent-commit"
    assert result["tests"] == "566 passed"
    assert result["changed_files"] != ["agent.py"]
    assert result["summary"] == "Preserve Agent evidence"
    assert result["future_unknown_field"] is True
    assert result["agent_result"]["status"] == "failure"
    assert result["agent_result"]["summary"] == "agent summary"


def test_missing_or_malformed_agent_result_cannot_publish_success(tmp_path):
    task_path = tmp_path / "task.json"
    output_path = tmp_path / "execution_result.json"
    task_path.write_text(json.dumps({"task_id": "parent-001"}), encoding="utf-8")
    agent_path = tmp_path / "agent_result.json"

    for content in (None, "not-json"):
        output_path.unlink(missing_ok=True)
        if content is None:
            agent_path.unlink(missing_ok=True)
        else:
            agent_path.write_text(content, encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                str(task_path),
                "HEAD",
                "tests passed",
                str(output_path),
                str(agent_path),
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert not output_path.exists()


def test_workflow_failure_fallback_retains_failure_diagnostics(tmp_path):
    workflow = (REPO / ".github" / "workflows" / "agent-dispatch.yml").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"python - \"\$RUNNER_TEMP/task\.json\".*?<<'PY'\n(?P<script>.*?)\n\s+PY",
        workflow,
        re.DOTALL,
    )
    assert match, "failure fallback Python block must remain present"
    task_path = tmp_path / "task.json"
    output_path = tmp_path / "execution_result.json"
    task_path.write_text(json.dumps({"task_id": "parent-001"}), encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(match.group("script")),
            str(task_path),
            str(output_path),
            "failure",
            "failure",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["failure_stage"] == "push"
    assert result["job_status"] == "failure"
    assert result["push_outcome"] == "failure"
