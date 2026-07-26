from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from winter.paths import AppFiles


def configure_logging(files: AppFiles) -> None:
    files.log_directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        files.log_file,
        maxBytes=1024 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
