from urllib.error import HTTPError, URLError

import pytest

from zuu.case14 import UnsupportedYaml
from zuu.case15 import (
    CheckOrigin,
    DocumentFormat,
    GitHubRawClient,
    GitHubVersionSource,
    RemoteDocumentError,
    check_version,
)


class TextClient:
    def __init__(self, text):
        self.text = text
        self.sources = []

    def fetch(self, source):
        self.sources.append(source)
        if isinstance(self.text, Exception):
            raise self.text
        return self.text


@pytest.mark.parametrize(
    ("source", "text", "expected"),
    [
        (
            GitHubVersionSource("o", "r", "pubspec.yaml", ["packages", 1, "version"]),
            "packages:\n  - version: 1.0.0\n  - version: 2.0.0\n",
            "2.0.0",
        ),
        (
            GitHubVersionSource("o", "r", "pyproject.toml", ["project", "version"]),
            '[project]\nversion = "3.0.0"\n',
            "3.0.0",
        ),
        (
            GitHubVersionSource("o", "r", "package.json", ["packages", 0, "version"]),
            '{"packages":[{"version":"4.0.0"}]}',
            "4.0.0",
        ),
        (
            GitHubVersionSource("o", "r", "release", [], format="json"),
            "42",
            42,
        ),
    ],
)
def test_supported_parsers_and_nested_extraction(source, text, expected) -> None:
    client = TextClient(text)
    result = check_version("local", source, client=client)
    assert result.remote == expected
    assert result.origin is CheckOrigin.REMOTE
    assert client.sources == [source]


def test_yaml_unsupported_value_can_be_compared() -> None:
    source = GitHubVersionSource("o", "r", "release.yml", ["version"])
    result = check_version("local", source, client=TextClient("version: [1, 2, 3]"))
    assert result.remote == UnsupportedYaml("[1, 2, 3]")
    assert result.update_needed


@pytest.mark.parametrize(
    ("format", "text"),
    [
        (DocumentFormat.YAML, "version:\n- unindented"),
        (DocumentFormat.TOML, 'version = "unterminated'),
        (DocumentFormat.JSON, '{"version":}'),
    ],
)
def test_parse_errors_are_normalized_with_causes(format, text) -> None:
    source = GitHubVersionSource("o", "r", f"release.{format.value}")
    with pytest.raises(RemoteDocumentError, match="could not parse") as error:
        check_version("1.0.0", source, client=TextClient(text))
    assert error.value.__cause__ is not None


def test_missing_path_is_normalized_with_cause() -> None:
    source = GitHubVersionSource("o", "r", "release.json", ["missing", 0])
    with pytest.raises(RemoteDocumentError, match="does not resolve") as error:
        check_version("1.0.0", source, client=TextClient("{}"))
    assert isinstance(error.value.__cause__, KeyError)


@pytest.mark.parametrize("failure", [RuntimeError("offline"), URLError("offline")])
def test_custom_client_failures_are_normalized(failure) -> None:
    source = GitHubVersionSource("o", "r", "release.json")
    with pytest.raises(RemoteDocumentError, match="could not fetch") as error:
        check_version("1.0.0", source, client=TextClient(failure))
    assert error.value.__cause__ is failure


def test_custom_client_must_return_text() -> None:
    source = GitHubVersionSource("o", "r", "release.json")
    with pytest.raises(RemoteDocumentError, match="return text"):
        check_version("1.0.0", source, client=TextClient(b'"1.0.0"'))


class Response:
    def __init__(self, payload):
        self.payload = payload
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        self.reads += 1
        return self.payload


def test_default_client_request_and_single_read(monkeypatch) -> None:
    source = GitHubVersionSource("an owner", "repo", "a file.json", [])
    response = Response(b'"1.2.3"')
    calls = []

    def open_request(request, *, timeout):
        calls.append((request, timeout))
        return response

    monkeypatch.setattr("zuu.case15.client.urlopen", open_request)
    assert GitHubRawClient(12.5).fetch(source) == '"1.2.3"'
    request, timeout = calls[0]
    assert request.full_url == source.url
    assert request.get_header("User-agent") == "zuu-case15"
    assert timeout == 12.5
    assert response.reads == 1


@pytest.mark.parametrize(
    "failure",
    [
        HTTPError("https://example.test", 404, "not found", {}, None),
        URLError("offline"),
        OSError("socket failed"),
    ],
)
def test_default_client_request_failures(monkeypatch, failure) -> None:
    source = GitHubVersionSource("o", "r", "release.json")

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr("zuu.case15.client.urlopen", fail)
    with pytest.raises(RemoteDocumentError, match="GitHub raw request failed") as error:
        GitHubRawClient().fetch(source)
    assert error.value.__cause__ is failure


def test_default_client_utf8_failure(monkeypatch) -> None:
    source = GitHubVersionSource("o", "r", "release.json")
    monkeypatch.setattr(
        "zuu.case15.client.urlopen", lambda *args, **kwargs: Response(b"\xff")
    )
    with pytest.raises(RemoteDocumentError) as error:
        GitHubRawClient().fetch(source)
    assert isinstance(error.value.__cause__, UnicodeDecodeError)
