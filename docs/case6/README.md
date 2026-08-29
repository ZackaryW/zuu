# case6: Affected target selection

`case6` chooses the smallest declared target set that safely covers changed
repository paths. It returns precise matches when every path is understood and
falls back to all declared targets when any input is invalid or uncovered.

## Dependencies

This case depends directly on `case5` for canonical repository paths and validated
glob matching.

## Declare targets

Each `AffectedTarget` has a stable name, a caller-owned value, and one or more
repository glob patterns. `AffectedTargets` preserves declaration order:

```python
from zuu.case6 import AffectedTarget, AffectedTargets


targets = AffectedTargets(
    [
        AffectedTarget("library", "unit", ["src/**", "tests/**"]),
        AffectedTarget("docs", "documentation", ["docs/**"]),
    ]
)
```

Patterns may be strings or prebuilt `case5.RepositoryGlob` instances. The target
value is generic and is returned unchanged, so it can be a command name, callable,
configuration object, or another application-defined value.

## Select affected targets

Call `select()` with changed path strings or `case5.RepositoryPath` values:

```python
selected = targets.select(["src/zuu/case6/__init__.py", "docs/case6/README.md"])

print([target.name for target in selected])
# ['library', 'docs']
```

Matches are deduplicated and returned in declaration order. An empty changed-path
set returns an empty tuple.

The conservative fallback is intentional. If one changed path is malformed or
matches none of the declared patterns, `select()` returns every target rather than
guessing that an unrecognized change is harmless. A path may match multiple targets;
all of those targets are selected.

## Errors

- `AffectedTargetsError` is raised for an empty target collection, duplicate target
  names, empty target names, or targets without patterns.
- `case5.RepositoryPathError` may be raised while constructing malformed target
  patterns. Invalid changed paths are handled by the conservative all-target
  fallback instead.

## Tests

Run the focused suite with:

```powershell
uv run pytest -q tests/case6
```
