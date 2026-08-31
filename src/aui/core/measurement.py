"""Per-layout-pass measurement cache."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import RLock

from .geometry import Size
from .view import View

_current_cache: ContextVar["MeasurementCache | None"] = ContextVar(
    "aui_measurement_cache", default=None
)


@dataclass(frozen=True)
class MeasurementStats:
    entries: int
    hits: int
    misses: int

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class MeasurementCache:
    """Memoize ``size_that_fits`` calls for one deterministic layout pass."""

    def __init__(self):
        self._values: dict[tuple[int, float, float], Size] = {}
        self._lock = RLock()
        self.hits = 0
        self.misses = 0

    def measure(self, view: View, proposal: Size) -> Size:
        key = (id(view), proposal.width, proposal.height)
        with self._lock:
            value = self._values.get(key)
            if value is not None:
                self.hits += 1
                return value
            value = view.size_that_fits(proposal)
            if not isinstance(value, Size):
                raise TypeError("size_that_fits must return Size")
            self._values[key] = value
            self.misses += 1
            return value

    def clear(self) -> None:
        with self._lock:
            self._values.clear()
            self.hits = 0
            self.misses = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._values)

    @property
    def stats(self) -> MeasurementStats:
        with self._lock:
            return MeasurementStats(len(self._values), self.hits, self.misses)


def measure(view: View, proposal: Size) -> Size:
    cache = _current_cache.get()
    return cache.measure(view, proposal) if cache is not None else view.size_that_fits(proposal)


@contextmanager
def measurement_context(cache: MeasurementCache):
    if not isinstance(cache, MeasurementCache):
        raise TypeError("measurement_context requires MeasurementCache")
    token = _current_cache.set(cache)
    try:
        yield cache
    finally:
        _current_cache.reset(token)


__all__ = [
    "MeasurementCache", "MeasurementStats", "measure", "measurement_context",
]
