# case8: Layered mappings

`case8` stacks configuration like transparent sheets: later JSON and typed
assignments cover earlier defaults without recursively merging or altering the
earlier sheets.

## Dependencies

This case is standalone and uses only the Python standard library.

## Compose layers

`LayeredMapping` applies four stages in a fixed order:

1. a defaults mapping;
2. JSON object strings, in declaration order;
3. plain `key=value` assignments, in declaration order;
4. typed `type+key=value` assignments, in declaration order.

Later values replace earlier values at the top level:

```python
from zuu.case8 import LayeredMapping


config = LayeredMapping(
    {"host": "localhost", "port": 80, "features": {"stable": True}},
    json_maps=['{"port": 8080, "features": {"preview": true}}'],
    assignments=["host=example.test", "token=part=part"],
    typed_assignments=["int+port=9000", "bool+secure=true"],
)

assert config["port"] == 9000
assert config["features"] == {"preview": True}
assert config["token"] == "part=part"
```

Composition is deliberately shallow. The `features` JSON object replaces the
default object instead of recursively merging with it. Input mappings are copied,
and the result exposes a read-only `Mapping` interface. Use `to_dict()` when a
consumer needs an independent mutable top-level copy.

## Typed assignments

The built-in casts are:

| Cast | Result |
|------|--------|
| `str` | The original text. |
| `int` | A Python integer. |
| `float` | A finite Python float. |
| `bool` | A boolean; only lowercase `true` and `false` are accepted. |
| `json` | Any value parsed from JSON. |

The final mapping must be representable as strict JSON. This retains value types
without silently accepting sets, non-finite floats, or non-string mapping keys.

Callers may extend or override casts with a mapping of names to one-argument
callables:

```python
config = LayeredMapping(
    typed_assignments=["upper+name=zuu"],
    casts={"upper": str.upper},
)

assert config["name"] == "ZUU"
```

Cast functions only convert a raw string. Schema validation, business rules, and
command-line parsing remain the caller's responsibility.

## Errors

`LayeredMappingError` is raised for malformed JSON, a non-object JSON root,
malformed assignment syntax, invalid keys, unknown or failed casts, invalid custom
cast declarations, and a final value that is not JSON-compatible.

## Tests

Run the focused suite with:

```powershell
uv run pytest -q tests/case8
```
