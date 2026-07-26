from __future__ import annotations

from dataclasses import dataclass
import logging
import math
import re
from typing import Final

import win32pdh


log = logging.getLogger(__name__)
_RETRY_SECONDS: Final = 30.0
_CPU_PACKAGE_INSTANCE = re.compile(r"(?:^|_)PKG(?:_|$)", re.IGNORECASE)
_GPU_DOMAIN_INSTANCE = re.compile(r"(?:^|_)(?:PP1|GPU)(?:_|$)", re.IGNORECASE)
_GPU_ENGINE_INSTANCE = re.compile(
    r"_luid_(?P<adapter>0x[0-9a-f]+_0x[0-9a-f]+)_phys_(?P<physical>\d+)"
    r"_eng_(?P<engine>\d+)_engtype_(?P<kind>.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class GraphicsCounters:
    utilization: float | None
    dedicated_memory: int | None


@dataclass(frozen=True, slots=True)
class PowerCounters:
    cpu_watts: float | None
    gpu_watts: float | None


class _WildcardQuery:
    def __init__(self, paths: tuple[str, ...]) -> None:
        self._paths = paths
        self._query = None
        self._counters: tuple[object, ...] = ()
        self._retry_at = 0.0
        self._reported_unavailable = False

    def collect(self, now: float) -> tuple[dict[str, float], ...] | None:
        if self._query is None and now < self._retry_at:
            return None
        if self._query is None:
            try:
                self._query = win32pdh.OpenQuery()
                self._counters = tuple(
                    win32pdh.AddEnglishCounter(self._query, path)
                    for path in self._paths
                )
                win32pdh.CollectQueryData(self._query)
                if self._reported_unavailable:
                    log.info("PDH source recovered")
                    self._reported_unavailable = False
                return None
            except Exception as error:
                self._discard(now)
                if not self._reported_unavailable:
                    log.info("PDH source unavailable: %s", error)
                    self._reported_unavailable = True
                return None

        try:
            win32pdh.CollectQueryData(self._query)
            return tuple(
                win32pdh.GetFormattedCounterArray(counter, win32pdh.PDH_FMT_DOUBLE)
                for counter in self._counters
            )
        except Exception as error:
            self._discard(now)
            if not self._reported_unavailable:
                log.warning("PDH source lost; retrying later: %s", error)
                self._reported_unavailable = True
            return None

    def _discard(self, now: float) -> None:
        if self._query is not None:
            try:
                win32pdh.CloseQuery(self._query)
            except Exception:
                pass
        self._query = None
        self._counters = ()
        self._retry_at = now + _RETRY_SECONDS

    def close(self) -> None:
        self._discard(float("inf"))


class WindowsPerformance:
    def __init__(self) -> None:
        self._graphics = _WildcardQuery(
            (
                r"\GPU Engine(*)\Utilization Percentage",
                r"\GPU Adapter Memory(*)\Dedicated Usage",
            )
        )
        self._power = _WildcardQuery((r"\Energy Meter(*)\Power",))

    def graphics(self, now: float) -> GraphicsCounters:
        result = self._graphics.collect(now)
        if result is None:
            return GraphicsCounters(None, None)
        engines, adapters = result
        utilization = self._gpu_utilization(engines)
        memory_readings = [
            max(0.0, value) for value in adapters.values() if math.isfinite(value)
        ]
        dedicated_memory = (
            int(sum(memory_readings))
            if memory_readings
            else (0 if not adapters else None)
        )
        return GraphicsCounters(
            utilization=utilization,
            dedicated_memory=dedicated_memory,
        )

    def power(self, now: float) -> PowerCounters:
        result = self._power.collect(now)
        if result is None:
            return PowerCounters(None, None)
        instances = result[0]
        return PowerCounters(
            cpu_watts=self._sum_watts(instances, _CPU_PACKAGE_INSTANCE),
            gpu_watts=self._sum_watts(instances, _GPU_DOMAIN_INSTANCE),
        )

    @staticmethod
    def _sum_watts(
        instances: dict[str, float],
        pattern: re.Pattern[str],
    ) -> float | None:
        readings = [
            max(0.0, value)
            for name, value in instances.items()
            if pattern.search(name) and math.isfinite(value)
        ]
        return sum(readings) / 1000.0 if readings else None

    @staticmethod
    def _gpu_utilization(instances: dict[str, float]) -> float | None:
        engine_totals: dict[tuple[str, str, str, str], float] = {}
        for name, value in instances.items():
            match = _GPU_ENGINE_INSTANCE.search(name)
            if match is None or not math.isfinite(value):
                continue
            engine = (
                match["adapter"].casefold(),
                match["physical"],
                match["engine"],
                match["kind"].casefold(),
            )
            engine_totals[engine] = engine_totals.get(engine, 0.0) + max(0.0, value)

        if engine_totals:
            return min(100.0, max(engine_totals.values()))
        return 0.0 if not instances else None

    def close(self) -> None:
        self._graphics.close()
        self._power.close()
