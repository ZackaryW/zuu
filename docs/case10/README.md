# case10: Tombstone overlays

`case10` personalizes a shared mapping like a correction sheet: a local entry can
replace a shared value, while a crossed-out key hides it without changing the
original mapping itself.

## Dependencies

This case is standalone and uses only the Python standard library.

## Build an overlay

A `TombstoneOverlay` has two disjoint pieces of local state:

- `bindings` replace inherited values or add new values;
- `hidden` keys are tombstones that suppress inherited values.

```python
from zuu.case10 import TombstoneOverlay


base = {"host": "localhost", "port": 80, "legacy": True}
overlay = TombstoneOverlay(
    {"port": 9000, "secure": True},
    hidden=["legacy"],
)

assert overlay.apply(base) == {
    "host": "localhost",
    "port": 9000,
    "secure": True,
}
assert base == {"host": "localhost", "port": 80, "legacy": True}
```

Applying an overlay returns a new dictionary. Existing base keys keep their base
order when replaced; new local-only bindings are appended in binding order.

## Change local state

Overlay transitions are immutable and composable:

- `bind(key, value)` creates a local binding and removes that key's tombstone;
- `hide(key)` creates a tombstone and removes that key's local binding;
- `clear(key)` removes both forms of local state, exposing any inherited value;
- `empty()` creates an overlay with no local state;
- `is_empty` reports whether the overlay has no effect.

Each operation returns a new overlay, so previous states remain reusable:

```python
hidden = TombstoneOverlay[str, int]().hide("port")
rebound = hidden.bind("port", 443)
inherited = rebound.clear("port")

assert hidden.apply({"port": 80}) == {}
assert rebound.apply({"port": 80}) == {"port": 443}
assert inherited.apply({"port": 80}) == {"port": 80}
```

Keys may be any hashable type and values are generic. The case intentionally keeps
the overlay in memory; parsing, persistence, synchronization, and base-map mutation
belong to consumers.

## Errors

`TombstoneOverlayError` is raised when the same key is declared in both `bindings`
and `hidden`. Normal `bind`, `hide`, and `clear` transitions preserve this invariant
automatically.

## Tests

Run the focused suite with:

```powershell
uv run pytest -q tests/case10
```
