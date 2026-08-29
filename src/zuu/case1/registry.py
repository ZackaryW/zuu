"""Strict JSON serialization for hash registry references."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .reference import HashReference


class RegistryFormatError(ValueError):
    """The configured reference returned malformed or unsupported registry data."""


def read_registry(reference: HashReference) -> dict[str, Any]:
    """Decode and validate the complete registry, or create empty in-memory state."""
    payload = reference.read()
    if payload is None:
        return {"version": 1, "entries": {}}
    if not isinstance(payload, bytes):
        raise RegistryFormatError("reference.read() must return bytes or None")
    try:
        registry = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RegistryFormatError("reference does not contain valid JSON") from error
    _validate_registry(registry)
    return registry


def write_registry(reference: HashReference, registry: Mapping[str, Any]) -> None:
    """Serialize the complete registry deterministically through its reference."""
    payload = json.dumps(
        registry,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    reference.write(payload)


def _validate_registry(registry: object) -> None:
    if not isinstance(registry, dict):
        raise RegistryFormatError("registry must be a JSON object")
    if registry.get("version") != 1 or not isinstance(registry.get("entries"), dict):
        raise RegistryFormatError("registry requires version 1 and an entries object")
    for identifier, entry in registry["entries"].items():
        valid = (
            isinstance(identifier, str)
            and isinstance(entry, dict)
            and isinstance(entry.get("paths"), list)
            and all(isinstance(path, str) for path in entry["paths"])
            and isinstance(entry.get("exclusions"), list)
            and all(isinstance(mask, str) for mask in entry["exclusions"])
            and isinstance(entry.get("hasher"), str)
            and isinstance(entry.get("digest"), str)
        )
        if not valid:
            raise RegistryFormatError(f"invalid registry entry for {identifier!r}")
