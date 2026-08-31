"""SwiftUI-like task and refreshable view lifecycles."""
from __future__ import annotations

import asyncio
import inspect
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .view import View, ViewModifier, _ModifiedContent, _apply


class TaskPhase:
    PENDING = "pending"; RUNNING = "running"; SUCCESS = "success"
    FAILURE = "failure"; CANCELLED = "cancelled"


class TaskHandle:
    """A cancellable background task with observable phase and result."""

    def __init__(self, action: Callable[[], Any], priority: str = "userInitiated"):
        if not callable(action): raise TypeError("task action must be callable")
        if priority not in {"high", "userInitiated", "medium", "utility", "low", "background"}:
            raise ValueError(f"unsupported task priority: {priority!r}")
        self.action, self.priority = action, priority
        self.phase, self.result, self.error = TaskPhase.PENDING, None, None
        self._cancelled = False; self._thread = None; self._done = threading.Event()
        self._listeners: list[Callable[["TaskHandle"], None]] = []

    def subscribe(self, listener):
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener) if listener in self._listeners else None

    def _notify(self):
        for listener in list(self._listeners): listener(self)

    def start(self) -> "TaskHandle":
        if self.phase != TaskPhase.PENDING: return self
        self.phase = TaskPhase.RUNNING; self._notify()
        self._thread = threading.Thread(target=self._run, daemon=True, name="aui-task")
        self._thread.start(); return self

    def _run(self):
        try:
            value = self.action()
            if inspect.isawaitable(value): value = asyncio.run(value)
            if self._cancelled: self.phase = TaskPhase.CANCELLED
            else: self.result, self.phase = value, TaskPhase.SUCCESS
        except BaseException as exc:
            if self._cancelled or isinstance(exc, asyncio.CancelledError): self.phase = TaskPhase.CANCELLED
            else: self.error, self.phase = exc, TaskPhase.FAILURE
        finally:
            self._done.set(); self._notify()

    def cancel(self) -> None:
        if self.phase in {TaskPhase.SUCCESS, TaskPhase.FAILURE, TaskPhase.CANCELLED}: return
        self._cancelled = True
        if self.phase == TaskPhase.PENDING:
            self.phase = TaskPhase.CANCELLED; self._done.set(); self._notify()

    @property
    def is_cancelled(self): return self._cancelled
    @property
    def is_done(self): return self.phase in {TaskPhase.SUCCESS, TaskPhase.FAILURE, TaskPhase.CANCELLED}
    def wait(self, timeout=None): self._done.wait(timeout); return self


@dataclass(frozen=True)
class TaskModifier(ViewModifier):
    action: Callable[[], Any]
    task_id: Any = None
    priority: str = "userInitiated"
    key: str = ""
    def __post_init__(self):
        if not callable(self.action): raise TypeError("task action must be callable")
        TaskHandle(self.action, self.priority)  # validate priority
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


class RefreshAction:
    def __init__(self, action: Callable[[], Any]):
        if not callable(action): raise TypeError("refresh action must be callable")
        self.action = action; self.latest: TaskHandle | None = None

    def __call__(self) -> TaskHandle:
        self.latest = TaskHandle(self.action, "userInitiated").start()
        return self.latest

    @property
    def is_refreshing(self): return bool(self.latest and self.latest.phase == TaskPhase.RUNNING)


@dataclass(frozen=True)
class RefreshableModifier(ViewModifier):
    refresh_action: RefreshAction
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def task(view: View, action, task_id=None, priority="userInitiated", key="") -> View:
    return _apply(view, TaskModifier(action, task_id, priority, str(key)))


def refreshable(view: View, action) -> View:
    return _apply(view, RefreshableModifier(RefreshAction(action)))


def refresh(view: View) -> TaskHandle:
    node = view
    while isinstance(node, _ModifiedContent):
        if isinstance(node._modifier, RefreshableModifier): return node._modifier.refresh_action()
        node = node._content
    raise LookupError("view is not refreshable")


def start_tasks(root: View, registry: Optional[Dict[str, tuple[Any, TaskHandle]]] = None,
                on_completion: Optional[Callable[[], None]] = None):
    registry = registry if registry is not None else {}
    for index, node in enumerate(root.flatten()):
        if not isinstance(node, _ModifiedContent) or not isinstance(node._modifier, TaskModifier): continue
        mod = node._modifier; key = mod.key or f"task:{index}:{type(node._content).__name__}"
        current = registry.get(key)
        if current is not None and current[0] == mod.task_id: continue
        if current is not None: current[1].cancel()
        handle = TaskHandle(mod.action, mod.priority)
        if on_completion is not None:
            handle.subscribe(lambda value, callback=on_completion: callback() if value.is_done else None)
        registry[key] = (mod.task_id, handle); handle.start()
    return registry


def cancel_tasks(registry):
    for _, handle in registry.values(): handle.cancel()
