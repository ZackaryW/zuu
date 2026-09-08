"""Standard-library client for public GitHub raw file content."""

from __future__ import annotations

import math
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import GitHubVersionSource, RemoteDocumentError, SourceError

HEADERS = {"User-Agent": "zuu-case15"}


@dataclass(frozen=True, slots=True)
class GitHubRawClient:
    """Fetch one public GitHub raw file with a finite timeout."""

    timeout: float = 30.0

    def __post_init__(self) -> None:
        if (
            type(self.timeout) not in (int, float)
            or not math.isfinite(self.timeout)
            or self.timeout <= 0
        ):
            raise SourceError("timeout must be a finite positive number")

    def fetch(self, source: GitHubVersionSource) -> str:
        """Read and UTF-8 decode the normalized source's raw content."""
        request = Request(source.url, headers=HEADERS)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
            return payload.decode("utf-8")
        except (HTTPError, URLError, OSError, UnicodeError) as error:
            raise RemoteDocumentError(
                f"GitHub raw request failed: {source.url}"
            ) from error
