# case13: Deep key traversal

`case13` reads, checks, initializes, updates, and removes nested values using an
explicit path of keys and an access policy. It is standalone and uses only the
Python standard library.

## Access policies

All six functions accept a keyword-only `policy=` argument:

| Policy | Behavior at each path component |
|--------|---------------------------------|
| `AccessPolicy.ITEM` (default) | Use `current[key]`, item assignment, and item deletion. |
| `AccessPolicy.ATTRIBUTE` | Use `getattr`, `setattr`, and `delattr`. |
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

## Check whether a path exists

```python
from zuu.case13 import deep_has

data = {"user": {"email": None}}
assert deep_has(data, ["user", "email"])
assert not deep_has(data, ["user", "missing"])
assert deep_has(data, [])
```

`deep_has(obj, keys)` returns a boolean using the same lookup rules as `deep_get`.
An existing falsey value is present. Missing keys, indexes, or attributes return
`False` according to the selected policy. Unsupported operations, type errors,
and exceptions from the wrong access protocol propagate. The empty path always
exists, even when the root is `None`. Custom getters can still have side effects.

## Remove and return a value

```python
from zuu.case13 import deep_pop

data = {"user": {"email": "ada@example.test"}, "values": [1, 2, 3]}
assert deep_pop(data, ["user", "email"]) == "ada@example.test"
assert data["user"] == {}
assert deep_pop(data, ["user", "email"], default=None) is None
assert deep_pop(data, ["values", -2]) == 2
assert data["values"] == [1, 3]
```

`deep_pop(obj, keys, default=...)` reads and deletes the leaf, returning the read
value by reference. It leaves parent containers in place and never creates
missing parents. A missing lookup at any depth returns the supplied default or
raises its normal missing exception. Deletion errors propagate even when a
default is supplied: a readable value on a read-only container is not absent.

Item deletion uses `del parent[key]`; removing a list element shifts the later
indexes. Attribute deletion uses `delattr`, including property deleters and
normal slot behavior. An empty path raises `ValueError`.

## Initialize only when missing

```python
from zuu.case13 import deep_setdefault

data = {}
tags = deep_setdefault(data, ["user", "tags"], [])
tags.append("staff")
assert deep_setdefault(data, ["user", "tags"], ["unused"]) is tags
assert data == {"user": {"tags": ["staff"]}}
```

`deep_setdefault(obj, keys, default=None, nullobject=...)` returns the existing
leaf without overwriting it, including falsey values. If the leaf is missing,
it stores and returns the supplied `default` by reference. No write is attempted
for an existing leaf, so that case works on a read-only container.

Missing intermediate components use the same independent copied templates and
staged attachment as `deep_set`. If a copied template already provides the leaf,
that template value is retained and returned. An unused template is never copied.
Normal container lookup behavior still applies: a `defaultdict` can supply its
own value before this function sees a missing key.

Empty paths raise `ValueError`. List indexes must already be in range; neither
missing intermediate indexes nor an out-of-range leaf cause automatic list growth.
This is a convenience operation, not an atomic concurrent initialization primitive.

## Transform an existing value

```python
from zuu.case13 import deep_update

data = {"stats": {"visits": 4}}
assert deep_update(data, ["stats", "visits"], lambda count: count + 1) == 5
assert data["stats"]["visits"] == 5
```

`deep_update(obj, keys, transform)` resolves the parent and reads the existing
leaf once, calls `transform(value)` once, assigns its result, and returns that
result by reference. If a property setter normalizes the value, the return value
is still the callback result, rather than a second read of the property.

Missing paths raise without calling the transform or creating containers.
The transform must be callable; invalid transforms raise `TypeError` before path
consumption. Empty paths raise `ValueError`. Callback exceptions propagate, and
assignment is attempted only after the callback returns successfully. An assignment
failure propagates after the callback has run.

The callback receives the actual stored value. Any mutation it performs on that
value or other objects persists even if it later raises. If the callback changes
the path's ancestry, assignment still targets the originally resolved parent.
There is no concurrency or rollback guarantee for callbacks or custom setters.

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
Item-mode writes and deletions additionally require item assignment or deletion
on the container being changed.
Read-only mappings and tuples can be traversed to reach mutable children, but
cannot themselves receive an assignment or deletion.

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
after the leaf is assigned or `deep_setdefault` finds it in the copied template.
With ordinary containers, a copy failure,
invalid later key, or unusable template therefore does not leave a partially
created branch in the original object.

Container and copy exceptions propagate normally. Custom `__getitem__`,
`__setitem__`, `__delitem__`, `__getattr__`, `__setattr__`, `__delattr__`, property
accessors, and `__deepcopy__`
methods retain their own side effects; these functions do not provide transaction
rollback for arbitrary user code. This
also means a `defaultdict` lookup can create its own default before Case 13
observes a missing-key exception.

## Tests

```powershell
uv run pytest -q tests/case13
```
