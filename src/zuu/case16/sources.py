"""Public GitHub release and tag discovery with complete pagination."""

from __future__ import annotations

import json
import math
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

from . import Candidate, ReleaseAsset, ReleaseResolverError, ResolutionSource, _component, _version


@dataclass(frozen=True, slots=True)
class GitHubReleaseClient:
    """Discover public GitHub metadata with a configurable socket timeout.

    Requests are unauthenticated. GitHub HTTP errors, including rate limits,
    propagate. Supply a CandidateSource for another transport or credentials.
    """

    timeout: float = 30.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.timeout, bool)
            or not isinstance(self.timeout, (int, float))
            or not math.isfinite(self.timeout)
            or self.timeout <= 0
        ):
            raise ReleaseResolverError("timeout must be a positive finite number")

    def latest_release(self, owner: str, repository: str) -> Candidate:
        """Parse GitHub's latest published full release, without version sorting."""
        data = self._get(self._base(owner, repository) + "/releases/latest")
        candidate = _candidate(data, ResolutionSource.RELEASE)
        if candidate.metadata.get("draft") or candidate.metadata.get("prerelease"):
            raise ReleaseResolverError("latest release response is not a published full release")
        return candidate

    def candidates(
        self, owner: str, repository: str, source: ResolutionSource | str
    ) -> Iterator[Candidate]:
        """Yield all tags or non-draft releases, following numbered API pages.

        Releases include prereleases so caller filters can decide eligibility.
        Continue through full pages until a short or empty page is received.
        """
        try:
            source = ResolutionSource(source)
        except (TypeError, ValueError) as error:
            raise ReleaseResolverError(f"unsupported source: {source!r}") from error
        endpoint = "tags" if source is ResolutionSource.TAG else "releases"
        base = self._base(owner, repository)
        page = 1
        while True:
            data = self._get(f"{base}/{endpoint}?per_page=100&page={page}")
            if not isinstance(data, list):
                raise ReleaseResolverError("candidate response must be a JSON array")
            for item in data:
                candidate = _candidate(item, source)
                if source is ResolutionSource.RELEASE and candidate.metadata.get("draft"):
                    continue
                yield candidate
            if len(data) < 100:
                return
            page += 1

    def release_assets(
        self, owner: str, repository: str, tag: str
    ) -> Iterator[ReleaseAsset]:
        """Find the exact tag's release and enumerate all uploaded binary assets.

        Asset pages are read separately from the release's embedded asset list to
        avoid truncated listings. Source-code archive links are not release assets.
        """
        _version(tag)
        base = self._base(owner, repository)
        release = self._get(f"{base}/releases/tags/{quote(tag, safe='')}")
        candidate = _candidate(release, ResolutionSource.RELEASE)
        if candidate.tag != tag or candidate.metadata.get("draft"):
            raise ReleaseResolverError("release does not match the requested published tag")
        release_id = candidate.metadata.get("id")
        if type(release_id) is not int or release_id <= 0:
            raise ReleaseResolverError("release response needs a positive integer id")
        page = 1
        while True:
            data = self._get(f"{base}/releases/{release_id}/assets?per_page=100&page={page}")
            if not isinstance(data, list):
                raise ReleaseResolverError("assets response must be a JSON array")
            for item in data:
                if not isinstance(item, dict):
                    raise ReleaseResolverError("asset must be a JSON object")
                state = item.get("state", "uploaded")
                if state == "starter":
                    continue
                if state != "uploaded":
                    raise ReleaseResolverError("invalid release asset state")
                yield ReleaseAsset(item.get("name"), item.get("browser_download_url"))
            if len(data) < 100:
                return
            page += 1

    def _base(self, owner: str, repository: str) -> str:
        owner = quote(_component(owner, "owner"), safe="")
        repository = quote(_component(repository, "repository"), safe="")
        return f"https://api.github.com/repos/{owner}/{repository}"

    def _get(self, url: str) -> object:
        request = Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "zuu-case16",
        })
        with urlopen(request, timeout=self.timeout) as response:
            try:
                return json.load(response)
            except (ValueError, UnicodeError) as error:
                raise ReleaseResolverError("invalid GitHub JSON response") from error


def _candidate(data: object, source: ResolutionSource) -> Candidate:
    if not isinstance(data, dict):
        raise ReleaseResolverError("candidate must be a JSON object")
    tag = data.get("name" if source is ResolutionSource.TAG else "tag_name")
    if source is ResolutionSource.RELEASE:
        for flag in ("draft", "prerelease"):
            if flag in data and type(data[flag]) is not bool:
                raise ReleaseResolverError(f"release {flag} must be a boolean")
    return Candidate(tag, source, data)
