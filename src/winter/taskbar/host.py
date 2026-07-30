from __future__ import annotations

import ctypes
import logging
import os
from ctypes import wintypes
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import win32api
import win32con
import win32gui
import win32process
from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtGui import QGuiApplication, QWindow

from winter.taskbar.events import ShellEvents
from winter.taskbar.geometry import Taskbar, choose, discover, is_taskbar_visible

if TYPE_CHECKING:
    from winter.ui.bridge import WinterView


log = logging.getLogger(__name__)
_GWL_STYLE = -16
_GWL_EXSTYLE = -20
_GWLP_HWNDPARENT = -8
_WS_EX_NOACTIVATE = 0x08000000
_WS_EX_LAYERED = 0x00080000
_DISPLAY_MODES = ("full", "compact", "minimal")
_CLR_INVALID = 0xFFFFFFFF

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_GDI32 = ctypes.WinDLL("gdi32", use_last_error=True)
_GET_DC = _USER32.GetDC
_GET_DC.argtypes = [wintypes.HWND]
_GET_DC.restype = wintypes.HDC
_RELEASE_DC = _USER32.ReleaseDC
_RELEASE_DC.argtypes = [wintypes.HWND, wintypes.HDC]
_RELEASE_DC.restype = ctypes.c_int
_GET_PIXEL = _GDI32.GetPixel
_GET_PIXEL.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
_GET_PIXEL.restype = wintypes.DWORD
_SET_WINDOW_LONG_PTR = _USER32.SetWindowLongPtrW
_SET_WINDOW_LONG_PTR.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
_SET_WINDOW_LONG_PTR.restype = ctypes.c_ssize_t


@dataclass(frozen=True, slots=True)
class _Placement:
    taskbar: Taskbar
    drag_start: int
    drag_end: int
    x: int
    y: int
    width: int
    height: int
    automatic_start: int


class TaskbarHost(QObject):
    def __init__(self, window: QWindow, view: WinterView) -> None:
        super().__init__()
        self._window = window
        self._view = view
        self._hwnd = int(window.winId())
        self._placement: _Placement | None = None
        self._drag_cursor_origin: tuple[int, int] | None = None
        self._drag_window_origin: tuple[int, int] | None = None
        self._dragging = False
        self._events = ShellEvents()
        self._events.foregroundChanged.connect(self._schedule_visibility)
        self._events.geometryChanged.connect(self._schedule_refresh)
        self._events.watchdog.connect(self.refresh)
        self._view.configurationChanged.connect(self.refresh)
        self._view.dragStarted.connect(self.begin_drag)
        self._view.dragUpdated.connect(self.drag)
        self._view.dragFinished.connect(self.finish_drag)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(100)
        self._refresh_timer.timeout.connect(self.refresh)
        self._visibility_timer = QTimer(self)
        self._visibility_timer.setSingleShot(True)
        self._visibility_timer.setInterval(100)
        self._visibility_timer.timeout.connect(self._update_visibility)

        app = QGuiApplication.instance()
        app.screenAdded.connect(self._screen_added)
        app.screenRemoved.connect(self._screen_removed)
        for screen in app.screens():
            self._watch_screen(screen)

    def _screen_added(self, screen) -> None:
        self._watch_screen(screen)
        QTimer.singleShot(100, self._view.refreshAvailableSources)
        self._schedule_refresh()

    def _screen_removed(self, _screen) -> None:
        QTimer.singleShot(100, self._view.refreshAvailableSources)
        self._schedule_refresh()

    def _watch_screen(self, screen) -> None:
        screen.geometryChanged.connect(lambda _rect: self._schedule_refresh())
        screen.logicalDotsPerInchChanged.connect(lambda _dpi: self._schedule_refresh())

    def start(self) -> None:
        self._apply_window_contract()
        self._events.start()
        self.refresh()

    def close(self) -> None:
        self._refresh_timer.stop()
        self._visibility_timer.stop()
        self._events.close()

    def _schedule_refresh(self) -> None:
        self._refresh_timer.start()

    def _schedule_visibility(self) -> None:
        self._visibility_timer.start()

    def _apply_window_contract(self) -> None:
        style = win32gui.GetWindowLong(self._hwnd, _GWL_STYLE)
        style = (style | win32con.WS_POPUP) & ~win32con.WS_CAPTION
        win32gui.SetWindowLong(self._hwnd, _GWL_STYLE, style)
        extended = win32gui.GetWindowLong(self._hwnd, _GWL_EXSTYLE)
        extended |= win32con.WS_EX_TOOLWINDOW | _WS_EX_NOACTIVATE | _WS_EX_LAYERED
        win32gui.SetWindowLong(self._hwnd, _GWL_EXSTYLE, extended)

    @Slot()
    def refresh(self) -> None:
        if self._dragging:
            return
        taskbars = discover()
        self._events.track({taskbar.hwnd for taskbar in taskbars})
        taskbar = choose(taskbars, self._view.taskbarMonitor)
        if taskbar is None:
            self._set_visible(False)
            self._placement = None
            return
        taskbar = self._preserve_transient_child_geometry(taskbar)

        placement, mode = self._place(taskbar)
        if placement is None:
            self._set_visible(False)
            self._placement = None
            return

        self._placement = placement
        self._window.setProperty("displayMode", mode)
        self._window.setProperty("vertical", not taskbar.edge.horizontal)
        self._window.setProperty("taskbarEdge", taskbar.edge.value)
        self._window.setProperty(
            "useLightForeground",
            self._prefer_light_foreground(taskbar, placement),
        )
        self._set_owner(taskbar.hwnd)
        win32gui.SetWindowPos(
            self._hwnd,
            win32con.HWND_TOPMOST,
            placement.x,
            placement.y,
            placement.width,
            placement.height,
            win32con.SWP_NOACTIVATE | win32con.SWP_NOOWNERZORDER,
        )
        self._update_visibility()

    def _preserve_transient_child_geometry(self, taskbar: Taskbar) -> Taskbar:
        if self._placement is None:
            return taskbar

        previous = self._placement.taskbar
        if (
            taskbar.hwnd != previous.hwnd
            or taskbar.bounds != previous.bounds
            or taskbar.screen != previous.screen
            or taskbar.edge is not previous.edge
            or taskbar.scale != previous.scale
        ):
            return taskbar

        return replace(
            taskbar,
            task_buttons=taskbar.task_buttons or previous.task_buttons,
            notification_area=taskbar.notification_area
            or previous.notification_area,
        )

    @staticmethod
    def _prefer_light_foreground(taskbar: Taskbar, placement: _Placement) -> bool:
        dc = _GET_DC(None)
        if not dc:
            return True

        samples: list[tuple[int, int, int]] = []
        bounds = taskbar.bounds
        try:
            for x_index in range(1, 18):
                x = bounds.left + round(bounds.width * x_index / 18)
                for y_index in range(1, 5):
                    y = bounds.top + round(bounds.height * y_index / 5)
                    if (
                        placement.x - 3 <= x <= placement.x + placement.width + 3
                        and placement.y - 3 <= y <= placement.y + placement.height + 3
                    ):
                        continue
                    colour = _GET_PIXEL(dc, x, y)
                    if colour != _CLR_INVALID:
                        samples.append(
                            (
                                colour & 0xFF,
                                (colour >> 8) & 0xFF,
                                (colour >> 16) & 0xFF,
                            )
                        )
        finally:
            _RELEASE_DC(None, dc)

        if not samples:
            return True
        red = sum(value[0] for value in samples) / len(samples) / 255.0
        green = sum(value[1] for value in samples) / len(samples) / 255.0
        blue = sum(value[2] for value in samples) / len(samples) / 255.0

        def linear(channel: float) -> float:
            if channel <= 0.04045:
                return channel / 12.92
            return ((channel + 0.055) / 1.055) ** 2.4

        luminance = (
            0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)
        )
        white_contrast = 1.05 / (luminance + 0.05)
        black_contrast = (luminance + 0.05) / 0.05
        return white_contrast >= black_contrast

    def _set_visible(self, visible: bool) -> None:
        if self._window.isVisible() != visible:
            self._window.setVisible(visible)

    def _place(self, taskbar: Taskbar) -> tuple[_Placement | None, str]:
        safe_start, safe_end = taskbar.usable_interval
        safe_span = safe_end - safe_start
        taskbar_config = self._view.config.taskbar
        for mode in _DISPLAY_MODES:
            logical_length = taskbar_config.total_width(mode)
            length = round(logical_length * taskbar.scale)
            if length <= safe_span:
                break
        else:
            return None, "minimal"

        shift_left_or_up = round(
            self._view.config.taskbar.position.shift_left_or_up * taskbar.scale
        )
        automatic_start = safe_end - length
        if taskbar.edge.horizontal:
            drag_start, drag_end = taskbar.bounds.left, taskbar.bounds.right
            width = length
            height = taskbar.bounds.height
            y = taskbar.bounds.top
        else:
            drag_start, drag_end = taskbar.bounds.top, taskbar.bounds.bottom
            width = taskbar.bounds.width
            height = length
            x = taskbar.bounds.left

        along = max(
            drag_start,
            min(drag_end - length, automatic_start - shift_left_or_up),
        )
        if taskbar.edge.horizontal:
            x = along
        else:
            y = along
        return (
            _Placement(
                taskbar=taskbar,
                drag_start=drag_start,
                drag_end=drag_end,
                x=x,
                y=y,
                width=width,
                height=height,
                automatic_start=automatic_start,
            ),
            mode,
        )

    def _set_owner(self, owner: int) -> None:
        ctypes.set_last_error(0)
        previous = _SET_WINDOW_LONG_PTR(self._hwnd, _GWLP_HWNDPARENT, owner)
        if previous == 0 and ctypes.get_last_error():
            log.warning("Could not assign the taskbar window owner")

    def _update_visibility(self) -> None:
        placement = self._placement
        if placement is None:
            self._set_visible(False)
            return
        visible = is_taskbar_visible(placement.taskbar)
        if visible and not self._view.visibleInFullscreen:
            visible = not self._foreground_covers(placement.taskbar)
        if visible:
            self._set_visible(True)
            win32gui.SetWindowPos(
                self._hwnd,
                win32con.HWND_TOPMOST,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_NOOWNERZORDER,
            )
        else:
            self._set_visible(False)

    def _foreground_covers(self, taskbar: Taskbar) -> bool:
        foreground = win32gui.GetForegroundWindow()
        if not foreground or foreground in {self._hwnd, taskbar.hwnd}:
            return False
        try:
            _, process_id = win32process.GetWindowThreadProcessId(foreground)
            if process_id == os.getpid():
                return False
            monitor = win32api.MonitorFromWindow(
                foreground, win32con.MONITOR_DEFAULTTONEAREST
            )
            info = win32api.GetMonitorInfo(monitor)
            if str(info["Device"]).casefold() != taskbar.monitor_name.casefold():
                return False
            window = win32gui.GetWindowRect(foreground)
        except win32gui.error:
            return False
        screen = taskbar.screen
        return all(
            abs(actual - expected) <= 2
            for actual, expected in zip(
                window, (screen.left, screen.top, screen.right, screen.bottom)
            )
        )

    @Slot()
    def begin_drag(self) -> None:
        if self._placement is None:
            return
        self._dragging = True
        self._drag_cursor_origin = win32api.GetCursorPos()
        self._drag_window_origin = (self._placement.x, self._placement.y)

    @Slot()
    def drag(self) -> None:
        placement = self._placement
        if (
            not self._dragging
            or placement is None
            or self._drag_cursor_origin is None
            or self._drag_window_origin is None
        ):
            return
        cursor_x, cursor_y = win32api.GetCursorPos()
        cursor_origin_x, cursor_origin_y = self._drag_cursor_origin
        window_origin_x, window_origin_y = self._drag_window_origin
        if placement.taskbar.edge.horizontal:
            x = window_origin_x + cursor_x - cursor_origin_x
            x = max(
                placement.drag_start,
                min(placement.drag_end - placement.width, x),
            )
            y = placement.y
        else:
            x = placement.x
            y = window_origin_y + cursor_y - cursor_origin_y
            y = max(
                placement.drag_start,
                min(placement.drag_end - placement.height, y),
            )
        win32gui.SetWindowPos(
            self._hwnd,
            win32con.HWND_TOPMOST,
            x,
            y,
            0,
            0,
            win32con.SWP_NOSIZE
            | win32con.SWP_NOACTIVATE
            | win32con.SWP_NOOWNERZORDER,
        )
        self._placement = _Placement(
            taskbar=placement.taskbar,
            drag_start=placement.drag_start,
            drag_end=placement.drag_end,
            x=x,
            y=y,
            width=placement.width,
            height=placement.height,
            automatic_start=placement.automatic_start,
        )

    @Slot()
    def finish_drag(self) -> None:
        placement = self._placement
        self._dragging = False
        self._drag_cursor_origin = None
        self._drag_window_origin = None
        if placement is None:
            return
        along = placement.x if placement.taskbar.edge.horizontal else placement.y
        shift_left_or_up = round(
            (placement.automatic_start - along) / placement.taskbar.scale
        )
        self._view.saveTaskbarPosition(shift_left_or_up)
