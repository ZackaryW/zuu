## Purpose

Allow callers to synchronize selected files from a GitHub directory using multiple include and exclude regular expressions, with reliable refreshes when the selection changes.

## ADDED Requirements

### Requirement: Multiple validated regex declarations

The source declaration SHALL accept optional keyword-only `include` and `exclude` sequences of regex strings, each defaulting to an empty sequence. It SHALL snapshot supplied sequences into immutable tuples and validate every regex during construction. Bare strings, bytes, non-sequence values, non-string elements, and invalid regex syntax SHALL raise `GitHubSubpathError` identifying the relevant field and, for element failures, its index, before network or target operations. Empty regex strings SHALL be valid. Existing positional constructor arguments SHALL retain their meaning.

#### Scenario: Multiple patterns are captured immutably
- **WHEN** a declaration receives lists containing two include regexes and two exclude regexes
- **THEN** all four patterns are accepted and stored as tuples
- **AND** later changes to the input lists do not change the declaration

#### Scenario: Invalid declarations fail early
- **WHEN** either field receives a bare string, a non-string element, or an invalid expression such as `[`
- **THEN** construction raises `GitHubSubpathError` with the field and applicable element index
- **AND** no download or target mutation occurs

### Requirement: Relative file path matching with exclude precedence

When either collection is non-empty, selection SHALL evaluate each regular file's complete path relative to the declared source directory, with `/` separators and without the repository wrapper or source prefix. Matching SHALL use Python regex search semantics, case-sensitive unless overridden by inline regex flags. A file SHALL qualify if the include collection is empty or at least one include expression matches, and SHALL be omitted if any exclude expression matches. Pattern order SHALL NOT affect selected content. Directory entries SHALL NOT be matched or implicitly prune descendants.

#### Scenario: Includes are alternatives and excludes win
- **GIVEN** files `app.py`, `README.md`, `tests/test_app.py`, `notes.txt`, and `draft.md`
- **WHEN** include is `(r'\.py$', r'\.md$')` and exclude is `(r'^tests/', r'^draft\.md$')`
- **THEN** only `app.py` and `README.md` are selected

#### Scenario: Exclude-only filtering
- **WHEN** include is empty and exclude is `(r'^tests/', r'\.tmp$')`
- **THEN** all regular files are eligible except those beneath `tests/` or ending in `.tmp`

#### Scenario: Search scope and case
- **GIVEN** the selected source is `templates/python` and contains `nested/app.py` and `nested/OTHER.PY`
- **WHEN** include is `(r'\.py$',)`
- **THEN** `nested/app.py` matches and `nested/OTHER.PY` does not
- **AND** matching uses `nested/app.py`, not the archive wrapper or `templates/python/nested/app.py`

#### Scenario: Directory names are not recursive rules
- **WHEN** exclude is `(r'^tests$',)` and the source contains `tests/test_app.py`
- **THEN** that file remains eligible because its full relative path does not match
- **AND** the caller can exclude its subtree with `r'^tests/'`

### Requirement: Filtered materialization and default compatibility

With active filters, synchronization SHALL write only qualifying regular files and the directories needed to contain them, preserving their relative hierarchy and existing executable-bit behavior. It SHALL NOT retain unrelated empty directories. Zero qualifying files from an otherwise valid source SHALL be a successful synchronization producing metadata only. Missing, file-only, and empty source directories rejected by existing source selection SHALL remain errors; filtering SHALL NOT turn those errors into success. With both filter collections empty, existing unfiltered extraction behavior SHALL be preserved except for the newly reserved metadata name.

#### Scenario: Ancestors survive a file-only include
- **WHEN** include is `(r'\.py$',)` and `nested/deeper/app.py` qualifies
- **THEN** `nested/deeper/app.py` is installed with both parent directories
- **AND** an unrelated empty directory is not installed

#### Scenario: All files are excluded
- **GIVEN** the source is valid and contains files
- **WHEN** exclude is `(r'.*',)`
- **THEN** synchronization succeeds with no source files and valid synchronization metadata
- **AND** stale files in an existing target are removed by replacement

#### Scenario: Defaults preserve directory handling
- **WHEN** both collections are empty
- **THEN** extraction retains the existing complete-subtree behavior, including explicit directory entries

### Requirement: Filters cannot bypass archive validation

Archive path and repository-wrapper validation SHALL run regardless of filters. Entry-type checks, destination-collision checks, file/directory conflict checks, and reserved-metadata checks SHALL apply to the entire requested subtree before filtering. Unsafe excluded entries SHALL still cause `GitHubSubpathError`. Both top-level `.commit` and `.zuu-filters.json` paths SHALL be reserved, including conflicting spellings under the host filesystem's case rules. Validation or staging failure SHALL leave the existing target untouched.

#### Scenario: Excluded unsafe content is still rejected
- **WHEN** the requested subtree contains a symbolic link, duplicate destination, file/directory conflict, or reserved metadata path even though a filter excludes it
- **THEN** synchronization fails before replacing the existing target

#### Scenario: Archive path validation is independent of selection
- **WHEN** an archive contains a traversal path outside the requested subtree
- **THEN** synchronization fails even if no filter would select that entry

### Requirement: Cache tracks the filter configuration

A cache hit SHALL require a matching commit and matching filter configuration. Filter order and duplicate occurrences SHALL NOT affect cache identity. A change to the set of distinct include or exclude expression strings SHALL cause replacement even at the same commit. Existing unfiltered targets containing only a valid `.commit` SHALL remain eligible for unfiltered cache hits. Filtered targets SHALL carry `.zuu-filters.json`; missing metadata for an active filter, malformed or unreadable metadata, unsupported metadata versions, and redirected or non-regular metadata entries SHALL be cache misses. Matching metadata SHALL remain authoritative without inspecting target content. Metadata SHALL be staged with the content and installed through existing replacement and recovery behavior.

#### Scenario: Filters change at a pinned commit
- **GIVEN** a target installed at a pinned SHA using include `(r'\.py$',)`
- **WHEN** synchronization uses the same SHA with include `(r'\.md$',)`
- **THEN** it downloads and replaces the target and returns `changed=True`

#### Scenario: Equivalent collection ordering is cached
- **GIVEN** a matching commit and metadata for includes `(r'\.py$', r'\.md$')`
- **WHEN** includes are reordered or an identical pattern is repeated
- **THEN** synchronization returns `changed=False` without an archive download

#### Scenario: Transition between filtered and unfiltered targets
- **WHEN** filters are added to a legacy unfiltered target or all filters are removed from a filtered target at the same SHA
- **THEN** synchronization replaces the target to reflect the new selection

#### Scenario: Legacy unfiltered cache hit
- **GIVEN** a target with a matching `.commit` and no filter metadata
- **WHEN** both filter collections are empty
- **THEN** synchronization returns `changed=False` without inspecting target files

#### Scenario: Broken filter metadata requires refresh
- **WHEN** an active filter has no metadata, or existing filter metadata is malformed, unreadable, unsupported, redirected, or non-regular
- **THEN** synchronization treats the target as a cache miss even if `.commit` matches

### Requirement: Filtering does not change transport

On a cache miss, the default client SHALL continue downloading the repository ZIP at the resolved commit and filtering during local extraction. Include and exclude patterns SHALL NOT alter the public GitHub client protocol or cause per-file download requests.

#### Scenario: A narrow include still uses an archive
- **WHEN** a cache miss occurs with include `(r'^app\.py$',)`
- **THEN** the client downloads the repository archive at the resolved SHA and extraction copies only eligible files
