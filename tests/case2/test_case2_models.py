from dataclasses import FrozenInstanceError
from collections.abc import Callable
from pathlib import Path

import pytest

from zuu.case2 import FileSystemSnapshot, SnapshotEntry, SnapshotKind


def test_file_root_and_filtered_properties_are_materialized(tmp_path: Path) -> None:
    source = tmp_path / "input.bin"
    source.write_bytes(b"content")

    snapshot = FileSystemSnapshot.capture([source])

    assert snapshot.roots == (source.resolve(),)
    assert snapshot.directories == ()
    assert len(snapshot.files) == 1
    assert snapshot.files[0].relative_path == "."
    assert snapshot.files[0].content == b"content"


@pytest.mark.parametrize(
    "entry",
    [
        lambda: SnapshotEntry(-1, "file", SnapshotKind.FILE, b"data", 0),
        lambda: SnapshotEntry(0, "", SnapshotKind.FILE, b"data", 0),
        lambda: SnapshotEntry(0, "file", SnapshotKind.FILE, None, 0),
        lambda: SnapshotEntry(0, "folder", SnapshotKind.DIRECTORY, b"data", 0),
    ],
)
def test_snapshot_entry_rejects_inconsistent_state(
    entry: Callable[[], SnapshotEntry],
) -> None:
    with pytest.raises(ValueError):
        entry()


def test_snapshot_models_are_immutable(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("content", encoding="utf-8")
    snapshot = FileSystemSnapshot.capture([source])

    with pytest.raises(FrozenInstanceError):
        snapshot.entries = ()  # type: ignore[misc]
