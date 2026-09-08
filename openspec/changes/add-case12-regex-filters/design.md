## Context

See `proposal.md` for motivation. `GitHubSubpath` is a frozen dataclass with five existing positional fields. Its `sync()` resolves a SHA and trusts `.commit` alone. On a miss, `_synchronize()` downloads a ZIP into sibling temporary storage, calls `materialize_subpath()`, writes `.commit`, and replaces the target with rollback on installation failure.

`archive.py` validates archive paths globally, selects a source prefix, and checks selected entry kinds and collisions while writing. Filters must not skip those validations. The transport protocol only resolves commits and downloads archives; it does not need selection arguments.

## Goals / Non-Goals

**Goals:** Keep selection deterministic across host path separators, preserve early validation and staged replacement, and invalidate caches when the requested file selection changes.

**Non-Goals:** Glob syntax, compiled-pattern inputs, per-pattern flag arguments, directory pruning rules, partial repository downloads, content hashing, source-identity tracking, authentication changes, or concurrency controls. Callers continue assigning a target to one repository and source path.

## Decisions

### 1. Keyword-only collections with immutable declaration state

Add `include` and `exclude` as keyword-only sequence fields defaulting to `()`, after existing fields so current positional calls remain valid. Accept lists and tuples through a `Sequence[str]` contract; reject strings, bytes, other non-sequences, and non-string members explicitly. Snapshot each collection to a tuple before validating. Preserve declared order and duplicates on public fields; normalize separately for cache identity.

Compile expressions once during construction using standard-library `re`. Keep compiled tuples in private dataclass fields excluded from initialization, representation, comparison, and hashing. Wrap compilation failures in `GitHubSubpathError` naming the collection and zero-based element index. Empty patterns retain standard regex semantics; inline flags such as `(?i)` are supported.

Alternative: accept any iterable or compiled expressions. Restricting inputs to string sequences gives reproducible declarations and serializable cache identity without generator consumption or flag-normalization ambiguities.

Example planned API:

```python
source = GitHubSubpath(
    "example-org",
    "shared-templates",
    "python/service",
    include=(r"\.py$", r"\.toml$"),
    exclude=(r"^tests/", r"(^|/)__pycache__/"),
)
```

### 2. Search regular file paths; construct directories from retained files

For active filters, build the candidate string with `"/".join(relative)` after stripping the wrapper and source prefix. Select using `(not includes or any(p.search(path) for p in includes)) and not any(p.search(path) for p in excludes)`. No host case normalization is applied to regex candidates. Regex flags determine any case-insensitive behavior.

Only regular file entries are matched. Their parent directories are created as needed; unrelated explicit empty directories are dropped. A directory-looking expression is not a pruning instruction: `^tests/` matches descendant file paths, while `^tests$` does not. When both collections are empty, retain the current extraction path, including explicit directories.

Alternative: `fullmatch` or matching directory entries as well. Search makes extension and subtree expressions concise, with `^` and `$` available for full-path constraints. Matching files alone avoids ancestor selection surprises and directory-entry differences across ZIP producers.

### 3. Validate the source before filtering

Retain global `_parts()` and wrapper checks, then select the source prefix using existing missing/file/empty-source rules. Separate structural validation from extraction so all entries in that subtree receive entry-type, reserved-name, normalized collision, and file/directory ancestor-conflict validation before regex selection. Use the existing host case rules for collision and reserved-name comparisons. Ancestor checks must allow an explicit directory entry alongside children while rejecting a regular file occupying an ancestor path.

After validation, an empty filtered file set is valid. Create staging and metadata normally. Keep content streaming and executable-bit preservation for included files. Unselected payload bytes need not be opened or CRC-checked; the pre-filter pass validates structure and metadata.

Alternative: filter before existing write-time validation. That would hide malformed entries and change archive rejection depending on filters. Structural validation followed by selection preserves the current safety boundary.

### 4. Add versioned filter metadata beside the existing commit marker

Reserve `.zuu-filters.json` at the selected source root, alongside `.commit`, and reject conflicting source entries before filtering. This is a narrow compatibility change for sources using the new name.

For active filters, write UTF-8 JSON with this logical schema:

```json
{"version": 1, "include": ["\\.py$"], "exclude": ["^tests/"]}
```

Serialize sorted, deduplicated pattern strings for each collection. Compare parsed, validated data against the desired configuration; reject unexpected schema, unsupported versions, invalid member types, or invalid patterns as cache misses. Require an ordinary metadata file and do not follow symlinks or junctions. Only missing metadata denotes the legacy unfiltered configuration; an existing invalid entry must not be treated as absent.

Require both SHA and configuration equality for a cache hit. Reordered or repeated patterns are equivalent; different regex text may refresh even when mathematically equivalent. Branch resolution still occurs before comparison; a matching pinned commit and configuration can skip all networking.

Filtered installs stage both metadata files with content. Unfiltered installs stage `.commit` only. Thus removing filters from a filtered target causes replacement and removes the additional marker, while old unfiltered targets retain their fast path. Cache hits continue to trust metadata without examining content.

Alternative: place selection information inside `.commit`, which would change its existing plain-SHA format. Trusting SHA alone would silently ignore filter changes. A separate marker preserves that format and makes configuration reviewable without hashing content.

### 5. Keep the archive download boundary unchanged

Pass the compiled filter configuration from the declaration to local materialization. `GitHubClient` and `GitHubApiClient` continue using the repository ZIP endpoint at the resolved SHA. Existing fake clients can exercise filtering and cache transitions offline.

## Risks / Trade-offs

- New reserved filename conflicts with an existing source → document the compatibility change and reject it before replacement, even when excluded.
- Regexes with expensive backtracking can slow selection → treat patterns as caller-controlled configuration and document that standard Python regex behavior applies; a timeout engine is outside this change.
- A full ZIP is still transferred for narrow filters → document that filtering saves extracted disk content, not download bandwidth.
- Metadata can be edited or deleted by callers → retain the existing authoritative-marker model; missing filtered metadata refreshes filtered requests, while absence for unfiltered requests intentionally permits legacy cache hits.
- Empty filtered results can remove all prior files → explicitly document and test metadata-only success and whole-target replacement.

## Migration Plan

No migration is required for legacy unfiltered targets. The first filtered call refreshes them even at the same SHA. Document the new reserved name and update API examples and cache guidance together with implementation. Existing result fields, client injection, source validation, and replacement recovery stay compatible.

If reverting to a version without filters, delete the owned target before resynchronizing: older versions trust `.commit` alone and could accept a filtered installation as complete.
