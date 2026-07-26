from __future__ import annotations

from collections import deque

from winter.telemetry.model import Snapshot


class RecentHistory:
    def __init__(self, duration_seconds: float) -> None:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        self._duration = duration_seconds
        self._samples: deque[Snapshot] = deque()

    def append(self, sample: Snapshot) -> None:
        if self._samples and sample.monotonic_time < self._samples[-1].monotonic_time:
            raise ValueError("samples must be appended in monotonic order")
        self._samples.append(sample)
        cutoff = sample.monotonic_time - self._duration
        while self._samples and self._samples[0].monotonic_time < cutoff:
            self._samples.popleft()

    def __len__(self) -> int:
        return len(self._samples)

    def snapshot(self) -> tuple[Snapshot, ...]:
        return tuple(self._samples)
