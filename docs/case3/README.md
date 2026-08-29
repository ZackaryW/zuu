# Case 3: Git-ignore management

Case3 plans, applies, and verifies root `.gitignore` coverage for selected paths. It
asks Git whether rules are effective, so existing globs, nested ignore files, and
negations are respected without reimplementing Git's matching rules.

## Dependency

Case3 is standalone and has no case dependencies. It requires the `git` executable
when using exact or pattern policy.

## Plan and apply exact rules

```python
from pathlib import Path

from zuu.case3 import apply_gitignore, plan_gitignore

repository = Path.cwd()
plan = plan_gitignore(
    repository,
    [repository / "build", repository / ".cache"],
)

if plan is not None:
    changed = apply_gitignore(plan)
    print("updated" if changed else "already covered")
```

Planning never writes `.gitignore`. Exact policy adds a root-relative rule only for
paths that are not already effectively ignored. Relative selected paths are resolved
from `project_root`, while the root `.gitignore` belongs to the containing Git
worktree.

## Policies

Exact policy is the default:

```python
from zuu.case3 import GitIgnorePolicy

policy = GitIgnorePolicy("exact")
```

Pattern policy appends one caller-selected pattern when any selected path is
uncovered. Applying the plan fails and rolls back if that pattern does not actually
cover every selected path:

```python
policy = GitIgnorePolicy("pattern", "/packages/*/generated")
plan = plan_gitignore(repository, generated_paths, policy=policy)
```

None policy bypasses Git and returns `None`:

```python
plan = plan_gitignore(
    repository,
    generated_paths,
    policy=GitIgnorePolicy("none"),
)
assert plan is None
```

## Plan lifecycle

A `GitIgnorePlan` records the discovered worktree, root ignore file, original bytes,
proposed bytes, and selected probe paths. Its `changed` property reports whether a
write is proposed.

`apply_gitignore()`:

1. refuses to overwrite `.gitignore` if it changed after planning;
2. writes proposed bytes atomically;
3. verifies every selected path through `git check-ignore --no-index`;
4. restores the original file, or removes a newly created file, if verification
   fails.

Call `verify_gitignore(plan)` directly when only verification is needed.

## Custom process runner

Planning and verification accept an injectable runner for testing or controlled
process execution:

```python
from pathlib import Path
from collections.abc import Sequence

from zuu.case3 import ProcessResult


def runner(argv: Sequence[str], cwd: Path) -> ProcessResult:
    # Execute argv without a shell and return decoded output.
    ...
```

The default `run_process` implementation uses `subprocess.run` with `shell=False`.

## Errors

`GitIgnoreError` is raised when Git cannot discover or evaluate the worktree, a
selected path lies outside it, `.gitignore` is not a regular UTF-8 file, a plan is
stale, or verification fails. `ValueError` reports invalid policy construction.

## Running the tests

```powershell
uv run pytest -q tests/case3
```
