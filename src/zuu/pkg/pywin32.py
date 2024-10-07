import win32process
import platform
import typing
import pygetwindow as gw
import psutil

def get_pid_from_hwnd(hwnd):
    """
    Get the process ID given the handle of a window.

    Args:
        hwnd (int or gw.Win32Window): The handle of the window. If it is an instance of gw.Win32Window, its handle will be extracted.

    Returns:
        int or None: The process ID of the window, or None if an error occurred.
    """
    if not isinstance(hwnd, int):
        assert isinstance(hwnd, gw.Win32Window)
        hwnd = hwnd._hWnd

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception as e:
        print(f"Error: {e}")
        return None


def get_process_wnds(*processes : typing.Tuple[psutil.Process]) -> typing.List[gw.BaseWindow]:
    """
    Get a list of all windows associated with the given processes.
    
    Args:
        processes (Tuple[psutil.Process]): A tuple of psutil.Process objects representing the processes to get windows for.
    
    Returns:
        List[gw.BaseWindow]: A list of all windows associated with the given processes.
    """
        

    procIds = [proc.pid for proc in processes]

    wnds = []
    for wnd in gw.getAllWindows():
        wnd: gw.Win32Window

        _, winpid = win32process.GetWindowThreadProcessId(wnd._hWnd)

        if winpid in procIds:
            wnds.append(wnd)
    return wnds
