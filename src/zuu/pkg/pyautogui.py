from time import sleep
import typing
import pygetwindow as gw
import pyautogui

def smart_type(
    text: str,
    delay: int = 0,
    repeats: int = 1,
    type_interval: int = 0.05,
    repeat_interval: int = 0.25,
    *targets: typing.Tuple[typing.Union[str, gw.Window]],
    stop_at_first_match: bool = False,
):
    """
    Types the given text into the specified target windows using pyautogui.

    Parameters:
    text (str): The text to type.
    delay (int): Delay before starting to type.
    repeats (int): Number of times to repeat typing the text.
    interval (float): Interval between each character typed.
    targets (tuple): A tuple of target window titles or gw.Window objects.
    stop_at_first_match (bool): If True, stop after the first successful match.
    """
    for target in targets:
        if isinstance(target, str):
            window = gw.getWindowsWithTitle(target)
            if window:
                window = window[0]
            else:
                continue
        elif isinstance(target, gw.Window):
            window = target
        else:
            continue

        window.activate()
        pyautogui.sleep(delay)
        for _ in range(repeats):
            pyautogui.typewrite(text, interval=type_interval)
        if stop_at_first_match:
            break

        sleep(repeat_interval)
