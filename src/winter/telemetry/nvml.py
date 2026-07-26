from __future__ import annotations

import ctypes
from ctypes import POINTER, Structure, byref, c_int, c_uint, c_ulonglong, c_void_p
from dataclasses import dataclass
import logging
from typing import Any


log = logging.getLogger(__name__)
_SUCCESS = 0
_TEMPERATURE_GPU = 0


def _first_symbol(library: Any, *names: str):
    for name in names:
        try:
            return getattr(library, name)
        except AttributeError:
            continue
    raise AttributeError(f"NVML does not export any of: {', '.join(names)}")


class _Memory(Structure):
    _fields_ = [
        ("total", c_ulonglong),
        ("free", c_ulonglong),
        ("used", c_ulonglong),
    ]


@dataclass(frozen=True, slots=True)
class NvidiaMemory:
    used: int | None
    total: int | None


@dataclass(frozen=True, slots=True)
class NvidiaSensors:
    watts: float | None
    celsius: float | None


class NvidiaMonitor:
    def __init__(self) -> None:
        self._library = None
        self._devices: tuple[c_void_p, ...] = ()
        self._retry_at = 0.0

    def memory(self, now: float) -> NvidiaMemory:
        if self._library is None and not self._connect(now):
            return NvidiaMemory(None, None)

        used: list[int] = []
        totals: list[int] = []
        for device in self._devices:
            memory = _Memory()
            if self._library.nvmlDeviceGetMemoryInfo(device, byref(memory)) == _SUCCESS:
                used.append(int(memory.used))
                totals.append(int(memory.total))
        return NvidiaMemory(
            used=sum(used) if used else None,
            total=sum(totals) if totals else None,
        )

    def sensors(self, now: float) -> NvidiaSensors:
        if self._library is None and not self._connect(now):
            return NvidiaSensors(None, None)

        powers: list[float] = []
        temperatures: list[float] = []
        for device in self._devices:
            milliwatts = c_uint()
            if (
                self._library.nvmlDeviceGetPowerUsage(device, byref(milliwatts))
                == _SUCCESS
            ):
                powers.append(milliwatts.value / 1000.0)

            temperature = c_uint()
            if (
                self._library.nvmlDeviceGetTemperature(
                    device, _TEMPERATURE_GPU, byref(temperature)
                )
                == _SUCCESS
            ):
                temperatures.append(float(temperature.value))

        return NvidiaSensors(
            watts=sum(powers) if powers else None,
            celsius=max(temperatures) if temperatures else None,
        )

    def _connect(self, now: float) -> bool:
        if now < self._retry_at:
            return False
        self._retry_at = now + 30.0
        library = None
        initialized = False
        try:
            library = ctypes.WinDLL("nvml.dll")
            initialize = _first_symbol(library, "nvmlInit_v2", "nvmlInit")
            get_count = _first_symbol(
                library,
                "nvmlDeviceGetCount_v2",
                "nvmlDeviceGetCount",
            )
            get_handle = _first_symbol(
                library,
                "nvmlDeviceGetHandleByIndex_v2",
                "nvmlDeviceGetHandleByIndex",
            )

            initialize.argtypes = []
            initialize.restype = c_int
            library.nvmlShutdown.argtypes = []
            library.nvmlShutdown.restype = c_int
            get_count.argtypes = [POINTER(c_uint)]
            get_count.restype = c_int
            get_handle.argtypes = [c_uint, POINTER(c_void_p)]
            get_handle.restype = c_int
            library.nvmlDeviceGetPowerUsage.argtypes = [c_void_p, POINTER(c_uint)]
            library.nvmlDeviceGetPowerUsage.restype = c_int
            library.nvmlDeviceGetTemperature.argtypes = [
                c_void_p,
                c_uint,
                POINTER(c_uint),
            ]
            library.nvmlDeviceGetTemperature.restype = c_int
            library.nvmlDeviceGetMemoryInfo.argtypes = [c_void_p, POINTER(_Memory)]
            library.nvmlDeviceGetMemoryInfo.restype = c_int

            if initialize() != _SUCCESS:
                return False
            initialized = True
            count = c_uint()
            if get_count(byref(count)) != _SUCCESS or count.value == 0:
                return False
            devices: list[c_void_p] = []
            for index in range(count.value):
                handle = c_void_p()
                if get_handle(index, byref(handle)) == _SUCCESS:
                    devices.append(handle)
            if not devices:
                return False
            self._library = library
            self._devices = tuple(devices)
            log.info("NVML connected to %d NVIDIA device(s)", len(devices))
            return True
        except (AttributeError, ctypes.ArgumentError, OSError) as error:
            log.info("NVML unavailable: %s", error)
            return False
        finally:
            if initialized and self._library is None and library is not None:
                library.nvmlShutdown()

    def close(self) -> None:
        if self._library is not None:
            try:
                self._library.nvmlShutdown()
            finally:
                self._library = None
                self._devices = ()
