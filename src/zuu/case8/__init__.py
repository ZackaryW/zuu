"""Typed composition of ordered, shallow configuration layers."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from types import MappingProxyType

from .parsing import (
    Cast,
    LayeredMappingError,
    cast_registry,
    ensure_json_compatible,
    parse_assignment,
    parse_json_map,
    parse_typed_assignment,
)

__purpose__ = (
    "Stack configuration like transparent sheets, letting later JSON and typed "
    "assignments cover earlier defaults without recursive merging."
)
__depends__ = ()


class LayeredMapping(Mapping[str, object]):
    """Compose defaults, JSON maps, and assignments into a read-only mapping.

    Later layers replace earlier values at the top level. Nested mappings are
    values and are therefore replaced rather than recursively merged.
    """

    __slots__ = ("_values",)

    def __init__(
        self,
        defaults: Mapping[str, object] | None = None,
        *,
        json_maps: Iterable[str] = (),
        assignments: Iterable[str] = (),
        typed_assignments: Iterable[str] = (),
        casts: Mapping[str, Cast] | None = None,
    ) -> None:
        values = dict(defaults or {})
        available_casts = cast_registry(casts)

        for source in json_maps:
            values.update(parse_json_map(source))
        for source in assignments:
            key, value = parse_assignment(source)
            values[key] = value
        for source in typed_assignments:
            key, value = parse_typed_assignment(source, available_casts)
            values[key] = value

        ensure_json_compatible(values)
        self._values = MappingProxyType(values)

    @property
    def values(self) -> Mapping[str, object]:
        """Return the composed values through a read-only mapping view."""
        return self._values

    def to_dict(self) -> dict[str, object]:
        """Return a shallow mutable copy of the composed mapping."""
        return dict(self._values)

    def __getitem__(self, key: str) -> object:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self._values)!r})"


__all__ = [
    "LayeredMapping",
    "LayeredMappingError",
    "Cast",
]
