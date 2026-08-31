"""Asynchronous remote images with SwiftUI-style loading phases."""
from __future__ import annotations

import threading
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

from .geometry import Point, Size
from .view import View


@dataclass(frozen=True)
class AsyncImagePhase:
    state: str = "empty"
    data: Optional[bytes] = None
    error: Optional[Exception] = None

    EMPTY = "empty"
    SUCCESS = "success"
    FAILURE = "failure"

    @property
    def is_empty(self) -> bool:
        return self.state == self.EMPTY

    @property
    def is_success(self) -> bool:
        return self.state == self.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self.state == self.FAILURE


_CACHE: dict[str, bytes] = {}
_INFLIGHT: dict[str, list["AsyncImage"]] = {}
_LOCK = threading.RLock()


def _default_loader(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "aUI/0.1 AsyncImage"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read()


class AsyncImage(View):
    """Load an image URL without blocking the native application event loop."""

    def __init__(self, url: str, size: Size = Size(120.0, 120.0),
                 loader: Optional[Callable[[str], bytes]] = None,
                 use_cache: bool = True):
        if not isinstance(url, str) or not url.strip():
            raise ValueError("AsyncImage url cannot be empty")
        if loader is not None and not callable(loader):
            raise TypeError("AsyncImage loader must be callable")
        self.url = url.strip()
        self.image_size = size
        self.loader = loader or _default_loader
        self.use_cache = bool(use_cache)
        self.phase = AsyncImagePhase()
        self._listeners: set[Callable[[AsyncImagePhase], None]] = set()
        self._started = False
        self._children = []
        if self.use_cache:
            with _LOCK:
                cached = _CACHE.get(self.url)
            if cached is not None:
                self.phase = AsyncImagePhase(AsyncImagePhase.SUCCESS, cached)

    def size_that_fits(self, proposal: Size) -> Size:
        return self.image_size

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self):
        return self._children

    def subscribe(self, listener: Callable[[AsyncImagePhase], None]) -> Callable[[], None]:
        if not callable(listener):
            raise TypeError("AsyncImage listener must be callable")
        self._listeners.add(listener)
        return lambda: self._listeners.discard(listener)

    def _finish(self, phase: AsyncImagePhase) -> None:
        self.phase = phase
        for listener in tuple(self._listeners):
            listener(phase)

    def load(self) -> AsyncImagePhase:
        """Load immediately in the caller, primarily for tests and custom workers."""
        try:
            data = self.loader(self.url)
            if not isinstance(data, (bytes, bytearray, memoryview)) or not data:
                raise ValueError("AsyncImage loader must return non-empty bytes")
            payload = bytes(data)
            if self.use_cache:
                with _LOCK:
                    _CACHE[self.url] = payload
            phase = AsyncImagePhase(AsyncImagePhase.SUCCESS, payload)
        except Exception as exc:
            phase = AsyncImagePhase(AsyncImagePhase.FAILURE, error=exc)
        self._finish(phase)
        return phase

    def start(self) -> None:
        if not self.phase.is_empty or self._started:
            return
        self._started = True
        if self.loader is not _default_loader or not self.use_cache:
            threading.Thread(target=self.load, daemon=True, name="aui-async-image").start()
            return
        with _LOCK:
            waiting = _INFLIGHT.get(self.url)
            if waiting is not None:
                waiting.append(self)
                return
            _INFLIGHT[self.url] = [self]

        def load_shared() -> None:
            phase = self.load()
            with _LOCK:
                images = _INFLIGHT.pop(self.url, [self])
            for image in images:
                if image is not self:
                    image._finish(phase)

        threading.Thread(target=load_shared, daemon=True, name="aui-async-image").start()

    @staticmethod
    def clear_cache(url: Optional[str] = None) -> None:
        with _LOCK:
            if url is None:
                _CACHE.clear()
            else:
                _CACHE.pop(url, None)


__all__ = ["AsyncImage", "AsyncImagePhase"]
