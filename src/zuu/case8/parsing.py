"""Parsing and casting support for layered mappings."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from typing import Any


class LayeredMappingError(ValueError):
    """A mapping layer, assignment, cast, or final value is invalid."""


Cast = Callable[[str], object]
_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\Z")
_CAST_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def parse_json_map(source: str) -> dict[str, object]:
    """Parse one JSON object used as a shallow mapping layer."""
    try:
        value = json.loads(source)
    except (TypeError, json.JSONDecodeError) as error:
        raise LayeredMappingError(f"invalid JSON mapping: {error}") from error

    if not isinstance(value, dict):
        raise LayeredMappingError("JSON mapping must contain an object at its root")
    return value


def parse_assignment(source: str) -> tuple[str, str]:
    """Parse a plain ``key=value`` assignment."""
    if not isinstance(source, str) or "=" not in source:
        raise LayeredMappingError("assignment must use key=value syntax")
    key, value = source.split("=", 1)
    _validate_key(key)
    return key, value


def parse_typed_assignment(
    source: str,
    casts: Mapping[str, Cast],
) -> tuple[str, object]:
    """Parse and cast a ``type+key=value`` assignment."""
    if not isinstance(source, str) or "+" not in source:
        raise LayeredMappingError("typed assignment must use type+key=value syntax")
    cast_name, assignment = source.split("+", 1)
    key, raw_value = parse_assignment(assignment)
    try:
        cast = casts[cast_name]
    except KeyError as error:
        raise LayeredMappingError(f"unknown cast: {cast_name!r}") from error

    try:
        return key, cast(raw_value)
    except Exception as error:
        raise LayeredMappingError(
            f"cast {cast_name!r} failed for {key!r}: {error}"
        ) from error


def cast_registry(overrides: Mapping[str, Cast] | None) -> dict[str, Cast]:
    """Return built-in casts extended or replaced by caller declarations."""
    casts: dict[str, Cast] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": _cast_bool,
        "json": json.loads,
    }
    if overrides is None:
        return casts

    for name, cast in overrides.items():
        if not isinstance(name, str) or not _CAST_NAME.fullmatch(name):
            raise LayeredMappingError(f"invalid cast name: {name!r}")
        if not callable(cast):
            raise LayeredMappingError(f"cast {name!r} must be callable")
        casts[name] = cast
    return casts


def ensure_json_compatible(values: Mapping[str, object]) -> None:
    """Reject values that cannot be represented by strict JSON."""
    _ensure_string_keys(values)
    try:
        json.dumps(values, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise LayeredMappingError(f"mapping is not JSON-compatible: {error}") from error


def _ensure_string_keys(value: object, seen: set[int] | None = None) -> None:
    seen = set() if seen is None else seen
    if isinstance(value, Mapping):
        if id(value) in seen:
            return
        seen.add(id(value))
        if any(not isinstance(key, str) for key in value):
            raise LayeredMappingError("mapping keys must be strings")
        for nested in value.values():
            _ensure_string_keys(nested, seen)
    elif isinstance(value, (list, tuple)):
        if id(value) in seen:
            return
        seen.add(id(value))
        for nested in value:
            _ensure_string_keys(nested, seen)


def _cast_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError("expected exactly 'true' or 'false'")


def _validate_key(key: Any) -> None:
    if not isinstance(key, str) or not _KEY.fullmatch(key):
        raise LayeredMappingError(f"invalid assignment key: {key!r}")
