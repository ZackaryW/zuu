"""Conflict-aware planning for managed output projections."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum

__purpose__ = (
    "Plan updates to managed outputs without overwriting unowned or locally changed content."
)
__depends__ = ()


class ProjectionPlanError(ValueError):
    """Projection declarations are empty, duplicated, or malformed."""


class ProjectionState(StrEnum):
    """Observed ownership and freshness of one managed output."""

    ABSENT = "absent"
    CURRENT = "current"
    OUTDATED = "outdated"
    MODIFIED = "modified"
    UNMANAGED = "unmanaged"
    FAILED = "failed"
    UNINSPECTABLE = "uninspectable"


class ProjectionDecision(StrEnum):
    """Non-mutating action chosen for one inspected projection."""

    CREATE = "create"
    UPDATE = "update"
    CURRENT = "current"
    CONFLICT = "conflict"
    REPAIR = "repair"
    PRESERVE = "preserve"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ManagedProjection:
    """Declare a managed output and the callback that inspects its state."""

    name: str
    inspect: Callable[[], ProjectionState] | None
    repairable: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ProjectionPlanError("projection name must not be empty")
        if self.inspect is not None and not callable(self.inspect):
            raise ProjectionPlanError(f"projection {self.name!r} inspector must be callable")


@dataclass(frozen=True, slots=True)
class ProjectionAction:
    """Record the observed state and planned decision for one output."""

    projection: ManagedProjection
    state: ProjectionState
    decision: ProjectionDecision
    detail: str | None = None


@dataclass(frozen=True, slots=True, init=False)
class ProjectionPlan:
    """Inspect managed projections once and plan safe actions without applying them."""

    actions: tuple[ProjectionAction, ...]

    def __init__(
        self,
        projections: Iterable[ManagedProjection],
        *,
        force: bool = False,
    ) -> None:
        declarations = tuple(projections)
        if not declarations:
            raise ProjectionPlanError("at least one managed projection is required")

        names = [projection.name for projection in declarations]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ProjectionPlanError(f"duplicate projection name: {duplicates[0]}")

        from .planning import inspect_projection

        actions = tuple(
            inspect_projection(projection, force=force)
            for projection in declarations
        )
        object.__setattr__(self, "actions", actions)

    @property
    def changes(self) -> tuple[ProjectionAction, ...]:
        """Return actions that would create, update, or repair managed output."""
        changes = {
            ProjectionDecision.CREATE,
            ProjectionDecision.UPDATE,
            ProjectionDecision.REPAIR,
        }
        return tuple(action for action in self.actions if action.decision in changes)

    @property
    def blocked(self) -> tuple[ProjectionAction, ...]:
        """Return conflicts and failed inspections that prevent a safe update."""
        blocked = {ProjectionDecision.CONFLICT, ProjectionDecision.BLOCKED}
        return tuple(action for action in self.actions if action.decision in blocked)

    @property
    def ok(self) -> bool:
        """Report whether the plan contains no conflicts or inspection failures."""
        return not self.blocked


__all__ = [
    "ProjectionPlan",
    "ManagedProjection",
    "ProjectionAction",
    "ProjectionState",
    "ProjectionDecision",
    "ProjectionPlanError",
]
