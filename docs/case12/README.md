# case12: Commit-cached GitHub subpaths

`case12` synchronizes one directory from a public GitHub repository into a local
directory owned by the caller. It treats the resolved commit like the date on a
sealed delivery: when `target/.commit` already records that date, the delivery is
accepted as current without reopening or inspecting its contents.

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

## Authoritative `.commit` marker

After a successful installation, case12 writes the normalized SHA followed by one
newline to `target/.commit`. That top-level path is reserved; synchronization rejects
a source directory that already contains a `.commit` file or directory.

When the marker matches the desired commit, case12 returns immediately. It does not
hash, inspect, restore, or protect the remaining target contents. Local edits may
therefore survive a cache hit and will be discarded when a later commit replaces the
target. This behavior is intentional: the developer is responsible for assigning
each target permanently to one repository and source subpath and for treating that
target as generated content.

An absent, malformed, unreadable, or non-regular marker is a cache miss.

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

`GitHubSubpathError` reports invalid owner, repository, source path, branch, or commit
declarations; invalid target states; GitHub metadata or archive failures; missing or
unsafe source content; and failed installation or restoration.

## Tests

Run the focused case12 suite:

```powershell
uv run pytest -q tests/case12
```
