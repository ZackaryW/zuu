"""Standard-library client for public GitHub repository archives."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from . import GitHubSubpathError

API_ROOT = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "zuu-case12",
}


@dataclass(frozen=True, slots=True)
class GitHubApiClient:
    """Access public GitHub metadata and ZIP archives through the REST API."""

    timeout: float = 30.0

    def resolve_commit(
        self,
        owner: str,
        repository: str,
        branch: str | None,
    ) -> str:
        """Resolve a selected branch, or the repository default, to a commit SHA."""
        selected = branch
        if selected is None:
            repository_data = self._read_json(self._repository_url(owner, repository))
            selected = repository_data.get("default_branch")
            if not isinstance(selected, str) or not selected:
                raise GitHubSubpathError(
                    "GitHub repository response has no default branch"
                )

        commit_data = self._read_json(
            f"{self._repository_url(owner, repository)}/commits/"
            f"{quote(selected, safe='')}"
        )
        commit = commit_data.get("sha")
        if not isinstance(commit, str):
            raise GitHubSubpathError("GitHub commit response has no SHA")
        return commit

    def download_archive(
        self,
        owner: str,
        repository: str,
        commit: str,
        destination: Path,
    ) -> None:
        """Follow GitHub's archive redirect and stream the ZIP to disk."""
        url = (
            f"{self._repository_url(owner, repository)}/zipball/"
            f"{quote(commit, safe='')}"
        )
        request = Request(url, headers=HEADERS)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                with destination.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
        except (HTTPError, URLError, OSError) as error:
            destination.unlink(missing_ok=True)
            raise GitHubSubpathError(
                f"GitHub archive request failed for {owner}/{repository}"
            ) from error

    def _read_json(self, url: str) -> dict[str, object]:
        request = Request(url, headers=HEADERS)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except (HTTPError, URLError, OSError) as error:
            raise GitHubSubpathError(f"GitHub API request failed: {url}") from error
        try:
            value = json.loads(payload)
        except (UnicodeError, json.JSONDecodeError) as error:
            raise GitHubSubpathError("GitHub API returned invalid JSON") from error
        if not isinstance(value, dict):
            raise GitHubSubpathError("GitHub API response must be a JSON object")
        return value

    @staticmethod
    def _repository_url(owner: str, repository: str) -> str:
        return f"{API_ROOT}/repos/{quote(owner, safe='')}/{quote(repository, safe='')}"
