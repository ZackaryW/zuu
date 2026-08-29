"""Safe repository-relative paths and bounded glob patterns."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .patterns import compile_pattern, normalize_relative, validate_pattern

__purpose__ = "Make repository-relative path selection safe and predictable across platforms."
__depends__ = ()


class RepositoryPathError(ValueError):
    """A repository-relative path or pattern is unsafe or unsupported."""


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


__all__ = ["RepositoryPath", "RepositoryGlob", "RepositoryPathError"]
