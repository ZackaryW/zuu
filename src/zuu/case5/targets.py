"""Strict target traversal and evidence comparison for confined paths."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterable
from pathlib import Path

from . import (
    ConfinedPath,
    ConfinedPathError,
    ConfinedTargetPlan,
    StaleTargetError,
    TargetEvidence,
    TargetState,
)


def inspect_path(
    path: ConfinedPath,
    root: str | os.PathLike[str],
    *,
    allowed: Iterable[TargetState] | None,
) -> ConfinedTargetPlan:
    """Capture a strict, non-mutating target plan beneath ``root``."""
    allowed_states = _allowed_states(allowed)
    plan = _capture(path, root, allowed_states)
    if plan.state not in allowed_states:
        expected = ", ".join(sorted(state.value for state in allowed_states))
        raise ConfinedPathError(
            f"target state is {plan.state.value}; expected one of: {expected}"
        )
    return plan


def revalidate_plan(plan: ConfinedTargetPlan) -> None:
    """Raise when a plan's root, component, state, or absence evidence changed."""
    try:
        current = _capture(plan.path, plan.declared_root, plan.allowed)
    except ConfinedPathError as error:
        raise StaleTargetError(f"target evidence is stale: {error}") from error

    comparable = (
        "root",
        "target",
        "state",
        "evidence",
        "missing",
    )
    if any(getattr(current, name) != getattr(plan, name) for name in comparable):
        raise StaleTargetError(f"target evidence is stale: {plan.path.value}")


def _allowed_states(
    allowed: Iterable[TargetState] | None,
) -> frozenset[TargetState]:
    if allowed is None:
        return frozenset(TargetState)
    try:
        states = frozenset(allowed)
    except TypeError as error:
        raise ConfinedPathError("allowed target states must be iterable") from error
    if not states:
        raise ConfinedPathError("at least one allowed target state is required")
    if any(not isinstance(state, TargetState) for state in states):
        raise ConfinedPathError("allowed target states must be TargetState values")
    return states


def _capture(
    path: ConfinedPath,
    root: str | os.PathLike[str],
    allowed: frozenset[TargetState],
) -> ConfinedTargetPlan:
    try:
        declared_root = Path(root).absolute()
        physical_root = declared_root.resolve(strict=True)
    except (TypeError, OSError) as error:
        raise ConfinedPathError(f"trusted root is unavailable: {root!r}") from error
    if not physical_root.is_dir():
        raise ConfinedPathError(f"trusted root is not a directory: {root!r}")

    try:
        root_details = os.lstat(physical_root)
    except OSError as error:
        raise ConfinedPathError(f"trusted root is unavailable: {root!r}") from error

    evidence = [_entry_evidence(".", root_details, TargetState.DIRECTORY)]
    target = physical_root.joinpath(*path.parts)
    current = physical_root
    traversed: list[str] = []

    for index, segment in enumerate(path.parts):
        current = current / segment
        traversed.append(segment)
        relative = "/".join(traversed)
        try:
            details = os.lstat(current)
        except FileNotFoundError:
            return ConfinedTargetPlan(
                path=path,
                declared_root=declared_root,
                root=physical_root,
                target=target,
                state=TargetState.ABSENT,
                allowed=allowed,
                evidence=tuple(evidence),
                missing=path.parts[index:],
            )
        except OSError as error:
            raise ConfinedPathError(f"target is unavailable: {path.value}") from error

        final = index == len(path.parts) - 1
        state = _entry_state(current, details, relative)
        evidence.append(_entry_evidence(relative, details, state))
        if not final and state is not TargetState.DIRECTORY:
            raise ConfinedPathError(f"target ancestor is not a directory: {relative}")
        if final:
            return ConfinedTargetPlan(
                path=path,
                declared_root=declared_root,
                root=physical_root,
                target=target,
                state=state,
                allowed=allowed,
                evidence=tuple(evidence),
                missing=(),
            )

    raise AssertionError("a validated confined path always has at least one segment")


def _entry_state(
    path: Path,
    details: os.stat_result,
    relative: str,
) -> TargetState:
    attributes = getattr(details, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    try:
        junction = path.is_junction()
    except OSError as error:
        raise ConfinedPathError(f"target entry is unavailable: {relative}") from error
    if stat.S_ISLNK(details.st_mode) or junction or bool(attributes & reparse_flag):
        raise ConfinedPathError(f"target entry is redirected: {relative}")
    if stat.S_ISREG(details.st_mode):
        return TargetState.FILE
    if stat.S_ISDIR(details.st_mode):
        return TargetState.DIRECTORY
    raise ConfinedPathError(f"target entry has unsupported kind: {relative}")


def _entry_evidence(
    relative: str,
    details: os.stat_result,
    state: TargetState,
) -> TargetEvidence:
    if state is TargetState.FILE:
        size: int | None = details.st_size
        modified_ns: int | None = details.st_mtime_ns
        changed_ns: int | None = details.st_ctime_ns
    else:
        size = modified_ns = changed_ns = None
    return TargetEvidence(
        relative_path=relative,
        state=state,
        device=details.st_dev,
        inode=details.st_ino,
        mode=details.st_mode,
        size=size,
        modified_ns=modified_ns,
        changed_ns=changed_ns,
        file_attributes=getattr(details, "st_file_attributes", None),
    )
