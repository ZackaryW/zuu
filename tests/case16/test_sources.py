import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from zuu.case16 import GitHubReleaseClient, GitHubReleaseResolver, ReleaseResolverError, ResolutionSource


def transport(monkeypatch, payloads):
    responses = iter(payloads)
    calls, opened = [], []

    def open_url(request, *, timeout):
        calls.append((request, timeout))
        payload = next(responses)
        response = BytesIO(payload if isinstance(payload, bytes) else json.dumps(payload).encode())
        opened.append(response)
        return response

    monkeypatch.setattr("zuu.case16.sources.urlopen", open_url)
    return calls, opened


def test_latest_release_parses_tag_and_preserves_metadata(monkeypatch):
    payload = {"tag_name": "v1.2", "name": "Friendly title", "prerelease": False, "draft": False, "assets": []}
    calls, responses = transport(monkeypatch, [payload])
    candidate = GitHubReleaseClient(timeout=4).latest_release("an owner", "répo")
    assert candidate.tag == "v1.2"
    assert candidate.source is ResolutionSource.RELEASE
    assert candidate.metadata == payload
    request, timeout = calls[0]
    assert request.full_url == "https://api.github.com/repos/an%20owner/r%C3%A9po/releases/latest"
    assert request.get_header("Accept") == "application/vnd.github+json"
    assert request.get_header("User-agent") == "zuu-case16"
    assert timeout == 4
    assert responses[0].closed


@pytest.mark.parametrize("source", ["tag", "release"])
def test_selection_reaches_highest_version_on_later_page(monkeypatch, source):
    name_key = "name" if source == "tag" else "tag_name"
    first = [{name_key: f"v1.{i}"} for i in range(100)]
    second = [{name_key: "v9.0", "extra": "metadata"}]
    calls, responses = transport(monkeypatch, [first, second])
    resolver = GitHubReleaseResolver(
        "owner", "repo", {("OS", "CPU"): "tool"}, source=source,
        candidate_filter=lambda candidate: True,
    )
    assert resolver.resolve_version() == "v9.0"
    endpoint = "tags" if source == "tag" else "releases"
    assert [request.full_url for request, _ in calls] == [
        f"https://api.github.com/repos/owner/repo/{endpoint}?per_page=100&page=1",
        f"https://api.github.com/repos/owner/repo/{endpoint}?per_page=100&page=2",
    ]
    assert all(response.closed for response in responses)


def test_exactly_full_page_ends_on_empty_page(monkeypatch):
    calls, _ = transport(monkeypatch, [[{"name": f"v{i}"} for i in range(100)], []])
    assert len(list(GitHubReleaseClient().candidates("owner", "repo", "tag"))) == 100
    assert len(calls) == 2


def test_release_candidates_skip_drafts_and_expose_prereleases(monkeypatch):
    payload = [
        {"tag_name": "v3", "draft": True},
        {"tag_name": "v2-rc.1", "prerelease": True, "assets": [{"name": "tool"}]},
        {"tag_name": "v1", "prerelease": False},
    ]
    transport(monkeypatch, [payload])
    candidates = list(GitHubReleaseClient().candidates("owner", "repo", "release"))
    assert [item.tag for item in candidates] == ["v2-rc.1", "v1"]
    assert candidates[0].metadata["assets"] == [{"name": "tool"}]


@pytest.mark.parametrize("payload", [
    b"not JSON", b"\xff", [], {}, {"tag_name": ""}, {"tag_name": "latest"},
    {"tag_name": "v1", "draft": True}, {"tag_name": "v1", "prerelease": True},
    {"tag_name": "v1", "draft": "false"}, {"tag_name": "v1", "prerelease": 0},
])
def test_bad_latest_release_responses(monkeypatch, payload):
    _, responses = transport(monkeypatch, [payload])
    with pytest.raises(ReleaseResolverError):
        GitHubReleaseClient().latest_release("owner", "repo")
    assert responses[0].closed


@pytest.mark.parametrize(("source", "payload"), [
    ("tag", {}), ("tag", [None]), ("tag", [{}]), ("tag", [{"name": 1}]),
    ("release", [{"tag_name": "v1", "draft": "true"}]),
])
def test_bad_candidate_responses(monkeypatch, source, payload):
    transport(monkeypatch, [payload])
    with pytest.raises(ReleaseResolverError):
        list(GitHubReleaseClient().candidates("owner", "repo", source))


def test_later_page_failure_does_not_select_from_incomplete_results(monkeypatch):
    transport(monkeypatch, [[{"name": f"v{i}"} for i in range(100)], {"error": "bad page"}])
    resolver = GitHubReleaseResolver("owner", "repo", {("OS", "CPU"): "tool"}, source="tag")
    with pytest.raises(ReleaseResolverError, match="JSON array"):
        resolver.resolve_version()


@pytest.mark.parametrize("code", [403, 404, 429])
def test_http_errors_propagate_without_fallback(monkeypatch, code):
    error = HTTPError("https://api.github.com/example", code, "failed", {}, None)

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr("zuu.case16.sources.urlopen", fail)
    with pytest.raises(HTTPError) as caught:
        GitHubReleaseClient().latest_release("owner", "repo")
    assert caught.value is error


@pytest.mark.parametrize("timeout", [0, -1, True, None, "1", float("nan"), float("inf")])
def test_invalid_timeouts(timeout):
    with pytest.raises(ReleaseResolverError):
        GitHubReleaseClient(timeout)


def test_invalid_client_arguments_fail_without_network(monkeypatch):
    calls, _ = transport(monkeypatch, [])
    with pytest.raises(ReleaseResolverError):
        GitHubReleaseClient().latest_release("../owner", "repo")
    with pytest.raises(ReleaseResolverError):
        list(GitHubReleaseClient().candidates("owner", "repo", "branch"))
    assert calls == []


def test_release_assets_use_exact_encoded_tag_and_published_browser_urls(monkeypatch):
    release = {"id": 42, "tag_name": "release/v1", "assets": []}
    published = {
        "name": "tool-x86_64-unknown-linux-musl",
        "browser_download_url": "https://downloads.example.com/exact-binary?revision=1",
        "state": "uploaded",
    }
    calls, responses = transport(monkeypatch, [release, [published, {"state": "starter"}]])
    assets = list(GitHubReleaseClient().release_assets("org", "repo", "release/v1"))
    assert len(assets) == 1
    assert assets[0].name == published["name"]
    assert assets[0].url == published["browser_download_url"]
    assert [request.full_url for request, _ in calls] == [
        "https://api.github.com/repos/org/repo/releases/tags/release%2Fv1",
        "https://api.github.com/repos/org/repo/releases/42/assets?per_page=100&page=1",
    ]
    assert all(response.closed for response in responses)


def test_automatic_selection_reads_later_asset_pages(monkeypatch):
    release = {"id": 42, "tag_name": "v1"}
    first = [{"name": f"checksum-{i}.txt", "browser_download_url": f"https://example.com/{i}"} for i in range(100)]
    second = [{"name": "another-project-x86_64-unknown-linux-musl", "browser_download_url": "https://example.com/binary"}]
    calls, _ = transport(monkeypatch, [release, first, second])
    resolver = GitHubReleaseResolver("org", "repo")
    selected = resolver.resolve_asset("v1", system="Linux", machine="x86_64")
    assert selected.url == "https://example.com/binary"
    assert calls[-1][0].full_url.endswith("/42/assets?per_page=100&page=2")


def test_latest_release_to_download_url_integration(monkeypatch):
    release = {"id": 42, "tag_name": "v1"}
    payload = [{"name": "tool-aarch64-apple-darwin", "browser_download_url": "https://example.com/mac"}]
    calls, _ = transport(monkeypatch, [release, release, payload])
    resolver = GitHubReleaseResolver("org", "repo")
    assert resolver.asset_url(system="Darwin", machine="arm64") == "https://example.com/mac"
    assert [request.full_url for request, _ in calls] == [
        "https://api.github.com/repos/org/repo/releases/latest",
        "https://api.github.com/repos/org/repo/releases/tags/v1",
        "https://api.github.com/repos/org/repo/releases/42/assets?per_page=100&page=1",
    ]


def test_full_asset_page_ends_on_empty_page(monkeypatch):
    full = [{"name": f"tool-{i}", "browser_download_url": f"https://example.com/{i}"} for i in range(100)]
    calls, _ = transport(monkeypatch, [{"id": 1, "tag_name": "v1"}, full, []])
    assert len(list(GitHubReleaseClient().release_assets("org", "repo", "v1"))) == 100
    assert len(calls) == 3


@pytest.mark.parametrize("release", [
    {}, {"id": 1, "tag_name": "v2"}, {"id": 1, "tag_name": "v1", "draft": True},
    {"tag_name": "v1"}, {"id": True, "tag_name": "v1"},
    {"id": 0, "tag_name": "v1"}, {"id": "1", "tag_name": "v1"},
])
def test_invalid_asset_release_metadata_fails_before_asset_listing(monkeypatch, release):
    calls, _ = transport(monkeypatch, [release])
    with pytest.raises(ReleaseResolverError):
        list(GitHubReleaseClient().release_assets("org", "repo", "v1"))
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [
    {}, [None], [{}], [{"name": "../escape", "browser_download_url": "https://example.com/a"}],
    [{"name": "tool", "browser_download_url": "file:///a"}],
    [{"state": "unknown"}], [{"name": "tool"}],
])
def test_invalid_asset_metadata(monkeypatch, payload):
    transport(monkeypatch, [{"id": 1, "tag_name": "v1"}, payload])
    with pytest.raises(ReleaseResolverError):
        list(GitHubReleaseClient().release_assets("org", "repo", "v1"))


def test_no_binary_is_selected_when_later_asset_page_fails(monkeypatch):
    first = [{"name": "tool-x86_64-unknown-linux-musl", "browser_download_url": "https://example.com/a"}]
    first += [{"name": f"sidecar-{i}.txt", "browser_download_url": f"https://example.com/{i}"} for i in range(99)]
    transport(monkeypatch, [{"id": 1, "tag_name": "v1"}, first, {"error": "bad page"}])
    with pytest.raises(ReleaseResolverError, match="JSON array"):
        GitHubReleaseResolver("org", "repo").resolve_asset("v1", system="Linux", machine="x86_64")


def test_missing_release_for_tag_propagates_without_source_archive_fallback(monkeypatch):
    error = HTTPError("https://api.github.com/example", 404, "no release", {}, None)

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr("zuu.case16.sources.urlopen", fail)
    with pytest.raises(HTTPError) as caught:
        GitHubReleaseResolver("org", "repo").resolve_asset("v1", system="Linux", machine="x86_64")
    assert caught.value is error
