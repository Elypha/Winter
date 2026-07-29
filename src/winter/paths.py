from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppFiles:
    root: Path

    @classmethod
    def discover(cls) -> "AppFiles":
        if getattr(sys, "frozen", False):
            root = Path(sys.executable).resolve().parent
        else:
            root = Path(__file__).resolve().parents[2]
        return cls(root=root)

    @property
    def default_configuration(self) -> Path:
        return self.root / "config.default.yaml"

    @property
    def user_configuration(self) -> Path:
        return self.root / "config" / "config.yaml"

    @property
    def log_directory(self) -> Path:
        return self.root / "logs"

    @property
    def log_file(self) -> Path:
        return self.log_directory / "Winter.log"

    @property
    def qml_directory(self) -> Path:
        return Path(__file__).resolve().parent / "ui" / "qml"

    @property
    def icon(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(__file__).resolve().parent / "assets" / "winter.ico"
        return self.root / "assets" / "winter.ico"
