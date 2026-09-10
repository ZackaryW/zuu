from pathlib import Path
from types import SimpleNamespace

import pytest

from zuu.case16 import GitHubReleaseResolver, ReleaseResolverError


@pytest.fixture
def resolver(monkeypatch):
    monkeypatch.setattr("zuu.case16.platform.system", lambda: "TestOS")
    monkeypatch.setattr("zuu.case16.platform.machine", lambda: "TestCPU")
    return GitHubReleaseResolver("owner", "repo", {("TestOS", "TestCPU"): "tool"})


def test_default_destination_and_repeated_downloads(tmp_path, monkeypatch, resolver):
    monkeypatch.chdir(tmp_path)
    calls = []

    def download(url, target):
        calls.append(url)
        target.write_bytes(str(len(calls)).encode())
        return "ignored return value"

    assert resolver.resolve("v1", downloader=download) == Path("tool")
    assert (tmp_path / "tool").read_bytes() == b"1"
    assert resolver.resolve("v1", downloader=download) == Path("tool")
    assert (tmp_path / "tool").read_bytes() == b"2"
    assert calls == ["https://github.com/owner/repo/releases/download/v1/tool"] * 2
    assert list(tmp_path.iterdir()) == [tmp_path / "tool"]


@pytest.mark.parametrize("as_string", [False, True])
def test_custom_destination_is_replaced_only_after_callback(tmp_path, resolver, as_string):
    dest = tmp_path / "custom.exe"
    dest.write_bytes(b"old")

    def download(url, target):
        assert isinstance(target, Path)
        assert target.parent == dest.parent
        assert target != dest
        target.write_bytes(b"new")
        assert dest.read_bytes() == b"old"

    assert resolver.resolve("v2", str(dest) if as_string else dest, downloader=download) == dest
    assert dest.read_bytes() == b"new"
    assert list(tmp_path.iterdir()) == [dest]


@pytest.mark.parametrize("existing", [False, True])
def test_failed_partial_download_preserves_destination_and_cleans_up(tmp_path, resolver, existing):
    dest = tmp_path / "binary"
    if existing:
        dest.write_bytes(b"old")
    failure = RuntimeError("offline")

    def download(url, target):
        target.write_bytes(b"partial")
        raise failure

    with pytest.raises(RuntimeError) as caught:
        resolver.resolve("v1", dest, downloader=download)
    assert caught.value is failure
    assert list(tmp_path.iterdir()) == ([dest] if existing else [])
    if existing:
        assert dest.read_bytes() == b"old"


@pytest.mark.parametrize("failure", ["tag", "platform", "parent"])
def test_invalid_request_fails_before_download(tmp_path, monkeypatch, resolver, failure):
    calls = []
    version = "" if failure == "tag" else "v1"
    dest = tmp_path / "missing" / "tool" if failure == "parent" else tmp_path / "tool"
    if failure == "platform":
        monkeypatch.setattr("zuu.case16.platform.machine", lambda: "unsupported")
    with pytest.raises((ReleaseResolverError, FileNotFoundError)):
        resolver.resolve(version, dest, downloader=lambda *args: calls.append(args))
    assert calls == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("host", ["posix", "nt"])
def test_executable_permissions_follow_host_os(tmp_path, monkeypatch, resolver, host):
    import zuu.case16.download as module

    monkeypatch.setattr(module, "os", SimpleNamespace(name=host))
    modes = []
    monkeypatch.setattr(Path, "chmod", lambda self, mode: modes.append(mode))
    dest = tmp_path / "tool"
    resolver.resolve("v1", dest, downloader=lambda url, target: target.write_bytes(b"binary"))
    assert len(modes) == (1 if host == "posix" else 0)
    if host == "posix":
        assert modes[0] & 0o111 == 0o111


def test_chmod_failure_preserves_old_binary(tmp_path, monkeypatch, resolver):
    import zuu.case16.download as module

    monkeypatch.setattr(module, "os", SimpleNamespace(name="posix"))
    dest = tmp_path / "tool"
    dest.write_bytes(b"old")

    def fail(*args):
        raise PermissionError("chmod denied")

    monkeypatch.setattr(Path, "chmod", fail)
    with pytest.raises(PermissionError, match="chmod denied"):
        resolver.resolve("v1", dest, downloader=lambda url, target: target.write_bytes(b"new"))
    assert dest.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [dest]


def test_replacement_failure_cleans_up(tmp_path, resolver):
    dest = tmp_path / "directory"
    dest.mkdir()
    (dest / "keep").write_bytes(b"old")
    with pytest.raises(OSError):
        resolver.resolve("v1", dest, downloader=lambda url, target: target.write_bytes(b"new"))
    assert (dest / "keep").read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [dest]


def test_destination_symlink_is_replaced_without_writing_through(tmp_path, resolver):
    original = tmp_path / "original"
    original.write_bytes(b"old")
    dest = tmp_path / "link"
    try:
        dest.symlink_to(original)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    resolver.resolve("v1", dest, downloader=lambda url, target: target.write_bytes(b"new"))
    assert not dest.is_symlink()
    assert dest.read_bytes() == b"new"
    assert original.read_bytes() == b"old"
