# case7: Managed projection planning

`case7` plans updates to managed outputs without overwriting unowned or locally
changed content. It inspects each declared projection once and records decisions;
it never creates, updates, repairs, or deletes an output itself.

## Dependencies

This case is standalone and uses only the Python standard library.

## Declare and inspect projections

A `ManagedProjection` names an output and supplies a zero-argument inspector that
returns its `ProjectionState`:

```python
from zuu.case7 import (
    ManagedProjection,
    ProjectionDecision,
    ProjectionPlan,
    ProjectionState,
)


projections = [
    ManagedProjection("generated-index", lambda: ProjectionState.OUTDATED),
    ManagedProjection("local-config", lambda: ProjectionState.UNMANAGED),
]
plan = ProjectionPlan(projections)

for action in plan.actions:
    print(action.projection.name, action.state, action.decision)
```

Names must be non-empty and unique within a plan. Validation happens before any
inspector runs. After validation, each inspector is called exactly once in
declaration order.

## Decision lifecycle

The normal planning matrix is:

| State | Decision | Meaning |
|-------|----------|---------|
| `ABSENT` | `CREATE` | The managed output can be created. |
| `CURRENT` | `CURRENT` | No update is needed. |
| `OUTDATED` | `UPDATE` | The owned output can be refreshed. |
| `MODIFIED` | `CONFLICT` | Local changes prevent a safe overwrite. |
| `UNMANAGED` | `PRESERVE` | The output is not owned and must remain untouched. |
| `FAILED` | `BLOCKED` | Inspection could not establish a safe action. |
| `UNINSPECTABLE` | `BLOCKED` | No usable inspector was available. |

An absent inspector produces `UNINSPECTABLE`. An exception or a return value that
is not a `ProjectionState` produces `FAILED`. Both cases retain an explanation in
`ProjectionAction.detail` and block the plan instead of guessing.

## Force and repairability

`ProjectionPlan(projections, force=True)` changes only two decisions:

- a `CURRENT` output becomes `UPDATE`, allowing an intentional refresh;
- a `MODIFIED` output becomes `REPAIR` only when its declaration also has
  `repairable=True`.

A modified output that is not declared repairable remains a conflict. An unmanaged
output is always preserved, including under force. `force` therefore does not grant
ownership or general overwrite permission.

```python
repairable = ManagedProjection(
    "generated-index",
    lambda: ProjectionState.MODIFIED,
    repairable=True,
)
plan = ProjectionPlan([repairable], force=True)
assert plan.actions[0].decision is ProjectionDecision.REPAIR
```

## Consume a plan

`plan.changes` contains `CREATE`, `UPDATE`, and `REPAIR` actions. `plan.blocked`
contains conflicts and failed inspections. `plan.ok` is true only when the blocked
collection is empty. All collections preserve declaration order.

Applying a change is deliberately outside this case. Callers may feed the planned
actions into their own renderer, writer, transaction, or approval workflow without
giving this utility mutation authority.

## Errors

`ProjectionPlanError` is raised for empty plans, empty projection names, non-callable
inspectors, and duplicate projection names. Runtime inspection failures are captured
as blocked actions rather than raised.

## Tests

Run the focused suite with:

```powershell
uv run pytest -q tests/case7
```
