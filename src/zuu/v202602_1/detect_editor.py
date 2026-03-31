from pathlib import Path
from typing import Iterable, Optional

import psutil

from .enum_vscode_editors import VSCODE_EDITORS


_EDITOR_ALIASES: dict[VSCODE_EDITORS, tuple[str, ...]] = {
    VSCODE_EDITORS.VSCODE: (
        "code",
        "code.exe",
        "code - insiders",
        "code-insiders",
        "visual studio code",
        "visual studio code.app",
        "vscode",
    ),
    VSCODE_EDITORS.CURSOR: (
        "cursor",
        "cursor.exe",
        "cursor.app",
    ),
    VSCODE_EDITORS.WINDSURF: (
        "windsurf",
        "windsurf.exe",
        "windsurf.app",
    ),
    VSCODE_EDITORS.ANTIGRAVITY: (
        "antigravity",
        "antigravity.exe",
        "antigravity.app",
    ),
    VSCODE_EDITORS.CLAUDE_CODE: (
        "claude",
        "claude.exe",
        "claude code",
        "claude code.exe",
        "claude code.app",
    ),
}


def _normalize_path(value: Path | str) -> str:
    return str(Path(value).expanduser().resolve(strict=False)).casefold()


def _iter_candidate_paths(cmdline: Iterable[str]) -> Iterable[Path]:
    for arg in cmdline:
        if not arg or arg.startswith("-"):
            continue

        try:
            yield Path(arg).expanduser().resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            continue


def _matches_open_path(open_path: Path, cmdline: Iterable[str]) -> bool:
    normalized_open_path = _normalize_path(open_path)

    for candidate in _iter_candidate_paths(cmdline):
        normalized_candidate = _normalize_path(candidate)

        if normalized_candidate == normalized_open_path:
            return True

        if normalized_open_path.startswith(normalized_candidate.rstrip("\\/") + "\\"):
            return True

        if normalized_open_path.startswith(normalized_candidate.rstrip("\\/") + "/"):
            return True

        if normalized_candidate.startswith(normalized_open_path.rstrip("\\/") + "\\"):
            return True

        if normalized_candidate.startswith(normalized_open_path.rstrip("\\/") + "/"):
            return True

    return False


def _detect_editor(process: psutil.Process) -> Optional[VSCODE_EDITORS]:
    name = (process.info.get("name") or "").casefold()  # ty:ignore[unresolved-attribute]
    exe = (process.info.get("exe") or "").casefold()  # ty:ignore[unresolved-attribute]
    cmdline = process.info.get("cmdline") or []  # ty:ignore[unresolved-attribute]
    haystack = " ".join(part.casefold() for part in cmdline)
    best_match: tuple[int, int, VSCODE_EDITORS] | None = None

    for editor, aliases in _EDITOR_ALIASES.items():
        for alias in aliases:
            match_score = 0

            if name == alias:
                match_score = 4
            elif exe.endswith(alias):
                match_score = 3
            elif alias in exe:
                match_score = 2
            elif alias in haystack:
                match_score = 1

            if match_score == 0:
                continue

            candidate = (match_score, len(alias), editor)
            if best_match is None or candidate > best_match:  # ty:ignore[unsupported-operator]
                best_match = candidate

    if best_match is None:
        return None

    return best_match[2]


def get_editors(cwd: Optional[Path] = None) -> list[VSCODE_EDITORS]:
    if cwd is None:
        cwd = Path.cwd()

    cwd = cwd.expanduser().resolve(strict=False)
    detected_editors: set[VSCODE_EDITORS] = set()

    for process in psutil.process_iter(["name", "exe", "cmdline"]):
        try:
            cmdline = process.info.get("cmdline") or []
            if not cmdline or not _matches_open_path(cwd, cmdline):
                continue

            editor = _detect_editor(process)
            if editor is not None:
                detected_editors.add(editor)
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            continue

    return [editor for editor in VSCODE_EDITORS if editor in detected_editors]
