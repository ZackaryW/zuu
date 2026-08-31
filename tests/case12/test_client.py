from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

import pytest

from zuu.case12 import GitHubSubpathError
from zuu.case12.client import GitHubApiClient


SHA = "a" * 40


class Response(BytesIO):
    def __enter__(self) -> Response:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_default_branch_and_commit_are_resolved_from_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[Request] = []
    responses = iter(
        [
            Response(b'{"default_branch":"main"}'),
            Response((f'{{"sha":"{SHA}"}}').encode()),
        ]
    )

    def open_request(request: Request, *, timeout: float) -> Response:
        requests.append(request)
        assert timeout == 4.0
        return next(responses)

    monkeypatch.setattr("zuu.case12.client.urlopen", open_request)

    commit = GitHubApiClient(timeout=4.0).resolve_commit("my org", "repo.name", None)

    assert commit == SHA
    assert requests[0].full_url == "https://api.github.com/repos/my%20org/repo.name"
    assert requests[1].full_url.endswith("/commits/main")
    assert requests[0].get_header("User-agent") == "zuu-case12"


def test_branch_slashes_are_encoded(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[Request] = []

    def open_request(request: Request, *, timeout: float) -> Response:
        requests.append(request)
        return Response((f'{{"sha":"{SHA}"}}').encode())

    monkeypatch.setattr("zuu.case12.client.urlopen", open_request)

    GitHubApiClient().resolve_commit("org", "repo", "feature/templates")

    assert requests[0].full_url.endswith("/commits/feature%2Ftemplates")


def test_archive_is_streamed_to_the_selected_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[Request] = []

    def open_request(request: Request, *, timeout: float) -> Response:
        requests.append(request)
        return Response(b"zip bytes")

    monkeypatch.setattr("zuu.case12.client.urlopen", open_request)
    destination = tmp_path / "archive.zip"

    GitHubApiClient().download_archive("org", "repo", SHA, destination)

    assert destination.read_bytes() == b"zip bytes"
    assert requests[0].full_url.endswith(f"/zipball/{SHA}")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"not-json", "invalid JSON"),
        (b"[]", "JSON object"),
        (b"{}", "default branch"),
    ],
)
def test_malformed_repository_responses_are_rejected(
    payload: bytes,
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "zuu.case12.client.urlopen",
        lambda request, timeout: Response(payload),
    )

    with pytest.raises(GitHubSubpathError, match=message):
        GitHubApiClient().resolve_commit("org", "repo", None)


def test_request_failures_are_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(request: Request, *, timeout: float) -> Response:
        raise URLError("offline")

    monkeypatch.setattr("zuu.case12.client.urlopen", fail)

    with pytest.raises(GitHubSubpathError, match="request failed"):
        GitHubApiClient().resolve_commit("org", "repo", "main")
