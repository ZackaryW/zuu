## 1. Filter declaration and matching

- [x] 1.1 Add keyword-only `include` and `exclude` string-sequence fields, immutable tuple normalization, and private compiled regex state to `GitHubSubpath`; verify contract tests cover existing positional calls, multiple patterns, input-list mutation, field/index errors, non-sequences, bare strings/bytes, non-string members, invalid regexes, and valid empty expressions.
- [x] 1.2 Implement relative POSIX file-path regex search with any-include and any-exclude precedence; verify tests cover multiple alternatives, exclude-only selection, overlap, anchoring, nested paths, inline flags, default case sensitivity, and order-independent results.

## 2. Archive validation and materialization

- [x] 2.1 Separate structural validation of the requested subtree from writing, including entry kinds, normalized collisions, file/ancestor conflicts, and reserved `.commit` and `.zuu-filters.json` names; verify archive fixtures reject excluded unsafe entries and host-case conflicts without touching the target, while accepting explicit directories with descendants.
- [x] 2.2 Wire declaration filters into local extraction without changing `GitHubClient`; verify fixture-based synchronization copies only matching files and their parents, preserves executable bits, omits unrelated empty directories under active filters, and retains unfiltered directory behavior and full-archive download calls.
- [x] 2.3 Support metadata-only success when a valid source has zero matching files; verify both unmatched includes and exclude-all remove previous target files, while missing, file-only, and previously rejected empty sources still fail without replacement.

## 3. Filter-aware cache lifecycle

- [x] 3.1 Add versioned `.zuu-filters.json` serialization and defensive reading using sorted, deduplicated pattern strings; verify tests cover stable identity across ordering/duplicates and cache misses for malformed, unsupported, unreadable, redirected, and non-regular metadata.
- [x] 3.2 Require commit and filter identity for cache hits and stage metadata with content; verify offline lifecycle tests cover same-filter hits, changed include/exclude sets at the same SHA, legacy unfiltered hits, both directions of filtered/unfiltered transitions, metadata-only hits, pinned-commit networking skips, and branch resolution before comparison.
- [x] 3.3 Preserve authoritative metadata and replacement recovery with filters; verify tests show local content is not inspected on cache hits, filtered staging failures preserve the old target and markers, installation failure restores the previous target when possible, and successful replacement cleans temporary files.

## 4. Documentation and integrated validation

- [x] 4.1 Update `docs/case12/README.md` and API docstrings with multiple-regex examples, relative-path search rules, directory and empty-result behavior, new reserved metadata, cache transitions, full-ZIP transport, and rollback guidance; verify examples and claims against the implemented contract and focused tests.
- [x] 4.2 Run `uv run pytest -q tests/case12` and `uv run pytest -q` for integrated regression coverage, then `openspec validate add-case12-regex-filters --strict` and `git diff --check`; resolve failures and record the outcomes before marking implementation complete.

## Validation results

- Case 12: 122 passed, 2 skipped (POSIX executable modes unavailable on Windows).
- Full repository: 477 passed, 3 platform-specific skips.
- Added tests/case12/__init__.py to resolve duplicate test module names during full-suite collection.
- OpenSpec strict validation and Git whitespace checks passed.
- Implementation complete; this change remains unarchived by user request.
