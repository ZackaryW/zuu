from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

ProcessLauncher = Callable[[Sequence[str]], None]

def launch_process(argv: Sequence[str]) -> None:
    subprocess.run(tuple(argv), check=True)

def open_directory(
    path: Path,
    *,
    platform: str = sys.platform,
    launch: ProcessLauncher = launch_process,
) -> None:
    if platform == "darwin":
        executable = "open"
    elif platform == "win32":
        executable = "explorer"
    else:
        executable = "xdg-open"
    launch((executable, str(path)))