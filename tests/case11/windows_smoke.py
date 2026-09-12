"""Opt-in native screen check: uv run python tests/case11/windows_smoke.py.

Creates an isolated hidden Windows console; never resizes the caller's console.
"""

import json
import subprocess
import sys


def exercise():
    import ctypes as c
    import msvcrt
    import os
    from ctypes import wintypes as w

    from zuu.case11 import TerminalUnavailableError
    from zuu.case11.state import Action, CheckboxState
    from zuu.case11.terminal import AnsiRenderer
    from zuu.case11.windows import WindowsConsoleApi, WindowsTerminalSession

    class Coord(c.Structure):
        _fields_ = [("x", w.SHORT), ("y", w.SHORT)]

    class Rect(c.Structure):
        _fields_ = [(name, w.SHORT) for name in ("left", "top", "right", "bottom")]

    class Info(c.Structure):
        _fields_ = [("size", Coord), ("cursor", Coord), ("attributes", w.WORD),
                    ("window", Rect), ("maximum", Coord)]

    class CursorInfo(c.Structure):
        _fields_ = [("size", w.DWORD), ("visible", w.BOOL)]

    api = c.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "GetConsoleScreenBufferInfo": [w.HANDLE, c.POINTER(Info)],
        "SetConsoleScreenBufferSize": [w.HANDLE, Coord],
        "SetConsoleWindowInfo": [w.HANDLE, w.BOOL, c.POINTER(Rect)],
        "SetConsoleCursorPosition": [w.HANDLE, Coord],
        "ReadConsoleOutputCharacterW": [w.HANDLE, w.LPWSTR, w.DWORD, Coord, c.POINTER(w.DWORD)],
        "GetConsoleCursorInfo": [w.HANDLE, c.POINTER(CursorInfo)],
        "SetConsoleOutputCP": [w.UINT],
    }
    for name, args in signatures.items():
        function = getattr(api, name)
        function.argtypes, function.restype = args, w.BOOL

    def call(name, *args):
        if not getattr(api, name)(*args):
            raise c.WinError(c.get_last_error())

    with open("CONIN$", "r", encoding="utf-8") as source, open(
        "CONOUT$", "w", encoding="utf-8", buffering=1
    ) as target:
        handle = msvcrt.get_osfhandle(target.fileno())
        call("SetConsoleOutputCP", 65001)

        def info():
            value = Info()
            call("GetConsoleScreenBufferInfo", handle, c.byref(value))
            return value

        def resize(width, height):
            call("SetConsoleWindowInfo", handle, True, c.byref(Rect(0, 0, 1, 1)))
            # Keep scrollback distinct from the visible viewport.
            call("SetConsoleScreenBufferSize", handle, Coord(width, 300))
            call("SetConsoleWindowInfo", handle, True, c.byref(Rect(0, 0, width - 1, height - 1)))
            assert tuple(os.get_terminal_size(target.fileno())) == (width, height)

        def rows():
            value = info()
            result = []
            for row in range(value.size.y):
                buffer = c.create_unicode_buffer(value.size.x + 1)
                count = w.DWORD()
                call("ReadConsoleOutputCharacterW", handle, buffer, value.size.x,
                     Coord(0, row), c.byref(count))
                result.append(buffer.value.rstrip())
            return result

        resize(38, 10)
        console = WindowsConsoleApi()
        before = (console.get_mode(source), console.get_mode(target))
        with WindowsTerminalSession(source, target):
            first = AnsiRenderer(target, "Select agents (--agent)", ("codex", "claude", "kimi", "pi"))
            state = CheckboxState(4, selected={0})
            first.render(state)
            state.apply(Action.SUBMIT)
            first.finish(state)
            assert info().cursor.y == 1, rows()
            assert rows()[0] == "? Select agents (--agent) [codex]"
            second = AnsiRenderer(target, "Select skills", tuple(f"skill-{i:02}" for i in range(17)))
            state = CheckboxState(17)
            second.render(state)
            assert rows()[0] == "? Select agents (--agent) [codex]", rows()
            for index in range(17):
                assert f"» ○ skill-{index:02}" in rows(), rows()
                state.apply(Action.DOWN)
                second.render(state)
            state.apply(Action.TOGGLE_ALL)
            second.render(state)
            state.apply(Action.SUBMIT)
            second.finish(state)
            assert info().cursor.y == 2, rows()
            assert not any(rows()[2:]), rows()

            third = AnsiRenderer(target, "Cancel", ("One", "Two"))
            state = CheckboxState(2, required=True)
            state.apply(Action.SUBMIT)
            third.render(state)
            state.apply(Action.CANCEL)
            third.finish(state)
            assert rows()[info().cursor.y - 1] == "? Cancel cancelled", rows()
            assert not any(rows()[info().cursor.y:]), rows()

            grow = AnsiRenderer(target, "Grow", tuple(f"item-{i:02}" for i in range(17)))
            state = CheckboxState(17, pointed=16, selected={0, 16})
            grow.render(state)
            resize(100, 30)
            grow.render(state)
            assert "  ◉ item-00" in rows() and "» ◉ item-16" in rows(), rows()
            resize(38, 10)
            snapshot = rows()
            try:
                grow.render(state)
            except TerminalUnavailableError as error:
                assert "resized" in str(error)
            else:
                raise AssertionError("shrink must not erase an uncertain origin")
            assert rows() == snapshot

        assert (console.get_mode(source), console.get_mode(target)) == before
        cursor = CursorInfo()
        call("GetConsoleCursorInfo", handle, c.byref(cursor))
        assert cursor.visible
        print(json.dumps({"result": "passed", "dimensions": [[38, 10], [100, 30]],
                          "checks": ["consecutive prompts", "17 choices", "submit", "cancel",
                                     "expand", "safe shrink", "modes and cursor restored"]}))


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("This opt-in smoke check requires Windows.")
    if "--child" in sys.argv:
        exercise()
    else:
        startup = subprocess.STARTUPINFO()
        startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        result = subprocess.run(
            [sys.executable, __file__, "--child"],
            creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=startup,
            capture_output=True, text=True, timeout=30,
        )
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        raise SystemExit(result.returncode)
