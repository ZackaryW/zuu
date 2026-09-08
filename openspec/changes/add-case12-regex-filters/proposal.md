## Why

Case 12 currently copies every entry beneath a selected GitHub directory. Callers need multiple include and exclude regular expressions to vendor only the files they need, with repeatable synchronization when their filters change.

## What Changes

- Add optional `include` and `exclude` collections of regex strings to `GitHubSubpath`, defaulting to no filtering.
- Match file paths relative to the declared source directory using case-sensitive Python regex search and forward slashes. Include matches are ORed; any exclude match wins; an empty include collection allows all files.
- Validate patterns at declaration time and retain archive safety checks before applying filters.
- Materialize matching files and their parent directories. A filter that selects no files produces a valid target containing synchronization metadata only.
- Track the filter configuration alongside `.commit` so changes to filters refresh the target at the same commit, while preserving cache hits for existing unfiltered targets.
- **BREAKING for conflicting sources:** Reserve the top-level `.zuu-filters.json` path for selection metadata.
- Document matching rules, examples, full-repository download behavior, cache behavior, and failure semantics.

## Capabilities

### New Capabilities

- `github-subpath-filtering`: Multiple regex filters for Case 12 archive selection, including declaration validation, extraction semantics, and filter-aware synchronization caching.

### Modified Capabilities

None. The canonical spec catalog does not currently contain a Case 12 capability.

## Impact

- Public API and cache lifecycle in `src/zuu/case12/__init__.py`.
- Selection and validation in `src/zuu/case12/archive.py`.
- Case 12 tests and `docs/case12/README.md`.
- New reserved top-level metadata path `.zuu-filters.json`; sources using that path will be rejected.
- The GitHub client protocol and whole-repository ZIP transport remain unchanged. No new runtime dependency is needed.
