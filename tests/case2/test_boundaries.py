import os

import pytest

from zuu.case2 import SnapshotError, capture_snapshot


def test_exclusions_remove_files_and_prune_directory_subtrees(tmp_path):
    root = tmp_path / "tree"
    generated = root / "generated"
    generated.mkdir(parents=True)
    (root / "source.py").write_text("source", encoding="utf-8")
    (root / "scratch.tmp").write_text("scratch", encoding="utf-8")
    (generated / "output.py").write_text("output", encoding="utf-8")

    snapshot = capture_snapshot(
        [root],
        exclusions=["*.tmp", "generated/**"],
    )

    assert [entry.relative_path for entry in snapshot.entries] == [".", "source.py"]


def test_rejects_missing_and_empty_root_sets(tmp_path):
    with pytest.raises(SnapshotError, match="at least one"):
        capture_snapshot([])
    with pytest.raises(SnapshotError, match="not materialized"):
        capture_snapshot([tmp_path / "missing"])


def test_rejects_a_symbolic_link_inside_a_snapshot(tmp_path):
    root = tmp_path / "tree"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = root / "linked.txt"
    try:
        os.symlink(outside, link)
    except OSError as error:
        pytest.skip(f"symbolic links are unavailable: {error}")

    with pytest.raises(SnapshotError, match="symbolic link"):
        capture_snapshot([root])


def test_rejects_a_symbolic_link_as_the_snapshot_root(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "root.link"
    try:
        os.symlink(target, link)
    except OSError as error:
        pytest.skip(f"symbolic links are unavailable: {error}")

    with pytest.raises(SnapshotError, match="root is a symbolic link"):
        capture_snapshot([link])


def test_an_excluded_symbolic_link_is_outside_the_snapshot_boundary(tmp_path):
    root = tmp_path / "tree"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = root / "ignored.link"
    try:
        os.symlink(outside, link)
    except OSError as error:
        pytest.skip(f"symbolic links are unavailable: {error}")

    snapshot = capture_snapshot([root], exclusions=["*.link"])

    assert [entry.relative_path for entry in snapshot.entries] == ["."]


def test_absolute_exclusion_masks_match_materialized_paths(tmp_path):
    root = tmp_path / "tree"
    root.mkdir()
    kept = root / "kept.txt"
    ignored = root / "ignored.txt"
    kept.write_text("kept", encoding="utf-8")
    ignored.write_text("ignored", encoding="utf-8")

    snapshot = capture_snapshot([root], exclusions=[ignored.resolve().as_posix()])

    assert [entry.relative_path for entry in snapshot.entries] == [".", "kept.txt"]
