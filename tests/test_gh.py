import subprocess

from zuu.v202602_1.gh import GitHubRepo
from zuu.v202602_1.gh import clone_repository
from zuu.v202602_1.gh import is_gh_logged_in
from zuu.v202602_1.gh import parse_gh_auth_status
from zuu.v202602_1.gh import parse_repository_search_output


def test_parse_gh_auth_status_returns_true_for_logged_in_output() -> None:
    output = """github.com
  ✓ Logged in to github.com account octocat (keyring)
  - Active account: true
  - Git operations protocol: https
"""

    assert parse_gh_auth_status(output) is True


def test_parse_gh_auth_status_returns_false_for_logged_out_output() -> None:
    output = "You are not logged into any GitHub hosts. To log in, run: gh auth login"

    assert parse_gh_auth_status(output) is False


def test_is_gh_logged_in_reads_combined_command_output(monkeypatch) -> None:
    is_gh_logged_in.cache_clear()

    monkeypatch.setattr("zuu.v202602_1.gh.is_gh_available", lambda: True)
    monkeypatch.setattr(
        "zuu.v202602_1.gh.run_command",
        lambda command, args: subprocess.CompletedProcess(
            args=[command, *args],
            returncode=0,
            stdout="",
            stderr="Logged in to github.com account octocat\n",
        ),
    )

    assert is_gh_logged_in() is True


def test_parse_repository_search_output_maps_missing_description_to_empty_string() -> None:
    output = (
        '[{"name":"zuu","description":null,"updatedAt":"2026-04-01T00:00:00Z"}]'
    )

    assert parse_repository_search_output(output) == [
        GitHubRepo(
            name="zuu",
            description="",
            updated_at="2026-04-01T00:00:00Z",
        )
    ]


def test_clone_repository_runs_gh_repo_clone(monkeypatch, tmp_path) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        "zuu.v202602_1.gh.run_command",
        lambda command, args: calls.append((command, args))
        or subprocess.CompletedProcess(args=[command, *args], returncode=0, stdout="", stderr=""),
    )

    clone_repository("octocat/hello-world", tmp_path / "hello-world")

    assert calls == [
        (
            "gh",
            ["repo", "clone", "octocat/hello-world", str(tmp_path / "hello-world")],
        )
    ]


def test_clone_repository_passes_branch_flags(monkeypatch, tmp_path) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        "zuu.v202602_1.gh.run_command",
        lambda command, args: calls.append((command, args))
        or subprocess.CompletedProcess(args=[command, *args], returncode=0, stdout="", stderr=""),
    )

    clone_repository("octocat/hello-world", tmp_path / "hello-world", branch="release/2026")

    assert calls == [
        (
            "gh",
            [
                "repo",
                "clone",
                "octocat/hello-world",
                str(tmp_path / "hello-world"),
                "--",
                "--branch",
                "release/2026",
                "--single-branch",
            ],
        )
    ]
