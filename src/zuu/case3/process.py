"""Default subprocess boundary for Git-ignore operations."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from . import GitIgnoreError, ProcessResult


def run_process(argv: Sequence[str], cwd: Path) -> ProcessResult:
    """Run one command without a shell and return captured decoded output."""
    try:
        completed = subprocess.run(
            tuple(argv),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
    except OSError as error:
        raise GitIgnoreError(f"process could not start: {argv[0]}") from error
    return ProcessResult(completed.returncode, completed.stdout, completed.stderr)
