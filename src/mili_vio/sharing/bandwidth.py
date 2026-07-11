"""Bandwidth manager for cooperative sharing (< 50 KB/s per drone)."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass
class BandwidthReport:
    bytes_sent_window: int
    bytes_per_sec: float
    budget_bytes_per_sec: int
    within_budget: bool
    reduction_vs_continuous_pct: float


class BandwidthManager:
    """Token-bucket rate limiter for UDP landmark sharing."""

    def __init__(self, max_bytes_per_sec: int = 51200) -> None:
        self.max_bytes_per_sec = max_bytes_per_sec
        self._window: deque[tuple[float, int]] = deque()
        self._total_sent = 0
        self._continuous_baseline = 0

    def can_send(self, nbytes: int) -> bool:
        self._prune()
        current_rate = sum(b for _, b in self._window)
        return current_rate + nbytes <= self.max_bytes_per_sec

    def record_send(self, nbytes: int, is_event: bool = True) -> None:
        now = time.perf_counter()
        self._window.append((now, nbytes))
        self._total_sent += nbytes
        if not is_event:
            self._continuous_baseline += nbytes

    def record_continuous_baseline(self, nbytes: int) -> None:
        """Track what continuous position sharing would have cost."""
        self._continuous_baseline += nbytes

    def report(self, event_only_bytes: int | None = None) -> BandwidthReport:
        self._prune()
        sent = sum(b for _, b in self._window)
        elapsed = 1.0
        if self._window:
            elapsed = max(time.perf_counter() - self._window[0][0], 0.001)
        rate = sent / elapsed

        baseline = self._continuous_baseline or sent * 3
        event_bytes = event_only_bytes if event_only_bytes is not None else sent
        reduction = (1.0 - event_bytes / baseline) * 100 if baseline > 0 else 0.0

        return BandwidthReport(
            bytes_sent_window=sent,
            bytes_per_sec=rate,
            budget_bytes_per_sec=self.max_bytes_per_sec,
            within_budget=rate <= self.max_bytes_per_sec,
            reduction_vs_continuous_pct=max(reduction, 0.0),
        )

    def _prune(self) -> None:
        cutoff = time.perf_counter() - 1.0
        while self._window and self._window[0][0] < cutoff:
            self._window.popleft()
