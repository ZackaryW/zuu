"""Immutable local bindings and tombstones over a read-only base mapping."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Generic, TypeVar

__purpose__ = (
    "Personalize a shared mapping like a correction sheet, overlaying local values "
    "and crossed-out keys without changing the original."
)
__depends__ = ()

Key = TypeVar("Key", bound=Hashable)
Value = TypeVar("Value")


class TombstoneOverlayError(ValueError):
    """Overlay declarations violate the binding and tombstone invariant."""


@dataclass(frozen=True, slots=True, init=False)
class TombstoneOverlay(Generic[Key, Value]):
    """Hold local bindings and hidden keys without mutating a base mapping.

    A key cannot be both locally bound and hidden. Every state transition returns
    a new overlay, leaving the previous overlay available to reuse.
    """

    bindings: Mapping[Key, Value]
    hidden: frozenset[Key]

    def __init__(
        self,
        bindings: Mapping[Key, Value] | None = None,
        hidden: Iterable[Key] = (),
    ) -> None:
        local = dict(bindings or {})
        tombstones = frozenset(hidden)
        overlap = local.keys() & tombstones
        if overlap:
            raise TombstoneOverlayError(
                f"keys cannot be both bound and hidden: {tuple(overlap)!r}"
            )
        object.__setattr__(self, "bindings", MappingProxyType(local))
        object.__setattr__(self, "hidden", tombstones)

    @classmethod
    def empty(cls) -> TombstoneOverlay[Key, Value]:
        """Create an overlay with no local bindings or tombstones."""
        return cls()

    @property
    def is_empty(self) -> bool:
        """Report whether applying this overlay would leave any base unchanged."""
        return not self.bindings and not self.hidden

    def bind(self, key: Key, value: Value) -> TombstoneOverlay[Key, Value]:
        """Return an overlay that locally binds ``key`` and removes its tombstone."""
        bindings = dict(self.bindings)
        bindings[key] = value
        return type(self)(bindings, self.hidden - {key})

    def hide(self, key: Key) -> TombstoneOverlay[Key, Value]:
        """Return an overlay that hides ``key`` and removes its local binding."""
        bindings = dict(self.bindings)
        bindings.pop(key, None)
        return type(self)(bindings, self.hidden | {key})

    def clear(self, key: Key) -> TombstoneOverlay[Key, Value]:
        """Remove local state for ``key`` so an inherited base value is visible."""
        bindings = dict(self.bindings)
        bindings.pop(key, None)
        return type(self)(bindings, self.hidden - {key})

    def apply(self, base: Mapping[Key, Value]) -> dict[Key, Value]:
        """Return a new mapping with tombstones removed and bindings applied."""
        result = dict(base)
        for key in self.hidden:
            result.pop(key, None)
        result.update(self.bindings)
        return result


__all__ = [
    "TombstoneOverlay",
    "TombstoneOverlayError",
]
