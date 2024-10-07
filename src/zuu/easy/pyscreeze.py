from pyscreeze import (  # noqa: E402
    center as center,
    locateAll as locateAll,
    locateAllOnScreen as locateAllOnScreen,
    locateCenterOnScreen as locateCenterOnScreen,
    locateOnScreen as locateOnScreen,
    locateOnWindow as locateOnWindow,
    pixel as pixel,
    pixelMatchesColor as pixelMatchesColor,
    screenshot as screenshot,
)


def screenshot_win32_full(imageFilename=None, region=None, allScreens=True):
    from pyscreeze import _screenshot_win32

    return _screenshot_win32(imageFilename, region, allScreens)
