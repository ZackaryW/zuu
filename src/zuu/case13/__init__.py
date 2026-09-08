"""Read and write nested values through explicit sequences of keys."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from types import SimpleNamespace
from typing import Any

__purpose__ = "Read, initialize, update, and remove nested values using item or attribute key paths."
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
        try:
            current = _read(current, key, mode)
        except _missing_errors(mode):
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
    path = _mutation_path(keys, "deep_set")
    target = _resolve_parent(obj, path, policy, create=True, nullobject=nullobject)
    assert target is not None
    _write(target.parent, target.key, value, target.mode)
    target.attach()


def deep_has(
    obj: Any,
    keys: Iterable[Any],
    *,
    policy: AccessPolicy | str = AccessPolicy.ITEM,
) -> bool:
    """Return whether the path resolves, including falsey values and an empty path.

    Only the selected access mode's missing lookup exceptions mean absence.
    Other errors propagate, and custom getters retain their normal side effects.
    """
    absent = object()
    return deep_get(obj, keys, default=absent, policy=policy) is not absent


def deep_pop(
    obj: Any,
    keys: Iterable[Any],
    default: Any = _MISSING,
    *,
    policy: AccessPolicy | str = AccessPolicy.ITEM,
) -> Any:
    """Remove and return an existing nested value without pruning empty parents.

    Missing lookups return ``default`` when supplied, otherwise raise. Deletion
    errors always propagate. List deletion shifts later indexes; empty paths
    are rejected. No intermediate containers are created.
    """
    policy = AccessPolicy(policy)
    path = _mutation_path(keys, "deep_pop")
    target = _resolve_parent(obj, path, policy, missing_ok=default is not _MISSING)
    if target is None:
        return default
    try:
        value = _read(target.parent, target.key, target.mode)
    except _missing_errors(target.mode):
        if default is _MISSING:
            raise
        return default
    if target.mode is AccessPolicy.ITEM:
        del target.parent[target.key]
    else:
        delattr(target.parent, target.key)
    return value


def deep_setdefault(
    obj: Any,
    keys: Iterable[Any],
    default: Any = None,
    nullobject: Any = _MISSING,
    *,
    policy: AccessPolicy | str = AccessPolicy.ITEM,
) -> Any:
    """Return the existing value or insert and return ``default`` by reference.

    Missing intermediates follow deep_set's template and staged-attachment
    rules. Existing falsey values are preserved. List bounds and empty-path
    restrictions are unchanged; this operation is not a concurrency primitive.
    """
    policy = AccessPolicy(policy)
    path = _mutation_path(keys, "deep_setdefault")
    target = _resolve_parent(obj, path, policy, create=True, nullobject=nullobject)
    assert target is not None
    try:
        value = _read(target.parent, target.key, target.mode)
    except _missing_errors(target.mode, include_index=False):
        value = default
        _write(target.parent, target.key, value, target.mode)
    target.attach()
    return value


def deep_update(
    obj: Any,
    keys: Iterable[Any],
    transform: Callable[[Any], Any],
    *,
    policy: AccessPolicy | str = AccessPolicy.ITEM,
) -> Any:
    """Transform an existing value once, assign the result, and return that result.

    Resolve the parent once. Missing paths raise without calling ``transform``.
    Assignment happens only after the callback returns; callback or custom
    setter side effects cannot be rolled back. Empty paths are rejected.
    """
    policy = AccessPolicy(policy)
    if not callable(transform):
        raise TypeError("transform must be callable")
    path = _mutation_path(keys, "deep_update")
    target = _resolve_parent(obj, path, policy)
    assert target is not None
    value = _read(target.parent, target.key, target.mode)
    result = transform(value)
    _write(target.parent, target.key, result, target.mode)
    return result


@dataclass(slots=True)
class _Target:
    parent: Any
    key: Any
    mode: AccessPolicy
    attachment: tuple[Any, Any, Any, AccessPolicy] | None

    def attach(self) -> None:
        if self.attachment is not None:
            _write(*self.attachment)


def _resolve_parent(
    obj: Any,
    path: tuple[Any, ...],
    policy: AccessPolicy,
    *,
    create: bool = False,
    nullobject: Any = _MISSING,
    missing_ok: bool = False,
) -> _Target | None:
    current = obj
    attachment = None

    for key in path[:-1]:
        mode = _access_mode(current, policy)
        try:
            child = _read(current, key, mode)
        except _missing_errors(mode, include_index=not create):
            if not create:
                if missing_ok:
                    return None
                raise
            if nullobject is _MISSING:
                child = {} if mode is AccessPolicy.ITEM else SimpleNamespace()
            else:
                child = deepcopy(nullobject)
            if attachment is None:
                attachment = (current, key, child, mode)
            else:
                _write(current, key, child, mode)
        current = child

    return _Target(current, path[-1], _access_mode(current, policy), attachment)


def _missing_errors(
    mode: AccessPolicy,
    *,
    include_index: bool = True,
) -> tuple[type[Exception], ...]:
    if mode is AccessPolicy.ATTRIBUTE:
        return (AttributeError,)
    return (KeyError, IndexError) if include_index else (KeyError,)


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


def _mutation_path(keys: Iterable[Any], operation: str) -> tuple[Any, ...]:
    path = _key_path(keys)
    if not path:
        raise ValueError(f"{operation} requires at least one key")
    return path


__all__ = [
    "deep_get",
    "deep_set",
    "deep_has",
    "deep_pop",
    "deep_setdefault",
    "deep_update",
    "AccessPolicy",
]
