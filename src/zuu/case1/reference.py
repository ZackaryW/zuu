"""Replaceable byte storage for the case1 hash registry."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol

Pathish = str | os.PathLike[str]


class HashReference(Protocol):
    """Byte-oriented registry storage, including encrypted or remote wrappers."""

    def read(self) -> bytes | None:
        """Return registry bytes, or `None` when no registry exists."""
        ...

    def write(self, data: bytes) -> None:
        """Replace the complete registry with serialized bytes."""
        ...


class FileReference:
    """Persist registry bytes through atomic replacement of one plain file."""

    def __init__(self, path: Pathish):
        self.path = Path(path)

    def read(self) -> bytes | None:
        """Read the stored bytes without creating a missing file."""
        try:
            return self.path.read_bytes()
        except FileNotFoundError:
            return None

    def write(self, data: bytes) -> None:
        """Flush bytes to a sibling temporary file before replacing the target."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                delete=False,
            ) as temporary:
                temporary.write(data)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            temporary_path.replace(self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
