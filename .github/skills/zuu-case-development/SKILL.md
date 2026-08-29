---
name: zuu-case-development
description: Create or extend numbered utility cases in the zuu repository with an agreed contract, explicit case dependencies, case-local Python code, pytest coverage, dedicated documentation, and the compact root README index. Use for work under src/zuu/caseN where N is greater than zero; do not use for unrelated Python maintenance or the reserved case0 primitives.
---

# Zuu Case Development

Develop one bounded utility case without turning the repository into a product-spec
project. Preserve the standard-library-only runtime unless the owner explicitly
changes that constraint.

## Clarify before implementation

Establish the public contract before editing code. Inspect the current case, related
tests, and repository conventions first, then resolve only questions that affect the
outcome. Do not infer overloaded terms such as "folder", "identifier", "register",
"match", "reference", or "cache" from a stub alone.

Reconcile these facts when relevant:

- the consumer and intended result;
- the lifecycle and ordering of operations;
- inputs, outputs, callback behavior, and failure behavior;
- persistence ownership and replaceable protocol boundaries;
- identity, integrity, path, exclusion, and compatibility semantics;
- whether a responsibility belongs in this case, a new dependent case, or case0;
- which pieces must remain composable;
- accepted examples, edge cases, and non-goals.

Ask one to three focused questions at a time when an outcome-changing fact is
missing. Explain the concrete interpretation that needs confirmation. If the request
already settles the contract, summarize it briefly and proceed without redundant
questions. Never implement while a material ambiguity remains.

## Preserve the case layout

For a numbered case `caseN`, where `N > 0`, use this layout as needed:

```text
src/zuu/caseN/
|-- __init__.py
|-- responsibility.py
`-- supporting_module.py

tests/caseN/
|-- test_lifecycle.py
`-- test_<responsibility>.py
docs/caseN/README.md
```

Keep case metadata and the primary public model or utility in
`src/zuu/caseN/__init__.py`. The initializer may contain substantive classes and
logic; do not reduce it mechanically to a re-export manifest. It also must not become
a dump for every concern. Move distinct responsibilities—such as persistence,
filesystem traversal, process execution, serialization, or lifecycle application—
into clearly named case-local modules when they can be understood independently.
Avoid one module per symbol and avoid generic names such as `helpers.py`.

A case may depend on case0 primitives, another numbered case's public API, or the
standard library. Do not import another case's private implementation.

Every numbered case package must define these exact metadata names near the top of
`__init__.py`:

```python
__purpose__ = "Concise sentence describing the case's user-facing purpose."
__depends__ = ()
```

Use `__purpose__`, not `__purposal__` or another spelling. Keep the value concise,
single-purpose, and suitable for the root README table. It describes why the case
exists, not its implementation mechanics.

Use `__depends__` as an immutable tuple containing the package names of every direct
case dependency, including case0 when it is imported. Do not list standard-library
modules, case-local modules, development tools, or transitive dependencies. Keep
multiple dependencies in numeric case order:

```python
__depends__ = ("case0", "case2")
```

An empty tuple means the case is standalone. Dependency declarations must match the
implemented imports and must not contain duplicates, missing cases, the declaring
case itself, or dependency cycles. A dependency gives access only to the depended-on
case's public API; it does not authorize reaching into its internal modules.

The first string in `__all__` identifies the case's primary utility for the root
README index. Order the public export list deliberately when another export is the
main entry point. If `__all__` is absent or empty, the index synchronizer uses the
last top-level class in `__init__.py`; if neither is available, it renders `N/A`.

## Keep case0 special

`src/zuu/case0` is reserved for small foundational utilities that other cases may
depend on. It is not an ordinary product case and is excluded from future dynamic
case discovery. Do not move a numbered capability into case0 merely to share it;
extract only genuinely small, reusable primitives when the owner accepts that
boundary.

Exclude case0 from the root README table. Do not require case0 to adopt numbered-case
metadata or documentation conventions unless the owner separately requests it.

## Implement the accepted contract

Prefer a small public API with case-local implementation details. Use protocols or
callables at boundaries that the accepted contract says must be replaceable, such as
storage references, encryption wrappers, launchers, or hashing strategies. Do not
make every internal helper configurable by default.

Add concise docstrings to public classes, protocols, functions, methods, and
properties when their contract, state transition, safety boundary, or return value
is not obvious from the signature. Document important failure and mutation behavior
where callers need it. Do not add docstrings that merely repeat a name, and do not
burden routine private helpers with ceremonial documentation.

Preserve explicit lifecycle guarantees in both code and tests. Examples include
idempotent registration, collision behavior, callback return propagation, updates
only after successful work, deterministic ordering, and strict handling of malformed
stored data. The accepted contract decides which guarantees apply.

When one useful responsibility can stand alone, prefer a separate case with an
explicit dependency over combining unrelated lifecycles. For example, a hash-check
case may depend on a snapshot case instead of owning both snapshot capture and stored
hash comparison. Do not split tightly coupled private helpers merely to create more
cases.

Keep runtime dependencies in `[project].dependencies` empty unless the utility
cannot reasonably use the standard library and the owner approves the dependency.
Development-only tools such as pytest belong in the development dependency group.

## Test with pytest

Add focused tests under `tests/caseN/` using descriptive `test_*.py` modules and
pytest fixtures such as `tmp_path`. Split modules by public responsibility—for
example lifecycle, exclusions, storage, or failure recovery—instead of accumulating
one test file for the whole case. Avoid empty packages and arbitrary one-test files.

Cover the public lifecycle and meaningful failure boundaries, not private line-by-
line implementation. Include composability tests when the case accepts custom
protocols or callables. Exercise dependencies through their public APIs and leave
the depended-on case's own behavior to its focused tests.

Run the focused case tests first:

```powershell
uv run pytest -q tests/caseN
```

Then run the complete suite when the focused tests pass:

```powershell
uv run pytest -q
```

## Write case documentation

Put the full explanation in `docs/caseN/README.md`, including the lifecycle, a basic
example, direct case dependencies, public options, extension points, errors, and the
focused pytest command. Examples must match the implemented API. Explain subtle
state transitions and path resolution rules explicitly.

Keep the repository root `README.md` as an index, not a duplicate guide. Preserve
this table shape:

```markdown
## Cases

| Case | Utility | Purpose | Depends on | Documentation |
|------|---------|---------|------------|---------------|
| caseN | `PublicUtility` | Value derived from `__purpose__`. | `case2` | [Guide](docs/caseN/README.md) |
```

Use `—` when `__depends__` is empty; otherwise render each direct dependency from the
tuple. Add or update only the affected row. Keep case rows in numeric order. Do not
append usage examples or full case explanations below the table.

Numbered-case rows are generated by `scripts/sync_readme.py` from `__purpose__`,
`__depends__`, the first item in `__all__`, and the presence of the dedicated guide.
The synchronizer discovers case directories in numeric order and excludes case0
from both discovery and the rendered table. Lefthook runs the synchronizer before
commits and stages a corrected README automatically.

## Finish

Review the diff for unrelated changes. Confirm declared dependencies match direct
case imports, the dependency graph remains acyclic, and the dedicated guide and root
index agree with `__purpose__` and `__depends__`. Report the public behavior and
pytest results. Do not commit or publish unless separately requested.
