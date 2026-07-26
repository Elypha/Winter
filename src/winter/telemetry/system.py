from __future__ import annotations

from dataclasses import dataclass
import socket
import time

import psutil


_MAX_PLAUSIBLE_RATE = 12_500_000_000.0


def resolve_default_network_interface() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("1.1.1.1", 9))
            local_address = probe.getsockname()[0]
    except OSError:
        return None

    for name, addresses in psutil.net_if_addrs().items():
        if any(
            address.family == socket.AF_INET and address.address == local_address
            for address in addresses
        ):
            return name
    return None


@dataclass(frozen=True, slots=True)
class TransferRates:
    upload: float
    download: float


@dataclass(frozen=True, slots=True)
class HostLoad:
    cpu_percent: float | None
    memory_used: int
    memory_total: int


class DefaultRoute:
    def __init__(self, cache_seconds: float = 15.0) -> None:
        self._cache_seconds = cache_seconds
        self._interface: str | None = None
        self._refresh_at = 0.0

    def interface(self, now: float) -> str | None:
        if now < self._refresh_at:
            return self._interface
        self._refresh_at = now + self._cache_seconds
        self._interface = resolve_default_network_interface()
        return self._interface


class NetworkMeter:
    def __init__(self) -> None:
        self._route = DefaultRoute()
        self._interface: str | None = None
        self._sent = 0
        self._received = 0
        self._observed_at: float | None = None

    def read(
        self,
        now: float,
        adapter_selection: str,
        adapter_name: str | None,
    ) -> TransferRates:
        interface = (
            self._route.interface(now)
            if adapter_selection == "automatic"
            else adapter_name
        )
        counters = psutil.net_io_counters(pernic=True, nowrap=True)
        current = counters.get(interface) if interface is not None else None

        if current is None:
            self._reset(interface)
            return TransferRates(0.0, 0.0)

        if self._interface != interface or self._observed_at is None:
            self._baseline(interface, current.bytes_sent, current.bytes_recv, now)
            return TransferRates(0.0, 0.0)

        elapsed = now - self._observed_at
        sent = current.bytes_sent - self._sent
        received = current.bytes_recv - self._received
        self._baseline(interface, current.bytes_sent, current.bytes_recv, now)

        if elapsed <= 0 or elapsed > 10.0:
            return TransferRates(0.0, 0.0)
        return TransferRates(
            upload=self._rate(sent, elapsed),
            download=self._rate(received, elapsed),
        )

    @staticmethod
    def _rate(delta: int, elapsed: float) -> float:
        if delta < 0:
            return 0.0
        value = delta / elapsed
        return value if value <= _MAX_PLAUSIBLE_RATE else 0.0

    def _baseline(self, interface: str, sent: int, received: int, now: float) -> None:
        self._interface = interface
        self._sent = sent
        self._received = received
        self._observed_at = now

    def _reset(self, interface: str | None) -> None:
        self._interface = interface
        self._sent = 0
        self._received = 0
        self._observed_at = None


class HostMeter:
    def __init__(self) -> None:
        psutil.cpu_percent(interval=None)
        self._cpu_ready_at = time.monotonic() + 0.1

    def read(self, now: float) -> HostLoad:
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        return HostLoad(
            cpu_percent=float(cpu) if now >= self._cpu_ready_at else None,
            memory_used=int(memory.used),
            memory_total=int(memory.total),
        )
