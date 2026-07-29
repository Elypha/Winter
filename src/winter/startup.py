from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

from win32com.client.dynamic import Dispatch

from winter.paths import AppFiles

_SHORTCUT_NAME = "Winter.lnk"
_SHORTCUT_DESCRIPTION = "Managed by Winter - start when signing in."


class StartupShortcutConflict(OSError):
    pass


class StartupShortcut:
    def __init__(
        self,
        target: Path,
        arguments: str,
        working_directory: Path,
        startup_directory: Path | None = None,
    ) -> None:
        self._target = target.absolute()
        self._arguments = arguments
        self._working_directory = working_directory.absolute()
        self._startup_directory = startup_directory

    @classmethod
    def for_current_process(cls, files: AppFiles) -> StartupShortcut:
        if getattr(sys, "frozen", False):
            target = Path(sys.executable)
            arguments = ""
            working_directory = target.parent
        else:
            executable = Path(sys.executable)
            windowed_executable = executable.with_name("pythonw.exe")
            target = windowed_executable if windowed_executable.exists() else executable
            arguments = "-m winter"
            working_directory = files.root
        return cls(target, arguments, working_directory)

    def is_enabled(self) -> bool:
        shell = Dispatch("WScript.Shell")
        shortcut_path = self._shortcut_path(shell)
        if not shortcut_path.exists():
            return False
        shortcut = shell.CreateShortcut(str(shortcut_path))
        return self._is_owned(shortcut) and self._matches_current_launch(shortcut)

    def enable(self) -> None:
        shell = Dispatch("WScript.Shell")
        shortcut_path = self._shortcut_path(shell)
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
        if shortcut_path.exists():
            existing = shell.CreateShortcut(str(shortcut_path))
            if not self._is_owned(existing):
                raise StartupShortcutConflict(
                    f"{shortcut_path} already exists and is not managed by Winter."
                )

        temporary_path = shortcut_path.with_name(
            f".{shortcut_path.stem}-{uuid4().hex}.lnk"
        )
        try:
            shortcut = shell.CreateShortcut(str(temporary_path))
            shortcut.TargetPath = str(self._target)
            shortcut.Arguments = self._arguments
            shortcut.WorkingDirectory = str(self._working_directory)
            shortcut.Description = _SHORTCUT_DESCRIPTION
            shortcut.Save()
            os.replace(temporary_path, shortcut_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def disable(self) -> None:
        shell = Dispatch("WScript.Shell")
        shortcut_path = self._shortcut_path(shell)
        if not shortcut_path.exists():
            return
        shortcut = shell.CreateShortcut(str(shortcut_path))
        if not self._is_owned(shortcut):
            raise StartupShortcutConflict(
                f"{shortcut_path} exists but is not managed by Winter."
            )
        shortcut_path.unlink()

    def _shortcut_path(self, shell) -> Path:
        startup_directory = self._startup_directory
        if startup_directory is None:
            startup_directory = Path(shell.SpecialFolders("Startup"))
        return startup_directory / _SHORTCUT_NAME

    @staticmethod
    def _is_owned(shortcut) -> bool:
        return shortcut.Description == _SHORTCUT_DESCRIPTION

    def _matches_current_launch(self, shortcut) -> bool:
        return (
            self._same_path(shortcut.TargetPath, self._target)
            and shortcut.Arguments.strip() == self._arguments
            and self._same_path(
                shortcut.WorkingDirectory,
                self._working_directory,
            )
        )

    @staticmethod
    def _same_path(actual: str, expected: Path) -> bool:
        if not actual:
            return False
        normalised_actual = os.path.normcase(
            os.path.abspath(os.path.expandvars(actual))
        )
        normalised_expected = os.path.normcase(os.path.abspath(expected))
        return normalised_actual == normalised_expected
