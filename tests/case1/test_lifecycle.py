import pytest

from zuu.case1 import IdentifierConflictError, UserLevelHasher


def test_register_then_match(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    (governed / "input.txt").write_text("first", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)

    hasher.register("build", [governed])

    assert hasher.match("build", lambda: "matched", lambda: "mismatched") == "matched"


def test_mismatch_advances_hash_after_callback(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    source = governed / "input.txt"
    source.write_text("first", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("build", [governed])
    source.write_text("second", encoding="utf-8")

    assert hasher.match("build", lambda: "matched", lambda: "rebuilt") == "rebuilt"
    assert hasher.match("build", lambda: "matched", lambda: "rebuilt") == "matched"


def test_failed_mismatch_does_not_advance_hash(tmp_path):
    governed = tmp_path / "input.txt"
    governed.write_text("first", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("build", [governed])
    governed.write_text("second", encoding="utf-8")

    def fail():
        raise RuntimeError("build failed")

    with pytest.raises(RuntimeError, match="build failed"):
        hasher.match("build", lambda: None, fail)

    assert hasher.match("build", lambda: "matched", lambda: "retried") == "retried"


def test_same_identifier_cannot_silently_change_definition(tmp_path):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("build", [first])

    with pytest.raises(IdentifierConflictError):
        hasher.register("build", [second])


def test_repeated_registration_does_not_reset_a_changed_baseline(tmp_path):
    governed = tmp_path / "input.txt"
    governed.write_text("first", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("build", [governed])
    governed.write_text("second", encoding="utf-8")

    hasher.register("build", [governed])

    assert hasher.match("build", lambda: True, lambda: False) is False


def test_default_reference_is_not_part_of_governed_folder_hash(tmp_path):
    (tmp_path / "input.txt").write_text("data", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)

    hasher.register("whole-folder", [tmp_path])

    assert hasher.match("whole-folder", lambda: True, lambda: False) is True
