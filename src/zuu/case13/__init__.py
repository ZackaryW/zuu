"""Read and write nested values through explicit sequences of keys."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from enum import StrEnum
from types import SimpleNamespace
from typing import Any

__purpose__ = (
    "Read and set nested values through key paths with item or attribute policies."
)
__depends__ = ()

_MISSING = object()


class AccessPolicy(StrEnum):
    """Choose item access, attribute access, or dispatch by each container's type.

    AUTO uses item access for Mapping and Sequence instances and attributes
    for other objects. It never retries a failed lookup with another mode.
    """

    ITEM = "item"
    ATTRIBUTE = "attribute"
    AUTO = "auto"


def deep_get(
    obj: Any,
    keys: Iterable[Any],
    default: Any = _MISSING,
    *,
    policy: AccessPolicy | str = AccessPolicy.ITEM,
) -> Any:
    """Follow a key path with the selected policy; an empty path returns the root.

    Missing items (KeyError/IndexError) or attributes (AttributeError) raise
    unless ``default`` is supplied. Only the selected mode's missing errors
    qualify for fallback; other errors propagate.
    """
    policy = AccessPolicy(policy)
    path = _key_path(keys)
    current = obj
    for key in path:
        mode = _access_mode(current, policy)
        missing = (
            (KeyError, IndexError) if mode is AccessPolicy.ITEM else (AttributeError,)
        )
        try:
            current = _read(current, key, mode)
        except missing:
            if default is _MISSING:
                raise
            return default
    return current


def deep_set(
    obj: Any,
    keys: Iterable[Any],
    value: Any,
    nullobject: Any = _MISSING,
    *,
    policy: AccessPolicy | str = AccessPolicy.ITEM,
) -> None:
    """Set a nested value in place, creating missing intermediate keys or attributes.

    Each missing component receives a deep copy of ``nullobject``. When omitted,
    item access creates dictionaries and attribute access creates SimpleNamespace
    objects. Existing values, including None, are traversed unchanged.
    Lists are not extended; empty paths are rejected. The assigned value is
    stored by reference. A new branch is attached only after it is built.
    """
    policy = AccessPolicy(policy)
    path = _key_path(keys)
    if not path:
        raise ValueError("deep_set requires at least one key")

    current = obj
    parent = _MISSING
    parent_key: Any = None
    parent_mode = AccessPolicy.ITEM
    branch: Any = None
    for key in path[:-1]:
        mode = _access_mode(current, policy)
        missing = (KeyError,) if mode is AccessPolicy.ITEM else (AttributeError,)
        try:
            child = _read(current, key, mode)
        except missing:
            if nullobject is _MISSING:
                child = {} if mode is AccessPolicy.ITEM else SimpleNamespace()
            else:
                child = deepcopy(nullobject)
            if parent is _MISSING:
                parent, parent_key, branch = current, key, child
                parent_mode = mode
            else:
                _write(current, key, child, mode)
        current = child

    _write(current, path[-1], value, _access_mode(current, policy))
    if parent is not _MISSING:
        _write(parent, parent_key, branch, parent_mode)


def _access_mode(obj: Any, policy: AccessPolicy) -> AccessPolicy:
    if policy is AccessPolicy.AUTO:
        return (
            AccessPolicy.ITEM
            if isinstance(obj, (Mapping, Sequence))
            else AccessPolicy.ATTRIBUTE
        )
    return policy


def _read(obj: Any, key: Any, mode: AccessPolicy) -> Any:
    return obj[key] if mode is AccessPolicy.ITEM else getattr(obj, key)


def _write(obj: Any, key: Any, value: Any, mode: AccessPolicy) -> None:
    if mode is AccessPolicy.ITEM:
        obj[key] = value
    else:
        setattr(obj, key, value)


def _key_path(keys: Iterable[Any]) -> tuple[Any, ...]:
    if isinstance(keys, (str, bytes, bytearray)):
        raise TypeError("keys must be an iterable of keys, not a string or bytes")
    return tuple(keys)


__all__ = ["deep_get", "deep_set", "AccessPolicy"]
