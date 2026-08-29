from pathlib import Path

import pytest

from zuu.case3 import (
    GitIgnoreError,
    GitIgnorePolicy,
    IgnoreMode,
    ProcessResult,
    plan_gitignore,
    run_process,
)


def init_repo(path: Path) -> Path:
    path.mkdir()
    result = run_process(("git", "init", "--quiet"), path)
    assert result.returncode == 0, result.stderr
    return path


def test_validates_exact_pattern_and_none_policies():
    assert GitIgnorePolicy() == GitIgnorePolicy(IgnoreMode.EXACT)
    assert GitIgnorePolicy("pattern", "/build/*").mode is IgnoreMode.PATTERN
    assert GitIgnorePolicy("none").mode is IgnoreMode.NONE

    with pytest.raises(ValueError, match="requires one"):
        GitIgnorePolicy("pattern")
    with pytest.raises(ValueError, match="does not accept"):
        GitIgnorePolicy("exact", "*.txt")
    with pytest.raises(ValueError, match="single-line"):
        GitIgnorePolicy("pattern", "one\ntwo")


def test_none_policy_bypasses_git_and_path_validation(tmp_path):
    def runner(argv, cwd):
        raise AssertionError("Git must not run")

    assert (
        plan_gitignore(
            tmp_path / "missing",
            [tmp_path / "outside"],
            policy=GitIgnorePolicy("none"),
            runner=runner,
        )
        is None
    )


def test_exact_policy_plans_only_uncovered_paths_without_writing(tmp_path):
    repo = init_repo(tmp_path / "repo")
    build = repo / "build"
    cache = repo / "cache"
    build.mkdir()
    cache.mkdir()
    ignore_file = repo / ".gitignore"
    ignore_file.write_bytes(b"# keep\n/build\n")

    plan = plan_gitignore(repo, [cache, build])

    assert plan is not None
    assert plan.probes == (build.resolve(), cache.resolve())
    assert plan.original == b"# keep\n/build\n"
    assert plan.proposed == b"# keep\n/build\n/cache\n"
    assert ignore_file.read_bytes() == plan.original


def test_relative_paths_resolve_from_the_selected_project(tmp_path):
    repo = init_repo(tmp_path / "repo")
    project = repo / "packages" / "app"
    target = project / "generated"
    target.mkdir(parents=True)

    plan = plan_gitignore(project, ["generated"])

    assert plan is not None
    assert plan.probes == (target.resolve(),)
    assert plan.proposed == b"/packages/app/generated\n"


def test_rejects_paths_outside_the_worktree(tmp_path):
    repo = init_repo(tmp_path / "repo")

    with pytest.raises(GitIgnoreError, match="outside"):
        plan_gitignore(repo, [tmp_path / "outside"])


def test_reports_git_discovery_and_evaluation_failures(tmp_path):
    def no_worktree(argv, cwd):
        return ProcessResult(128, "", "not a repository")

    with pytest.raises(GitIgnoreError, match="worktree"):
        plan_gitignore(tmp_path, [tmp_path / "build"], runner=no_worktree)

    calls = 0

    def bad_check(argv, cwd):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ProcessResult(0, f"{tmp_path}\n", "")
        return ProcessResult(2, "", "unexpected")

    with pytest.raises(GitIgnoreError, match="evaluate"):
        plan_gitignore(tmp_path, [tmp_path / "build"], runner=bad_check)
