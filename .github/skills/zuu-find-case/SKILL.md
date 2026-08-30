---
name: zuu-find-case
description: Match a Python consumer's utility need to the smallest existing zuu case or case composition by inspecting a local zuu checkout or a temporary clone of the canonical repository. Use when an agent needs to choose, compare, or explain which zuu case to consume; do not use to discover new case ideas from unrelated packages or to implement changes in zuu.
---

# Zuu Find Case

Recommend the existing zuu public API that most directly satisfies the consumer's
need. Prefer one case, or the smallest necessary composition of cases, over a broad
package tour.

## Establish the consumer need

Extract the desired result, relevant inputs, state or mutation lifecycle, failure
expectations, and required extension boundaries from the request. Clarify only when
two plausible cases have materially different behavior that the request does not
resolve.

Do not treat case numbers as versions, rankings, or implementation order. A declared
case dependency means that the public API of one case is directly consumed by
another; it does not make the cases interchangeable.

## Resolve a trustworthy source

Use an explicit local zuu repository path when the user supplies one. Otherwise use
the current workspace when it contains `README.md`, `src/zuu`, and numbered case
packages. Prefer this local source even when network access is available because it
represents the consumer's actual checkout.

Do not crawl the user's machine looking for a checkout. If the user says one exists
but neither its path nor an identifiable current workspace is available, ask for the
path.

Keep inspection read-only. Do not import or execute repository code merely to learn
its API, and do not run installation, build, hook, or test commands. Read source,
documentation, and tests as text.

When no local checkout is available, clone the canonical repository shallowly into
a newly created operating-system temporary directory:

```powershell
$zuuClone = Join-Path ([System.IO.Path]::GetTempPath()) ("zuu-" + [guid]::NewGuid())
git clone --depth 1 https://github.com/ZackaryW/zuu $zuuClone
```

```bash
zuu_clone="$(mktemp -d)"
git clone --depth 1 https://github.com/ZackaryW/zuu "$zuu_clone"
```

Do not clone submodules or place the checkout in the consumer repository. Record the
inspected commit with `git -C <checkout> rev-parse HEAD`. Remove only the exact clone
directory created by this workflow when inspection finishes, after verifying that it
is inside the operating-system temporary directory. Never remove a user-supplied or
pre-existing local checkout.

If cloning fails, report that current source evidence is unavailable. Do not invent
a recommendation from remembered case names.

## Build the shortlist

Inspect the source in this order, stopping when the evidence resolves the choice:

1. Read the root `README.md` case index for primary utilities, purposes, direct
   dependencies, and guide links.
2. Shortlist cases whose purposes match the requested result rather than sharing
   only vocabulary with the request.
3. Read each shortlisted `docs/caseN/README.md` for lifecycle, options, extensions,
   errors, and non-goals.
4. Confirm the public contract in `src/zuu/caseN/__init__.py`, including
   `__purpose__`, `__depends__`, `__all__`, signatures, and docstrings.
5. Read focused `tests/caseN/test_*.py` only when examples or boundary behavior
   remain ambiguous.

Use only public exports. Do not recommend private helpers or reach into another
case's private modules. Follow `__depends__` recursively and distinguish the primary
case from dependencies the consumer receives indirectly or may compose directly.

Case0 is intentionally absent from the numbered index. Inspect `src/zuu/case0` only
when no numbered case fits a small foundational operation or when dependency evidence
requires it. Label such a result as a foundational utility, not a numbered case.

## Select conservatively

Recommend a case when its documented public lifecycle satisfies the need without
source changes or product-specific policy. Recommend a composition only when each
case contributes an independently necessary public responsibility. Prefer the case
that already owns the required state transition instead of asking the consumer to
rebuild it from lower-level pieces.

If several cases remain plausible, compare the concrete lifecycle difference and
ask one focused question. If no current case fits, say so and identify the missing
generic responsibility. Do not redirect automatically into case development or
`zuu-discover`; those are separate workflows requiring an explicit request.

## Report the recommendation

Lead with the selected case and primary public utility. Include:

- why its observable lifecycle matches the consumer need;
- direct and relevant transitive case dependencies;
- the smallest import and usage example supported by the inspected source;
- important options, extension boundaries, and failure behavior;
- the strongest alternative and why it is less suitable, when one exists; and
- whether evidence came from a local checkout or temporary clone, including the
  inspected commit SHA.

Keep the answer proportional to the request. Do not install zuu, edit the consumer
repository, or implement integration code unless the user separately asks for that
mutation.
