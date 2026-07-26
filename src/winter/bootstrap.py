from __future__ import annotations

import os
import sys

from winter.paths import AppFiles


def _prepare_process() -> AppFiles:
    files = AppFiles.discover()
    sys.dont_write_bytecode = True
    os.environ["QML_DISABLE_DISK_CACHE"] = "1"
    os.environ["QSG_RHI_DISABLE_DISK_CACHE"] = "1"
    return files


def start() -> int:
    files = _prepare_process()

    from winter.application import run

    return run(files)
