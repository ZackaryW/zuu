## Context

See `proposal.md` for motivation. Case5 currently owns portable repository-relative
identities, bounded globs, and existing regular-file confinement. The new capability
extends that same safe-path family to arbitrary trusted roots, directories, absent
targets, and explicit revalidation without adding another numbered case.

Python 3.12 and the standard library remain the runtime boundary. Filesystem identity
and redirection differ across Windows, macOS, and Linux, so the design must make its
cooperative-concurrency and content-integrity limits explicit.

## Goals / Non-Goals

**Goals:**

- Present one discoverable case for portable safe-path identity, repository matching,
  confined target inspection, and revalidation.
- Preserve current `RepositoryPath`, `RepositoryGlob`, and `resolve_file()` behavior.
- Represent file, directory, and absent target states through immutable public models.
- Detect ordinary changes to the root, traversed components, or target between
  inspection and an explicit revalidation call.

**Non-Goals:**

- Create missing parents or mutate a target.
- Snapshot or hash regular-file bytes or directory contents.
- Eliminate hostile races after revalidation with platform-specific directory handles.
- Stage, validate, activate, back up, restore, or batch filesystem changes.
- Introduce case11, case12, or a new runtime dependency.

## Decisions

### Fold confined targets into case5

Case5 will become the single safe rooted-path family. A separate case would duplicate
the same portable identity grammar and force consumers to distinguish two utilities
whose shared user question is whether a relative path is safe beneath a root.

The broadened analogy-led purpose will describe paths as addresses inside a fenced
property. The new generic confined-path utility will be the first `__all__` export so
the generated index presents the broader entry point, while existing repository path
and glob exports remain available and compatible.

Creating case11 was rejected because its distinction was primarily vocabulary and
lifecycle depth, not an independent consumer responsibility. Moving the grammar into
case0 was rejected because it is already a cohesive case5 concern and no other case
needs a new foundational dependency.

### Add strict inspection without tightening existing resolution

The confined target lifecycle will reject every redirected descendant component,
including an in-root symbolic link or Windows junction. It promises evidence about
the exact lexical target, so following a shortcut would change what was surveyed.

`RepositoryPath.resolve_file()` will retain its current compatibility rule: it may
resolve a link whose destination remains beneath the root. The stricter behavior is
opt-in through the new target inspection entry point instead of a silent breaking
change to current consumers.

### Keep the public model small and case-local

The public surface will contain a generic confined path, target state enum, immutable
target plan/evidence model, one base error family, and a distinct stale-plan error.
The primary model and metadata remain in `case5.__init__`; traversal and evidence
comparison belong in a named case-local module rather than expanding the initializer
with platform-specific filesystem logic.

Inspection accepts a trusted root, a portable relative identity, and an allowed-state
collection. It resolves the root physically, walks descendants lexically with
`lstat`, stops at the first absent segment, and never creates the remainder.

### Capture entry evidence rather than content snapshots

Evidence records the physical root, each existing component's relative identity and
kind, and a conservative metadata fingerprint using stable standard-library fields
available on the host. Redirection indicators are recorded or rejected before an
entry can be accepted. For an absent target, the plan also records the remaining
lexical segments.

Revalidation repeats the same walk and compares the new evidence with the captured
evidence. Any mismatch raises the stale-plan error and never mutates or refreshes the
original frozen plan.

This detects ordinary entry replacement, creation, removal, and kind changes. It does
not claim that directory contents or file bytes are unchanged; consumers can compose
case2 snapshots, case1 hashes, or domain inspection when content identity matters.

### Test the strict lifecycle inside temporary roots

Focused case5 tests will retain existing path and pattern matrices, then add target
state, expected-state, redirection, absence, and stale-evidence modules. Every
filesystem scenario uses `tmp_path`. Link and junction scenarios skip only when the
host cannot create the required entry; core confinement remains platform-independent.

Verification runs only `uv run pytest -q tests/case5`, followed by README
synchronization and strict OpenSpec validation. The repository-wide suite remains
outside this case-development workflow.

## Risks / Trade-offs

- [Two link policies exist in case5] -> Name and document strict inspection separately
  while preserving the established `resolve_file()` contract.
- [Portable metadata cannot close every race] -> Revalidate immediately before caller
  action and document that changes after the check require platform-specific handles.
- [Entry evidence can be mistaken for content integrity] -> Expose the boundary in
  public docstrings, the guide, and explicit content-change tests or examples.
- [The case5 initializer could become crowded] -> Keep primary models and metadata
  there while moving traversal and fingerprint comparison into a named module.

## Migration Plan

1. Add the confined target models and strict traversal behind new case5 exports.
2. Verify new target behavior and all existing case5 compatibility through the
   focused `tests/case5` suite.
3. Expand the case5 guide and synchronize its existing root index row.

Rollback removes only the new exports, implementation module, focused target tests,
and added documentation. Existing case5 APIs require no migration.
