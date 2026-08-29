import os

from zuu.case1 import UserLevelHasher


def test_content_strategy_ignores_a_timestamp_only_change(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("same", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("content", [source])
    original = source.stat().st_mtime_ns

    os.utime(source, ns=(original + 1_000_000, original + 1_000_000))

    assert hasher.match("content", lambda: True, lambda: False) is True


def test_content_and_mtime_strategy_observes_a_timestamp_change(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("same", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("modified", [source], hasher="content-and-mtime")
    original = source.stat().st_mtime_ns

    os.utime(source, ns=(original + 1_000_000, original + 1_000_000))

    assert hasher.match("modified", lambda: True, lambda: False) is False


def test_registry_creation_does_not_change_a_whole_folder_mtime_hash(tmp_path):
    (tmp_path / "input.txt").write_text("data", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)

    hasher.register("whole-folder", [tmp_path], hasher="content-and-mtime")

    assert hasher.match("whole-folder", lambda: True, lambda: False) is True
