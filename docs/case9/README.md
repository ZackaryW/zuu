# case9: Temporary JSON environments

`case9` hands structured settings to child processes like a short-lived luggage
locker: the environment variable carries the claim ticket, while the JSON payload
remains in the locker until the caller leaves the context and cleanup removes it.

## Dependencies

This case is standalone and uses only the Python standard library.

## Create a child environment

`TemporaryJsonEnvironment` copies a base environment, writes a deterministic UTF-8
JSON file, and points a caller-selected environment variable at that file:

```python
import subprocess

from zuu.case9 import TemporaryJsonEnvironment


with TemporaryJsonEnvironment(
    {"profile": "preview", "retries": 2},
    variable="MY_TOOL_CONFIG",
) as environment:
    subprocess.run(["my-tool"], env=environment, check=True)
```

The file is closed before the environment is yielded, so a child process can read
it on Windows as well as POSIX systems. On context exit the file is removed,
including when the caller or child-process handling raises an exception.

Neither `os.environ`, a supplied base mapping, nor the payload mapping is mutated.
When `base` is omitted, the current process environment is copied upon context
entry. Pass `base={}` for an intentionally minimal child environment.

## Empty payloads and stale references

An empty payload creates no file. The configured variable is still removed from
the copied environment, preventing an inherited stale path from reaching the child:

```python
with TemporaryJsonEnvironment(
    {},
    variable="MY_TOOL_CONFIG",
    base={"MY_TOOL_CONFIG": "stale.json", "KEEP": "yes"},
) as environment:
    assert environment == {"KEEP": "yes"}
```

Use `directory=...` to select the temporary-file directory. The directory must
already exist. One context instance may be reused sequentially, but cannot be
entered again while it is active.

## Boundaries and errors

This case owns serialization, temporary-file lifetime, and environment projection.
It does not start a process, select an executable, encrypt the file, provide
long-lived configuration storage, or act as a general IPC channel.

`TemporaryJsonEnvironmentError` is raised for an invalid variable name, non-string
base environment entries, a non-mapping or non-serializable payload, concurrent
re-entry, temporary-file creation failure, or cleanup failure. If cleanup fails
while another exception is already active, the cleanup detail is attached as a
note so the original failure remains primary.

## Tests

Run the focused suite with:

```powershell
uv run pytest -q tests/case9
```
