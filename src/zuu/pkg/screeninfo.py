import screeninfo
import pygetwindow as gw
import typing

def get_screen_dimensions(monitor_index=0):
    """
    Returns the dimensions and position of a specific monitor.

    Args:
        monitor_index (int, optional): The index of the monitor to retrieve information from. Defaults to 0.

    Returns:
        tuple: A tuple containing the width, height, x-coordinate, and y-coordinate of the monitor.

    Raises:
        ValueError: If the monitor_index is invalid.

    """
    monitors = screeninfo.get_monitors()
    if monitor_index < 0 or monitor_index >= len(monitors):
        raise ValueError("Invalid monitor index")
    monitor = monitors[monitor_index]
    # Return both dimensions and the position of the monitor
    return (monitor.width, monitor.height, monitor.x, monitor.y)


def get_wnd_monitor(wnd: gw.BaseWindow):
    """
    Determine which monitor a window is currently on based on its position.

    Args:
        wnd (gw.Window): The window to determine the monitor for.

    Returns:
        screeninfo.Monitor or None: The monitor the window is currently on, or None if the window is not on any monitor.
    """

    midpoint = (wnd.left + wnd.width / 2, wnd.top + wnd.height / 2)
    for monitor in screeninfo.get_monitors():
        if (
            monitor.x <= midpoint[0] < monitor.x + monitor.width
            and monitor.y <= midpoint[1] < monitor.y + monitor.height
        ):
            return monitor
    return None


def get_primary_monitor():
    """
    Returns the primary monitor object from the list of all monitors.

    This function iterates over the list of monitors obtained from the `screeninfo.get_monitors()` function and checks if each monitor is the primary monitor. If a primary monitor is found, it is returned. If no primary monitor is found, a `ValueError` is raised with the message "No primary monitor found".

    Returns:
        screeninfo.Monitor: The primary monitor object.

    Raises:
        ValueError: If no primary monitor is found.
    """
    for monitor in screeninfo.get_monitors():
        if monitor.is_primary:
            return monitor

    raise ValueError("No primary monitor found")


def wnd_to_monitor(
    wnd: gw.BaseWindow,
    monitor: typing.Union[screeninfo.Monitor, int] = None,
    coord: typing.Tuple[int, int] = None,
):
    """
    Moves a window to a specific monitor and position.

    Args:
        wnd (gw.Window): The window to move.
        monitor (typing.Union[screeninfo.Monitor, int], optional): The monitor to move the window to. If not provided, the primary monitor is used.
        coord (typing.Tuple[int, int], optional): The coordinates to move the window to. If not provided, the window is centered on the monitor.

    Returns:
        None
    """
    if monitor is None:
        monitor = get_primary_monitor()

    if isinstance(monitor, int):
        monitor = screeninfo.get_monitors()[monitor]

    if not coord:
        # Calculate the middle point of the monitor
        middle_x = monitor.x + monitor.width // 2 - wnd.width // 2
        middle_y = monitor.y + monitor.height // 2 - wnd.height // 2
        coord = (middle_x, middle_y)

    wnd.move(coord[0], coord[1])


def wnd_to_primary(wnd: gw.BaseWindow):
    """
    Moves a window to the primary monitor.

    Args:
        wnd (gw.Window): The window to move.

    Returns:
        None
    """
    monitor = get_primary_monitor()
    wnd_to_monitor(wnd, monitor)


def get_monitor_center(monitor_index):
    """
    Returns the center of the monitor specified by the index.

    Args:
        monitor_index (int): The index of the monitor to retrieve center from.

    Returns:
        tuple: A tuple containing the x-coordinate and y-coordinate of the monitor's center.
    """
    monitors = screeninfo.get_monitors()
    if monitor_index < 0 or monitor_index >= len(monitors):
        raise ValueError("Invalid monitor index")
    monitor = monitors[monitor_index]
    return (monitor.x + monitor.width / 2, monitor.y + monitor.height / 2)


def get_monitor_bounds(monitor_index):
    """
    Returns the bounds of the monitor specified by the index.

    Args:
        monitor_index (int): The index of the monitor to retrieve bounds from.

    Returns:
        tuple: A tuple containing the x-coordinate, y-coordinate, width, and height of the monitor.
    """
    monitors = screeninfo.get_monitors()
    if monitor_index < 0 or monitor_index >= len(monitors):
        raise ValueError("Invalid monitor index")
    monitor = monitors[monitor_index]
    return (monitor.x, monitor.y, monitor.x + monitor.width, monitor.y + monitor.height)
