"""Safe selection of one directory subtree from a GitHub ZIP archive."""

from __future__ import annotations

import os
import re
import shutil
import stat
from pathlib import Path
from zipfile import BadZipFile, ZipFile, ZipInfo

from zuu.case5 import RepositoryPath

from . import GitHubSubpathError, _FILTER_MARKER


def materialize_subpath(
    archive_path: Path,
    source: RepositoryPath,
    destination: Path,
    *,
    include: tuple[re.Pattern[str], ...] = (),
    exclude: tuple[re.Pattern[str], ...] = (),
) -> None:
    """Materialize one safe directory subtree without extracting other entries."""
    try:
        with ZipFile(archive_path) as archive:
            entries = tuple((_parts(info), info) for info in archive.infolist())
            roots = {parts[0] for parts, _ in entries}
            if len(roots) != 1:
                raise GitHubSubpathError(
                    "GitHub archive must contain one repository root"
                )
            prefix = (next(iter(roots)), *source.parts)
            selected = _selected_entries(entries, prefix)
            _validate_entries(selected)
            if include or exclude:
                selected = tuple(
                    (relative, info)
                    for relative, info in selected
                    if not info.is_dir()
                    and _matches("/".join(relative), include, exclude)
                )
            destination.mkdir()
            _write_entries(archive, selected, destination)
    except GitHubSubpathError:
        raise
    except (BadZipFile, OSError) as error:
        raise GitHubSubpathError("GitHub archive could not be materialized") from error


def _selected_entries(
    entries: tuple[tuple[tuple[str, ...], ZipInfo], ...],
    prefix: tuple[str, ...],
) -> tuple[tuple[tuple[str, ...], ZipInfo], ...]:
    selected: list[tuple[tuple[str, ...], ZipInfo]] = []
    source_found = False
    for parts, info in entries:
        if parts[: len(prefix)] != prefix:
            continue
        source_found = True
        relative = parts[len(prefix) :]
        if not relative:
            if not info.is_dir():
                raise GitHubSubpathError("GitHub source subpath is not a directory")
            continue
        selected.append((relative, info))
    if not source_found or not selected:
        raise GitHubSubpathError("GitHub source directory was not found in the archive")
    return tuple(selected)


def _matches(
    path: str,
    include: tuple[re.Pattern[str], ...],
    exclude: tuple[re.Pattern[str], ...],
) -> bool:
    return (
        not include or any(pattern.search(path) for pattern in include)
    ) and not any(pattern.search(path) for pattern in exclude)


def _validate_entries(
    entries: tuple[tuple[tuple[str, ...], ZipInfo], ...],
) -> None:
    seen: dict[tuple[str, ...], bool] = {}
    for relative, info in entries:
        canonical = tuple(os.path.normcase(part) for part in relative)
        if canonical in seen:
            raise GitHubSubpathError(
                f"GitHub source contains a colliding path: {'/'.join(relative)}"
            )
        seen[canonical] = info.is_dir()
        if canonical[0] in {".commit", _FILTER_MARKER}:
            raise GitHubSubpathError(
                f"GitHub source uses the reserved top-level {relative[0]} path"
            )
        _validate_kind(info, relative)
    for relative in seen:
        for length in range(1, len(relative)):
            if seen.get(relative[:length]) is False:
                raise GitHubSubpathError(
                    f"GitHub source contains a file/directory conflict: {'/'.join(relative)}"
                )


def _write_entries(
    archive: ZipFile,
    entries: tuple[tuple[tuple[str, ...], ZipInfo], ...],
    destination: Path,
) -> None:
    for relative, info in entries:
        target = destination.joinpath(*relative)
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source_stream:
            with target.open("xb") as target_stream:
                shutil.copyfileobj(source_stream, target_stream)
        executable = (info.external_attr >> 16) & 0o111
        if executable:
            target.chmod(target.stat().st_mode | executable)


def _validate_kind(info: ZipInfo, relative: tuple[str, ...]) -> None:
    mode = (info.external_attr >> 16) & 0xFFFF
    kind = stat.S_IFMT(mode)
    if info.is_dir():
        if kind not in (0, stat.S_IFDIR):
            raise GitHubSubpathError(
                f"GitHub source contains an unsafe entry: {'/'.join(relative)}"
            )
        return
    if kind not in (0, stat.S_IFREG):
        raise GitHubSubpathError(
            f"GitHub source contains an unsafe entry: {'/'.join(relative)}"
        )


def _parts(info: ZipInfo) -> tuple[str, ...]:
    name = info.filename
    trimmed = name[:-1] if name.endswith("/") else name
    parts = tuple(trimmed.split("/"))
    if (
        not trimmed
        or name.startswith("/")
        or "\\" in name
        or "\0" in name
        or any(not part or part in {".", ".."} for part in parts)
    ):
        raise GitHubSubpathError(f"GitHub archive contains an unsafe path: {name!r}")
    return parts
