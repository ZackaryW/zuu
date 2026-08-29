import pytest

from zuu.case7 import (
    ManagedProjection,
    ProjectionDecision,
    ProjectionPlan,
    ProjectionPlanError,
    ProjectionState,
)


def test_each_projection_is_inspected_once() -> None:
    calls: list[str] = []

    def inspect() -> ProjectionState:
        calls.append("output")
        return ProjectionState.CURRENT

    plan = ProjectionPlan([ManagedProjection("output", inspect)])

    assert calls == ["output"]
    assert plan.actions[0].state is ProjectionState.CURRENT


def test_duplicate_names_fail_before_inspection() -> None:
    inspected = False

    def inspect() -> ProjectionState:
        nonlocal inspected
        inspected = True
        return ProjectionState.CURRENT

    with pytest.raises(ProjectionPlanError, match="duplicate projection name"):
        ProjectionPlan(
            [
                ManagedProjection("output", inspect),
                ManagedProjection("output", inspect),
            ]
        )

    assert not inspected


def test_missing_inspector_is_blocked() -> None:
    action = ProjectionPlan([ManagedProjection("output", None)]).actions[0]

    assert action.state is ProjectionState.UNINSPECTABLE
    assert action.decision is ProjectionDecision.BLOCKED
    assert action.detail == "no inspector was declared"


def test_inspection_exception_is_blocked() -> None:
    def inspect() -> ProjectionState:
        raise OSError("cannot read output")

    action = ProjectionPlan([ManagedProjection("output", inspect)]).actions[0]

    assert action.state is ProjectionState.FAILED
    assert action.decision is ProjectionDecision.BLOCKED
    assert action.detail == "inspection failed: cannot read output"


def test_invalid_inspection_state_is_blocked() -> None:
    action = ProjectionPlan(
        [ManagedProjection("output", lambda: "current")]  # type: ignore[arg-type]
    ).actions[0]

    assert action.state is ProjectionState.FAILED
    assert action.decision is ProjectionDecision.BLOCKED
    assert action.detail == "inspector returned invalid state: 'current'"


def test_empty_plan_is_rejected() -> None:
    with pytest.raises(ProjectionPlanError, match="at least one managed projection"):
        ProjectionPlan([])


def test_empty_projection_name_is_rejected() -> None:
    with pytest.raises(ProjectionPlanError, match="projection name must not be empty"):
        ManagedProjection("", None)


def test_non_callable_inspector_is_rejected() -> None:
    with pytest.raises(ProjectionPlanError, match="inspector must be callable"):
        ManagedProjection("output", "current")  # type: ignore[arg-type]
