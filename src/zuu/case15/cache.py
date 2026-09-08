"""File-backed storage for one Case 15 cache record."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class FileVersionCache:
    """Read and atomically replace cache bytes at a caller-selected path."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)

    def read(self) -> bytes | None:
        """Return cache bytes without creating a missing file."""
        try:
            return self.path.read_bytes()
        except FileNotFoundError:
            return None

    def write(self, data: bytes) -> None:
        """Flush bytes to a sibling temporary file before replacing the cache."""
        if not isinstance(data, bytes):
            raise TypeError("cache data must be bytes")
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
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FileVersionCache) and self.path == other.path
