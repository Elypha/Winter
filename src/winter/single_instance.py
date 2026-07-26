from __future__ import annotations

from contextlib import AbstractContextManager
from types import TracebackType

import win32api
import win32event
import winerror


class SessionLock(AbstractContextManager["SessionLock"]):
    def __init__(self, name: str = r"Local\Winter.Instance") -> None:
        self._name = name
        self._handle = None
        self.acquired = False

    def __enter__(self) -> "SessionLock":
        self._handle = win32event.CreateMutex(None, False, self._name)
        self.acquired = win32api.GetLastError() != winerror.ERROR_ALREADY_EXISTS
        if not self.acquired:
            win32api.CloseHandle(self._handle)
            self._handle = None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._handle is not None:
            win32api.CloseHandle(self._handle)
            self._handle = None
