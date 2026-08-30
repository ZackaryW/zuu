"""Portable path identities, bounded globs, and confined target evidence."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Self

from .patterns import compile_pattern, normalize_relative, validate_pattern

__purpose__ = (
    "Treat paths like addresses inside a fenced property, keeping repository "
    "selection and exact target planning portable and confined."
)
__depends__ = ()


class ConfinedPathError(ValueError):
    """A confined identity, root, target state, or filesystem entry is invalid."""


class StaleTargetError(ConfinedPathError):
    """Captured target evidence no longer matches the filesystem."""


class RepositoryPathError(ConfinedPathError):
    """A repository-relative path or pattern is unsafe or unsupported."""


class TargetState(StrEnum):
    """Filesystem states supported by strict confined target inspection."""

    ABSENT = "absent"
    FILE = "file"
    DIRECTORY = "directory"


@dataclass(frozen=True, slots=True)
class TargetEvidence:
    """Observable entry identity captured for one root or target component.

    File size and timestamps are recorded only for regular files. Directory
    descendants and file bytes remain outside the evidence boundary.
    """

    relative_path: str
    state: TargetState
    device: int
    inode: int
    mode: int
    size: int | None
    modified_ns: int | None
    changed_ns: int | None
    file_attributes: int | None


@dataclass(frozen=True, slots=True)
class ConfinedTargetPlan:
    """Immutable target state and evidence beneath one trusted root."""

    path: ConfinedPath
    declared_root: Path
    root: Path
    target: Path
    state: TargetState
    allowed: frozenset[TargetState]
    evidence: tuple[TargetEvidence, ...]
    missing: tuple[str, ...]

    def revalidate(self) -> Self:
        """Return this plan when its evidence is unchanged, otherwise raise."""
        from .targets import revalidate_plan

        revalidate_plan(self)
        return self


@dataclass(frozen=True, slots=True)
class ConfinedPath:
    """A portable relative identity that can inspect an exact confined target."""

    value: str

    def __post_init__(self) -> None:
        try:
            normalized = normalize_relative(self.value, label="confined path")
        except (TypeError, ValueError) as error:
            raise ConfinedPathError(str(error)) from error
        object.__setattr__(self, "value", normalized)

    @property
    def parts(self) -> tuple[str, ...]:
        """Return the canonical path segments."""
        return PurePosixPath(self.value).parts

    def inspect(
        self,
        root: str | os.PathLike[str],
        *,
        allowed: Iterable[TargetState] | None = None,
    ) -> ConfinedTargetPlan:
        """Inspect an exact target below ``root`` without following descendants."""
        from .targets import inspect_path

        return inspect_path(self, root, allowed=allowed)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class RepositoryPath:
    """A canonical repository-relative path using portable POSIX separators."""

    value: str

    def __post_init__(self) -> None:
        try:
            normalized = normalize_relative(self.value)
        except (TypeError, ValueError) as error:
            raise RepositoryPathError(str(error)) from error
        object.__setattr__(self, "value", normalized)

    @property
    def parts(self) -> tuple[str, ...]:
        """Return the canonical path segments."""
        return PurePosixPath(self.value).parts

    def resolve_file(self, root: Path) -> Path:
        """Resolve an existing regular file while confining it to `root`."""
        try:
            resolved_root = root.resolve(strict=True)
            candidate = resolved_root.joinpath(*self.parts).resolve(strict=True)
        except OSError as error:
            raise RepositoryPathError(
                f"repository file is unavailable: {self.value}"
            ) from error
        if not resolved_root.is_dir():
            raise RepositoryPathError(f"repository root is not a directory: {root}")
        try:
            candidate.relative_to(resolved_root)
        except ValueError as error:
            raise RepositoryPathError(
                f"repository file escapes its root: {self.value}"
            ) from error
        if not candidate.is_file():
            raise RepositoryPathError(
                f"repository path is not a file: {self.value}"
            )
        return candidate

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class RepositoryGlob:
    """A validated glob that matches one complete repository-relative path."""

    pattern: str

    def __post_init__(self) -> None:
        try:
            validate_pattern(self.pattern)
        except (TypeError, ValueError) as error:
            raise RepositoryPathError(str(error)) from error

    def matches(self, path: str | RepositoryPath) -> bool:
        """Return whether the complete canonical path matches this pattern."""
        candidate = path if isinstance(path, RepositoryPath) else RepositoryPath(path)
        return compile_pattern(self.pattern).match(candidate.value) is not None


__all__ = [
    "ConfinedPath",
    "ConfinedTargetPlan",
    "TargetEvidence",
    "TargetState",
    "ConfinedPathError",
    "StaleTargetError",
    "RepositoryPath",
    "RepositoryGlob",
    "RepositoryPathError",
]
