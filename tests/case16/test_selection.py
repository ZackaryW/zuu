from dataclasses import replace

import pytest

from zuu.case16 import (
    Candidate,
    GitHubReleaseResolver,
    ReleaseResolverError,
    ResolutionSource,
    parse_version,
)


class Source:
    def __init__(self, tags=(), releases=()):
        self.tags = tags
        self.releases = releases
        self.calls = []

    def latest_release(self, owner, repository):
        self.calls.append(("latest", owner, repository))
        return Candidate("v3.0", "release", {"name": "Current release"})

    def candidates(self, owner, repository, source):
        self.calls.append((source.value, owner, repository))
        return iter(self.tags if source is ResolutionSource.TAG else self.releases)


def resolver(client, **kwargs):
    return GitHubReleaseResolver("owner", "repo", {("OS", "CPU"): "tool"}, client=client, **kwargs)


@pytest.mark.parametrize("version", [None, "latest", "LATEST"])
def test_default_release_selection_uses_latest_endpoint(version):
    client = Source()
    assert resolver(client).resolve_version(version) == "v3.0"
    assert client.calls == [("latest", "owner", "repo")]


@pytest.mark.parametrize("source", ["tag", "release"])
def test_explicit_version_bypasses_source_filter_and_parser(source):
    def fail(*args):
        pytest.fail("explicit versions must bypass discovery and selection callbacks")

    configured = resolver(object(), source=source, candidate_filter=fail, version_parser=fail)
    assert configured.resolve_version("release/special") == "release/special"
    assert configured.asset_url("release/special", system="OS", machine="CPU").endswith(
        "/release%2Fspecial/tool"
    )


def test_tag_source_chooses_highest_parsed_version_in_any_order():
    client = Source(tags=[Candidate(tag, "tag") for tag in ["v1.9", "nightly", "v1.10", "v1.2"]])
    assert resolver(client, source="tag").resolve_version() == "v1.10"
    assert client.calls == [("tag", "owner", "repo")]


@pytest.mark.parametrize("source", ["tag", "release"])
def test_filters_see_selected_source_metadata_before_parsing(source):
    candidates = [
        Candidate("not-a-version", source, {"eligible": False}),
        Candidate("v9", source, {"eligible": False}),
        Candidate("v1", source, {"eligible": True}),
        Candidate("v2", source, {"eligible": True}),
    ]
    client = Source(tags=candidates, releases=candidates)
    filtered, parsed = [], []

    def accept(candidate):
        filtered.append(candidate)
        assert candidate.source == source
        return candidate.metadata["eligible"]

    def parse(tag):
        parsed.append(tag)
        return parse_version(tag)

    configured = resolver(client, source=source, candidate_filter=accept, version_parser=parse)
    assert configured.resolve_version() == "v2"
    assert filtered == candidates
    assert parsed == ["v1", "v2"]
    assert client.calls == [(source, "owner", "repo")]


def test_release_filter_uses_highest_version_instead_of_latest_release():
    client = Source(releases=[
        Candidate("v10-rc.1", "release", {"prerelease": True}),
        Candidate("v2", "release", {"prerelease": False}),
        Candidate("v4", "release", {"prerelease": False}),
    ])
    configured = resolver(client, candidate_filter=lambda item: not item.metadata["prerelease"])
    assert configured.resolve_version() == "v4"
    assert client.calls == [("release", "owner", "repo")]


@pytest.mark.parametrize("source", ["tag", "release"])
def test_custom_parser_supports_nonstandard_names_and_zero_keys(source):
    candidates = [Candidate(tag, source) for tag in ["build_0", "unknown", "build_20", "build_3"]]
    client = Source(tags=candidates, releases=candidates)

    def parse(tag):
        return int(tag[6:]) if tag.startswith("build_") else None

    assert resolver(client, source=source, version_parser=parse).resolve_version() == "build_20"
    zero = Source(tags=[Candidate("build_0", "tag")])
    assert resolver(zero, source="tag", version_parser=parse).resolve_version() == "build_0"


def test_equal_keys_keep_first_candidate():
    client = Source(tags=[Candidate(tag, "tag") for tag in ["v1.0+first", "v1.0.0+second"]])
    assert resolver(client, source="tag").resolve_version() == "v1.0+first"


@pytest.mark.parametrize("mode", ["empty", "unparseable", "filtered"])
def test_no_eligible_candidate_is_an_error(mode):
    client = Source(tags=[] if mode == "empty" else [Candidate("v1" if mode == "filtered" else "nightly", "tag")])
    configured = resolver(client, source="tag", candidate_filter=lambda item: mode != "filtered")
    with pytest.raises(ReleaseResolverError, match="no eligible version"):
        configured.resolve_version()


@pytest.mark.parametrize("boundary", ["source", "filter", "parser"])
def test_selection_failures_propagate_before_files_or_downloads(tmp_path, monkeypatch, boundary):
    monkeypatch.setattr("zuu.case16.platform.system", lambda: "OS")
    monkeypatch.setattr("zuu.case16.platform.machine", lambda: "CPU")
    failure = RuntimeError(boundary)

    def fail(*args):
        raise failure

    client = Source(tags=[Candidate("v1", "tag")])
    kwargs = {}
    if boundary == "source":
        client.candidates = fail
    else:
        kwargs["candidate_filter" if boundary == "filter" else "version_parser"] = fail
    configured = resolver(client, source="tag", **kwargs)
    dest = tmp_path / "tool"
    dest.write_bytes(b"old")
    with pytest.raises(RuntimeError) as caught:
        configured.resolve(dest=dest, downloader=lambda *args: pytest.fail("unexpected download"))
    assert caught.value is failure
    assert dest.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [dest]


def test_automatic_url_and_download_resolve_only_once(tmp_path, monkeypatch):
    monkeypatch.setattr("zuu.case16.platform.system", lambda: "OS")
    monkeypatch.setattr("zuu.case16.platform.machine", lambda: "CPU")
    client = Source()
    configured = resolver(client)
    expected = "https://github.com/owner/repo/releases/download/v3.0/tool"
    assert configured.asset_url() == expected
    assert len(client.calls) == 1
    calls = []

    def download(url, dest):
        calls.append(url)
        dest.write_bytes(b"binary")

    dest = tmp_path / "tool"
    assert configured.resolve(dest=dest, downloader=download) == dest
    assert dest.read_bytes() == b"binary"
    assert calls == [expected]
    assert len(client.calls) == 2


def test_default_client_is_used_without_injection(monkeypatch):
    client = Source()
    monkeypatch.setattr("zuu.case16.GitHubReleaseClient", lambda: client)
    configured = GitHubReleaseResolver("owner", "repo", {("OS", "CPU"): "tool"})
    assert configured.resolve_version() == "v3.0"
    assert client.calls == [("latest", "owner", "repo")]


@pytest.mark.parametrize("kwargs", [{"source": "branch"}, {"candidate_filter": False}, {"version_parser": None}])
def test_invalid_selection_configuration(kwargs):
    with pytest.raises(ReleaseResolverError):
        resolver(Source(), **kwargs)


def test_bad_filter_return_and_incomparable_keys_fail():
    client = Source(tags=[Candidate("v1", "tag"), Candidate("v2", "tag")])
    configured = resolver(client, source="tag", candidate_filter=lambda item: 1)
    with pytest.raises(ReleaseResolverError, match="return bool"):
        configured.resolve_version()
    configured = replace(configured, candidate_filter=None, version_parser=lambda tag: 1 if tag == "v1" else "two")
    with pytest.raises(TypeError):
        configured.resolve_version()


@pytest.mark.parametrize("candidate", [None, Candidate("v1", "release")])
def test_invalid_source_candidates_are_rejected(candidate):
    with pytest.raises(ReleaseResolverError, match="mismatched candidate"):
        resolver(Source(tags=[candidate]), source="tag").resolve_version()


def test_candidate_metadata_is_copied_and_read_only():
    metadata = {"name": "release"}
    candidate = Candidate("v1", "release", metadata)
    metadata.clear()
    assert candidate.metadata["name"] == "release"
    assert candidate.source is ResolutionSource.RELEASE
    with pytest.raises(TypeError):
        candidate.metadata["name"] = "changed"


@pytest.mark.parametrize("args", [("latest", "tag", {}), ("v1", "branch", {}), ("v1", "tag", [])])
def test_invalid_candidate_models(args):
    with pytest.raises(ReleaseResolverError):
        Candidate(*args)
