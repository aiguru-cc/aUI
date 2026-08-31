"""SwiftUI-inspired application and scene storage property wrappers."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Optional

from .state import State


class MemoryStore(MutableMapping):
    """Thread-safe in-memory key/value storage."""

    def __init__(self, values=None):
        self._values = dict(values or {})
        self._lock = threading.RLock()

    def __getitem__(self, key):
        with self._lock:
            return self._values[key]

    def __setitem__(self, key, value):
        with self._lock:
            self._values[key] = value

    def __delitem__(self, key):
        with self._lock:
            del self._values[key]

    def __iter__(self):
        with self._lock:
            return iter(tuple(self._values))

    def __len__(self):
        with self._lock:
            return len(self._values)


class JSONStore(MutableMapping):
    """A small JSON-backed store using atomic file replacement."""

    def __init__(self, path):
        self.path = Path(path).expanduser()
        self._lock = threading.RLock()
        self._values = self._read()

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read JSON store {self.path}") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON store root must be an object")
        return value

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._values, ensure_ascii=False, indent=2, sort_keys=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def __getitem__(self, key):
        with self._lock:
            return self._values[key]

    def __setitem__(self, key, value):
        with self._lock:
            missing = object()
            previous = self._values.get(key, missing)
            self._values[key] = value
            try:
                self._write()
            except (TypeError, OSError):
                if previous is missing:
                    self._values.pop(key, None)
                else:
                    self._values[key] = previous
                raise

    def __delitem__(self, key):
        with self._lock:
            previous = self._values.pop(key)
            try:
                self._write()
            except (TypeError, OSError):
                self._values[key] = previous
                raise

    def __iter__(self):
        with self._lock:
            return iter(tuple(self._values))

    def __len__(self):
        with self._lock:
            return len(self._values)


_DEFAULT_APP_STORE = MemoryStore()
_SCENE_STORES: dict[str, MemoryStore] = {}


class AppStorage(State):
    """A State value synchronized to a key/value store."""

    def __init__(self, key: str, default: Any, store: Optional[MutableMapping] = None,
                 owner=None):
        if not key:
            raise ValueError("AppStorage key cannot be empty")
        self.key = key
        self.store = store if store is not None else _DEFAULT_APP_STORE
        initial = self.store.get(key, default)
        super().__init__(initial, owner=owner)
        if key not in self.store:
            self.store[key] = default

    @State.wrapped_value.setter
    def wrapped_value(self, value):
        if self._value != value:
            self.store[self.key] = value
            self._value = value
            if self._owner is not None:
                self._owner._invalidate()


class SceneStorage(AppStorage):
    """State retained within one named scene session, but not persisted to disk."""

    def __init__(self, key: str, default: Any, scene_id: str = "main", owner=None):
        if scene_id not in _SCENE_STORES:
            _SCENE_STORES[scene_id] = MemoryStore()
        self.scene_id = scene_id
        super().__init__(key, default, store=_SCENE_STORES[scene_id], owner=owner)


__all__ = ["AppStorage", "JSONStore", "MemoryStore", "SceneStorage"]
