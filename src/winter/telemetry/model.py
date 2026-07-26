from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class Snapshot:
    captured_at: datetime
    monotonic_time: float
    upload_bytes_per_second: float = 0.0
    download_bytes_per_second: float = 0.0
    cpu_percent: float | None = None
    cpu_watts: float | None = None
    memory_used_bytes: int | None = None
    memory_total_bytes: int | None = None
    gpu_percent: float | None = None
    gpu_watts: float | None = None
    gpu_celsius: float | None = None
    vram_used_bytes: int | None = None
    vram_total_bytes: int | None = None

    @classmethod
    def empty(cls, monotonic_time: float = 0.0) -> "Snapshot":
        return cls(
            captured_at=datetime.now(UTC),
            monotonic_time=monotonic_time,
        )
