from io import BytesIO
from urllib.error import URLError

import pytest

from zuu.case16 import GitHubReleaseResolver


def test_default_transport_streams_and_closes_response(tmp_path, monkeypatch):
    payload = b"binary" * 100_000
    response = BytesIO(payload)
    calls = []

    def open_url(url, *, timeout):
        calls.append((url, timeout))
        return response

    monkeypatch.setattr("zuu.case16.download.urllib.request.urlopen", open_url)
    monkeypatch.setattr("zuu.case16.platform.system", lambda: "Linux")
    monkeypatch.setattr("zuu.case16.platform.machine", lambda: "x86_64")
    resolver = GitHubReleaseResolver("org", "app", {("Linux", "x86_64"): "app-linux"})
    dest = tmp_path / "app"
    assert resolver.resolve("v1", dest) == dest
    assert dest.read_bytes() == payload
    assert response.closed
    assert calls == [("https://github.com/org/app/releases/download/v1/app-linux", 30)]


def test_network_error_propagates_without_replacing_file(tmp_path, monkeypatch):
    failure = URLError("offline")

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr("zuu.case16.download.urllib.request.urlopen", fail)
    monkeypatch.setattr("zuu.case16.platform.system", lambda: "Windows")
    monkeypatch.setattr("zuu.case16.platform.machine", lambda: "AMD64")
    resolver = GitHubReleaseResolver("org", "app", {("Windows", "AMD64"): "app.exe"})
    dest = tmp_path / "app.exe"
    dest.write_bytes(b"old")
    with pytest.raises(URLError) as caught:
        resolver.resolve("v1", dest)
    assert caught.value is failure
    assert dest.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [dest]
