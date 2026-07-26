from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal


_EVENT_SYSTEM_FOREGROUND = 0x0003
_EVENT_OBJECT_LOCATIONCHANGE = 0x800B
_WINEVENT_OUTOFCONTEXT = 0x0000
_OBJID_WINDOW = 0
_WIN_EVENT_CALLBACK = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD,
)
_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_SET_WIN_EVENT_HOOK = _USER32.SetWinEventHook
_SET_WIN_EVENT_HOOK.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HMODULE,
    _WIN_EVENT_CALLBACK,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
]
_SET_WIN_EVENT_HOOK.restype = wintypes.HANDLE
_UNHOOK_WIN_EVENT = _USER32.UnhookWinEvent
_UNHOOK_WIN_EVENT.argtypes = [wintypes.HANDLE]
_UNHOOK_WIN_EVENT.restype = wintypes.BOOL


class ShellEvents(QObject):
    foregroundChanged = Signal()
    geometryChanged = Signal()
    watchdog = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._tracked: set[int] = set()
        self._hooks: list[int] = []
        self._callback = _WIN_EVENT_CALLBACK(self._on_event)
        self._timer = QTimer(self)
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self.watchdog)

    def start(self) -> None:
        for event in (_EVENT_SYSTEM_FOREGROUND, _EVENT_OBJECT_LOCATIONCHANGE):
            hook = _SET_WIN_EVENT_HOOK(
                event,
                event,
                0,
                self._callback,
                0,
                0,
                _WINEVENT_OUTOFCONTEXT,
            )
            if hook:
                self._hooks.append(hook)
        self._timer.start()

    def track(self, hwnds: set[int]) -> None:
        self._tracked = set(hwnds)

    def _on_event(
        self,
        _hook,
        event: int,
        hwnd: int,
        object_id: int,
        _child_id: int,
        _thread: int,
        _time: int,
    ) -> None:
        if event == _EVENT_SYSTEM_FOREGROUND:
            self.foregroundChanged.emit()
        elif object_id == _OBJID_WINDOW and hwnd in self._tracked:
            self.geometryChanged.emit()

    def close(self) -> None:
        self._timer.stop()
        for hook in self._hooks:
            _UNHOOK_WIN_EVENT(hook)
        self._hooks.clear()
