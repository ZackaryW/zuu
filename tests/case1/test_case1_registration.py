from pathlib import Path

import pytest

from zuu.case1 import UserLevelHasher


def test_registration_validates_identifier_paths_and_strategy(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("content", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)

    with pytest.raises(ValueError, match="identifier"):
        hasher.register("", [source])
    with pytest.raises(ValueError, match="at least one governed path"):
        hasher.register("build", [])
    with pytest.raises(ValueError, match="unknown hasher"):
        hasher.register("build", [source], hasher="missing")


def test_replace_changes_the_complete_registered_definition(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("build", [first])

    hasher.register("build", [second], replace=True)
    first.write_text("changed", encoding="utf-8")

    assert hasher.match("build", lambda: "same", lambda: "changed") == "same"

    second.write_text("changed", encoding="utf-8")
    assert hasher.match("build", lambda: "same", lambda: "changed") == "changed"


def test_matching_an_unknown_identifier_fails(tmp_path: Path) -> None:
    with pytest.raises(KeyError, match="not registered"):
        UserLevelHasher(tmp_path).match("missing", lambda: None, lambda: None)


def test_mismatch_baseline_captures_callback_output(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("first", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("build", [source])
    source.write_text("changed", encoding="utf-8")

    def rebuild() -> str:
        source.write_text("rebuilt", encoding="utf-8")
        return "rebuilt"

    assert hasher.match("build", lambda: "same", rebuild) == "rebuilt"
    assert hasher.match("build", lambda: "same", rebuild) == "same"
