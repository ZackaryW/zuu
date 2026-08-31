"""Commit-cached synchronization of one public GitHub repository subpath."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from zuu.case5 import RepositoryPath

__purpose__ = (
    "Synchronize an owned directory from a public GitHub repository subpath, "
    "using its resolved commit as the cache marker."
)
__depends__ = ("case5",)

Pathish = str | os.PathLike[str]
_COMMIT = re.compile(r"[0-9a-fA-F]{40}")


class GitHubSubpathError(ValueError):
    """A source declaration or synchronization lifecycle could not complete."""


class GitHubClient(Protocol):
    """Resolve public GitHub revisions and download repository ZIP archives."""

    def resolve_commit(
        self,
        owner: str,
        repository: str,
        branch: str | None,
    ) -> str:
        """Return the full commit SHA for a branch or the default branch."""
        ...

    def download_archive(
        self,
        owner: str,
        repository: str,
        commit: str,
        destination: Path,
    ) -> None:
        """Write the ZIP archive for ``commit`` to ``destination``."""
        ...


@dataclass(frozen=True, slots=True)
class GitHubSyncResult:
    """Describe the resolved revision and whether the owned target changed."""

    target: Path
    commit: str
    changed: bool


@dataclass(frozen=True, slots=True)
class GitHubSubpath:
    """Declare one directory subpath in a public GitHub repository."""

    owner: str
    repository: str
    path: str
    branch: str | None = None
    commit: str | None = None

    def __post_init__(self) -> None:
        _validate_repository_component(self.owner, "owner")
        _validate_repository_component(self.repository, "repository")
        try:
            source_path = RepositoryPath(self.path)
        except ValueError as error:
            raise GitHubSubpathError(str(error)) from error
        object.__setattr__(self, "path", source_path.value)

        if self.branch is not None and self.commit is not None:
            raise GitHubSubpathError("branch and commit are mutually exclusive")
        if self.branch is not None:
            _validate_branch(self.branch)
        if self.commit is not None:
            object.__setattr__(self, "commit", _normalize_commit(self.commit))

    def sync(
        self,
        target: Pathish,
        *,
        client: GitHubClient | None = None,
    ) -> GitHubSyncResult:
        """Synchronize the owned target and return its resolved commit state.

        A matching ``.commit`` marker is authoritative: target content is not
        inspected. When the marker differs, the complete target is replaced.
        """
        destination = _inspect_target(target)
        active_client = client
        if self.commit is None:
            active_client = active_client or _default_client()
            try:
                desired_commit = _normalize_commit(
                    active_client.resolve_commit(
                        self.owner,
                        self.repository,
                        self.branch,
                    )
                )
            except GitHubSubpathError:
                raise
            except Exception as error:
                raise GitHubSubpathError(
                    "could not resolve the requested GitHub revision"
                ) from error
        else:
            desired_commit = self.commit

        if _read_marker(destination) == desired_commit:
            return GitHubSyncResult(destination, desired_commit, False)

        active_client = active_client or _default_client()
        _synchronize(
            self,
            destination,
            desired_commit,
            active_client,
        )
        return GitHubSyncResult(destination, desired_commit, True)


def _default_client() -> GitHubClient:
    from .client import GitHubApiClient

    return GitHubApiClient()


def _synchronize(
    source: GitHubSubpath,
    target: Path,
    commit: str,
    client: GitHubClient,
) -> None:
    from .archive import materialize_subpath

    parent = target.parent
    try:
        with tempfile.TemporaryDirectory(
            dir=parent,
            prefix=f".{target.name}.zuu-",
        ) as temporary_name:
            temporary = Path(temporary_name)
            archive = temporary / "repository.zip"
            staged = temporary / "content"
            try:
                client.download_archive(
                    source.owner,
                    source.repository,
                    commit,
                    archive,
                )
            except GitHubSubpathError:
                raise
            except Exception as error:
                raise GitHubSubpathError(
                    "could not download the requested GitHub archive"
                ) from error
            materialize_subpath(archive, RepositoryPath(source.path), staged)
            (staged / ".commit").write_text(commit + "\n", encoding="ascii")
            _replace_target(staged, target, temporary / "previous")
    except GitHubSubpathError:
        raise
    except OSError as error:
        raise GitHubSubpathError(f"could not synchronize target: {target}") from error


def _replace_target(staged: Path, target: Path, backup: Path) -> None:
    previous_moved = False
    try:
        if target.exists():
            target.replace(backup)
            previous_moved = True
        staged.replace(target)
    except OSError as error:
        if previous_moved and backup.exists() and not target.exists():
            try:
                backup.replace(target)
            except OSError as restore_error:
                error.add_note(f"failed to restore previous target: {restore_error}")
        raise


def _inspect_target(value: Pathish) -> Path:
    try:
        target = Path(value).absolute()
    except (TypeError, OSError) as error:
        raise GitHubSubpathError(f"invalid target path: {value!r}") from error
    if not target.name:
        raise GitHubSubpathError("target must name a directory below an existing parent")
    parent = target.parent
    if not parent.is_dir():
        raise GitHubSubpathError(f"target parent is not a directory: {parent}")
    try:
        redirected = target.is_symlink() or target.is_junction()
    except OSError as error:
        raise GitHubSubpathError(f"target is unavailable: {target}") from error
    if redirected:
        raise GitHubSubpathError(f"target must not be redirected: {target}")
    if target.exists() and not target.is_dir():
        raise GitHubSubpathError(f"target is not a directory: {target}")
    return target


def _read_marker(target: Path) -> str | None:
    if not target.is_dir():
        return None
    marker = target / ".commit"
    try:
        if marker.is_symlink() or not marker.is_file():
            return None
        value = marker.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return None
    return value if _COMMIT.fullmatch(value) else None


def _validate_repository_component(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(character in value for character in "/\\\0\r\n")
    ):
        raise GitHubSubpathError(f"{label} must be one non-empty GitHub path segment")


def _validate_branch(branch: str) -> None:
    if (
        not isinstance(branch, str)
        or not branch
        or branch != branch.strip()
        or any(character in branch for character in "\0\r\n")
    ):
        raise GitHubSubpathError("branch must be a non-empty single-line name")


def _normalize_commit(commit: str) -> str:
    if not isinstance(commit, str) or _COMMIT.fullmatch(commit) is None:
        raise GitHubSubpathError("commit must be a full 40-character hexadecimal SHA")
    return commit.lower()


__all__ = [
    "GitHubSubpath",
    "GitHubSyncResult",
    "GitHubClient",
    "GitHubSubpathError",
]
