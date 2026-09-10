"""Resolve platform binaries from public GitHub tags or releases."""

from __future__ import annotations

import os
import platform
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol
from urllib.parse import quote, urlsplit

from .versions import parse_version

__purpose__ = "Discover and download matching platform binaries from GitHub tags or releases."
__depends__ = ()

Downloader = Callable[[str, Path], object]
VersionParser = Callable[[str], Any | None]


class ReleaseResolverError(ValueError):
    """A release declaration, tag, or platform cannot be resolved."""


class ResolutionSource(StrEnum):
    """Choose repository tags or published releases as version candidates."""

    TAG = "tag"
    RELEASE = "release"


def _text(value: str, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or not value.isprintable()
    ):
        raise ReleaseResolverError(
            f"{label} must be a nonempty printable string without surrounding whitespace"
        )
    return value


def _component(value: str, label: str) -> str:
    value = _text(value, label)
    if value in (".", "..") or any(char in value for char in '/\\:<>"|?*'):
        raise ReleaseResolverError(f"{label} must be one filename-safe component")
    if value.endswith("."):
        raise ReleaseResolverError(f"{label} must not end with a dot")
    return value


@dataclass(frozen=True, slots=True)
class Candidate:
    """A tag and its source metadata, exposed to caller-owned filters.

    ``metadata`` is a shallow read-only copy of the source record. GitHub release
    records include fields such as name, prerelease, and assets; tag records
    include name and commit. Treat nested metadata as read-only as well.
    """

    tag: str
    source: ResolutionSource | str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _version(self.tag)
        try:
            object.__setattr__(self, "source", ResolutionSource(self.source))
        except (TypeError, ValueError) as error:
            raise ReleaseResolverError(f"unsupported candidate source: {self.source!r}") from error
        if not isinstance(self.metadata, Mapping):
            raise ReleaseResolverError("candidate metadata must be a mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


CandidateFilter = Callable[[Candidate], bool]


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """A published asset's local filename and HTTPS browser download URL."""

    name: str
    url: str

    def __post_init__(self) -> None:
        _component(self.name, "asset")
        _text(self.url, "asset URL")
        try:
            parsed = urlsplit(self.url)
            valid = (
                parsed.scheme == "https" and parsed.hostname
                and parsed.username is None and parsed.password is None
                and not parsed.fragment and not any(char.isspace() for char in self.url)
                and "\\" not in self.url
            )
            parsed.port
        except ValueError as error:
            raise ReleaseResolverError("asset URL must be an absolute HTTPS URL") from error
        if not valid:
            raise ReleaseResolverError("asset URL must be an absolute HTTPS URL without credentials or fragment")


AssetSelector = Callable[[tuple[ReleaseAsset, ...], str, str], ReleaseAsset]


class CandidateSource(Protocol):
    """Replace discovery independently of platform selection and downloading."""

    def latest_release(self, owner: str, repository: str) -> Candidate:
        """Return the provider's latest published full release."""
        ...

    def candidates(
        self, owner: str, repository: str, source: ResolutionSource
    ) -> Iterable[Candidate]:
        """Yield all candidates of the requested kind, including later pages."""
        ...

    def release_assets(
        self, owner: str, repository: str, tag: str
    ) -> Iterable[ReleaseAsset]:
        """Yield all published assets attached to exactly this tag's release."""
        ...


@dataclass(frozen=True, slots=True)
class GitHubReleaseResolver:
    """Discover release assets and select a binary for the host platform.

    The default selector recognizes common Rust target suffixes. Optional assets
    provide an exact (OS, architecture) mapping instead of asset discovery.
    Versions default to the latest release; tags and filtered releases use the
    highest parsed version.
    """

    owner: str
    repository: str
    assets: Mapping[tuple[str, str], str] | None = None
    source: ResolutionSource | str = ResolutionSource.RELEASE
    candidate_filter: CandidateFilter | None = None
    version_parser: VersionParser = parse_version
    client: CandidateSource | None = None
    asset_selector: AssetSelector | None = None

    def __post_init__(self) -> None:
        _component(self.owner, "owner")
        _component(self.repository, "repository")
        if self.assets is not None:
            if not isinstance(self.assets, Mapping) or not self.assets:
                raise ReleaseResolverError("assets must be a nonempty platform-to-asset mapping")
            copied = {}
            for pair, asset in self.assets.items():
                if not isinstance(pair, tuple) or len(pair) != 2:
                    raise ReleaseResolverError("asset keys must be (system, machine) tuples")
                _text(pair[0], "system")
                _text(pair[1], "machine")
                copied[pair] = _component(asset, "asset")
            object.__setattr__(self, "assets", MappingProxyType(copied))
        if self.asset_selector is not None:
            if not callable(self.asset_selector):
                raise ReleaseResolverError("asset_selector must be callable")
            if self.assets is not None:
                raise ReleaseResolverError("use either assets or asset_selector, not both")
        try:
            object.__setattr__(self, "source", ResolutionSource(self.source))
        except (TypeError, ValueError) as error:
            raise ReleaseResolverError(f"unsupported source: {self.source!r}") from error
        if self.candidate_filter is not None and not callable(self.candidate_filter):
            raise ReleaseResolverError("candidate_filter must be callable")
        if not callable(self.version_parser):
            raise ReleaseResolverError("version_parser must be callable")

    def resolve_version(self, version: str | None = None) -> str:
        """Return an explicit tag or discover the latest eligible source version.

        None or 'latest' (case-insensitive) requests automatic selection. An
        explicit tag bypasses discovery, filters, and parsing. For candidate
        selection, filter first, then parse; None keys are skipped and the highest
        comparable key wins. Equal keys retain the first source candidate.
        Callback and transport exceptions propagate without fallback.
        """
        if version is not None:
            _text(version, "version")
            if version.lower() != "latest":
                _version(version)
                return version

        client = self.client if self.client is not None else GitHubReleaseClient()
        if (
            self.source is ResolutionSource.RELEASE
            and self.candidate_filter is None
            and self.version_parser is parse_version
        ):
            candidate = client.latest_release(self.owner, self.repository)
            self._check_candidate(candidate)
            return candidate.tag

        selected = None
        selected_key = None
        for candidate in client.candidates(self.owner, self.repository, self.source):
            self._check_candidate(candidate)
            if self.candidate_filter is not None:
                accepted = self.candidate_filter(candidate)
                if type(accepted) is not bool:
                    raise ReleaseResolverError("candidate_filter must return bool")
                if not accepted:
                    continue
            key = self.version_parser(candidate.tag)
            if key is None:
                continue
            if selected is None or key > selected_key:
                selected, selected_key = candidate, key
        if selected is None:
            raise ReleaseResolverError(f"no eligible version in {self.source.value} source")
        return selected.tag

    def _check_candidate(self, candidate: Candidate) -> None:
        if not isinstance(candidate, Candidate) or candidate.source is not self.source:
            raise ReleaseResolverError("source returned an invalid or mismatched candidate")

    def asset_name(
        self, version: str | None = None, *, system: str | None = None, machine: str | None = None
    ) -> str:
        """Discover a matching asset name; an explicit mapping needs no I/O."""
        system, machine = _platform(system, machine)
        if self.assets is None:
            return self.resolve_asset(version, system=system, machine=machine).name
        return self._mapped_asset_name(system, machine)

    def _mapped_asset_name(self, system: str, machine: str) -> str:
        try:
            return self.assets[(system, machine)]
        except KeyError as error:
            raise ReleaseResolverError(
                f"no release asset for platform ({system}, {machine})"
            ) from error

    def resolve_asset(
        self, version: str | None = None, *, system: str | None = None, machine: str | None = None
    ) -> ReleaseAsset:
        """Resolve one version and its binary before any filesystem mutation.

        Automatic selection uses published asset metadata and the selected
        browser URL. A custom selector must return one of the discovered assets.
        A manual mapping bypasses asset discovery and constructs the direct URL.
        """
        system, machine = _platform(system, machine)
        if self.assets is not None:
            name = self._mapped_asset_name(system, machine)
            return ReleaseAsset(name, self._url(self.resolve_version(version), name))
        tag = self.resolve_version(version)
        client = self.client if self.client is not None else GitHubReleaseClient()
        available = tuple(client.release_assets(self.owner, self.repository, tag))
        if any(not isinstance(asset, ReleaseAsset) for asset in available):
            raise ReleaseResolverError("source returned an invalid release asset")
        if len({asset.name for asset in available}) != len(available):
            raise ReleaseResolverError("source returned duplicate asset names")
        selector = self.asset_selector if self.asset_selector is not None else select_rust_asset
        selected = selector(available, system, machine)
        if not isinstance(selected, ReleaseAsset) or selected not in available:
            raise ReleaseResolverError("asset_selector must return a discovered ReleaseAsset")
        return selected

    def asset_url(
        self, version: str | None = None, *, system: str | None = None, machine: str | None = None
    ) -> str:
        """Return the selected asset URL, discovering version/assets as needed."""
        return self.resolve_asset(version, system=system, machine=machine).url

    def resolve(
        self,
        version: str | None = None,
        dest: str | os.PathLike[str] | None = None,
        *,
        downloader: Downloader | None = None,
    ) -> Path:
        """Download for the host and atomically replace the destination on success.

        The default destination is the asset filename in the current directory.
        Its parent must already exist. Every call downloads again. A custom
        downloader receives (URL, temporary Path), writes the complete binary,
        and returns any value (ignored). Exceptions propagate; failed downloads,
        permission changes, and replacements preserve any existing destination.
        """
        from .download import install_binary

        asset = self.resolve_asset(version)
        destination = Path(asset.name if dest is None else dest)
        install_binary(asset.url, destination, downloader=downloader)
        return destination

    def _url(self, version: str, asset: str) -> str:
        owner, repository, version, asset = (
            quote(value, safe="") for value in (self.owner, self.repository, version, asset)
        )
        return f"https://github.com/{owner}/{repository}/releases/download/{version}/{asset}"


def _version(value: str) -> None:
    _text(value, "version")
    if value.lower() == "latest" or value in (".", ".."):
        raise ReleaseResolverError("version must be an explicit release tag, not latest")


def _platform(system: str | None, machine: str | None) -> tuple[str, str]:
    return (
        _text(platform.system() if system is None else system, "system"),
        _text(platform.machine() if machine is None else machine, "machine"),
    )


from .assets import select_rust_asset
from .sources import GitHubReleaseClient

__all__ = [
    "GitHubReleaseResolver",
    "ResolutionSource",
    "Candidate",
    "CandidateSource",
    "GitHubReleaseClient",
    "ReleaseAsset",
    "AssetSelector",
    "select_rust_asset",
    "CandidateFilter",
    "VersionParser",
    "parse_version",
    "ReleaseResolverError",
    "Downloader",
]
