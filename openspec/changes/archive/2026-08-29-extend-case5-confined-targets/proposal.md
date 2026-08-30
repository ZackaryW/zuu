## Why

Agents need to inspect existing or not-yet-created filesystem targets safely beneath
an arbitrary trusted root, then verify that the location has not changed before they
act. This belongs beside case5's portable path and confinement behavior rather than
in a second overlapping safe-path case.

## What Changes

- Broaden case5 from repository-file selection to a safe rooted-path family while
  preserving the existing `RepositoryPath` and `RepositoryGlob` APIs.
- Add a generic confined target model that distinguishes an absent target, regular
  file, and directory beneath an existing trusted root.
- Capture immutable filesystem-entry evidence and support explicit revalidation that
  reports stale plans instead of silently refreshing them.
- Reject symbolic links, junctions, and unsupported entries in the strict confined
  target lifecycle without changing `RepositoryPath.resolve_file()` compatibility.
- Keep inspection and revalidation non-mutating; creation, deletion, replacement,
  rendering, validation, and transaction recovery remain outside case5.
- Expand focused case5 tests and its guide, then update only the existing case5 row
  in the root index. No case11 or case12 package is introduced.

## Capabilities

### New Capabilities

- `confined-path-planning`: Inspect and revalidate exact existing or absent targets
  beneath a trusted filesystem root through the existing case5 safe-path family.

### Modified Capabilities

<!-- No canonical OpenSpec capability exists yet for the current case5 API. -->

## Impact

- Public API additions and named implementation modules under `src/zuu/case5`.
- Expanded focused coverage under `tests/case5` using pytest temporary roots.
- Revised `docs/case5/README.md`, case5 `__purpose__`, exports, and generated root
  index row.
- No new numbered case, case dependency, third-party runtime dependency, mutation
  engine, or change to existing case5 path and glob behavior.
