"""Git-ignore policies, plans, and public lifecycle operations."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

__purpose__ = "Plan, apply, and verify Git-ignore coverage for selected paths."
__depends__ = ()

Pathish = str | os.PathLike[str]


class GitIgnoreError(ValueError):
    """A Git-ignore request cannot be established safely."""


class IgnoreMode(StrEnum):
    """Supported policies for selected ignore paths."""

    EXACT = "exact"
    PATTERN = "pattern"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class GitIgnorePolicy:
    """Select exact rules, one caller pattern, or complete Git bypass."""

    mode: IgnoreMode = IgnoreMode.EXACT
    pattern: str | None = None

    def __post_init__(self) -> None:
        mode = IgnoreMode(self.mode)
        object.__setattr__(self, "mode", mode)
        if mode is IgnoreMode.PATTERN:
            if self.pattern is None or not self.pattern:
                raise ValueError("pattern ignore policy requires one pattern")
            if any(character in self.pattern for character in "\r\n\0"):
                raise ValueError("ignore pattern must be a single-line string")
        elif self.pattern is not None:
            raise ValueError(f"{mode.value} ignore policy does not accept a pattern")


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Decoded result returned by a Git process runner."""

    returncode: int
    stdout: str
    stderr: str


class ProcessRunner(Protocol):
    """Injectable command boundary used for Git discovery and evaluation."""

    def __call__(self, argv: Sequence[str], cwd: Path) -> ProcessResult: ...


@dataclass(frozen=True, slots=True)
class GitIgnorePlan:
    """A non-mutating proposal tied to the observed root `.gitignore` bytes."""

    worktree: Path
    ignore_file: Path
    original: bytes | None
    proposed: bytes | None
    probes: tuple[Path, ...]

    @property
    def changed(self) -> bool:
        """Whether applying this plan would write `.gitignore`."""
        return self.proposed is not None


from .gitignore import apply_gitignore, plan_gitignore, verify_gitignore
from .process import run_process

__all__ = [
    "GitIgnoreError",
    "GitIgnorePlan",
    "GitIgnorePolicy",
    "IgnoreMode",
    "ProcessResult",
    "ProcessRunner",
    "apply_gitignore",
    "plan_gitignore",
    "run_process",
    "verify_gitignore",
]
