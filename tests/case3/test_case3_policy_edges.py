from pathlib import Path

import pytest

from zuu.case3 import (
    GitIgnoreError,
    GitIgnorePolicy,
    apply_gitignore,
    plan_gitignore,
    run_process,
)


def init_repo(path: Path) -> Path:
    path.mkdir()
    result = run_process(("git", "init", "--quiet"), path)
    assert result.returncode == 0, result.stderr
    return path


def test_pattern_policy_applies_one_caller_owned_rule(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    target = repo / "build" / "nested"
    target.mkdir(parents=True)
    plan = plan_gitignore(
        repo,
        [target],
        policy=GitIgnorePolicy("pattern", "/build/"),
    )
    assert plan is not None

    assert plan.proposed == b"/build/\n"
    assert apply_gitignore(plan)


def test_rules_append_after_a_file_without_a_final_newline(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    target = repo / "cache"
    target.mkdir()
    (repo / ".gitignore").write_bytes(b"# existing")

    plan = plan_gitignore(repo, [target])

    assert plan is not None
    assert plan.proposed == b"# existing\n/cache\n"


def test_selected_paths_are_sorted_and_deduplicated(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    first = repo / "a"
    second = repo / "b"
    first.mkdir()
    second.mkdir()

    plan = plan_gitignore(repo, [second, first, second])

    assert plan is not None
    assert plan.probes == (first.resolve(), second.resolve())
    assert plan.proposed == b"/a\n/b\n"


def test_rejects_empty_paths_and_the_worktree_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    with pytest.raises(GitIgnoreError, match="at least one selected path"):
        plan_gitignore(repo, [])
    with pytest.raises(GitIgnoreError, match="root cannot be ignored"):
        plan_gitignore(repo, [repo])
