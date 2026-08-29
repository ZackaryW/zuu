"""Named hash registration and match lifecycle."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, TypeVar

from zuu.case2 import FileSystemSnapshot

from .reference import FileReference, HashReference, Pathish
from .registry import RegistryFormatError, read_registry, write_registry
from .utils import _hash_snapshot

__purpose__ = "Store and check named hashes for composable filesystem inputs."
__depends__ = ("case2",)

MatchResult = TypeVar("MatchResult")
MismatchResult = TypeVar("MismatchResult")
SnapshotHasher = Callable[[FileSystemSnapshot], str]


class IdentifierConflictError(ValueError):
    """An existing identifier was registered with a different definition."""


def _content_hasher(snapshot: FileSystemSnapshot) -> str:
    return _hash_snapshot(snapshot)


def _modified_hasher(snapshot: FileSystemSnapshot) -> str:
    return _hash_snapshot(snapshot, include_modified=True)


class UserLevelHasher:
    """Persist and check named hashes for composable filesystem snapshots."""

    def __init__(
        self,
        folder_path: Pathish,
        *,
        reference: HashReference | None = None,
        hashers: Mapping[str, SnapshotHasher] | None = None,
    ):
        self.folder_path = Path(folder_path).resolve()
        self.reference = reference or FileReference(
            self.folder_path / ".zuu-hashes.json"
        )
        self.hashers: dict[str, SnapshotHasher] = {
            "content": _content_hasher,
            "content-and-mtime": _modified_hasher,
        }
        if hashers:
            self.hashers.update(hashers)

    def register(
        self,
        identifier: str,
        paths: Iterable[Pathish],
        *,
        exclusions: Iterable[str] = (),
        hasher: str = "content",
        replace: bool = False,
    ) -> None:
        """Store an initial baseline or intentionally replace its full definition."""
        if not identifier:
            raise ValueError("identifier must not be empty")
        self._get_hasher(hasher)

        stored_paths = self._normalise_paths(paths)
        if not stored_paths:
            raise ValueError("at least one governed path is required")
        stored_exclusions = tuple(exclusions)
        definition: dict[str, Any] = {
            "paths": list(stored_paths),
            "exclusions": list(stored_exclusions),
            "hasher": hasher,
        }

        registry = read_registry(self.reference)
        current = registry["entries"].get(identifier)
        if current is not None and not replace:
            current_definition = {
                key: current[key] for key in ("paths", "exclusions", "hasher")
            }
            if current_definition != definition:
                raise IdentifierConflictError(
                    f"identifier {identifier!r} already governs a different definition"
                )
            return

        resolved_paths = self._resolve_paths(stored_paths)
        definition["digest"] = self._calculate(
            hasher,
            resolved_paths,
            stored_exclusions,
        )
        registry["entries"][identifier] = definition
        write_registry(self.reference, registry)

    def match(
        self,
        identifier: str,
        on_match: Callable[[], MatchResult],
        on_mismatch: Callable[[], MismatchResult],
    ) -> MatchResult | MismatchResult:
        """Dispatch by digest and advance state only after mismatch work succeeds."""
        registry = read_registry(self.reference)
        try:
            entry = registry["entries"][identifier]
        except KeyError:
            raise KeyError(f"identifier {identifier!r} is not registered") from None

        paths = self._resolve_paths(entry["paths"])
        exclusions = tuple(entry["exclusions"])
        current_digest = self._calculate(entry["hasher"], paths, exclusions)
        if current_digest == entry["digest"]:
            return on_match()

        result = on_mismatch()
        entry["digest"] = self._calculate(entry["hasher"], paths, exclusions)
        write_registry(self.reference, registry)
        return result

    def _calculate(
        self,
        hasher_name: str,
        paths: Sequence[str],
        exclusions: Sequence[str],
    ) -> str:
        effective_exclusions = list(exclusions)
        if isinstance(self.reference, FileReference):
            effective_exclusions.append(self.reference.path.resolve().as_posix())
        snapshot = FileSystemSnapshot.capture(
            paths,
            exclusions=effective_exclusions,
        )
        return self._get_hasher(hasher_name)(snapshot)

    def _get_hasher(self, name: str) -> SnapshotHasher:
        try:
            return self.hashers[name]
        except KeyError:
            choices = ", ".join(sorted(self.hashers))
            raise ValueError(f"unknown hasher {name!r}; expected one of: {choices}") from None

    def _normalise_paths(self, paths: Iterable[Pathish]) -> tuple[str, ...]:
        normalised: set[str] = set()
        for value in paths:
            path = Path(value)
            resolved = (
                path.resolve()
                if path.is_absolute()
                else (self.folder_path / path).resolve()
            )
            try:
                stored = resolved.relative_to(self.folder_path).as_posix()
            except ValueError:
                stored = str(resolved)
            normalised.add(stored)
        return tuple(sorted(normalised))

    def _resolve_paths(self, paths: Sequence[str]) -> tuple[str, ...]:
        resolved: list[str] = []
        for value in paths:
            path = Path(value)
            if not path.is_absolute():
                path = self.folder_path / path
            resolved.append(str(path.resolve()))
        return tuple(resolved)


__all__ = [
    "FileReference",
    "HashReference",
    "IdentifierConflictError",
    "RegistryFormatError",
    "SnapshotHasher",
    "UserLevelHasher",
]
