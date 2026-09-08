from datetime import timedelta

import pytest

from zuu import case15
from zuu.case15 import (
    CheckOrigin,
    CheckPolicy,
    DocumentFormat,
    GitHubRawClient,
    GitHubVersionSource,
    ListenPolicy,
    SourceError,
    check_version,
)


def test_case_metadata_exports_and_enum_values() -> None:
    assert case15.__depends__ == ("case13", "case14")
    assert "cached GitHub" in case15.__purpose__
    assert case15.__all__ == [
        "check_version",
        "GitHubVersionSource",
        "CheckPolicy",
        "VersionCheckResult",
        "DocumentFormat",
        "ListenPolicy",
        "CheckOrigin",
        "VersionCache",
        "RawDocumentClient",
        "FileVersionCache",
        "GitHubRawClient",
        "VersionCheckError",
        "SourceError",
        "RemoteDocumentError",
        "ComparisonError",
    ]
    assert list(DocumentFormat) == ["auto", "yaml", "toml", "json"]
    assert list(ListenPolicy) == [
        "difference",
        "major_change",
        "minor_change",
        "micro_change",
        "regression",
    ]
    assert list(CheckOrigin) == ["remote", "fresh_cache", "stale_cache"]


def test_source_defaults_and_encoded_url() -> None:
    source = GitHubVersionSource(
        "an owner",
        "répo",
        "config files/release.yaml",
        iter(["releases", 0, "version"]),
    )
    assert source.ref == "HEAD"
    assert source.format is DocumentFormat.YAML
    assert source.value_path == ("releases", 0, "version")
    assert source.url == (
        "https://raw.githubusercontent.com/an%20owner/r%C3%A9po/HEAD/"
        "config%20files/release.yaml"
    )


def test_explicit_format_and_ref_are_normalized() -> None:
    source = GitHubVersionSource(
        "owner",
        "repository",
        "release",
        [],
        ref="feature/topic",
        format="json",
    )
    assert source.format is DocumentFormat.JSON
    assert source.url.endswith("/feature%2Ftopic/release")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("owner", ""),
        ("owner", " owner"),
        ("owner", "a/b"),
        ("owner", "a\\b"),
        ("repository", "."),
        ("repository", "repo\nnext"),
        ("ref", ""),
        ("ref", "main\rnext"),
        ("path", "/config.json"),
        ("path", "a\\config.json"),
        ("path", "a//config.json"),
        ("path", "a/./config.json"),
        ("path", "a/../config.json"),
        ("path", "config.json/"),
    ],
)
def test_invalid_source_components(field, value) -> None:
    values = {"owner": "owner", "repository": "repo", "path": "config.json"}
    values[field] = value
    with pytest.raises(SourceError):
        GitHubVersionSource(**values)


@pytest.mark.parametrize(
    "value_path", ["version", b"version", None, [True], [1.5], [object()]]
)
def test_invalid_value_paths(value_path) -> None:
    with pytest.raises(SourceError, match="value_path"):
        GitHubVersionSource("owner", "repo", "config.json", value_path)


@pytest.mark.parametrize("path", ["release", "release.txt", "release.xml"])
def test_ambiguous_auto_format(path) -> None:
    with pytest.raises(SourceError, match="cannot be inferred"):
        GitHubVersionSource("owner", "repo", path)


@pytest.mark.parametrize("format", ["xml", "", None, 1])
def test_invalid_explicit_format(format) -> None:
    with pytest.raises(SourceError, match="format"):
        GitHubVersionSource("owner", "repo", "release", format=format)


def test_check_policy_defaults_and_strings() -> None:
    assert CheckPolicy() == CheckPolicy(
        timedelta(hours=6), True, ListenPolicy.DIFFERENCE
    )
    assert CheckPolicy(listen="major_change").listen is ListenPolicy.MAJOR_CHANGE


@pytest.mark.parametrize(
    "max_age",
    [-1, 1, None, timedelta(microseconds=-1)],
)
def test_invalid_cache_duration(max_age) -> None:
    with pytest.raises(SourceError, match="max_age"):
        CheckPolicy(max_age=max_age)


def test_large_finite_cache_duration_is_supported() -> None:
    assert CheckPolicy(max_age=timedelta.max).max_age == timedelta.max


@pytest.mark.parametrize("stale", [0, 1, None, "yes"])
def test_invalid_stale_policy(stale) -> None:
    with pytest.raises(SourceError, match="stale_if_error"):
        CheckPolicy(stale_if_error=stale)


@pytest.mark.parametrize("listen", ["major", "", None, 1])
def test_invalid_listening_policy(listen) -> None:
    with pytest.raises(SourceError, match="listening policy"):
        CheckPolicy(listen=listen)


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), True, "30"])
def test_invalid_client_timeout(timeout) -> None:
    with pytest.raises(SourceError, match="timeout"):
        GitHubRawClient(timeout)


def test_check_validates_contract_before_collaborators() -> None:
    class Unexpected:
        def read(self):
            pytest.fail("cache was read")

        def fetch(self, source):
            pytest.fail("client was called")

    source = GitHubVersionSource("owner", "repo", "config.json")
    collaborator = Unexpected()
    with pytest.raises(TypeError, match="source"):
        check_version("1", object(), cache=collaborator, client=collaborator)
    with pytest.raises(TypeError, match="policy"):
        check_version(
            "1", source, policy=object(), cache=collaborator, client=collaborator
        )
    with pytest.raises(TypeError, match="compare"):
        check_version(
            "1", source, compare=object(), cache=collaborator, client=collaborator
        )
