# confined-path-planning Specification

## Purpose

Treat a filesystem destination like a surveyed plot inside a fenced property,
identifying its exact state and rechecking the recorded landmarks before a caller
acts without creating a second safe-path case.

## Requirements

### Requirement: Portable relative target identity
The capability SHALL accept only a non-empty portable relative target identity with
`/` separators. It SHALL reject absolute paths, drive-qualified paths, backslashes,
null bytes, empty segments, redundant separators, and `.` or `..` segments before
inspecting the filesystem.

#### Scenario: Accept a nested target identity
- **WHEN** a caller declares `profiles/team/default.toml`
- **THEN** the capability preserves that canonical identity and its ordered segments

#### Scenario: Reject traversal syntax
- **WHEN** a caller declares `profiles/../outside`, an absolute path, or a drive-qualified path
- **THEN** the capability rejects the identity before resolving a target

### Requirement: Confined target inspection
The capability SHALL resolve an existing trusted root to one physical directory and
inspect one declared descendant without allowing any traversed descendant to redirect
the lexical target. It SHALL classify an absent target, regular file, or directory
and SHALL reject symbolic links, junctions, and unsupported entry kinds.

#### Scenario: Inspect an existing regular target
- **WHEN** every descendant component is ordinary and the target is a regular file or directory
- **THEN** inspection returns its canonical identity, confined physical path, and observed state without mutation

#### Scenario: Inspect an absent nested target
- **WHEN** the target is absent and every existing ancestor below the trusted root is an ordinary directory
- **THEN** inspection returns the confined candidate and absent state without creating missing entries

#### Scenario: Reject redirected traversal
- **WHEN** an existing descendant component is a symbolic link, junction, or equivalent redirection
- **THEN** inspection rejects the target even when the redirection would remain beneath the trusted root

#### Scenario: Reject an unavailable root
- **WHEN** the trusted root is missing or does not resolve to a directory
- **THEN** inspection fails before returning target state

### Requirement: Expected target states
A caller SHALL be able to constrain inspection to the states valid for its operation.
An unexpected absence, occupied target, or mismatched existing kind SHALL fail instead
of being silently accepted or coerced.

#### Scenario: Require an existing directory
- **WHEN** a caller allows only a directory but the target is absent or a regular file
- **THEN** inspection reports the observed state mismatch without changing the target

#### Scenario: Require an available creation target
- **WHEN** a caller allows only absence but a file or directory occupies the target
- **THEN** inspection reports that the target is occupied

### Requirement: Immutable target evidence and revalidation
A successful inspection SHALL return immutable evidence for the physical root,
traversed existing components, observed target state, and any remaining absent
segments. Explicit revalidation SHALL confirm the same evidence or report a stale
plan without returning a refreshed replacement implicitly.

#### Scenario: Revalidate unchanged evidence
- **WHEN** the root, traversed ancestors, and target still match the captured evidence
- **THEN** revalidation confirms the same confined target and state

#### Scenario: Detect changed target evidence
- **WHEN** a captured component is replaced, redirected, created, removed, or changes kind
- **THEN** revalidation reports a stale plan instead of approving the earlier target

#### Scenario: Detect a newly occupied absent segment
- **WHEN** any previously absent segment is created after inspection
- **THEN** revalidation reports a stale plan without inspecting it as a new plan

### Requirement: Evidence boundary
Target evidence SHALL describe filesystem entries and their observable metadata, not
the contents of regular files or descendants inside a directory. Callers requiring
content integrity SHALL compose a snapshot, hash, or domain-specific inspector.

#### Scenario: Keep content integrity caller-owned
- **WHEN** a caller needs to prove that file bytes or a directory tree remain unchanged
- **THEN** the capability exposes no content-equality claim beyond its recorded entry evidence

### Requirement: Non-mutating compatibility
Inspection and revalidation SHALL NOT create, move, replace, or delete filesystem
entries. Existing repository path resolution and glob matching SHALL retain their
current public behavior while the stricter target lifecycle remains opt-in.

#### Scenario: Plan an absent target without mutation
- **WHEN** a caller inspects an absent nested target
- **THEN** the filesystem remains unchanged after inspection and revalidation

#### Scenario: Preserve existing case5 behavior
- **WHEN** a caller uses the existing repository path or glob APIs
- **THEN** their accepted inputs, results, and error behavior remain compatible
