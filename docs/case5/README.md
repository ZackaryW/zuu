# case5: Safe rooted paths

`case5` treats paths like addresses inside a fenced property. It keeps portable
identities and repository globs predictable, and it can survey an exact file,
directory, or empty destination beneath a trusted root before a caller acts.

## Dependencies

This case is standalone and uses only the Python standard library.

## Inspect a confined target

`ConfinedPath` accepts a non-empty relative identity written with `/` separators.
Absolute paths, Windows drive paths, backslashes, `.` or `..` segments, redundant
separators, empty values, and null bytes are rejected before filesystem inspection.

```python
from pathlib import Path

from zuu.case5 import ConfinedPath, TargetState


root = Path.home() / ".config" / "my-tool"
plan = ConfinedPath("profiles/team/default.toml").inspect(
    root,
    allowed={TargetState.ABSENT, TargetState.FILE},
)

print(plan.state)
print(plan.target)
```

The trusted root must already resolve to a directory. Inspection classifies the
target as `ABSENT`, `FILE`, or `DIRECTORY`. An absent nested target does not cause
case5 to create its missing parent chain; `plan.missing` records those remaining
segments instead.

`allowed` defaults to all three states. Supply a non-empty set of `TargetState`
values when an operation needs a stricter precondition. For example, allowing only
`ABSENT` prevents a create workflow from silently accepting an occupied target.

The returned `ConfinedTargetPlan` is frozen and contains:

- `path`: the portable `ConfinedPath` identity;
- `declared_root`: the absolute root spelling supplied at inspection time;
- `root`: the resolved physical root directory;
- `target`: the exact lexical candidate beneath that physical root;
- `state` and `allowed`: the observation and accepted-state declaration;
- `evidence`: ordered immutable evidence for the root and existing components;
- `missing`: remaining segments after the first absent component.

Inspection never creates, moves, replaces, or deletes an entry.

## Strict descendant policy

Confined target inspection works like a survey of one exact lot. A symbolic link,
Windows junction, or other redirected descendant would point at a different lot, so
the strict lifecycle rejects it even when its destination remains inside the root.
Unsupported entry kinds such as FIFOs are also rejected.

The trusted root itself may be an intentional alias: case5 resolves it to one
physical directory and retains both the declared and physical roots. Revalidation
then detects if that declared root is redirected somewhere else.

## Revalidate before acting

Call `revalidate()` immediately before a caller-owned operation:

```python
plan = ConfinedPath("generated/index.json").inspect(
    root,
    allowed={TargetState.ABSENT, TargetState.FILE},
)

# Rendering, approval, or other preparation happens without touching plan.target.

plan.revalidate()
# The caller may now perform its own operation, subject to the documented race boundary.
```

An unchanged plan returns itself. `StaleTargetError` is raised if the physical root,
an existing component, the observed target, or a previously absent segment no longer
matches. Revalidation never replaces the original plan with a refreshed observation.

This is cooperative stale-plan protection, not an adversarial filesystem lock. A
change can still occur after the final check; eliminating that race requires
platform-specific directory handles outside this utility.

## Entry evidence is not content integrity

Evidence describes filesystem entries and observable regular-file metadata. It does
not snapshot file bytes or descendants inside a directory. Editing a file inside a
planned directory therefore does not make case5 claim that the directory tree is
unchanged.

When content equality matters, compose the plan with a case2 filesystem snapshot,
a case1 stored hash, or a domain-specific inspector. Case5 answers “is this still the
surveyed target?” rather than “does every byte beneath it remain identical?”

## Repository paths and globs

The existing repository APIs remain compatible. `RepositoryPath` preserves one
canonical repository-relative identity, and `RepositoryGlob` provides a bounded glob
dialect:

```python
from zuu.case5 import RepositoryGlob, RepositoryPath


path = RepositoryPath("src/zuu/case5/__init__.py")
pattern = RepositoryGlob("src/**/test_*.py")

print(path.parts)
print(pattern.matches("src/zuu/case5/test_paths.py"))
```

The glob operators are:

- `*` for zero or more characters inside one segment;
- `?` for one character inside one segment;
- `[abc]` and `[!abc]` character classes inside one segment;
- `**` as an entire segment for zero or more path segments.

`RepositoryPath.resolve_file(root)` still resolves an existing regular file and may
follow a symbolic link whose destination remains beneath the repository root:

```python
source = RepositoryPath("pyproject.toml").resolve_file(Path.cwd())
```

That compatibility behavior is intentionally different from strict
`ConfinedPath.inspect()`. Use repository resolution to locate an existing repository
file; use confined inspection when the exact lexical target and later revalidation
matter.

## Errors

- `ConfinedPathError` reports unsafe identities, unavailable roots, invalid allowed
  states, state mismatches, redirected entries, and unsupported entry kinds.
- `StaleTargetError` is a `ConfinedPathError` raised only when captured evidence no
  longer matches during revalidation.
- `RepositoryPathError` retains the existing repository path and glob error contract
  and is also a `ConfinedPathError`.

## Tests

Run the focused suite with:

```powershell
uv run pytest -q tests/case5
```
