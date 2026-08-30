from pathlib import Path

from zuu.case1 import FileReference


def test_file_reference_reads_missing_storage_without_creating_it(tmp_path: Path) -> None:
    path = tmp_path / "registry" / "hashes.json"
    reference = FileReference(path)

    assert reference.read() is None
    assert not path.exists()


def test_file_reference_creates_parents_and_replaces_complete_bytes(tmp_path: Path) -> None:
    path = tmp_path / "registry" / "hashes.json"
    reference = FileReference(path)

    reference.write(b"first")
    reference.write(b"second")

    assert reference.read() == b"second"
    assert list(path.parent.iterdir()) == [path]
