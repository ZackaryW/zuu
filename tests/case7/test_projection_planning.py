import pytest

from zuu.case7 import (
    ManagedProjection,
    ProjectionDecision,
    ProjectionPlan,
    ProjectionState,
)


def projection(
    state: ProjectionState,
    *,
    repairable: bool = False,
) -> ManagedProjection:
    return ManagedProjection(state.value, lambda: state, repairable=repairable)


@pytest.mark.parametrize(
    "state, decision",
    [
        (ProjectionState.ABSENT, ProjectionDecision.CREATE),
        (ProjectionState.CURRENT, ProjectionDecision.CURRENT),
        (ProjectionState.OUTDATED, ProjectionDecision.UPDATE),
        (ProjectionState.MODIFIED, ProjectionDecision.CONFLICT),
        (ProjectionState.UNMANAGED, ProjectionDecision.PRESERVE),
        (ProjectionState.FAILED, ProjectionDecision.BLOCKED),
        (ProjectionState.UNINSPECTABLE, ProjectionDecision.BLOCKED),
    ],
)
def test_default_decision_matrix(
    state: ProjectionState,
    decision: ProjectionDecision,
) -> None:
    action = ProjectionPlan([projection(state)]).actions[0]

    assert action.decision is decision


def test_force_refreshes_current_output() -> None:
    action = ProjectionPlan(
        [projection(ProjectionState.CURRENT)],
        force=True,
    ).actions[0]

    assert action.decision is ProjectionDecision.UPDATE


def test_force_repairs_modified_output_only_when_declared_repairable() -> None:
    repair = ProjectionPlan(
        [projection(ProjectionState.MODIFIED, repairable=True)],
        force=True,
    ).actions[0]
    conflict = ProjectionPlan(
        [projection(ProjectionState.MODIFIED)],
        force=True,
    ).actions[0]

    assert repair.decision is ProjectionDecision.REPAIR
    assert conflict.decision is ProjectionDecision.CONFLICT


def test_force_preserves_unmanaged_output() -> None:
    action = ProjectionPlan(
        [projection(ProjectionState.UNMANAGED)],
        force=True,
    ).actions[0]

    assert action.decision is ProjectionDecision.PRESERVE


def test_plan_summarizes_changes_and_blockers_in_declaration_order() -> None:
    projections = [
        ManagedProjection("create", lambda: ProjectionState.ABSENT),
        ManagedProjection("preserve", lambda: ProjectionState.UNMANAGED),
        ManagedProjection("conflict", lambda: ProjectionState.MODIFIED),
        ManagedProjection("update", lambda: ProjectionState.OUTDATED),
    ]

    plan = ProjectionPlan(projections)

    assert [action.projection.name for action in plan.changes] == ["create", "update"]
    assert [action.projection.name for action in plan.blocked] == ["conflict"]
    assert not plan.ok


def test_plan_without_blockers_is_ok() -> None:
    plan = ProjectionPlan(
        [
            projection(ProjectionState.CURRENT),
            projection(ProjectionState.UNMANAGED),
        ]
    )

    assert plan.ok
    assert plan.blocked == ()


def test_force_change_summary_includes_refresh_and_repair() -> None:
    plan = ProjectionPlan(
        [
            projection(ProjectionState.CURRENT),
            projection(ProjectionState.MODIFIED, repairable=True),
            projection(ProjectionState.UNMANAGED),
        ],
        force=True,
    )

    assert [action.decision for action in plan.changes] == [
        ProjectionDecision.UPDATE,
        ProjectionDecision.REPAIR,
    ]
    assert plan.ok
