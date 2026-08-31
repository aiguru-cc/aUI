"""Deterministic UI-thread dispatch shared by every backend."""
from __future__ import annotations

from collections import deque
from threading import RLock, get_ident
from typing import Callable, Hashable, Optional


class UIDispatcher:
    """Serialize callbacks onto the thread that owns a backend.

    A native backend may provide ``scheduler`` to enqueue work in its event
    loop. Headless and terminal backends use :meth:`drain` from their loop.
    ``schedule_once`` coalesces repeated invalidations until the callback runs.
    """

    def __init__(self, scheduler: Optional[Callable[[Callable[[], None]], None]] = None):
        self._owner = get_ident()
        self._scheduler = scheduler
        self._queue: deque[Callable[[], None]] = deque()
        self._pending: set[Hashable] = set()
        self._lock = RLock()
        self._closed = False

    @property
    def is_ui_thread(self) -> bool:
        return get_ident() == self._owner

    def adopt_current_thread(self) -> None:
        """Make the calling thread the owner before an event loop starts."""
        with self._lock:
            if self._closed:
                raise RuntimeError("dispatcher is closed")
            if self._queue or self._pending:
                raise RuntimeError("cannot change UI thread while callbacks are pending")
            self._owner = get_ident()

    def dispatch(self, callback: Callable[[], None]) -> bool:
        """Run now on the UI thread, otherwise enqueue for that thread."""
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            if self._closed:
                return False
        if self.is_ui_thread:
            callback()
            return True
        return self._enqueue(callback)

    def schedule_once(self, key: Hashable, callback: Callable[[], None]) -> bool:
        """Enqueue one callback for ``key`` until that callback has run."""
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            if self._closed or key in self._pending:
                return False
            self._pending.add(key)

        def run() -> None:
            with self._lock:
                self._pending.discard(key)
                if self._closed:
                    return
            callback()

        if not self._enqueue(run):
            with self._lock:
                self._pending.discard(key)
            return False
        return True

    def _enqueue(self, callback: Callable[[], None]) -> bool:
        with self._lock:
            if self._closed:
                return False
            scheduler = self._scheduler
            if scheduler is None:
                self._queue.append(callback)
                return True
        try:
            scheduler(callback)
        except Exception:
            return False
        return True

    def drain(self, limit: Optional[int] = None) -> int:
        """Execute queued callbacks in FIFO order on the owning UI thread."""
        if not self.is_ui_thread:
            raise RuntimeError("UI callbacks may only be drained by the owning thread")
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        count = 0
        while limit is None or count < limit:
            with self._lock:
                if self._closed or not self._queue:
                    break
                callback = self._queue.popleft()
            callback()
            count += 1
        return count

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._queue.clear()
            self._pending.clear()
