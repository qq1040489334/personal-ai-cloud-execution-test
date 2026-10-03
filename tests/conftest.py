"""Ensure the canonical ``src`` package is importable in tests.

This also contains a single, transparent compatibility shim for the kernel's
per-argument limit (``MAX_ARG_STRLEN``, 128 KiB). Several suites execute the
production Worker bundle with ``node --input-type=module -e <bundle+probe>``.
As the Worker gains features the bundle no longer fits in a single argv string,
which raises ``OSError: [Errno 7] Argument list too long`` before Node even
starts. The shim spills that combined script to a temporary ``.mjs`` module
file instead, so every Node-backed regression suite keeps executing the real
production source unmodified.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_ORIGINAL_RUN = subprocess.run


def _spill_node_eval(argv):
    args = list(argv)
    if not args or os.path.basename(str(args[0])) not in {"node", "node.exe"}:
        return None
    if "-e" not in args:
        return None
    index = args.index("-e")
    if index + 1 >= len(args):
        return None
    script = args[index + 1]
    remainder = args[index + 2 :]
    handle, path = tempfile.mkstemp(suffix=".mjs", prefix="worker_probe_")
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(script)
    return [args[0], path, *remainder], path


def _patched_run(*args, **kwargs):
    if args and isinstance(args[0], (list, tuple)):
        spilled = _spill_node_eval(args[0])
        if spilled is not None:
            new_argv, path = spilled
            try:
                return _ORIGINAL_RUN(new_argv, *args[1:], **kwargs)
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
    return _ORIGINAL_RUN(*args, **kwargs)


subprocess.run = _patched_run
