import pytest

from zuu.case16 import GitHubReleaseResolver, ReleaseResolverError


SAUCEPAN_ASSETS = {
    ("Darwin", "arm64"): "saucepan-aarch64-apple-darwin",
    ("Darwin", "x86_64"): "saucepan-x86_64-apple-darwin",
    ("Windows", "AMD64"): "saucepan-x86_64-pc-windows-msvc.exe",
    ("Windows", "ARM64"): "saucepan-aarch64-pc-windows-msvc.exe",
    ("Windows", "x86"): "saucepan-i686-pc-windows-msvc.exe",
    ("Linux", "x86_64"): "saucepan-x86_64-unknown-linux-musl",
}


@pytest.mark.parametrize(("pair", "asset"), SAUCEPAN_ASSETS.items())
def test_saucepan_platforms_and_direct_urls(pair, asset):
    resolver = GitHubReleaseResolver("ZackaryW", "saucepan", SAUCEPAN_ASSETS)
    system, machine = pair
    assert resolver.asset_name(system=system, machine=machine) == asset
    assert resolver.asset_url("v0.2.0", system=system, machine=machine) == (
        f"https://github.com/ZackaryW/saucepan/releases/download/v0.2.0/{asset}"
    )


def test_host_detection_partial_overrides_and_copied_mapping(monkeypatch):
    assets = {("Linux", "x86_64"): "tool", ("Darwin", "arm64"): "other"}
    resolver = GitHubReleaseResolver("owner", "repo", assets)
    assets.clear()
    monkeypatch.setattr("zuu.case16.platform.system", lambda: "Linux")
    monkeypatch.setattr("zuu.case16.platform.machine", lambda: "arm64")
    assert resolver.asset_name(machine="x86_64") == "tool"
    assert resolver.asset_name(system="Darwin") == "other"
    with pytest.raises(TypeError):
        resolver.assets[("Linux", "x86_64")] = "changed"
    with pytest.raises(ReleaseResolverError, match=r"\(Linux, arm64\)"):
        resolver.asset_name()


def test_url_components_and_tag_are_encoded():
    resolver = GitHubReleaseResolver("an owner", "répo", {("OS", "CPU"): "my tool"})
    assert resolver.asset_url("release/v1+#?", system="OS", machine="CPU") == (
        "https://github.com/an%20owner/r%C3%A9po/releases/download/"
        "release%2Fv1%2B%23%3F/my%20tool"
    )


@pytest.mark.parametrize("version", [1, "", " ", " v1", "v1\n", ".", ".."])
def test_invalid_tags_are_rejected(version):
    resolver = GitHubReleaseResolver("owner", "repo", {("OS", "CPU"): "tool"})
    with pytest.raises(ReleaseResolverError):
        resolver.asset_url(version, system="OS", machine="CPU")


@pytest.mark.parametrize("value", [None, 1, "", " ", ".", "..", "a/b", "a\\b", "a\n", "a:", "a."])
@pytest.mark.parametrize("field", ["owner", "repository", "asset"])
def test_invalid_source_components(field, value):
    args = {"owner": "owner", "repository": "repo", "assets": {("OS", "CPU"): "tool"}}
    if field == "asset":
        args["assets"] = {("OS", "CPU"): value}
    else:
        args[field] = value
    with pytest.raises(ReleaseResolverError):
        GitHubReleaseResolver(**args)


@pytest.mark.parametrize("assets", [[], {}, {"OS": "tool"}, {("OS",): "tool"}, {("OS", 1): "tool"}, {("", "CPU"): "tool"}])
def test_invalid_platform_mappings(assets):
    with pytest.raises(ReleaseResolverError):
        GitHubReleaseResolver("owner", "repo", assets)


@pytest.mark.parametrize("override", [{"system": ""}, {"machine": 1}, {"machine": "cpu"}])
def test_invalid_or_unknown_platform_override(override):
    resolver = GitHubReleaseResolver("owner", "repo", {("OS", "CPU"): "tool"})
    with pytest.raises(ReleaseResolverError):
        resolver.asset_name(**override)
