# case16: GitHub binary resolver

Discover a version, automatically select its platform binary, and download it.
Only the public GitHub owner and repository are required. Standard library only;
no direct case dependencies. Examples below reuse `resolver` from the first block.

## Download the latest release

```python
from dataclasses import replace
from pathlib import Path
from zuu.case16 import GitHubReleaseResolver

resolver = GitHubReleaseResolver(
    owner="ZackaryW",         # Any public GitHub account or organization.
    repository="saucepan",    # The repository publishing your binaries.
)

binary: Path = resolver.resolve()
print(binary)
# Windows AMD64: saucepan-x86_64-pc-windows-msvc.exe
# Saved in the current directory using the discovered asset filename.
```

No asset mapping is needed for supported Rust target names. The filename prefix
can differ from the repository name.

## Choose the destination file

```python
import os

folder = Path(".tools")
folder.mkdir(parents=True, exist_ok=True)  # The caller creates parent directories.
destination = folder / ("saucepan.exe" if os.name == "nt" else "saucepan")

# Latest release, renamed locally.
binary = resolver.resolve(dest=destination)
assert binary == destination

# Pin an exact version and use the same destination.
binary = resolver.resolve("v0.3.0", dest=destination)

# Strings work too; resolve() still returns a Path.
binary = resolver.resolve("v0.3.0", dest=str(destination))
```

| Destination behavior | Contract |
|----------------------|----------|
| `dest` | A file path, not a directory. |
| Omitted | Discovered asset filename in the current working directory. |
| Relative path | Interpreted from the current directory; returned as a relative `Path`. |
| Parent directories | Must exist; create them yourself. |
| Existing file | Replaced after successful download and permission setup. |
| Existing symlink | The link itself is replaced; its target is untouched. Parent symlinks follow normal filesystem behavior. |
| Name transformations | No automatic `~` expansion or `.exe` suffix. |

## Select releases, tags, or an explicit version

```python
from zuu.case16 import ResolutionSource

# Default: honor GitHub's latest published full release.
by_release = GitHubReleaseResolver("ZackaryW", "saucepan", source="release")
release_tag = by_release.resolve_version()

# Tags: parse all tag names and choose the highest version.
by_tag = GitHubReleaseResolver("ZackaryW", "saucepan", source="tag")
highest_tag = by_tag.resolve_version()

# Enum values work too.
by_tag = replace(resolver, source=ResolutionSource.TAG)
by_release = replace(resolver, source=ResolutionSource.RELEASE)

# None and case-insensitive "latest" both request automatic selection.
tag = resolver.resolve_version(None)
tag = resolver.resolve_version("latest")

# Explicit tags bypass version discovery, filtering, and parsing.
assert resolver.resolve_version("v0.3.0") == "v0.3.0"
binary = resolver.resolve("v0.3.0", dest=destination)
```

An explicit version still needs asset discovery unless you provide a manual
mapping. Tag mode downloads binaries attached to that tag's published release;
a tag with only source-code archives cannot supply a binary.

## Inspect without downloading

```python
# Version only; no binary download.
tag = resolver.resolve_version()

# Inspect another platform using the same selected version.
selected = resolver.resolve_asset(tag, system="Windows", machine="AMD64")
print(selected.name)  # ReleaseAsset.name
print(selected.url)   # ReleaseAsset.url: the published browser_download_url

name = resolver.asset_name(tag, system="Darwin", machine="arm64")
url = resolver.asset_url(tag, system="Linux", machine="x86_64")

# Omit either platform component to detect that component from the host.
name = resolver.asset_name(tag)

# Reuse the selected tag when downloading for the host.
binary = resolver.resolve(tag, dest=destination)
```

Inspection methods fetch metadata as needed. Platform overrides only affect that
inspection; `resolve()` detects its own host. Each call starts fresh: there is no
version or binary cache, and every download runs again even for the same tag.

## Automatic Rust asset matching

| Host | Preferred filename ending | Fallback ending |
|------|---------------------------|-----------------|
| macOS ARM64 | `aarch64-apple-darwin` | `universal-apple-darwin` |
| macOS x86-64 | `x86_64-apple-darwin` | `universal-apple-darwin` |
| Windows | `<arch>-pc-windows-msvc.exe` | `<arch>-pc-windows-gnu.exe` |
| Linux | `<arch>-unknown-linux-musl` | `<arch>-unknown-linux-gnu` |

Windows/Linux `<arch>` supports `x86_64`, `aarch64`, and `i686`. Matching ignores
case and recognizes these aliases:

```text
AMD64 / x64 / x86_64  -> x86_64
ARM64 / aarch64      -> aarch64
x86 / i386 / i686    -> i686

saucepan-aarch64-apple-darwin        -> native macOS ARM64 binary
saucepan-universal-apple-darwin      -> fallback when native macOS asset is absent
saucepan-x86_64-unknown-linux-musl   -> Linux x86-64 binary
saucepan-x86_64-unknown-linux-musl.zip     -> ignored archive
saucepan-x86_64-unknown-linux-musl.sha256  -> ignored checksum
```

The ending may stand alone or follow any prefix plus a hyphen. Archives,
signatures, and sidecars do not match raw binary endings. Multiple best matches
raise an ambiguity error. Other platforms/naming schemes need a custom selector
or mapping. These preferences do not verify runtime-library compatibility.

## Filter versions from either source

```python
# Highest parsed non-prerelease version from the release listing.
stable = replace(
    resolver,
    source="release",
    candidate_filter=lambda candidate: not candidate.metadata.get("prerelease", False),
)
tag = stable.resolve_version()

# Highest parsed tag in one version series.
series_two = replace(
    resolver,
    source="tag",
    candidate_filter=lambda candidate: candidate.tag.startswith("v2."),
)
tag = series_two.resolve_version()
```

`CandidateFilter` receives `Candidate(tag, source, metadata)` and must return
`bool`. Metadata is a shallow read-only copy of the source record; treat nested
values as read-only too. Release records can include `name`, `prerelease`,
`published_at`, and `assets`; tag records include `name` and `commit`.

```text
Tag source, or release source with a filter/custom parser:
all source candidates -> filter -> parse tag -> highest key -> discover asset

Default release source without either customization:
GitHub latest-release designation -> discover asset
```

Release listings exclude drafts but include prereleases. Filters run before the
parser. Equal keys keep the first source candidate; no eligible version raises
an error. Filtered release selection can differ from GitHub's latest designation.

## Parse custom version names

```python
from zuu.case16 import parse_version

assert parse_version("v1.10") > parse_version("v1.9")
assert parse_version("1.0-rc.1") < parse_version("1.0")
assert parse_version("V1.02.0+build.9") == parse_version("1.2")
assert parse_version("nightly") is None

# A VersionParser returns a comparable key, or None to skip the tag.
def build_version(tag: str) -> int | None:
    prefix, separator, number = tag.partition("_")
    if prefix == "build" and separator and number.isdecimal():
        return int(number)
    return None

builds = replace(resolver, source="tag", version_parser=build_version)
# build_20 ranks above build_3; unrelated names are skipped.
```

The default parser accepts a whole numeric dotted tag of any length, an optional
`v`/`V`, prerelease identifiers, and build metadata. Leading zeroes, trailing zero
components, and build metadata do not affect ordering. Prerelease identifiers use
SemVer-style numeric/text ordering. A higher-core prerelease can outrank a
lower-core stable version. Returned tuples are ordering keys. A custom parser in
release mode also switches to the full release listing.

## Choose among multiple binaries or other naming schemes

```python
from zuu.case16 import select_rust_asset

# An AssetSelector receives the discovered assets plus detected OS/architecture.
def choose_server(assets, system, machine):
    eligible = tuple(asset for asset in assets if asset.name.startswith("server-"))
    return select_rust_asset(eligible, system, machine)

server = replace(resolver, asset_selector=choose_server)

# Or implement your own naming convention; return one discovered ReleaseAsset.
def choose_custom(assets, system, machine):
    expected = "server.exe" if system == "Windows" else "server"
    return next(asset for asset in assets if asset.name == expected)

custom = replace(resolver, asset_selector=choose_custom)
```

The selector receives a tuple of `ReleaseAsset(name, url)` objects. Unknown return
values are rejected; selector exceptions propagate.

## Override exact filenames manually

```python
manual = GitHubReleaseResolver(
    "your-org", "your-project",
    assets={
        ("Windows", "AMD64"): "custom-binary.exe",
        ("Linux", "x86_64"): "custom-binary",
    },
)

# Mapping + explicit version constructs a URL without metadata requests.
url = manual.asset_url("v1.0", system="Windows", machine="AMD64")
# https://github.com/your-org/your-project/releases/download/v1.0/custom-binary.exe
```

Mappings are optional, nonempty when supplied, copied, and read-only. Keys are
exact and case-sensitive with no alias normalization; several keys may select
the same file. `assets=None` enables discovery. Do not combine `assets` with
`asset_selector`. With a mapping, `asset_name` needs no I/O and ignores its version
argument because the mapping is version-independent.

## Replace the metadata source

```python
from collections.abc import Iterable
from zuu.case16 import Candidate, GitHubReleaseClient, ReleaseAsset, ResolutionSource

# Built-in unauthenticated public GitHub API client; positive finite socket timeout.
with_timeout = replace(resolver, client=GitHubReleaseClient(timeout=10.0))

# A CandidateSource can own credentials, transport, and metadata discovery.
class InternalSource:
    def latest_release(self, owner: str, repository: str) -> Candidate:
        return Candidate("v3.0", ResolutionSource.RELEASE)

    def candidates(
        self, owner: str, repository: str, source: ResolutionSource
    ) -> Iterable[Candidate]:
        yield Candidate("v2.0", source, {"approved": True})
        yield Candidate("v3.0", source, {"approved": True})

    def release_assets(
        self, owner: str, repository: str, tag: str
    ) -> Iterable[ReleaseAsset]:
        yield ReleaseAsset(
            "tool-x86_64-pc-windows-msvc.exe",
            f"https://downloads.example.com/{tag}/tool.exe",
        )

internal = replace(resolver, client=InternalSource(), source="tag")
assert internal.resolve_version() == "v3.0"
selected = internal.resolve_asset("v3.0", system="Windows", machine="AMD64")
```

Candidates must match the requested source. Asset discovery must return the
complete list for the exact tag. Duplicate names and invalid models are errors.
The default client reads pages of 100 until a short/empty page, including separate
asset pages, and skips assets still uploading. Later-page failures abort selection.

GitHub API references: [latest release](https://docs.github.com/en/rest/releases/releases#get-the-latest-release),
[release listing](https://docs.github.com/en/rest/releases/releases#list-releases),
[tag listing](https://docs.github.com/en/rest/repos/repos#list-repository-tags),
[published assets](https://docs.github.com/en/rest/releases/assets#list-release-assets).

## Replace the downloader

```python
from urllib.request import urlopen
from shutil import copyfileobj

# Downloader receives (URL, existing temporary Path), not the final destination.
def download(url: str, temporary: Path) -> None:
    with urlopen(url, timeout=10) as response:
        with temporary.open("wb") as output:
            copyfileobj(response, output)

binary = resolver.resolve(dest=destination, downloader=download)
```

Write the complete binary and return normally; the return value is ignored.
Raising aborts publication. The default downloader streams the published URL with
a 30-second socket timeout and normal redirects.

```text
Resolve version/assets -> download sibling temporary file
-> add POSIX execute bits (skip on Windows) -> atomically replace destination
```

Failures preserve an existing destination and clean up the temporary file.
Normal filesystem errors also apply to temporary-file creation and cleanup.
No checksum verification, archive extraction, binary execution, or content
validation is performed; empty content is permitted.

## Handle errors

```python
from urllib.error import HTTPError, URLError
from zuu.case16 import ReleaseResolverError

try:
    binary = resolver.resolve(dest=destination)
except ReleaseResolverError as error:
    print(f"Cannot select a version or binary: {error}")
except (HTTPError, URLError) as error:
    print(f"GitHub request/download failed: {error}")
except OSError as error:
    print(f"Filesystem operation failed: {error}")
```

`ReleaseResolverError` is a `ValueError`: it covers invalid declarations/metadata,
unsupported platforms, invalid filter/selector results, empty selections, and
missing or ambiguous binaries. Network, filesystem, callback, and custom-key
comparison errors propagate. Failures never silently choose another version,
source, source archive, or existing local binary.

| Input | Validation |
|-------|------------|
| Names and explicit tags | Nonempty printable strings without surrounding whitespace. |
| Owner, repository, asset filename | One component; no path separators, `:` / `<` / `>` / `"` / `\|` / `?` / `*`, dot-only names, or trailing dots. Filesystems may impose more restrictions. |
| Explicit tag | No `.` or `..`; `latest` requests automatic selection. URL components, including tag slashes, are encoded. |
| Asset URL | Absolute HTTPS URL without credentials, fragments, whitespace, or backslashes. |

## Verify this case

```powershell
uv run pytest -q tests/case16
```

Tests cover selection, filters/parsers, platform matching, source/asset pagination,
custom interfaces, destinations, replacement and failure cleanup, permissions,
and symlinks where supported. Filesystem fixtures use temporary directories;
network calls are substituted.
