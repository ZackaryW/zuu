import time

__all__ = ["remaining_time", "sleep_until"]


def remaining_time(string: str | int) -> None | int:
    """
    Parses a time string and returns the remaining time in seconds until the specified time.

    The function supports the following time string formats:
    - 10:25pm / 3:25am
    - 21:24
    - 555 (interpreted as seconds)

    If the specified time has already passed, the function returns `None`. Otherwise, it returns the remaining time in seconds.
    """

    if isinstance(string, int):
        return string

    if string.isdigit():
        return int(string)

    current_time = time.localtime()
    current_seconds = (
        current_time.tm_hour * 3600 + current_time.tm_min * 60 + current_time.tm_sec
    )

    if "am" in string or "pm" in string:
        time_struct = time.strptime(string, "%I:%M%p")
    elif ":" in string:
        time_struct = time.strptime(string, "%H:%M")
    else:
        total_seconds = int(string)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        time_struct = time.struct_time((0, 0, 0, hours, minutes, seconds, 0, 0, 0))

    target_seconds = (
        time_struct.tm_hour * 3600 + time_struct.tm_min * 60 + time_struct.tm_sec
    )
    remaining_seconds = target_seconds - current_seconds

    if remaining_seconds < 0:
        return None

    return remaining_seconds


def sleep_until(string: str | int):
    """
    sleeps until time
    supports
    10:25pm / 3:25am
    21:24
    555
    """
    remaining = remaining_time(string)
    if remaining is None:
        raise ValueError("time has already passed")
    print(f"sleeping for {remaining} seconds till {string}")
    time.sleep(remaining)


def unix_timestamp():
    return int(time.time() * 1000)
