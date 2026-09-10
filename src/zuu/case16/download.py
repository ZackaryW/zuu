"""Download and publish a binary without exposing partial destination content."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
import urllib.request
from pathlib import Path

from . import Downloader


def _download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=30) as response:
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output)


def install_binary(url: str, destination: Path, *, downloader: Downloader | None) -> None:
    # A sibling temporary file keeps replacement on the destination filesystem.
    with tempfile.NamedTemporaryFile(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
    ) as output:
        temporary = Path(output.name)
    try:
        (downloader if downloader is not None else _download)(url, temporary)
        if os.name != "nt":
            temporary.chmod(temporary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
