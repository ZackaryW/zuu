# case5: Safe repository paths

`case5` makes repository-relative path selection safe and predictable across
platforms. It provides one canonical path representation, a bounded glob dialect,
and strict file resolution confined to a repository root.

## Dependencies

This case is standalone and uses only the Python standard library.

## Define paths and patterns

`RepositoryPath` accepts a non-empty relative path written with `/` separators and
preserves that canonical spelling:

```python
from zuu.case5 import RepositoryGlob, RepositoryPath


path = RepositoryPath("src/zuu/case5/__init__.py")
pattern = RepositoryGlob("src/**/test_*.py")

print(path.parts)
print(pattern.matches("src/zuu/case5/test_paths.py"))
```

Absolute paths, Windows drive paths, backslashes, `.` or `..` segments, redundant
separators, empty values, and null bytes are rejected. This deliberately avoids
platform-dependent normalization: callers receive either the exact portable path
dialect or an error.

## Glob dialect

`RepositoryGlob.matches()` checks the complete canonical path. The supported
operators are:

- `*` for zero or more characters inside one path segment;
- `?` for one character inside one path segment;
- `[abc]` and `[!abc]` character classes inside one segment;
- `**` as an entire segment for zero or more path segments.

For example, `tests/**/test_*.py` matches both `tests/test_api.py` and
`tests/case5/test_paths.py`. A partial prefix does not count as a match. Malformed
character classes and `**` embedded inside another segment are rejected when the
glob is constructed.

## Resolve a confined file

`RepositoryPath.resolve_file(root)` resolves an existing regular file beneath an
existing repository directory:

```python
from pathlib import Path

from zuu.case5 import RepositoryPath


source = RepositoryPath("pyproject.toml").resolve_file(Path.cwd())
```

The root and candidate are resolved strictly. Missing paths, directories, and
symlinks whose final target escapes the resolved root are rejected. The returned
`Path` is absolute and resolved; this method does not create or modify files.

## Errors

`RepositoryPathError` is raised for unsafe paths, unsupported glob syntax, missing
files or roots, non-file candidates, and resolution outside the repository root.

## Tests

Run the focused suite with:

```powershell
uv run pytest -q tests/case5
```
