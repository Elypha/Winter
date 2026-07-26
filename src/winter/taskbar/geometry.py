from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import ctypes
from ctypes import wintypes

import win32api
import win32con
import win32gui


_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_GET_DPI_FOR_WINDOW = getattr(_USER32, "GetDpiForWindow", None)
if _GET_DPI_FOR_WINDOW is not None:
    _GET_DPI_FOR_WINDOW.argtypes = [wintypes.HWND]
    _GET_DPI_FOR_WINDOW.restype = wintypes.UINT


class Edge(Enum):
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"

    @property
    def horizontal(self) -> bool:
        return self in {Edge.TOP, Edge.BOTTOM}


@dataclass(frozen=True, slots=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @classmethod
    def from_tuple(cls, value: tuple[int, int, int, int]) -> "Rect":
        return cls(*value)

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)


@dataclass(frozen=True, slots=True)
class Taskbar:
    hwnd: int
    monitor_name: str
    primary: bool
    edge: Edge
    bounds: Rect
    screen: Rect
    task_buttons: Rect | None
    notification_area: Rect | None
    scale: float

    @property
    def usable_interval(self) -> tuple[int, int]:
        if self.edge.horizontal:
            start = (
                self.task_buttons.right
                if self.task_buttons is not None
                else self.bounds.left
            )
            if self.notification_area is not None:
                end = self.notification_area.left
            elif self.primary:
                end = self.bounds.right
            else:
                end = self.bounds.right - self.bounds.height * 5
        else:
            start = (
                self.task_buttons.bottom
                if self.task_buttons is not None
                else self.bounds.top
            )
            if self.notification_area is not None:
                end = self.notification_area.top
            elif self.primary:
                end = self.bounds.bottom
            else:
                end = self.bounds.bottom - self.bounds.width * 5
        return min(start, end), max(start, end)


def _descendants(hwnd: int) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}

    def collect(child: int, _context: object) -> None:
        try:
            found.setdefault(win32gui.GetClassName(child), []).append(child)
        except win32gui.error:
            pass

    win32gui.EnumChildWindows(hwnd, collect, None)
    return found


def _first_rect(
    children: dict[str, list[int]], classes: tuple[str, ...]
) -> Rect | None:
    for class_name in classes:
        for hwnd in children.get(class_name, ()):
            try:
                bounds = Rect.from_tuple(win32gui.GetWindowRect(hwnd))
            except win32gui.error:
                continue
            if bounds.width or bounds.height:
                return bounds
    return None


def _edge(taskbar: Rect, screen: Rect) -> Edge:
    if taskbar.width >= taskbar.height:
        return (
            Edge.TOP
            if abs(taskbar.top - screen.top) <= abs(screen.bottom - taskbar.bottom)
            else Edge.BOTTOM
        )
    return (
        Edge.LEFT
        if abs(taskbar.left - screen.left) <= abs(screen.right - taskbar.right)
        else Edge.RIGHT
    )


def _taskbar_windows() -> list[int]:
    windows: list[int] = []
    primary = win32gui.FindWindow("Shell_TrayWnd", None)
    if primary:
        windows.append(primary)
    after = 0
    while True:
        after = win32gui.FindWindowEx(0, after, "Shell_SecondaryTrayWnd", None)
        if not after:
            break
        windows.append(after)
    return windows


def discover() -> tuple[Taskbar, ...]:
    taskbars: list[Taskbar] = []
    for hwnd in _taskbar_windows():
        if not win32gui.IsWindow(hwnd):
            continue
        monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
        info = win32api.GetMonitorInfo(monitor)
        children = _descendants(hwnd)
        bounds = Rect.from_tuple(win32gui.GetWindowRect(hwnd))
        screen = Rect.from_tuple(info["Monitor"])
        dpi = int(_GET_DPI_FOR_WINDOW(hwnd)) if _GET_DPI_FOR_WINDOW else 96
        taskbars.append(
            Taskbar(
                hwnd=hwnd,
                monitor_name=str(info["Device"]),
                primary=bool(info["Flags"] & 1),
                edge=_edge(bounds, screen),
                bounds=bounds,
                screen=screen,
                task_buttons=_first_rect(
                    children, ("MSTaskListWClass", "MSTaskSwWClass", "ReBarWindow32")
                ),
                notification_area=_first_rect(children, ("TrayNotifyWnd",)),
                scale=max(1.0, dpi / 96.0),
            )
        )
    return tuple(taskbars)


def choose(taskbars: tuple[Taskbar, ...], monitor_name: str | None) -> Taskbar | None:
    if monitor_name:
        for taskbar in taskbars:
            if taskbar.monitor_name.casefold() == monitor_name.casefold():
                return taskbar
    return next((taskbar for taskbar in taskbars if taskbar.primary), None)


def is_taskbar_visible(taskbar: Taskbar) -> bool:
    if not win32gui.IsWindowVisible(taskbar.hwnd):
        return False
    current = Rect.from_tuple(win32gui.GetWindowRect(taskbar.hwnd))
    intersection_width = max(
        0,
        min(current.right, taskbar.screen.right)
        - max(current.left, taskbar.screen.left),
    )
    intersection_height = max(
        0,
        min(current.bottom, taskbar.screen.bottom)
        - max(current.top, taskbar.screen.top),
    )
    visible_thickness = (
        intersection_height if taskbar.edge.horizontal else intersection_width
    )
    return visible_thickness > 5
