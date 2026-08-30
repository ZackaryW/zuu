import os
from pathlib import Path

import pytest

from zuu.case3 import GitIgnoreError, plan_gitignore, run_process


def init_repo(path: Path) -> Path:
    path.mkdir()
    result = run_process(("git", "init", "--quiet"), path)
    assert result.returncode == 0, result.stderr
    return path


def test_rejects_non_utf8_ignore_content(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "build").mkdir()
    (repo / ".gitignore").write_bytes(b"\xff")

    with pytest.raises(GitIgnoreError, match="UTF-8"):
        plan_gitignore(repo, ["build"])


def test_rejects_a_directory_in_place_of_the_ignore_file(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "build").mkdir()
    (repo / ".gitignore").mkdir()

    with pytest.raises(GitIgnoreError, match="regular file"):
        plan_gitignore(repo, ["build"])


def test_rejects_a_symbolic_link_ignore_file(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "build").mkdir()
    outside = tmp_path / "outside.ignore"
    outside.write_text("# outside\n", encoding="utf-8")
    link = repo / ".gitignore"
    try:
        os.symlink(outside, link)
    except OSError as error:
        pytest.skip(f"symbolic links are unavailable: {error}")

    with pytest.raises(GitIgnoreError, match="regular file"):
        plan_gitignore(repo, ["build"])


def test_run_process_wraps_launch_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("missing executable")

    monkeypatch.setattr("zuu.case3.process.subprocess.run", fail)

    with pytest.raises(GitIgnoreError, match="could not start: missing-command"):
        run_process(("missing-command",), tmp_path)
