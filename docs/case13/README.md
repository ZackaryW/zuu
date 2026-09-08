# case13: Deep key traversal

`case13` reads and writes nested values using an explicit path of keys and an
access policy. It is standalone and uses only the Python standard library.

## Access policies

Both functions accept a keyword-only `policy=` argument:

| Policy | Behavior at each path component |
|--------|---------------------------------|
| `AccessPolicy.ITEM` (default) | Use `current[key]` and item assignment. |
| `AccessPolicy.ATTRIBUTE` | Use `getattr(current, key)` and `setattr(current, key, value)`. |
| `AccessPolicy.AUTO` | Use item access for `collections.abc.Mapping` and `Sequence` instances; use attributes for other objects. |

The lowercase strings `"item"`, `"attribute"`, and `"auto"` are also accepted.
An unknown policy raises `ValueError` before the path is consumed or traversed.
The default remains item access, preserving existing calls.

Attribute access works with ordinary instances, dataclasses, properties, slots,
and dynamic attributes according to Python's normal rules:

```python
from types import SimpleNamespace
from zuu.case13 import AccessPolicy, deep_get, deep_set

person = SimpleNamespace(address=SimpleNamespace(city="Paris"))
assert deep_get(person, ["address", "city"], policy=AccessPolicy.ATTRIBUTE) == "Paris"
deep_set(person, ["address", "city"], "London", policy=AccessPolicy.ATTRIBUTE)
assert person.address.city == "London"
```

`AUTO` reselects the access style at every step, so a path can mix objects,
dictionaries, lists, and tuples:

```python
root = SimpleNamespace(data={"people": [person]})
deep_set(root, ["data", "people", 0, "address", "city"], "Rome", policy=AccessPolicy.AUTO)
assert deep_get(root, ["data", "people", 0, "address", "city"], policy="auto") == "Rome"
```

Selection is based on type, not lookup success. `AUTO` does not try an attribute
after a missing item, or an item after a missing attribute. Mapping and sequence
subclasses use items even if they also have attributes with the same name. Strings
are sequences and use item access too. A custom object with `__getitem__` that is
not a `Mapping` or `Sequence` uses attributes in `AUTO`; choose `ITEM` explicitly
to use that object's item protocol.

## Read a nested value

```python
from zuu.case13 import deep_get, deep_set

data = {"users": [{"name": "Ada", "settings": {"theme": "dark"}}]}

assert deep_get(data, ["users", 0, "name"]) == "Ada"
assert deep_get(data, ["users", 0, "settings", "theme"]) == "dark"
assert deep_get(data, ["users", 0, "missing"], default=None) is None
```

With the default `ITEM` policy, `deep_get(obj, keys, default=...)` applies
`current[key]` at each step. Without `default`, missing keys raise `KeyError`
and out-of-range indexes raise `IndexError`.
With `default`, either missing condition returns that exact fallback object.
Existing values such as `None`, `False`, zero, and empty containers are returned
unchanged. A `TypeError`, such as trying to index an integer or traverse through
`None`, still propagates even when a fallback was supplied.

For an attribute step, a missing attribute raises `AttributeError`, or returns
the supplied `default`. This includes `AttributeError` raised by a property or
`__getattr__`, matching normal Python attribute lookup semantics. Attribute names
must be strings; non-string names raise `TypeError`. Only the selected access mode's
missing exceptions receive fallback handling: a property's `KeyError`, or an item
getter's `AttributeError`, propagates. Other errors also propagate normally.

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

Missing intermediate items create independent dictionaries by default. Missing
intermediate attributes create independent `types.SimpleNamespace` objects.
In `AUTO`, the access style of the parent where the component is missing decides
which default container is created. For example:

```python
person = SimpleNamespace()
deep_set(person, ["address", "city"], "Paris", policy="attribute")
assert person.address.city == "Paris"
```

Set `nullobject` to a template to customize those containers:

```python
template = {"labels": []}
data = {}
deep_set(data, ["first", "value"], 1, nullobject=template)
deep_set(data, ["second", "value"], 2, nullobject=template)

data["first"]["labels"].append("one")
assert data["second"]["labels"] == []
assert template == {"labels": []}
```

Every missing intermediate component receives a separate `copy.deepcopy(nullobject)`
when a template is explicitly supplied. Templates are honored without conversion:
use a `SimpleNamespace` or your own instance for `ATTRIBUTE`; `AUTO` can switch
to item access inside a supplied dictionary template. Supplying `{}` under pure
`ATTRIBUTE` mode fails when the path requires assigning dictionary attributes.

Omitting the argument uses the policy-aware fresh containers described above,
without sharing a mutable default between calls. The template is copied only when
an intermediate item lookup raises `KeyError` or an attribute lookup raises
`AttributeError`; it is not a factory and is not called. Its existing content is
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
Item-mode writes additionally require item assignment on the container being changed.
Read-only mappings and tuples can be traversed to reach mutable children, but
cannot themselves receive an assignment.

Under `ATTRIBUTE`, each path component must be a string naming a single attribute.
Names remain literal: `["a.b"]` addresses one attribute named `a.b`, rather than
two fields. The same policy applies throughout a path; select `AUTO` to mix item
and attribute access. Read-only properties and unavailable slots reject writes
through normal `AttributeError` exceptions.

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
`__setitem__`, `__getattr__`, `__setattr__`, property accessors, and `__deepcopy__`
methods retain their own side effects; these functions do not provide transaction
rollback for arbitrary user code. This
also means a `defaultdict` lookup can create its own default before Case 13
observes a missing-key exception.

## Tests

```powershell
uv run pytest -q tests/case13
```
