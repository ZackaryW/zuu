from pathlib import Path

import psutil

from zuu.v202602_1.detect_editor import _detect_editor
from zuu.v202602_1.detect_editor import _matches_open_path
from zuu.v202602_1.detect_editor import get_editors
from zuu.v202602_1.enum_vscode_editors import VSCODE_EDITORS


class FakeProcess:
    def __init__(self, *, name: str = "", exe: str = "", cmdline: list[str] | None = None):
        self.info = {
            "name": name,
            "exe": exe,
            "cmdline": cmdline or [],
        }


class AccessDeniedProcess:
    @property
    def info(self) -> dict[str, str]:
        raise psutil.AccessDenied()


def test_matches_open_path_for_exact_path(tmp_path: Path) -> None:
    open_path = tmp_path / "workspace"
    open_path.mkdir()

    assert _matches_open_path(open_path, ["code", str(open_path)]) is True


def test_matches_open_path_for_nested_path(tmp_path: Path) -> None:
    open_path = tmp_path / "workspace"
    nested_path = open_path / "src"
    nested_path.mkdir(parents=True)

    assert _matches_open_path(open_path, ["code", str(nested_path)]) is True


def test_detect_editor_matches_process_name() -> None:
    process = FakeProcess(name="cursor.exe", cmdline=["cursor.exe"])

    assert _detect_editor(process) is VSCODE_EDITORS.CURSOR


def test_detect_editor_matches_command_line_alias() -> None:
    process = FakeProcess(
        name="node.exe",
        exe=r"C:\Program Files\Claude\launcher.exe",
        cmdline=["node.exe", "claude code", r"D:\zuu"],
    )

    assert _detect_editor(process) is VSCODE_EDITORS.CLAUDE_CODE


def test_get_editors_filters_by_open_path_and_deduplicates(monkeypatch, tmp_path: Path) -> None:
    cwd = tmp_path / "repo"
    cwd.mkdir()

    processes = [
        FakeProcess(name="windsurf.exe", cmdline=["windsurf.exe", str(cwd)]),
        FakeProcess(name="code.exe", cmdline=["code.exe", str(cwd)]),
        FakeProcess(name="code.exe", cmdline=["code.exe", str(cwd)]),
        FakeProcess(name="cursor.exe", cmdline=["cursor.exe", str(tmp_path / "other")]),
        AccessDeniedProcess(),
    ]

    monkeypatch.setattr(psutil, "process_iter", lambda attrs: iter(processes))

    assert get_editors(cwd) == [VSCODE_EDITORS.VSCODE, VSCODE_EDITORS.WINDSURF]


def test_get_editors_ignores_unknown_processes(monkeypatch, tmp_path: Path) -> None:
    cwd = tmp_path / "repo"
    cwd.mkdir()

    processes = [
        FakeProcess(name="python.exe", exe=r"C:\Python\python.exe", cmdline=["python.exe", str(cwd)]),
    ]

    monkeypatch.setattr(psutil, "process_iter", lambda attrs: iter(processes))

    assert get_editors(cwd) == []