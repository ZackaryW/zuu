"""Conservative affected-target selection for changed repository paths."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar

from zuu.case5 import RepositoryGlob, RepositoryPath, RepositoryPathError

__purpose__ = "Choose the smallest declared target set that safely covers changed repository paths."
__depends__ = ("case5",)

TargetValue = TypeVar("TargetValue")


class AffectedTargetsError(ValueError):
    """Affected-target definitions are empty, duplicated, or malformed."""


@dataclass(frozen=True, slots=True, init=False)
class AffectedTarget(Generic[TargetValue]):
    """One stable target value and the path patterns that affect it."""

    name: str
    value: TargetValue
    patterns: tuple[RepositoryGlob, ...]

    def __init__(
        self,
        name: str,
        value: TargetValue,
        patterns: Iterable[str | RepositoryGlob],
    ) -> None:
        if not name:
            raise AffectedTargetsError("target name must not be empty")
        compiled = tuple(
            pattern
            if isinstance(pattern, RepositoryGlob)
            else RepositoryGlob(pattern)
            for pattern in patterns
        )
        if not compiled:
            raise AffectedTargetsError(f"target {name!r} requires at least one pattern")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "patterns", compiled)


@dataclass(frozen=True, slots=True, init=False)
class AffectedTargets(Generic[TargetValue]):
    """Select declared targets conservatively from changed repository paths."""

    targets: tuple[AffectedTarget[TargetValue], ...]

    def __init__(self, targets: Iterable[AffectedTarget[TargetValue]]) -> None:
        selected = tuple(targets)
        if not selected:
            raise AffectedTargetsError("at least one affected target is required")
        names = [target.name for target in selected]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise AffectedTargetsError(f"duplicate target name: {duplicates[0]}")
        object.__setattr__(self, "targets", selected)

    def select(
        self,
        changed_paths: Iterable[str | RepositoryPath],
    ) -> tuple[AffectedTarget[TargetValue], ...]:
        """Return ordered matches, or every target when any path is uncovered."""
        paths = tuple(changed_paths)
        if not paths:
            return ()

        matched: set[str] = set()
        for value in paths:
            try:
                path = value if isinstance(value, RepositoryPath) else RepositoryPath(value)
            except RepositoryPathError:
                return self.targets
            names = {
                target.name
                for target in self.targets
                if any(pattern.matches(path) for pattern in target.patterns)
            }
            if not names:
                return self.targets
            matched.update(names)
        return tuple(target for target in self.targets if target.name in matched)


__all__ = ["AffectedTargets", "AffectedTarget", "AffectedTargetsError"]
