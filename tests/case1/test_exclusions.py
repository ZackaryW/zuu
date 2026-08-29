from zuu.case1 import UserLevelHasher


def test_exclusion_masks_ignore_matching_files(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    source = governed / "input.txt"
    ignored = governed / "scratch.tmp"
    source.write_text("source", encoding="utf-8")
    ignored.write_text("one", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("build", [governed], exclusions=["*.tmp"])
    ignored.write_text("two", encoding="utf-8")

    assert hasher.match("build", lambda: True, lambda: False) is True

    source.write_text("changed", encoding="utf-8")
    assert hasher.match("build", lambda: True, lambda: False) is False


def test_directory_exclusion_prunes_the_subtree(tmp_path):
    governed = tmp_path / "governed"
    ignored = governed / "generated"
    ignored.mkdir(parents=True)
    (governed / "input.txt").write_text("source", encoding="utf-8")
    output = ignored / "output.txt"
    output.write_text("one", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("build", [governed], exclusions=["generated/**"])

    output.write_text("two", encoding="utf-8")

    assert hasher.match("build", lambda: True, lambda: False) is True


def test_renaming_a_governed_file_invalidates_the_hash(tmp_path):
    folder = tmp_path / "folder"
    folder.mkdir()
    first = folder / "a.txt"
    first.write_text("one", encoding="utf-8")
    hasher = UserLevelHasher(tmp_path)
    hasher.register("tree", [folder])

    first.rename(folder / "renamed.txt")

    assert hasher.match("tree", lambda: True, lambda: False) is False
