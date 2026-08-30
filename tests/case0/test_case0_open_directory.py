from pathlib import Path

import pytest

from zuu.case0.open import launch_process, open_directory


@pytest.mark.parametrize(
    ("platform", "executable"),
    [
        ("darwin", "open"),
        ("win32", "explorer"),
        ("linux", "xdg-open"),
        ("freebsd", "xdg-open"),
    ],
)
def test_open_directory_selects_the_platform_launcher(
    tmp_path: Path,
    platform: str,
    executable: str,
) -> None:
    calls: list[tuple[str, ...]] = []

    open_directory(tmp_path, platform=platform, launch=lambda argv: calls.append(tuple(argv)))

    assert calls == [(executable, str(tmp_path))]


def test_open_directory_propagates_launcher_failures(tmp_path: Path) -> None:
    def fail(argv: object) -> None:
        raise OSError("launcher unavailable")

    with pytest.raises(OSError, match="launcher unavailable"):
        open_directory(tmp_path, launch=fail)


def test_launch_process_uses_checked_argument_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[str, ...], bool]] = []

    def run(argv: tuple[str, ...], *, check: bool) -> None:
        calls.append((argv, check))

    monkeypatch.setattr("zuu.case0.open.subprocess.run", run)

    launch_process(["viewer", "folder"])

    assert calls == [(('viewer', 'folder'), True)]
