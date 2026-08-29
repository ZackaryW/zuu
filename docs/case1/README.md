# Case 1: user-level hashing

`UserLevelHasher` keeps named SHA-256 baselines for files and folders. It is useful
for deciding whether cached work can be reused or an operation needs to run again.

The runtime package uses only the Python standard library. Registries and hashing
strategies are replaceable, so callers can supply encrypted storage or a different
way of calculating a digest.

## Dependency

Case1 depends directly on case2. Case2 captures the filesystem snapshot; case1
turns that snapshot into a digest and manages the stored match state.

## Lifecycle

The API has two stages:

1. `register()` associates an identifier with its governed paths and records their
   current digest.
2. `match()` recalculates the digest and invokes either `on_match` or `on_mismatch`.

If `on_mismatch` succeeds, the new digest is stored. If it raises an exception, the
old digest remains in place so the work will be retried later.

## Basic usage

```python
from pathlib import Path

from zuu.case1 import UserLevelHasher

project = Path.cwd()
cache_folder = Path.home() / ".cache" / "my-tool"
hasher = UserLevelHasher(cache_folder)

# This is safe to call on every run. Repeating the same registration does not reset
# its existing baseline.
hasher.register(
    "project-inputs",
    [
        project / "src",
        project / "pyproject.toml",
    ],
    exclusions=[
        "__pycache__/**",
        "*.pyc",
    ],
)


def use_cached_result() -> str:
    print("Inputs are unchanged")
    return "cached"


def rebuild() -> str:
    print("Inputs changed; rebuilding")
    # Perform the rebuild here. Raising an exception prevents the digest update.
    return "rebuilt"


result = hasher.match(
    "project-inputs",
    on_match=use_cached_result,
    on_mismatch=rebuild,
)
```

The first registration establishes a baseline; it does not invoke either callback.
An immediate `match()` therefore selects `on_match`.

## Storage folder and governed paths

The constructor's `folder_path` is the registry anchor:

```python
hasher = UserLevelHasher(Path.home() / ".cache" / "my-tool")
```

By default, the registry is written atomically to:

```text
<folder_path>/.zuu-hashes.json
```

Relative governed paths are resolved from `folder_path`. Use absolute paths for
files or directories elsewhere:

```python
hasher.register(
    "inputs",
    [
        "local-input.txt",
        Path.cwd() / "src",
    ],
)
```

The default registry file is automatically excluded when its containing folder is
governed, so writing the registry does not invalidate its own digest.

## Identifiers

An identifier is any non-empty string. A UUID is useful for a stable opaque key:

```python
from uuid import uuid4

identifier = str(uuid4())
hasher.register(identifier, [Path.cwd() / "src"])
```

A hash of the canonical governed paths can instead bind the key to that path set:

```python
from hashlib import sha256
from pathlib import Path

paths = [Path.cwd() / "src", Path.cwd() / "pyproject.toml"]
canonical = "\0".join(sorted(str(path.resolve()) for path in paths))
identifier = sha256(canonical.encode("utf-8")).hexdigest()

hasher.register(identifier, paths)
```

Registering an existing identifier with the same definition is a no-op. Registering
it with different paths, exclusions, or a different strategy raises
`IdentifierConflictError`. Use `replace=True` only when intentionally replacing its
definition and baseline:

```python
hasher.register("inputs", [Path.cwd() / "new-src"], replace=True)
```

## Exclusion masks

The case2 snapshot capture used by both built-in strategies supports glob-style
exclusions:

```python
hasher.register(
    "source",
    [Path.cwd()],
    exclusions=[
        ".git/**",
        ".venv/**",
        "build/**",
        "*.pyc",
    ],
)
```

Masks are checked against relative paths, file names, and canonical absolute paths.
A directory mask ending in `/**` prunes the entire directory subtree.

## Built-in strategies

The default strategy hashes path identity and file content:

```python
hasher.register("content", [Path.cwd() / "src"], hasher="content")
```

Use `content-and-mtime` when modification timestamps must also invalidate the
baseline:

```python
hasher.register(
    "timestamp-sensitive",
    [Path.cwd() / "src"],
    hasher="content-and-mtime",
)
```

The `content` strategy is usually preferable because merely touching a file does not
invalidate it.

## Custom hash strategies

A strategy receives the captured `FileSystemSnapshot` and returns a string digest.
Register named strategies when constructing the hasher:

```python
from hashlib import sha256

from zuu.case2 import FileSystemSnapshot


def path_names_only(snapshot: FileSystemSnapshot) -> str:
    value = "\0".join(
        f"{entry.root_index}:{entry.relative_path}:{entry.kind.value}"
        for entry in snapshot.entries
    )
    return sha256(value.encode("utf-8")).hexdigest()


hasher = UserLevelHasher(
    cache_folder,
    hashers={"path-names-only": path_names_only},
)
hasher.register(
    "layout",
    [project / "src"],
    hasher="path-names-only",
)
```

Exclusions have already been applied before a custom strategy receives the snapshot.

## Custom or encrypted registry storage

Pass an object implementing `HashReference` to replace the default plain JSON file.
The interface deliberately operates on bytes so encryption and serialization can be
composed around it:

```python
from collections.abc import Callable
from pathlib import Path


class EncryptedFileReference:
    def __init__(
        self,
        path: Path,
        *,
        encrypt: Callable[[bytes], bytes],
        decrypt: Callable[[bytes], bytes],
    ):
        self.path = path
        self.encrypt = encrypt
        self.decrypt = decrypt

    def read(self) -> bytes | None:
        try:
            encrypted = self.path.read_bytes()
        except FileNotFoundError:
            return None
        return self.decrypt(encrypted)

    def write(self, data: bytes) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(self.encrypt(data))


reference = EncryptedFileReference(
    cache_folder / "hashes.enc",
    encrypt=encrypt_bytes,
    decrypt=decrypt_bytes,
)
hasher = UserLevelHasher(cache_folder, reference=reference)
```

`read()` must return decrypted registry bytes or `None` when no registry exists.
`write()` receives the complete serialized registry as bytes.

## Errors

- `KeyError`: `match()` was called with an unregistered identifier.
- `IdentifierConflictError`: an existing identifier was registered with a different
  definition without `replace=True`.
- `RegistryFormatError`: the configured reference returned malformed registry data.
- `FileNotFoundError` or `NotADirectoryError`: a governed path does not exist or has
  the wrong type.
- `ValueError`: an identifier is empty or a requested hash strategy is unknown.

## Running the tests

```powershell
uv run pytest -q tests/case1
```
