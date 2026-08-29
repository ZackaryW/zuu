from zuu.case2 import FileSystemSnapshot, SnapshotKind, capture_snapshot


def test_captures_files_and_empty_directories_in_deterministic_order(tmp_path):
    root = tmp_path / "tree"
    (root / "nested").mkdir(parents=True)
    (root / "empty").mkdir()
    (root / "z.txt").write_bytes(b"z")
    (root / "nested" / "a.txt").write_bytes(b"a")

    snapshot = capture_snapshot([root])

    assert snapshot.roots == (root.resolve(),)
    assert [(entry.relative_path, entry.kind) for entry in snapshot.entries] == [
        (".", SnapshotKind.DIRECTORY),
        ("empty", SnapshotKind.DIRECTORY),
        ("nested", SnapshotKind.DIRECTORY),
        ("z.txt", SnapshotKind.FILE),
        ("nested/a.txt", SnapshotKind.FILE),
    ]
    assert [entry.content for entry in snapshot.files] == [b"z", b"a"]


def test_canonicalizes_sorts_and_deduplicates_roots(tmp_path):
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_bytes(b"a")
    second.write_bytes(b"b")

    snapshot = FileSystemSnapshot.capture([second, first, second])

    assert snapshot.roots == (first.resolve(), second.resolve())
    assert [entry.root_index for entry in snapshot.entries] == [0, 1]


def test_snapshot_equality_observes_content_and_metadata_changes(tmp_path):
    source = tmp_path / "input.txt"
    source.write_bytes(b"first")
    first = capture_snapshot([source])

    source.write_bytes(b"second")
    second = capture_snapshot([source])

    assert second != first
    assert second.files[0].content == b"second"
