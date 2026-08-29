"""Git-ignore planning, verification, and rollback-safe application."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path

from . import (
    GitIgnoreError,
    GitIgnorePlan,
    GitIgnorePolicy,
    IgnoreMode,
    Pathish,
    ProcessRunner,
)
from .process import run_process


def plan_gitignore(
    project_root: Pathish,
    paths: Iterable[Pathish],
    *,
    policy: GitIgnorePolicy = GitIgnorePolicy(),
    runner: ProcessRunner = run_process,
) -> GitIgnorePlan | None:
    """Build a root `.gitignore` proposal without mutating the worktree."""
    if policy.mode is IgnoreMode.NONE:
        return None

    project = Path(project_root).resolve()
    result = runner(("git", "rev-parse", "--show-toplevel"), project)
    if result.returncode != 0 or not result.stdout.strip():
        raise GitIgnoreError("ignore planning requires a containing Git worktree")
    worktree = Path(result.stdout.strip()).resolve()
    _require_within(worktree, project)

    probes = _normalise_paths(project, worktree, paths)
    if not probes:
        raise GitIgnoreError("ignore planning requires at least one selected path")

    ignore_file = worktree / ".gitignore"
    if ignore_file.is_symlink() or (ignore_file.exists() and not ignore_file.is_file()):
        raise GitIgnoreError("root .gitignore is not a writable regular file")
    try:
        original = ignore_file.read_bytes() if ignore_file.exists() else None
        existing = original or b""
        existing.decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise GitIgnoreError("root .gitignore cannot be read as UTF-8") from error

    uncovered = [
        path for path in probes if not _is_ignored(worktree, path, runner=runner)
    ]
    additions: list[str] = []
    if uncovered:
        if policy.mode is IgnoreMode.PATTERN:
            assert policy.pattern is not None
            additions.append(policy.pattern)
        else:
            additions.extend(_exact_rule(worktree, path) for path in uncovered)
    proposed = _append_rules(existing, additions) if additions else None
    return GitIgnorePlan(worktree, ignore_file, original, proposed, probes)


def verify_gitignore(
    plan: GitIgnorePlan,
    *,
    runner: ProcessRunner = run_process,
) -> None:
    """Require every selected plan path to be effectively ignored by Git."""
    if not all(_is_ignored(plan.worktree, probe, runner=runner) for probe in plan.probes):
        raise GitIgnoreError("Git-ignore plan is ineffective")


def apply_gitignore(
    plan: GitIgnorePlan,
    *,
    runner: ProcessRunner = run_process,
) -> bool:
    """Atomically apply and verify a fresh plan, restoring bytes on failure."""
    if plan.ignore_file.is_symlink():
        raise GitIgnoreError("root .gitignore changed to a symbolic link")
    try:
        current = plan.ignore_file.read_bytes() if plan.ignore_file.exists() else None
    except OSError as error:
        raise GitIgnoreError("root .gitignore cannot be read") from error
    if current != plan.original:
        raise GitIgnoreError("root .gitignore changed after the plan was created")

    if plan.proposed is None:
        verify_gitignore(plan, runner=runner)
        return False

    _atomic_write(plan.ignore_file, plan.proposed)
    try:
        verify_gitignore(plan, runner=runner)
    except BaseException:
        if plan.original is None:
            plan.ignore_file.unlink(missing_ok=True)
        else:
            _atomic_write(plan.ignore_file, plan.original)
        raise
    return True


def _normalise_paths(
    project: Path,
    worktree: Path,
    paths: Iterable[Pathish],
) -> tuple[Path, ...]:
    normalised: dict[str, Path] = {}
    for value in paths:
        candidate = Path(value)
        path = (
            candidate.resolve()
            if candidate.is_absolute()
            else (project / candidate).resolve()
        )
        _require_within(worktree, path)
        if path == worktree:
            raise GitIgnoreError("the Git worktree root cannot be ignored")
        normalised[path.as_posix()] = path
    return tuple(normalised[key] for key in sorted(normalised))


def _require_within(worktree: Path, path: Path) -> None:
    try:
        path.relative_to(worktree)
    except ValueError as error:
        raise GitIgnoreError("managed ignore path lies outside the Git worktree") from error


def _is_ignored(
    worktree: Path,
    path: Path,
    *,
    runner: ProcessRunner,
) -> bool:
    relative = path.relative_to(worktree).as_posix()
    result = runner(
        ("git", "check-ignore", "--no-index", "-q", "--", relative),
        worktree,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise GitIgnoreError("Git could not evaluate effective ignore rules")


def _exact_rule(worktree: Path, path: Path) -> str:
    return f"/{path.relative_to(worktree).as_posix().rstrip('/')}"


def _append_rules(existing: bytes, rules: Sequence[str]) -> bytes:
    separator = b"" if not existing or existing.endswith(b"\n") else b"\n"
    return existing + separator + "".join(f"{rule}\n" for rule in rules).encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
