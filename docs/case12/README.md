# case12: Commit-cached GitHub subpaths

`case12` synchronizes one directory from a public GitHub repository into a local
directory owned by the caller. It treats the resolved commit like the date on a
sealed delivery: when `target/.commit` records that date and the stored filters
match, the delivery is accepted without reopening or inspecting its contents.

## Dependency

Case12 depends on case5's public `RepositoryPath` validation for the portable source
subpath. It otherwise uses only the Python standard library and does not require the
Git executable.

## Synchronize a repository directory

Declare the GitHub owner, repository name, and non-empty directory subpath, then
synchronize it to a target whose parent already exists:

```python
from pathlib import Path

from zuu.case12 import GitHubSubpath


source = GitHubSubpath(
    owner="example-org",
    repository="shared-templates",
    path="python/service",
)
result = source.sync(Path("vendor") / "service-template")

print(result.commit)
print("updated" if result.changed else "already current")
```

The default client resolves the repository's default branch, downloads GitHub's ZIP
archive for the resulting full commit SHA, selects only the declared directory, and
installs its contents directly at the target. The GitHub-generated archive wrapper
and unrelated repository files are not copied.

`GitHubSyncResult.target` is the absolute target path, `commit` is the normalized
full SHA, and `changed` reports whether this call replaced the target.

## Revision selectors

Pass `branch` to follow a named branch:

```python
source = GitHubSubpath(
    "example-org",
    "shared-templates",
    "python/service",
    branch="preview/templates",
)
```

Pass a full 40-character commit SHA to pin the source:

```python
source = GitHubSubpath(
    "example-org",
    "shared-templates",
    "python/service",
    commit="0123456789abcdef0123456789abcdef01234567",
)
```

`branch` and `commit` are mutually exclusive. When both are omitted, the repository's
default branch is used. A branch or default branch is resolved on every call before
the marker comparison. An explicit commit can produce a cache hit without making any
network request.

## Include and exclude regex patterns

Pass multiple Python regex strings as keyword-only `include` and `exclude`
sequences. Lists and tuples are accepted and copied into immutable tuples:

```python
source = GitHubSubpath(
    "example-org",
    "shared-templates",
    "python/service",
    include=(r"\.py$", r"\.toml$"),
    exclude=(r"^tests/", r"(^|/)__pycache__/"),
)
```

Patterns use `re.search` on file paths relative to `python/service`, with forward
slashes on every platform. For example, `nested/app.py` is the candidate, without
the GitHub wrapper or source prefix. Any include match qualifies a file, and any
exclude match removes it. An empty include collection allows every regular file;
an empty exclude collection removes none. Pattern ordering and duplicates have no
effect on selection or caching.

Matching is case-sensitive by default; use inline flags such as `(?i)` when needed.
Use anchors to restrict a whole path, for example `r"^app\.py$"`. These are regexes,
not shell globs. Empty regex strings are valid and match every path. Expressions
are compiled at construction; invalid syntax or non-string elements raise
`GitHubSubpathError` naming the field and zero-based element index. A bare string
is not a pattern collection. Patterns use standard Python regex behavior, including
its performance characteristics; supply caller-controlled expressions.

With active filters, only matching files and their required parent directories are
copied. Empty directories are omitted. Directory entries are not matched:
`r"^tests/"` excludes files beneath `tests`, while `r"^tests$"` does not. With both
collections empty, the complete subtree, including explicit directories, is copied.

If a valid source has no matching files, synchronization succeeds with metadata
only and removes any previous target content. A missing, file-only, or empty source
directory rejected by normal source selection remains an error.

Filtering happens locally after downloading the **whole repository ZIP**. It
reduces extracted content, not network transfer.

## Authoritative commit and filter markers

After a successful installation, case12 writes the normalized SHA followed by one
newline to `target/.commit`. Filtered installations also write versioned JSON to
`target/.zuu-filters.json`, recording sorted, deduplicated include and exclude
patterns. Both top-level names are reserved; synchronization rejects a source
directory containing either path, even when a filter would exclude it.

When the commit and filter configuration match, case12 returns immediately. It does
not hash, inspect, restore, or protect the remaining target contents. Local edits
may survive a cache hit and will be discarded when a commit or filter change
replaces the target. This behavior is intentional: the developer is responsible for assigning
each target permanently to one repository and source subpath and for treating that
target as generated content.

An absent, malformed, unreadable, or non-regular marker is a cache miss.

Adding, removing, or changing a distinct regex triggers replacement even at the
same commit. Reordering or repeating patterns does not. Existing unfiltered targets
with only `.commit` remain cacheable without migration. Removing all filters from
a filtered target refreshes it and removes `.zuu-filters.json`.

Missing filter metadata requires refresh when filters are active. Existing malformed,
unreadable, unsupported, redirected, or non-regular filter metadata is always a
cache miss. Keep markers under case12's control: deleting filter metadata and then
requesting an unfiltered sync can make a filtered target look like a legacy target.

If reverting to an older case12 version without filter support, delete the owned
target before resynchronizing; that version trusts `.commit` alone.

## Complete replacement and failure recovery

Changed content is downloaded and materialized in a temporary sibling directory.
Only after the archive and selected subtree are valid does case12 move an existing
target aside and install the staged directory. If installation fails after that move,
case12 attempts to restore the previous target. Download, ZIP, source-selection, and
staging failures occur before the existing target is touched.

Replacement is whole-directory synchronization, not merging. Files that exist only
in the previous target disappear after a successful update. The target itself must
be absent or an ordinary directory; symbolic links, Windows junctions, regular files,
and missing target parents are rejected.

## Archive safety and boundaries

Case12 writes only entries beneath the selected archive prefix. It rejects unsafe or
ambiguous archive paths, multiple repository wrappers, duplicate destination names,
symbolic links, special entries, a file in place of the selected directory, and a
missing or empty selected directory. Executable bits are preserved on platforms that
support POSIX modes.

Structural checks run before filtering, including entry types, reserved names,
duplicate destinations, and file/directory ancestor conflicts in the requested
subtree. Excluding an unsafe entry does not bypass validation. Payload bytes of
excluded files are not extracted or CRC-checked.

The default client supports public repositories on `github.com`. Private repository
tokens, GitHub Enterprise hosts, Git history, submodule materialization, Git LFS
hydration, file-only sources, local-change detection, and cross-process locking are
outside this case.

## Replace the GitHub client boundary

Pass an object implementing the public `GitHubClient` protocol to test offline or
provide controlled transport behavior:

```python
from pathlib import Path


class PreparedClient:
    def resolve_commit(self, owner, repository, branch):
        return "0123456789abcdef0123456789abcdef01234567"

    def download_archive(self, owner, repository, commit, destination: Path):
        destination.write_bytes(prepared_zip_bytes)


prepared_zip_bytes = Path("fixtures/repository.zip").read_bytes()
result = source.sync("vendor/service-template", client=PreparedClient())
```

The client must return a full hexadecimal SHA and write a GitHub-shaped ZIP archive
to the supplied temporary destination. Boundary failures are reported as
`GitHubSubpathError` without modifying an existing target.

## Errors

`GitHubSubpathError` reports invalid owner, repository, source path, branch, commit,
or regex declarations; invalid target states; GitHub metadata or archive failures; missing or
unsafe source content; and failed installation or restoration.

## Tests

Run the focused case12 suite:

```powershell
uv run pytest -q tests/case12
```
