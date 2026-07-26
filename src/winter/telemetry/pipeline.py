from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
import logging
import math
import threading
import time
from typing import TypeVar

from winter.settings import Config
from winter.telemetry.model import Snapshot
from winter.telemetry.nvml import NvidiaMonitor
from winter.telemetry.pdh import WindowsPerformance
from winter.telemetry.system import HostMeter, NetworkMeter


log = logging.getLogger(__name__)
_Reading = TypeVar("_Reading")


class Telemetry:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._network = NetworkMeter()
        self._host = HostMeter()
        self._windows = WindowsPerformance()
        self._nvidia = NvidiaMonitor()
        now = time.monotonic()
        self._latest = Snapshot.empty(now)
        self._next_network = now
        self._next_host = now
        self._next_sensor = now
        self._failed_sources: set[str] = set()

    def update_config(self, config: Config) -> None:
        self._config = config

    def sample(self, now: float | None = None) -> Snapshot | None:
        current = time.monotonic() if now is None else now
        latest = self._latest
        changed = False

        if current >= self._next_network:
            self._next_network = self._advance(
                self._next_network,
                self._config.telemetry.network_sample_seconds,
                current,
            )
            rates = self._read_source(
                "Network",
                lambda: self._network.read(
                    current,
                    self._config.network.adapter_selection,
                    self._config.network.adapter_name,
                ),
            )
            latest = replace(
                latest,
                upload_bytes_per_second=0.0 if rates is None else rates.upload,
                download_bytes_per_second=0.0 if rates is None else rates.download,
            )
            changed = True

        if current >= self._next_host:
            self._next_host = self._advance(
                self._next_host,
                self._config.telemetry.system_sample_seconds,
                current,
            )
            host = self._read_source("Host", lambda: self._host.read(current))
            graphics = self._read_source(
                "Windows graphics",
                lambda: self._windows.graphics(current),
            )
            nvidia_memory = self._read_source(
                "NVIDIA memory",
                lambda: self._nvidia.memory(current),
            )

            latest = replace(
                latest,
                cpu_percent=None if host is None else host.cpu_percent,
                memory_used_bytes=None if host is None else host.memory_used,
                memory_total_bytes=None if host is None else host.memory_total,
                gpu_percent=None if graphics is None else graphics.utilization,
                vram_used_bytes=(
                    nvidia_memory.used
                    if nvidia_memory is not None and nvidia_memory.used is not None
                    else (None if graphics is None else graphics.dedicated_memory)
                ),
                vram_total_bytes=(
                    None if nvidia_memory is None else nvidia_memory.total
                ),
            )
            changed = True

        if current >= self._next_sensor:
            self._next_sensor = self._advance(
                self._next_sensor,
                self._config.telemetry.sensor_sample_seconds,
                current,
            )
            power = self._read_source(
                "Windows power",
                lambda: self._windows.power(current),
            )
            nvidia = self._read_source(
                "NVIDIA sensors",
                lambda: self._nvidia.sensors(current),
            )

            latest = replace(
                latest,
                cpu_watts=None if power is None else power.cpu_watts,
                gpu_watts=(
                    nvidia.watts
                    if nvidia is not None and nvidia.watts is not None
                    else (None if power is None else power.gpu_watts)
                ),
                gpu_celsius=None if nvidia is None else nvidia.celsius,
            )
            changed = True

        if not changed:
            return None
        latest = replace(
            latest,
            captured_at=datetime.now(UTC),
            monotonic_time=current,
        )
        self._latest = latest
        return latest

    @staticmethod
    def _advance(deadline: float, period: float, now: float) -> float:
        elapsed_periods = math.floor((now - deadline) / period) + 1
        return deadline + elapsed_periods * period

    def seconds_until_due(self, now: float | None = None) -> float:
        current = time.monotonic() if now is None else now
        next_deadline = min(
            self._next_network,
            self._next_host,
            self._next_sensor,
        )
        return max(0.0, next_deadline - current)

    def _read_source(
        self,
        source: str,
        read: Callable[[], _Reading],
    ) -> _Reading | None:
        try:
            value = read()
        except Exception as error:
            self._report_failure(source, error)
            return None
        self._report_recovery(source)
        return value

    def _report_failure(self, source: str, error: Exception) -> None:
        if source not in self._failed_sources:
            log.warning("%s telemetry failed: %s", source, error)
            self._failed_sources.add(source)

    def _report_recovery(self, source: str) -> None:
        if source in self._failed_sources:
            log.info("%s telemetry recovered", source)
            self._failed_sources.remove(source)

    def close(self) -> None:
        self._windows.close()
        self._nvidia.close()


class SamplingLoop:
    def __init__(self, telemetry: Telemetry) -> None:
        self._telemetry = telemetry
        self._stop = threading.Event()

    def run(self, publish: Callable[[Snapshot], None]) -> None:
        try:
            while not self._stop.is_set():
                sample = self._telemetry.sample()
                if sample is not None:
                    publish(sample)
                self._stop.wait(self._telemetry.seconds_until_due())
        finally:
            self._telemetry.close()

    def stop(self) -> None:
        self._stop.set()
