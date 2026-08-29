"""Public snapshot models and capture entry points."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Self

__purpose__ = "Capture deterministic snapshots of files and directory trees."
__depends__ = ()

Pathish = str | os.PathLike[str]


class SnapshotError(ValueError):
    """A governed path cannot be represented as a safe regular snapshot."""


class SnapshotKind(StrEnum):
    """Filesystem entry kinds supported by a snapshot."""

    FILE = "file"
    DIRECTORY = "directory"


@dataclass(frozen=True, slots=True)
class SnapshotEntry:
    """One file or directory captured relative to a selected snapshot root."""

    root_index: int
    relative_path: str
    kind: SnapshotKind
    content: bytes | None
    modified_ns: int

    def __post_init__(self) -> None:
        if self.root_index < 0:
            raise ValueError("snapshot root index must not be negative")
        if not self.relative_path:
            raise ValueError("snapshot relative path must not be empty")
        if self.kind is SnapshotKind.FILE and self.content is None:
            raise ValueError("snapshot file entries require content")
        if self.kind is SnapshotKind.DIRECTORY and self.content is not None:
            raise ValueError("snapshot directory entries cannot contain content")


@dataclass(frozen=True, slots=True)
class FileSystemSnapshot:
    """An immutable deterministic capture of one or more filesystem roots."""

    roots: tuple[Path, ...]
    entries: tuple[SnapshotEntry, ...]

    @classmethod
    def capture(
        cls,
        paths: Iterable[Pathish],
        *,
        exclusions: Iterable[str] = (),
    ) -> Self:
        """Capture materialized regular paths without following symbolic links."""
        from .snapshot import capture_components

        roots, entries = capture_components(paths, exclusions=exclusions)
        return cls(roots, entries)

    @property
    def files(self) -> tuple[SnapshotEntry, ...]:
        """Return only captured regular-file entries."""
        return tuple(entry for entry in self.entries if entry.kind is SnapshotKind.FILE)

    @property
    def directories(self) -> tuple[SnapshotEntry, ...]:
        """Return only captured directory entries, including selected roots."""
        return tuple(
            entry for entry in self.entries if entry.kind is SnapshotKind.DIRECTORY
        )


def capture_snapshot(
    paths: Iterable[Pathish],
    *,
    exclusions: Iterable[str] = (),
) -> FileSystemSnapshot:
    """Capture paths through the public `FileSystemSnapshot` model."""
    return FileSystemSnapshot.capture(paths, exclusions=exclusions)


__all__ = [
    "FileSystemSnapshot",
    "SnapshotEntry",
    "SnapshotError",
    "SnapshotKind",
    "capture_snapshot",
]
