from pathlib import Path

import pytest

from zuu.case5 import RepositoryPath, RepositoryPathError


def test_repository_path_preserves_one_canonical_posix_value() -> None:
    path = RepositoryPath("tools/build/task.py")

    assert path.value == "tools/build/task.py"
    assert path.parts == ("tools", "build", "task.py")
    assert str(path) == "tools/build/task.py"


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "../escape",
        "a/../escape",
        "/absolute",
        "C:/drive",
        "a\\b",
        "a//b",
        "a/./b",
        "bad\x00path",
    ],
)
def test_repository_path_rejects_unsafe_or_noncanonical_values(value: str) -> None:
    with pytest.raises(RepositoryPathError):
        RepositoryPath(value)


def test_resolve_file_returns_an_existing_confined_file(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    selected = root / "src" / "app.py"
    selected.parent.mkdir(parents=True)
    selected.write_text("source", encoding="utf-8")

    assert RepositoryPath("src/app.py").resolve_file(root) == selected.resolve()


def test_resolve_file_rejects_a_directory(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    (root / "src").mkdir(parents=True)

    with pytest.raises(RepositoryPathError, match="not a file"):
        RepositoryPath("src").resolve_file(root)


def test_resolve_file_rejects_a_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = root / "linked.txt"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlinks are unavailable: {error}")

    with pytest.raises(RepositoryPathError, match="escapes"):
        RepositoryPath("linked.txt").resolve_file(root)
