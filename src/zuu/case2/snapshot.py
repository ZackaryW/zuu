"""Filesystem traversal and snapshot materialization."""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from fnmatch import fnmatchcase
from pathlib import Path

from . import Pathish, SnapshotEntry, SnapshotError, SnapshotKind


def capture_components(
    paths: Iterable[Pathish],
    *,
    exclusions: Iterable[str] = (),
) -> tuple[tuple[Path, ...], tuple[SnapshotEntry, ...]]:
    """Materialize canonical roots and deterministically ordered snapshot entries."""
    roots = _canonical_roots(paths)
    masks = tuple(mask.replace("\\", "/") for mask in exclusions)
    entries: list[SnapshotEntry] = []
    for root_index, root in enumerate(roots):
        entries.extend(_capture_root(root_index, root, masks))
    return roots, tuple(entries)


def _canonical_roots(paths: Iterable[Pathish]) -> tuple[Path, ...]:
    roots: dict[str, Path] = {}
    for value in paths:
        candidate = Path(value)
        if candidate.is_symlink():
            raise SnapshotError(f"snapshot root is a symbolic link: {candidate}")
        try:
            root = candidate.resolve(strict=True)
        except OSError as error:
            raise SnapshotError(f"snapshot root is not materialized: {candidate}") from error
        if not root.is_file() and not root.is_dir():
            raise SnapshotError(f"snapshot root is not a regular file or directory: {root}")
        roots[root.as_posix()] = root
    if not roots:
        raise SnapshotError("snapshot requires at least one root")
    return tuple(roots[key] for key in sorted(roots))


def _capture_root(
    root_index: int,
    root: Path,
    exclusions: Sequence[str],
) -> list[SnapshotEntry]:
    if root.is_file():
        return [_file_entry(root_index, ".", root)]

    entries = [_directory_entry(root_index, ".", root)]
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(directory_names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if _is_excluded(path, relative, exclusions):
                continue
            if path.is_symlink():
                raise SnapshotError(f"snapshot contains a symbolic link: {relative}")
            if not path.is_dir():
                raise SnapshotError(f"snapshot contains an unsupported entry: {relative}")
            kept_directories.append(name)
            entries.append(_directory_entry(root_index, relative, path))
        directory_names[:] = kept_directories

        for name in sorted(file_names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if _is_excluded(path, relative, exclusions):
                continue
            if path.is_symlink():
                raise SnapshotError(f"snapshot contains a symbolic link: {relative}")
            if not path.is_file():
                raise SnapshotError(f"snapshot contains an unsupported entry: {relative}")
            entries.append(_file_entry(root_index, relative, path))
    return entries


def _file_entry(root_index: int, relative: str, path: Path) -> SnapshotEntry:
    try:
        content = path.read_bytes()
        modified_ns = path.stat().st_mtime_ns
    except OSError as error:
        raise SnapshotError(f"snapshot file cannot be read: {path}") from error
    return SnapshotEntry(
        root_index,
        relative,
        SnapshotKind.FILE,
        content,
        modified_ns,
    )


def _directory_entry(root_index: int, relative: str, path: Path) -> SnapshotEntry:
    try:
        modified_ns = path.stat().st_mtime_ns
    except OSError as error:
        raise SnapshotError(f"snapshot directory cannot be inspected: {path}") from error
    return SnapshotEntry(
        root_index,
        relative,
        SnapshotKind.DIRECTORY,
        None,
        modified_ns,
    )


def _is_excluded(path: Path, relative: str, exclusions: Sequence[str]) -> bool:
    candidates = (relative, path.name, path.absolute().as_posix())
    for mask in exclusions:
        if any(fnmatchcase(candidate, mask) for candidate in candidates):
            return True
        if mask.endswith("/**") and relative == mask[:-3].rstrip("/"):
            return True
    return False
