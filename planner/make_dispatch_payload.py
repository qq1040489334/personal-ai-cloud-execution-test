"""Build the repository_dispatch payload from a task contract.

Run: python planner/make_dispatch_payload.py <contract.json> <out_payload.json>
"""

from __future__ import annotations

import json
import sys

EVENT_TYPE = "gpt_task"


def main() -> int:
    contract_path, out_path = sys.argv[1:3]
    contract = json.loads(open(contract_path, encoding="utf-8").read())
    payload = {"event_type": EVENT_TYPE, "client_payload": {"task": contract}}
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out_path} (event_type={EVENT_TYPE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
