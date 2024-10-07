from dataclasses import dataclass
from functools import cached_property
import re
import typing
import pygetwindow as gw
import psutil
from sched import scheduler
import threading
import time

@dataclass
class PID:
    pid : int = None
    name : str = None
    pattern : bool = False

    def process(self):
        matched = []
        for proc in psutil.process_iter():
            if self.pattern and self.pid and re.search(self.pid, proc.name()):
                matched.append(proc)
            elif not self.pattern and self.pid and proc.pid == self.pid:
                matched.append(proc)
            elif self.pattern and self.name and re.search(self.name, proc.name()):
                matched.append(proc)
            elif not self.pattern and self.name and proc.name() == self.name:
                matched.append(proc)
        return matched


@dataclass
class Wnd:
    title : str = None
    pattern : bool = False

    def process(self):
        matched = []
        for window in gw.getWindowsWithTitle(self.title):
            if self.pattern and self.title and re.search(self.title, window.title):
                matched.append(window)
            elif not self.pattern and self.title and window.title == self.title:
                matched.append(window)
        return matched

@dataclass
class LifetimeGlob:
    lifetime : typing.Union[str, int]
    matching : typing.List[str, gw.Window, psutil.Process, PID, Wnd]
    reverse : bool = False
    method : typing.Literal["detached_thread", "thread", "sched"] = "detached_thread"

    @cached_property
    def stoppingSignal(self) -> threading.Event:
        return threading.Event()

    def __gather_windows__(self) -> typing.List[typing.Union[gw.Window, psutil.Process]]:
        """
        Gathers all windows that match the matching criteria.
        """
        matched_windows = []
        matched_procs = []

        for match in self.matching:
            if isinstance(match, gw.Window):
                matched_windows.append(match)
            elif isinstance(match, psutil.Process):
                matched_procs.append(match)
            elif isinstance(match, PID) :
                matched_procs.extend(match.process())
            elif isinstance(match, Wnd) :
                matched_windows.extend(match.process())
            else:
                raise ValueError(f"Unsupported type: {type(match)}")

        if self.reverse:
            rwnds = []
            rprocs = []
            for wnd in gw.getAllWindows():
                if wnd not in matched_windows:
                    rwnds.append(wnd)
            for proc in psutil.process_iter():
                if proc not in matched_procs:
                    rprocs.append(proc)
            matched_windows = rwnds
            matched_procs = rprocs

        return matched_windows, matched_procs

    def __worker__(self):
        """
        Worker method that runs a countdown based on the lifetime attribute.
        """
        countdown = int(self.lifetime)
        while countdown > 0:
            if self.stoppingSignal.is_set():
                return
                
            countdown -= 1
            time.sleep(1)

        wnds, procs = self.__gather_windows__()

        for wnd in wnds:
            try:
                wnd.close()
            except Exception:
                continue

        for proc in procs:
            try:
                proc.kill()
            except Exception:
                continue

    def __post_init__(self):
        """
        Post-initialization method that starts the worker based on the method attribute.
        """
        match self.method:
            case "detached_thread":
                thread = threading.Thread(target=self.__worker__)
                thread.daemon = True
                thread.start()
            case "thread":
                thread = threading.Thread(target=self.__worker__)
                thread.start()
            case "sched":
                sched = scheduler(time.time, time.sleep)
                sched.enter(0, 1, self.__worker__)
                sched.run()
