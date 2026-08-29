# Case 2: filesystem snapshots

`FileSystemSnapshot` captures an immutable, deterministic representation of regular
files and directory trees. It records canonical roots, relative paths, entry kinds,
file bytes, and nanosecond modification times without calculating a hash.

## Dependency

Case2 is standalone and has no case dependencies. Case1 consumes its public snapshot
model when calculating stored hashes.

## Capture a snapshot

```python
from pathlib import Path

from zuu.case2 import FileSystemSnapshot

snapshot = FileSystemSnapshot.capture(
    [Path.cwd() / "src", Path.cwd() / "pyproject.toml"],
    exclusions=["__pycache__/**", "*.pyc"],
)

for entry in snapshot.entries:
    print(entry.root_index, entry.relative_path, entry.kind)
```

The equivalent convenience function is:

```python
from zuu.case2 import capture_snapshot

snapshot = capture_snapshot([Path.cwd() / "src"])
```

## Snapshot model

Each `SnapshotEntry` contains:

- `root_index`: the entry's owning root in `snapshot.roots`;
- `relative_path`: a POSIX-style path relative to that root, with `.` representing
  the root itself;
- `kind`: `SnapshotKind.FILE` or `SnapshotKind.DIRECTORY`;
- `content`: file bytes, or `None` for a directory;
- `modified_ns`: the entry's nanosecond modification time.

Use `snapshot.files` and `snapshot.directories` for filtered immutable tuples.
Canonical roots are sorted and deduplicated, and entries are captured in deterministic
order. Empty directories remain visible in the snapshot.

## Exclusions

Exclusion masks are checked against relative paths, entry names, and canonical
absolute paths:

```python
snapshot = FileSystemSnapshot.capture(
    [Path.cwd()],
    exclusions=[
        ".git/**",
        ".venv/**",
        "build/**",
        "*.tmp",
    ],
)
```

A directory mask ending in `/**` removes the directory and prunes its entire subtree.
An excluded entry is outside the snapshot boundary.

## Filesystem safety

Snapshot roots must already exist and must be regular files or directories. Symbolic
link roots and non-excluded symbolic links inside a directory are rejected rather
than followed. Unsupported filesystem entries and unreadable files also fail the
capture.

`SnapshotError` reports these boundary failures. A failed capture returns no partial
snapshot.

## Comparison

Snapshots are frozen dataclasses, so ordinary equality compares roots and all entry
data:

```python
before = FileSystemSnapshot.capture([Path.cwd() / "src"])
# Filesystem activity occurs here.
after = FileSystemSnapshot.capture([Path.cwd() / "src"])

if before != after:
    print("The snapshot changed")
```

Case2 deliberately does not decide how snapshots are hashed, persisted, diffed, or
restored. Those are separate responsibilities.

## Running the tests

```powershell
uv run pytest -q tests/case2
```
