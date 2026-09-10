from dataclasses import replace

import pytest

from zuu.case16 import (
    Candidate,
    GitHubReleaseResolver,
    ReleaseAsset,
    ReleaseResolverError,
    select_rust_asset,
)


def asset(name):
    return ReleaseAsset(name, "https://github.com/org/project/releases/download/v1/" + name)


NAMES = (
    "saucepan-aarch64-apple-darwin",
    "saucepan-aarch64-pc-windows-msvc.exe",
    "saucepan-i686-pc-windows-msvc.exe",
    "saucepan-universal-apple-darwin",
    "saucepan-x86_64-apple-darwin",
    "saucepan-x86_64-pc-windows-msvc.exe",
    "saucepan-x86_64-unknown-linux-musl",
)


@pytest.mark.parametrize(("system", "machine", "index"), [
    ("Darwin", "arm64", 0), ("Darwin", "aarch64", 0),
    ("Darwin", "x86_64", 4), ("Darwin", "AMD64", 4),
    ("Windows", "ARM64", 1), ("Windows", "aarch64", 1),
    ("Windows", "x86", 2), ("Windows", "i386", 2), ("Windows", "i686", 2),
    ("Windows", "AMD64", 5), ("Windows", "x86_64", 5), ("Windows", "x64", 5),
    ("Linux", "x86_64", 6), ("linux", "amd64", 6),
])
def test_user_saucepan_assets_match_host_and_aliases(system, machine, index):
    assets = tuple(map(asset, NAMES))
    assert select_rust_asset(assets, system, machine) == assets[index]


@pytest.mark.parametrize("machine", ["arm64", "x86_64"])
def test_macos_universal_fallback_and_native_preference(machine):
    universal = asset("any-name-universal-apple-darwin")
    assert select_rust_asset((universal,), "Darwin", machine) == universal
    arch = "aarch64" if machine == "arm64" else "x86_64"
    native = asset(f"different-project-v3-{arch}-apple-darwin")
    assert select_rust_asset((universal, native), "Darwin", machine) == native


@pytest.mark.parametrize(("system", "preferred", "fallback"), [
    ("Linux", "x86_64-unknown-linux-musl", "x86_64-unknown-linux-gnu"),
    ("Windows", "x86_64-pc-windows-msvc.exe", "x86_64-pc-windows-gnu.exe"),
])
def test_abi_preferences_and_fallbacks(system, preferred, fallback):
    first, second = asset("tool-" + preferred), asset("tool-" + fallback)
    assert select_rust_asset((second, first), system, "x86_64") == first
    assert select_rust_asset((second,), system, "x86_64") == second


@pytest.mark.parametrize(("machine", "arch"), [("ARM64", "aarch64"), ("x86", "i686")])
def test_other_linux_architectures(machine, arch):
    candidate = asset(f"tool-{arch}-unknown-linux-musl")
    assert select_rust_asset((candidate,), "Linux", machine) == candidate


def test_target_without_project_prefix_and_case_insensitive_matching():
    candidate = asset("X86_64-UNKNOWN-LINUX-MUSL")
    assert select_rust_asset((candidate,), "Linux", "x86_64") == candidate


@pytest.mark.parametrize("ending", [".zip", ".tar.gz", ".sha256", ".sig", ".exe", "-debug", ".txt"])
def test_archives_sidecars_and_extra_suffixes_are_not_raw_binaries(ending):
    candidate = asset("tool-x86_64-unknown-linux-musl" + ending)
    with pytest.raises(ReleaseResolverError, match="no matching Rust binary"):
        select_rust_asset((candidate,), "Linux", "x86_64")


def test_no_substring_matching_or_wrong_architecture():
    assets = (asset("tool-notx86_64-unknown-linux-musl"), asset("tool-aarch64-unknown-linux-musl"))
    with pytest.raises(ReleaseResolverError, match="no matching"):
        select_rust_asset(assets, "Linux", "x86_64")


@pytest.mark.parametrize(("system", "machine"), [("FreeBSD", "amd64"), ("Linux", "riscv64"), ("Darwin", "i686")])
def test_unsupported_platform_is_explicit(system, machine):
    with pytest.raises(ReleaseResolverError, match="unsupported Rust platform"):
        select_rust_asset((), system, machine)


def test_empty_asset_listing_and_ambiguous_binaries():
    with pytest.raises(ReleaseResolverError, match="no matching"):
        select_rust_asset((), "Windows", "AMD64")
    assets = (asset("server-x86_64-unknown-linux-musl"), asset("client-x86_64-unknown-linux-musl"))
    with pytest.raises(ReleaseResolverError, match="ambiguous.*server.*client"):
        select_rust_asset(assets, "Linux", "x86_64")


class Source:
    def __init__(self, assets):
        self.assets = assets
        self.calls = []

    def latest_release(self, owner, repository):
        self.calls.append(("latest", owner, repository))
        return Candidate("v1", "release")

    def candidates(self, owner, repository, source):
        self.calls.append(("candidates", source))
        yield Candidate("v1", source)
        yield Candidate("v2", source)

    def release_assets(self, owner, repository, tag):
        self.calls.append(("assets", owner, repository, tag))
        return iter(self.assets)


@pytest.fixture
def automatic(monkeypatch):
    monkeypatch.setattr("zuu.case16.platform.system", lambda: "Windows")
    monkeypatch.setattr("zuu.case16.platform.machine", lambda: "AMD64")
    client = Source(tuple(map(asset, NAMES)))
    return GitHubReleaseResolver("org", "project", client=client), client


def test_automatic_download_needs_only_repository_configuration(tmp_path, monkeypatch, automatic):
    resolver, client = automatic
    monkeypatch.chdir(tmp_path)
    downloads = []

    def download(url, target):
        downloads.append(url)
        target.write_bytes(b"binary")

    path = resolver.resolve(downloader=download)
    assert path.name == NAMES[5]
    assert path.read_bytes() == b"binary"
    assert downloads == [client.assets[5].url]
    assert client.calls == [("latest", "org", "project"), ("assets", "org", "project", "v1")]
    assert list(tmp_path.iterdir()) == [tmp_path / NAMES[5]]


def test_asset_inspection_and_partial_platform_overrides(automatic):
    resolver, client = automatic
    assert resolver.resolve_asset("v1") == client.assets[5]
    assert resolver.asset_name("v1", system="Darwin") == NAMES[4]
    assert resolver.asset_url("v1", machine="ARM64") == client.assets[1].url
    assert client.calls == [("assets", "org", "project", "v1")] * 3


@pytest.mark.parametrize("source", ["tag", "release"])
def test_asset_discovery_uses_filtered_selected_tag(automatic, source):
    resolver, client = automatic
    configured = replace(resolver, source=source, candidate_filter=lambda c: c.tag == "v2")
    assert configured.resolve_asset().name == NAMES[5]
    assert client.calls == [("candidates", source), ("assets", "org", "project", "v2")]


def test_custom_selector_can_filter_and_reuse_default_matching(automatic):
    resolver, client = automatic
    client.assets = (asset("one-x86_64-pc-windows-msvc.exe"), asset("two-x86_64-pc-windows-msvc.exe"))
    calls = []

    def selector(assets, system, machine):
        calls.append((assets, system, machine))
        return select_rust_asset(tuple(a for a in assets if a.name.startswith("two-")), system, machine)

    selected = replace(resolver, asset_selector=selector).resolve_asset("v1")
    assert selected == client.assets[1]
    assert calls == [(client.assets, "Windows", "AMD64")]


def test_custom_selector_supports_other_naming_and_platforms(automatic):
    resolver, client = automatic
    client.assets = (asset("custom.bin"),)
    selected = replace(resolver, asset_selector=lambda assets, system, machine: assets[0])
    assert selected.resolve_asset("v1", system="OtherOS", machine="OtherCPU") == client.assets[0]


@pytest.mark.parametrize("problem", ["empty", "ambiguous", "invalid", "duplicate", "selector", "discovery"])
def test_asset_selection_failure_preserves_destination(tmp_path, automatic, problem):
    resolver, client = automatic
    if problem == "empty":
        client.assets = ()
    elif problem == "ambiguous":
        client.assets = (asset("one-x86_64-pc-windows-msvc.exe"), asset("two-x86_64-pc-windows-msvc.exe"))
    elif problem == "invalid":
        client.assets = (None,)
    elif problem == "duplicate":
        client.assets = (client.assets[5], client.assets[5])
    else:
        def fail(*args):
            raise RuntimeError("failed callback")
        if problem == "selector":
            resolver = replace(resolver, asset_selector=fail)
        else:
            client.release_assets = fail
    dest = tmp_path / "existing"
    dest.write_bytes(b"old")
    with pytest.raises((ReleaseResolverError, RuntimeError)):
        resolver.resolve("v1", dest, downloader=lambda *args: pytest.fail("unexpected download"))
    assert dest.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [dest]


@pytest.mark.parametrize("selected", [None, "filename", asset("fabricated")])
def test_custom_selector_must_return_discovered_asset(automatic, selected):
    resolver, _ = automatic
    with pytest.raises(ReleaseResolverError, match="discovered ReleaseAsset"):
        replace(resolver, asset_selector=lambda *args: selected).resolve_asset("v1")


def test_manual_mapping_still_bypasses_discovery():
    resolver = GitHubReleaseResolver("org", "repo", {("OtherOS", "CPU"): "custom"}, client=object())
    selected = resolver.resolve_asset("v1", system="OtherOS", machine="CPU")
    assert selected == ReleaseAsset("custom", "https://github.com/org/repo/releases/download/v1/custom")


def test_invalid_selector_configuration():
    with pytest.raises(ReleaseResolverError, match="must be callable"):
        GitHubReleaseResolver("org", "repo", asset_selector=False)
    with pytest.raises(ReleaseResolverError, match="either assets or asset_selector"):
        GitHubReleaseResolver("org", "repo", {("OS", "CPU"): "tool"}, asset_selector=lambda *args: None)


@pytest.mark.parametrize("url", [None, "", "relative", "http://example.com/a", "https:///a", "https://user:pass@example.com/a", "https://example.com/a#fragment", "https://example.com/a b", "https://example.com:bad/a", "https://[invalid/a", "https://example.com\\a"])
def test_bad_asset_urls_are_rejected(url):
    with pytest.raises(ReleaseResolverError):
        ReleaseAsset("tool", url)


@pytest.mark.parametrize("name", [None, "", "..", "../tool", "C:\\tool", "tool\n"])
def test_bad_asset_names_are_rejected(name):
    with pytest.raises(ReleaseResolverError):
        ReleaseAsset(name, "https://example.com/tool")
