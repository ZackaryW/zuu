"""Inspection and decision rules for managed projections."""

from __future__ import annotations

from . import (
    ManagedProjection,
    ProjectionAction,
    ProjectionDecision,
    ProjectionState,
)


def inspect_projection(
    projection: ManagedProjection,
    *,
    force: bool,
) -> ProjectionAction:
    """Inspect once and map the result to a conflict-aware planning decision."""
    if projection.inspect is None:
        return ProjectionAction(
            projection,
            ProjectionState.UNINSPECTABLE,
            ProjectionDecision.BLOCKED,
            "no inspector was declared",
        )

    try:
        state = projection.inspect()
    except Exception as error:
        return ProjectionAction(
            projection,
            ProjectionState.FAILED,
            ProjectionDecision.BLOCKED,
            f"inspection failed: {error}",
        )

    if not isinstance(state, ProjectionState):
        return ProjectionAction(
            projection,
            ProjectionState.FAILED,
            ProjectionDecision.BLOCKED,
            f"inspector returned invalid state: {state!r}",
        )

    return ProjectionAction(
        projection,
        state,
        _decision_for(state, force=force, repairable=projection.repairable),
    )


def _decision_for(
    state: ProjectionState,
    *,
    force: bool,
    repairable: bool,
) -> ProjectionDecision:
    if state is ProjectionState.ABSENT:
        return ProjectionDecision.CREATE
    if state is ProjectionState.OUTDATED:
        return ProjectionDecision.UPDATE
    if state is ProjectionState.CURRENT:
        return ProjectionDecision.UPDATE if force else ProjectionDecision.CURRENT
    if state is ProjectionState.MODIFIED:
        if force and repairable:
            return ProjectionDecision.REPAIR
        return ProjectionDecision.CONFLICT
    if state is ProjectionState.UNMANAGED:
        return ProjectionDecision.PRESERVE
    return ProjectionDecision.BLOCKED
