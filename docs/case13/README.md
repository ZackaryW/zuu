# case13: Deep key traversal

`case13` reads and writes nested values using an explicit path of keys. It is
standalone and uses only the Python standard library.

## Read a nested value

```python
from zuu.case13 import deep_get, deep_set

data = {"users": [{"name": "Ada", "settings": {"theme": "dark"}}]}

assert deep_get(data, ["users", 0, "name"]) == "Ada"
assert deep_get(data, ["users", 0, "settings", "theme"]) == "dark"
assert deep_get(data, ["users", 0, "missing"], default=None) is None
```

`deep_get(obj, keys, default=...)` applies `current[key]` at each step. Without
`default`, missing keys raise `KeyError` and out-of-range indexes raise `IndexError`.
With `default`, either missing condition returns that exact fallback object.
Existing values such as `None`, `False`, zero, and empty containers are returned
unchanged. A `TypeError`, such as trying to index an integer or traverse through
`None`, still propagates even when a fallback was supplied.

An empty path returns the original root object. Reads return the stored value by
reference, without copying it.

## Set a nested value

```python
data = {}

deep_set(data, ["service", "database", "port"], 5432)
assert data == {"service": {"database": {"port": 5432}}}

deep_set(data, ["service", "database", "port"], 5433)
assert deep_get(data, ["service", "database", "port"]) == 5433
```

`deep_set(obj, keys, value, nullobject=...)` mutates the original object and returns
`None`. It replaces or adds the final key and stores `value` by reference. Existing
intermediate containers retain their identity, and sibling values are preserved.
An empty path raises `ValueError`: this function cannot replace the root itself.

Missing intermediate keys create independent dictionaries by default. Set
`nullobject` to a template to customize those containers:

```python
template = {"labels": []}
data = {}
deep_set(data, ["first", "value"], 1, nullobject=template)
deep_set(data, ["second", "value"], 2, nullobject=template)

data["first"]["labels"].append("one")
assert data["second"]["labels"] == []
assert template == {"labels": []}
```

Every missing intermediate key receives a separate `copy.deepcopy(nullobject)`.
Omitting the argument is equivalent to providing `{}`, without sharing a mutable
default between calls. The template is copied only when an intermediate lookup
raises `KeyError`; it is not a factory and is not called. Its existing content is
retained. Explicit `nullobject=None` supplies a `None` template and will fail if
the path needs to traverse or assign inside it.

Existing intermediate values are never replaced automatically. For example,
`deep_set({"a": None}, ["a", "b"], 1)` raises `TypeError` instead of replacing
`None` with a dictionary. Lists are not grown, padded, or appended automatically;
out-of-range indexes raise `IndexError`.

## Key paths and supported containers

Paths may be lists, tuples, or other iterables, including generators. The path is
consumed before traversal. Bare strings and byte strings are rejected to avoid
treating a key name as a sequence of characters; use `["name"]` for one key.
Keys are literal: `"a.b"` is one key, and tuple or integer mapping keys work as
they do in normal Python indexing. There is no dotted-path parsing or wildcard
expansion. Traversal is iterative and does not consume recursion depth per key.

Dictionary keys, list indexes, and tuple indexes can be mixed, including negative
sequence indexes. Containers determine which key types are valid. Any custom
object implementing item access can participate, such as `collections.UserDict`.
Writes additionally require item assignment on the container being changed.
Read-only mappings and tuples can be traversed to reach mutable children, but
cannot themselves receive an assignment.

Class-instance attributes such as `person.address.city` are not resolved through
dot access. A path uses `person["address"]["city"]`, requiring item access on
those objects.

A list template can supply existing positions when needed:

```python
data = {}
deep_set(data, ["group", 0, "name"], "Ada", nullobject=[{}])
assert data == {"group": [{"name": "Ada"}]}
```

## Failure and mutation behavior

New branches are built separately and attached at the first missing key only
after the final assignment succeeds. With ordinary containers, a copy failure,
invalid later key, or unusable template therefore does not leave a partially
created branch in the original object.

Container and copy exceptions propagate normally. Custom `__getitem__`,
`__setitem__`, and `__deepcopy__` methods retain their own side effects; these
functions do not provide transaction rollback for arbitrary user code. This
also means a `defaultdict` lookup can create its own default before Case 13
observes a missing-key exception.

## Tests

```powershell
uv run pytest -q tests/case13
```
