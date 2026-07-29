from __future__ import annotations

import ctypes
import logging
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from winter.logging_setup import configure_logging
from winter.paths import AppFiles
from winter.settings import Config
from winter.single_instance import SessionLock
from winter.taskbar.host import TaskbarHost
from winter.ui.bridge import WinterView

log = logging.getLogger(__name__)


def _report_startup_failure(message: str) -> None:
    print(message, file=sys.stderr)
    ctypes.windll.user32.MessageBoxW(None, message, "Winter", 0x10)


def _launch(files: AppFiles) -> int:
    try:
        configure_logging(files)
    except OSError as error:
        _report_startup_failure(
            f"Winter cannot write to its application folder:\n{files.root}\n\n{error}"
        )
        return 1

    default_config = Config.load(files.default_configuration)
    config = Config.load_overrides(default_config, files.user_configuration)
    log.info("Winter starting")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Winter")
    app.setOrganizationName("Winter")
    app.setWindowIcon(QIcon(str(files.icon)))
    app.setQuitOnLastWindowClosed(False)

    view = WinterView(files.user_configuration, default_config, config)
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"view": view})
    engine.load(QUrl.fromLocalFile(str(files.qml_directory / "Taskbar.qml")))
    engine.setInitialProperties({"view": view})
    engine.load(QUrl.fromLocalFile(str(files.qml_directory / "ControlCenter.qml")))
    roots = engine.rootObjects()
    if len(roots) != 2 or not all(isinstance(root, QQuickWindow) for root in roots):
        message = "Winter could not load its user interface. See logs/Winter.log."
        log.error(message)
        _report_startup_failure(message)
        return 1

    taskbar_window, control_center = roots
    host = TaskbarHost(taskbar_window, view)

    def open_control_center() -> None:
        control_center.show()
        control_center.raise_()
        control_center.requestActivate()

    view.openControlCenterRequested.connect(open_control_center)
    view.exitRequested.connect(app.quit)
    app.aboutToQuit.connect(host.close)
    app.aboutToQuit.connect(view.close)
    host.start()
    view.start()
    return app.exec()


def run(files: AppFiles) -> int:
    try:
        with SessionLock() as lock:
            if not lock.acquired:
                return 0
            return _launch(files)
    except OSError as error:
        _report_startup_failure(f"Winter could not start.\n\n{error}")
        return 1
