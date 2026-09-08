"""Read and write nested values through explicit sequences of keys."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

__purpose__ = "Read and set nested values through explicit key paths."
__depends__ = ()

_MISSING = object()


def deep_get(obj: Any, keys: Iterable[Any], default: Any = _MISSING) -> Any:
    """Follow bracket access through keys, returning the root for an empty path.

    Missing keys or indexes raise their normal exceptions unless ``default``
    is supplied. Type errors and other container errors are never suppressed.
    """
    path = _key_path(keys)
    current = obj
    for key in path:
        try:
            current = current[key]
        except (KeyError, IndexError):
            if default is _MISSING:
                raise
            return default
    return current


def deep_set(
    obj: Any,
    keys: Iterable[Any],
    value: Any,
    nullobject: Any = _MISSING,
) -> None:
    """Set a nested value in place, creating missing intermediate keys.

    Each missing key receives a deep copy of ``nullobject`` (a fresh dictionary
    when omitted). Existing values, including None, are traversed unchanged.
    Lists are not extended; empty paths are rejected. The assigned value is
    stored by reference. A new branch is attached only after it is built.
    """
    path = _key_path(keys)
    if not path:
        raise ValueError("deep_set requires at least one key")

    current = obj
    parent = _MISSING
    parent_key: Any = None
    branch: Any = None
    for key in path[:-1]:
        try:
            child = current[key]
        except KeyError:
            child = {} if nullobject is _MISSING else deepcopy(nullobject)
            if parent is _MISSING:
                parent, parent_key, branch = current, key, child
            else:
                current[key] = child
        current = child

    current[path[-1]] = value
    if parent is not _MISSING:
        parent[parent_key] = branch


def _key_path(keys: Iterable[Any]) -> tuple[Any, ...]:
    if isinstance(keys, (str, bytes, bytearray)):
        raise TypeError("keys must be an iterable of keys, not a string or bytes")
    return tuple(keys)


__all__ = ["deep_get", "deep_set"]
