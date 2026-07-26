from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Thread
from typing import Any

import psutil
from PySide6.QtCore import (
    QObject,
    Property,
    Signal,
    Slot,
)

from winter.settings import Config, NetworkChartConfig
from winter.taskbar.geometry import discover
from winter.telemetry.history import RecentHistory
from winter.telemetry.model import Snapshot
from winter.telemetry.pipeline import SamplingLoop, Telemetry
from winter.telemetry.system import resolve_default_network_interface


class HistoryStore(QObject):
    changed = Signal()

    def __init__(
        self,
        retention_seconds: float,
        chart: NetworkChartConfig,
        control_center_history_seconds: float,
    ) -> None:
        super().__init__()
        self._history = RecentHistory(retention_seconds)
        self._history_seconds = chart.history_seconds
        self._smoothing_seconds = chart.smoothing_seconds
        self._control_center_history_seconds = control_center_history_seconds

    def append(self, sample: Snapshot) -> None:
        self._history.append(sample)
        self.changed.emit()

    @Slot(result="QVariantList")
    def networkWindow(self) -> list[dict[str, float]]:
        samples = self._history.snapshot()
        if not samples:
            return []

        latest = samples[-1].monotonic_time
        visible = [
            sample
            for sample in samples
            if sample.monotonic_time >= latest - self._history_seconds
        ]
        points: list[dict[str, float]] = []
        start = 0
        upload_sum = 0.0
        download_sum = 0.0
        for end, sample in enumerate(visible):
            upload_sum += sample.upload_bytes_per_second
            download_sum += sample.download_bytes_per_second
            cutoff = sample.monotonic_time - self._smoothing_seconds
            while visible[start].monotonic_time < cutoff:
                upload_sum -= visible[start].upload_bytes_per_second
                download_sum -= visible[start].download_bytes_per_second
                start += 1
            count = end - start + 1
            points.append(
                {
                    "age": latest - sample.monotonic_time,
                    "upload": upload_sum / count,
                    "download": download_sum / count,
                }
            )
        return points

    @Slot(result="QVariantList")
    def controlCenterWindow(self) -> list[dict[str, float]]:
        samples = self._history.snapshot()
        if not samples:
            return []

        latest = samples[-1].monotonic_time
        samples = tuple(
            sample
            for sample in samples
            if sample.monotonic_time >= latest - self._control_center_history_seconds
        )
        upload_sum = 0.0
        download_sum = 0.0
        smoothing_start = 0
        points: list[dict[str, float]] = []

        def number(value: float | int | None) -> float:
            return float("nan") if value is None else float(value)

        for end, sample in enumerate(samples):
            upload_sum += sample.upload_bytes_per_second
            download_sum += sample.download_bytes_per_second
            cutoff = sample.monotonic_time - self._smoothing_seconds
            while samples[smoothing_start].monotonic_time < cutoff:
                upload_sum -= samples[smoothing_start].upload_bytes_per_second
                download_sum -= samples[smoothing_start].download_bytes_per_second
                smoothing_start += 1
            count = end - smoothing_start + 1
            points.append(
                {
                    "age": latest - sample.monotonic_time,
                    "upload": upload_sum / count,
                    "download": download_sum / count,
                    "cpu": number(sample.cpu_percent),
                    "cpuWatts": number(sample.cpu_watts),
                    "memoryUsed": number(sample.memory_used_bytes),
                    "gpu": number(sample.gpu_percent),
                    "gpuWatts": number(sample.gpu_watts),
                    "gpuCelsius": number(sample.gpu_celsius),
                    "vramUsed": number(sample.vram_used_bytes),
                }
            )
        return points


class _Delivery(QObject):
    sampleReady = Signal(object)


class WinterView(QObject):
    telemetryChanged = Signal()
    configurationChanged = Signal()
    availableSourcesChanged = Signal()
    openControlCenterRequested = Signal()
    exitRequested = Signal()
    dragStarted = Signal()
    dragUpdated = Signal()
    dragFinished = Signal()

    def __init__(
        self,
        config_path: Path,
        config: Config,
    ) -> None:
        super().__init__()
        self._config_path = config_path
        self._config = config
        self._automatic_network_adapter = ""
        self._sample = Snapshot.empty()
        self._history = HistoryStore(
            config.telemetry.retention_seconds,
            config.network.chart,
            config.control_center.history_seconds,
        )
        self._delivery = _Delivery()
        self._delivery.sampleReady.connect(self._accept_sample)
        self._telemetry = Telemetry(config)
        self._loop = SamplingLoop(self._telemetry)
        self._thread = Thread(
            target=self._loop.run,
            args=(self._delivery.sampleReady.emit,),
            name="Winter telemetry",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._loop.stop()
        self._thread.join(timeout=3.0)

    @property
    def config(self) -> Config:
        return self._config

    @Slot(object)
    def _accept_sample(self, sample: Snapshot) -> None:
        self._sample = sample
        self._history.append(sample)
        self.telemetryChanged.emit()

    @Property(QObject, constant=True)
    def history(self) -> QObject:
        return self._history

    @Property(float, notify=telemetryChanged)
    def uploadRate(self) -> float:
        return self._sample.upload_bytes_per_second

    @Property(float, notify=telemetryChanged)
    def downloadRate(self) -> float:
        return self._sample.download_bytes_per_second

    @staticmethod
    def _number(value: float | int | None) -> float:
        return float("nan") if value is None else float(value)

    @Property(float, notify=telemetryChanged)
    def cpuPercent(self) -> float:
        return self._number(self._sample.cpu_percent)

    @Property(float, notify=telemetryChanged)
    def cpuWatts(self) -> float:
        return self._number(self._sample.cpu_watts)

    @Property(float, notify=telemetryChanged)
    def memoryUsed(self) -> float:
        return self._number(self._sample.memory_used_bytes)

    @Property(float, notify=telemetryChanged)
    def memoryTotal(self) -> float:
        return self._number(self._sample.memory_total_bytes)

    @Property(float, notify=telemetryChanged)
    def gpuPercent(self) -> float:
        return self._number(self._sample.gpu_percent)

    @Property(float, notify=telemetryChanged)
    def gpuWatts(self) -> float:
        return self._number(self._sample.gpu_watts)

    @Property(float, notify=telemetryChanged)
    def gpuCelsius(self) -> float:
        return self._number(self._sample.gpu_celsius)

    @Property(float, notify=telemetryChanged)
    def vramUsed(self) -> float:
        return self._number(self._sample.vram_used_bytes)

    @Property(float, notify=telemetryChanged)
    def vramTotal(self) -> float:
        return self._number(self._sample.vram_total_bytes)

    @Property(str, notify=configurationChanged)
    def networkAdapterSelection(self) -> str:
        return self._config.network.adapter_selection

    @Property(str, notify=configurationChanged)
    def networkAdapterName(self) -> str:
        return self._config.network.adapter_name or ""

    @Property(str, notify=configurationChanged)
    def networkChartSeriesLayout(self) -> str:
        return self._config.network.chart.series_layout

    @Property("QVariantMap", notify=configurationChanged)
    def networkChart(self) -> dict[str, Any]:
        return self._config.network.chart.model_dump(mode="json")

    @Property("QVariantMap", notify=configurationChanged)
    def taskbarColors(self) -> dict[str, Any]:
        return self._config.taskbar.colors.model_dump(mode="json")

    @Property("QVariantMap", notify=configurationChanged)
    def taskbarText(self) -> dict[str, Any]:
        return self._config.taskbar.text.model_dump(mode="json")

    @Property("QVariantMap", notify=configurationChanged)
    def taskbarSize(self) -> dict[str, Any]:
        return self._config.taskbar.size.model_dump(mode="json")

    @Property("QVariantMap", notify=configurationChanged)
    def taskbarPosition(self) -> dict[str, Any]:
        return self._config.taskbar.position.model_dump(mode="json")

    @Property("QVariantMap", notify=configurationChanged)
    def controlCenterColors(self) -> dict[str, Any]:
        palette = getattr(
            self._config.control_center,
            self._config.control_center.theme,
        )
        return palette.model_dump(mode="json")

    @Property("QVariantMap", notify=configurationChanged)
    def controlCenterText(self) -> dict[str, Any]:
        return self._config.control_center.text.model_dump(mode="json")

    @Property(str, notify=configurationChanged)
    def controlCenterTheme(self) -> str:
        return self._config.control_center.theme

    @Property(float, notify=configurationChanged)
    def controlCenterHistorySeconds(self) -> float:
        return self._config.control_center.history_seconds

    @Property(str, notify=configurationChanged)
    def taskbarMonitor(self) -> str:
        return self._config.taskbar.monitor or ""

    @Property(bool, notify=configurationChanged)
    def visibleInFullscreen(self) -> bool:
        return self._config.taskbar.visible_in_fullscreen

    @Property("QStringList", notify=availableSourcesChanged)
    def networkInterfaces(self) -> list[str]:
        return sorted(psutil.net_if_stats(), key=str.casefold)

    @Property(str, notify=availableSourcesChanged)
    def automaticNetworkAdapter(self) -> str:
        return self._automatic_network_adapter

    @Property("QStringList", notify=availableSourcesChanged)
    def monitors(self) -> list[str]:
        return [taskbar.monitor_name for taskbar in discover()]

    @Slot()
    def refreshAvailableSources(self) -> None:
        self._automatic_network_adapter = resolve_default_network_interface() or ""
        self.availableSourcesChanged.emit()

    @Slot(str, str)
    def setNetworkAdapter(self, adapter_selection: str, adapter_name: str) -> None:
        if adapter_selection not in {"automatic", "named"}:
            return
        adapter_name = str(adapter_name).strip() if adapter_name else None
        if adapter_selection == "named" and adapter_name is None:
            return
        if adapter_selection == "automatic":
            adapter_name = None
        self._update_config(
            lambda document: document["network"].update(
                {
                    "adapter_selection": adapter_selection,
                    "adapter_name": adapter_name,
                }
            )
        )

    @Slot(object)
    def setTaskbarMonitor(self, taskbar_monitor) -> None:
        monitor = str(taskbar_monitor).strip() if taskbar_monitor else None
        self._update_config(
            lambda document: document["taskbar"].update({"monitor": monitor})
        )

    @Slot(bool)
    def setVisibleInFullscreen(self, visible: bool) -> None:
        self._update_config(
            lambda document: document["taskbar"].update(
                {"visible_in_fullscreen": visible}
            )
        )

    @Slot(str)
    def setControlCenterTheme(self, theme: str) -> None:
        if theme not in {"dark", "light"}:
            return
        self._update_config(
            lambda document: document["control_center"].update({"theme": theme})
        )

    @Slot(str)
    def setNetworkChartSeriesLayout(self, series_layout: str) -> None:
        if series_layout not in {"shared", "separate"}:
            return
        self._update_config(
            lambda document: document["network"]["chart"].update(
                {"series_layout": series_layout}
            )
        )

    def saveTaskbarPosition(self, shift_left_or_up: int) -> None:
        self._update_config(
            lambda document: document["taskbar"]["position"].update(
                {"shift_left_or_up": shift_left_or_up}
            )
        )

    def _update_config(self, mutate: Callable[[dict[str, Any]], None]) -> None:
        document = self._config.model_dump(mode="python")
        mutate(document)
        updated = Config.model_validate(document)
        if updated == self._config:
            return
        updated.save(self._config_path)
        self._config = updated
        self._telemetry.update_config(updated)
        self.configurationChanged.emit()

    @Slot()
    def resetTaskbarPosition(self) -> None:
        self.saveTaskbarPosition(0)

    @Slot()
    def openControlCenter(self) -> None:
        self.openControlCenterRequested.emit()

    @Slot()
    def exitWinter(self) -> None:
        self.exitRequested.emit()

    @Slot()
    def beginTaskbarDrag(self) -> None:
        self.dragStarted.emit()

    @Slot()
    def updateTaskbarDrag(self) -> None:
        self.dragUpdated.emit()

    @Slot()
    def endTaskbarDrag(self) -> None:
        self.dragFinished.emit()
