"""Digest strategies for captured filesystem snapshots."""

from __future__ import annotations

import hashlib
from typing import Any

from zuu.case2 import FileSystemSnapshot, SnapshotKind


def _update(hasher: Any, value: str | bytes) -> None:
    encoded = value if isinstance(value, bytes) else value.encode("utf-8")
    hasher.update(len(encoded).to_bytes(8, "big"))
    hasher.update(encoded)


def _hash_snapshot(
    snapshot: FileSystemSnapshot,
    *,
    include_modified: bool = False,
) -> str:
    """Hash framed snapshot identity, paths, kinds, bytes, and optional file mtimes."""
    hasher = hashlib.sha256()
    for root in snapshot.roots:
        _update(hasher, root.as_posix())
    for entry in snapshot.entries:
        _update(hasher, str(entry.root_index))
        _update(hasher, entry.relative_path)
        _update(hasher, entry.kind.value)
        if entry.kind is SnapshotKind.FILE:
            assert entry.content is not None
            _update(hasher, entry.content)
            if include_modified:
                _update(hasher, str(entry.modified_ns))
    return hasher.hexdigest()
