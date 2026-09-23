"""Phase 2 — simulated GPT Planner (no real GPT API).

Takes a fixed natural-language input and emits a structured task contract
following `task_contract_v0.json`. Deterministic by design: this is a stand-in
for the GPT planning step, not a general planner.

Run: python planner/planner_sim.py [--out task_contract_v0.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

#: The fixed natural-language input for this verification.
NL_INPUT = "Add function gpt_bridge_test() to hello.py and add pytest."

#: The structured contract the simulated planner produces from NL_INPUT.
CONTRACT = {
    "task_id": "gpt-bridge-001",
    "goal": NL_INPUT,
    "instructions": [
        "In hello.py add a function gpt_bridge_test that returns the string 'gpt bridge ok'.",
        "Add a pytest test for it in test_hello.py.",
        "Run python -m pytest -q and commit.",
    ],
    "risk_level": "LOW",
    "expected_files": ["hello.py", "test_hello.py"],
    "acceptance": [
        "gpt_bridge_test exists in hello.py and returns 'gpt bridge ok'",
        "test_hello.py contains a test for gpt_bridge_test",
        "python -m pytest -q passes",
    ],
}


def plan(nl_input: str) -> dict:
    """Return a structured contract for the fixed input (deterministic)."""
    if nl_input.strip() != NL_INPUT:
        raise SystemExit(
            "planner_sim is a fixed stand-in; unexpected input. "
            f"expected {NL_INPUT!r}"
        )
    return dict(CONTRACT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="task_contract_v0.json")
    args = parser.parse_args()

    contract = plan(NL_INPUT)
    Path(args.out).write_text(
        json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("=== SIMULATED GPT PLANNER ===")
    print(f"NL input: {NL_INPUT}")
    print(f"structured task written to: {args.out}")
    print(json.dumps(contract, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
