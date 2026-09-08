# case15: Cached GitHub version checks

Case 15 reads one value from a public GitHub raw YAML, TOML, or JSON file and
compares it with a caller-supplied value. It uses Case 14 for YAML parsing and
Case 13 for nested item traversal. TOML and JSON use `tomllib` and `json` from
the standard library. It requests the declared raw file directly and does not
download a repository archive.

```python
from datetime import timedelta
from pathlib import Path

from zuu.case15 import (
    CheckPolicy,
    FileVersionCache,
    GitHubVersionSource,
    ListenPolicy,
    check_version,
)

source = GitHubVersionSource(
    owner="example",
    repository="application",
    ref="main",
    path="pubspec.yaml",
    value_path=["version"],
)
result = check_version(
    "1.4.2",
    source,
    cache=FileVersionCache(Path(".cache") / "application-version.json"),
    policy=CheckPolicy(
        max_age=timedelta(hours=6),
        listen=ListenPolicy.MINOR_CHANGE,
    ),
)

if result.update_needed:
    print(f"remote version: {result.remote}")
```

The source defaults to ref `HEAD` and infers its parser from `.yaml`, `.yml`,
`.toml`, or `.json`. Set `format=` explicitly for an extensionless or differently
named file. `value_path` is a literal Case 13 item path: strings select mapping
keys and integers select list indexes. An empty path selects the complete parsed
document.

## Check lifecycle

With no cache, every call fetches the raw file. With a cache, Case 15 reads a
versioned JSON record and verifies that its GitHub source exactly matches the
current source. The record stores the normalized source, a snapshot of the cache
and listening policy, the UTC time of the successful remote check, and the raw
document text. It does not serialize custom comparison functions.

The current `max_age` decides freshness, even when it differs from the policy
recorded earlier. The default is six hours. A cached document is fresh only while
its age is strictly less than that duration, so the exact boundary refreshes and
a zero duration always refreshes. Changing the listener can reuse the same fresh
raw document.

Successful results identify their data origin:

| `origin` | Meaning |
|----------|---------|
| `CheckOrigin.REMOTE` | A new raw response was fetched, parsed, extracted, compared, and cached. |
| `CheckOrigin.FRESH_CACHE` | A matching fresh document was parsed and compared without a request. |
| `CheckOrigin.STALE_CACHE` | Refresh failed and a matching stale document supplied the result. |

Cached results retain the timestamp of the remote check that produced the
record. A stale result also exposes the failed refresh as `refresh_error`.

`FileVersionCache` stores bytes at the caller-selected path. It flushes a sibling
temporary file and atomically replaces the target. Applications can instead
supply any object with `read() -> bytes | None` and `write(data: bytes) -> None`.
Likewise, a custom raw client only needs `fetch(source) -> str`.

## Listening policies

`CheckPolicy.listen` accepts five policies:

| Policy | Reports an update when |
|--------|------------------------|
| `DIFFERENCE` | The supplied and remote values compare unequal using Python equality. This is the default and accepts arbitrary values. |
| `MAJOR_CHANGE` | The remote major component is greater. |
| `MINOR_CHANGE` | The majors match and the remote minor component is greater. |
| `MICRO_CHANGE` | The major and minor components match and the remote micro component is greater. |
| `REGRESSION` | The remote numeric core is lower than the supplied numeric core. |

The four numeric policies require strings with exactly three nonnegative decimal
components: `major.minor.micro`. They accept optional prerelease and build
suffixes, such as `1.2.3-beta+4`, but ignore those suffixes when deciding. Leading
zeroes have no numeric significance. Equality, suffix-only differences, and
forward changes at a different component level do not trigger the component
listeners.

A custom `compare` callback overrides the listener. It receives the original
supplied and extracted values exactly once and must return an actual `bool`:

```python
result = check_version(
    {"accepted": "stable"},
    source,
    compare=lambda local, remote: local["accepted"] != remote,
)
```

## Failure behavior

Source, path, format, policy, and callback configuration errors fail before cache
or network access. Fetch, UTF-8 decoding, parsing, and missing value-path failures
are exposed as `RemoteDocumentError` with their original cause attached.

When a refresh fails during those acquisition steps, a matching stale cache is
used by default if its document still parses and resolves. Set
`stale_if_error=False` to require a successful refresh. Corrupt, mismatched,
future-dated, non-UTC, and unsupported cache records are ignored.

The cache is replaced only after fetch, parse, traversal, and comparison all
succeed. Invalid numeric versions, callback exceptions, and non-boolean callback
returns raise `ComparisonError` and preserve the previous cache bytes. Cache read
and write errors propagate because Case 15 cannot honor the selected storage
lifecycle.

## Dependencies and tests

Case 15 directly depends on `case13` and `case14`. It does not use Case 12.

```powershell
uv run pytest -q tests/case15
```
