from dataclasses import FrozenInstanceError
from pathlib import Path
import re

import pytest

import zuu.case12 as case12
from zuu.case12 import GitHubSubpath, GitHubSubpathError


SHA = "a" * 40


def test_filters_are_keyword_only_immutable_snapshots() -> None:
    include = [r"\.py$", r"\.md$"]
    exclude = [r"^tests/", r"^draft"]
    source = GitHubSubpath(
        "org", "repo", "templates", None, SHA, include=include, exclude=exclude
    )
    include.clear()
    exclude.append("new")
    assert source.include == (r"\.py$", r"\.md$")
    assert source.exclude == (r"^tests/", r"^draft")
    assert hash(source) == hash(
        GitHubSubpath(
            "org",
            "repo",
            "templates",
            None,
            SHA,
            include=source.include,
            exclude=source.exclude,
        )
    )
    with pytest.raises(FrozenInstanceError):
        source.include = ()
    with pytest.raises(TypeError):
        GitHubSubpath("org", "repo", "templates", None, SHA, ())


@pytest.mark.parametrize("field", ["include", "exclude"])
@pytest.mark.parametrize("value", [".*", b".*", None, 3, {"a"}, iter(["a"])])
def test_invalid_filter_collections(field: str, value: object) -> None:
    with pytest.raises(GitHubSubpathError, match=field):
        GitHubSubpath("org", "repo", "templates", **{field: value})


@pytest.mark.parametrize("field", ["include", "exclude"])
@pytest.mark.parametrize(
    "value", [42, b"a", re.compile("a"), "[", "a{999999999999999999}"]
)
def test_invalid_filter_elements_identify_the_index(field: str, value: object) -> None:
    with pytest.raises(GitHubSubpathError, match=rf"{field}\[1\]"):
        GitHubSubpath("org", "repo", "templates", **{field: ["valid", value]})


def test_empty_regex_is_valid() -> None:
    source = GitHubSubpath("org", "repo", "templates", include=("",), exclude=("",))
    assert source.include == source.exclude == ("",)


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
