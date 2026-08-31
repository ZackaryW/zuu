from pathlib import Path

import pytest

import zuu.case12 as case12
from zuu.case12 import GitHubSubpath, GitHubSubpathError


SHA = "a" * 40


def test_case12_exposes_its_primary_contract_and_dependency() -> None:
    assert case12.__all__[0] == "GitHubSubpath"
    assert case12.__depends__ == ("case5",)
    assert "resolved commit" in case12.__purpose__
    assert set(case12.__all__) == {
        "GitHubSubpath",
        "GitHubSyncResult",
        "GitHubClient",
        "GitHubSubpathError",
    }


@pytest.mark.parametrize(
    "arguments",
    [
        {"owner": "", "repository": "repo", "path": "templates"},
        {"owner": "org/name", "repository": "repo", "path": "templates"},
        {"owner": "org", "repository": " repo", "path": "templates"},
        {"owner": "org", "repository": "repo", "path": "../templates"},
        {"owner": "org", "repository": "repo", "path": "templates\\python"},
        {"owner": "org", "repository": "repo", "path": "/templates"},
        {"owner": "org", "repository": "repo", "path": "templates", "branch": ""},
        {
            "owner": "org",
            "repository": "repo",
            "path": "templates",
            "branch": "main\nnext",
        },
        {"owner": "org", "repository": "repo", "path": "templates", "commit": "abc"},
        {
            "owner": "org",
            "repository": "repo",
            "path": "templates",
            "commit": "z" * 40,
        },
        {
            "owner": "org",
            "repository": "repo",
            "path": "templates",
            "branch": "main",
            "commit": SHA,
        },
    ],
)
def test_invalid_source_declarations_are_rejected(arguments: dict[str, str]) -> None:
    with pytest.raises(GitHubSubpathError):
        GitHubSubpath(**arguments)


def test_source_identity_is_normalized() -> None:
    source = GitHubSubpath(
        "org",
        "repo",
        "templates/python",
        commit="ABCDEF0123456789ABCDEF0123456789ABCDEF01",
    )

    assert source.path == "templates/python"
    assert source.commit == "abcdef0123456789abcdef0123456789abcdef01"


def test_target_parent_must_exist(tmp_path: Path) -> None:
    source = GitHubSubpath("org", "repo", "templates", commit=SHA)

    with pytest.raises(GitHubSubpathError, match="parent"):
        source.sync(tmp_path / "missing" / "target")


def test_existing_target_must_be_a_directory(tmp_path: Path) -> None:
    source = GitHubSubpath("org", "repo", "templates", commit=SHA)
    target = tmp_path / "target"
    target.write_text("occupied", encoding="utf-8")

    with pytest.raises(GitHubSubpathError, match="not a directory"):
        source.sync(target)


def test_redirected_target_is_rejected_when_supported(tmp_path: Path) -> None:
    source = GitHubSubpath("org", "repo", "templates", commit=SHA)
    actual = tmp_path / "actual"
    actual.mkdir()
    target = tmp_path / "target"
    try:
        target.symlink_to(actual, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks are unavailable: {error}")

    with pytest.raises(GitHubSubpathError, match="redirected"):
        source.sync(target)
