from pathlib import Path

import pytest

from zuu.case3 import (
    GitIgnoreError,
    GitIgnorePolicy,
    apply_gitignore,
    plan_gitignore,
    run_process,
    verify_gitignore,
)


def init_repo(path: Path) -> Path:
    path.mkdir()
    result = run_process(("git", "init", "--quiet"), path)
    assert result.returncode == 0, result.stderr
    return path


def test_applies_and_verifies_exact_rules(tmp_path):
    repo = init_repo(tmp_path / "repo")
    build = repo / "build"
    build.mkdir()
    plan = plan_gitignore(repo, [build])
    assert plan is not None

    changed = apply_gitignore(plan)

    assert changed is True
    assert (repo / ".gitignore").read_bytes() == b"/build\n"
    verify_gitignore(plan)
    repeated = plan_gitignore(repo, [build])
    assert repeated is not None
    assert repeated.changed is False
    assert apply_gitignore(repeated) is False


def test_ineffective_pattern_rolls_back_an_existing_ignore_file(tmp_path):
    repo = init_repo(tmp_path / "repo")
    target = repo / "build"
    target.mkdir()
    ignore_file = repo / ".gitignore"
    ignore_file.write_bytes(b"# original\n")
    plan = plan_gitignore(
        repo,
        [target],
        policy=GitIgnorePolicy("pattern", "*.txt"),
    )
    assert plan is not None

    with pytest.raises(GitIgnoreError, match="ineffective"):
        apply_gitignore(plan)

    assert ignore_file.read_bytes() == b"# original\n"


def test_ineffective_pattern_removes_a_new_ignore_file_during_rollback(tmp_path):
    repo = init_repo(tmp_path / "repo")
    target = repo / "build"
    target.mkdir()
    plan = plan_gitignore(
        repo,
        [target],
        policy=GitIgnorePolicy("pattern", "*.txt"),
    )
    assert plan is not None

    with pytest.raises(GitIgnoreError, match="ineffective"):
        apply_gitignore(plan)

    assert not (repo / ".gitignore").exists()


def test_rejects_a_stale_plan_without_overwriting_new_content(tmp_path):
    repo = init_repo(tmp_path / "repo")
    target = repo / "build"
    target.mkdir()
    plan = plan_gitignore(repo, [target])
    assert plan is not None
    ignore_file = repo / ".gitignore"
    ignore_file.write_bytes(b"# concurrent edit\n")

    with pytest.raises(GitIgnoreError, match="changed after"):
        apply_gitignore(plan)

    assert ignore_file.read_bytes() == b"# concurrent edit\n"
