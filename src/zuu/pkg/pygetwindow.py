from time import sleep
import typing
import pygetwindow as gw


def activate_wnd(wnd: gw.BaseWindow):
    """
    Activates the given window if it is not already active.

    Args:
        wnd (gw.Window): The window to activate.

    Returns:
        None

    Raises:
        None
    """
    try:
        if wnd.isActive:
            return
        wnd.activate()
    except gw.PyGetWindowException:
        pass


def grid_orientation(
    wnds: typing.List[gw.Win32Window],
    row: int,
    col: int,
    maxwidth: float | None = None,
    maxheight: float | None = None,
    minwidth: float | None = None,
    minheight: float | None = None,
    monitor: int = 0,
    sleepTime: float = 0.2,
):
    """
    Arrange the given windows in a grid layout with the specified number of rows and columns.

    Args:
        wnds (List[gw.Window]): The list of windows to arrange.
        row (int): The number of rows in the grid layout.
        col (int): The number of columns in the grid layout.
        maxwidth (float, optional): The maximum width of each window. Defaults to None.
        maxheight (float, optional): The maximum height of each window. Defaults to None.
        minwidth (float, optional): The minimum width of each window. Defaults to None.
        minheight (float, optional): The minimum height of each window. Defaults to None.
        monitor (int, optional): The index of the monitor to use for the grid layout. Defaults to 0.
        sleepTime (float, optional): The time to sleep between each window arrangement. Defaults to 0.2.

    Returns:
        None

    Raises:
        None
    """
    from zuu.extpkg.screeninfo import get_screen_dimensions

    screen_width, screen_height, monitor_x, monitor_y = get_screen_dimensions(
        monitor_index=monitor
    )
    num_windows = len(wnds)
    if num_windows == 0 or row == 0 or col == 0:
        return  # Early return if invalid input

    window_width = screen_width // col
    window_height = screen_height // row

    # Apply max and min dimensions
    if maxwidth is not None:
        window_width = min(window_width, maxwidth)
    if maxheight is not None:
        window_height = min(window_height, maxheight)
    if minwidth is not None:
        window_width = max(window_width, minwidth)
    if minheight is not None:
        window_height = max(window_height, minheight)

    for index, window_instance in enumerate(wnds):
        window_instance: gw.Win32Window
        new_x = (index % col) * window_width + monitor_x
        new_y = (index // col) * window_height + monitor_y

        activate_wnd(window_instance)
        window_instance.resizeTo(window_width, window_height)
        window_instance.moveTo(new_x, new_y)

        if index == row * col - 1:
            break

        sleep(sleepTime)


def get_window_pos(wnd: gw.BaseWindow) -> typing.Tuple[float, float, float, float]:
    """
    Get the position and size of the window.

    Args:
        wnd (gw.Window): The window from which to retrieve the position and size.

    Returns:
        typing.Tuple[float, float, float, float]: A tuple containing the left, top, width, and height of the window.
    """
    return (wnd.left, wnd.top, wnd.width, wnd.height)


def filter_visible_windows(
    wnds: typing.Iterable[gw.BaseWindow],
) -> typing.List[gw.BaseWindow]:
    rwnds = []
    for wnd in wnds:
        if wnd.height > 0 and wnd.width > 0:
            rwnds.append(wnd)
    return rwnds


def filter_titled_windows(
    wnds: typing.Iterable[gw.BaseWindow],
) -> typing.List[gw.BaseWindow]:
    """
    Filter non-titled windows.

    Args:
        wnds (typing.Iterable[gw.Window]): An iterable of windows to filter.

    Returns:
        typing.List[gw.Window]: A list of windows with titles.
    """
    rwnds = []
    for wnd in wnds:
        if wnd.title:
            rwnds.append(wnd)
    return rwnds
