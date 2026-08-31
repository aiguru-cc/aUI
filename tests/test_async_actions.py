import asyncio
import threading

import pytest

from aui import (
    RefreshAction, TaskHandle, TaskPhase, Text, VStack,
)
from aui.core.async_actions import cancel_tasks, refresh, start_tasks


def test_task_handle_runs_sync_action_and_notifies():
    phases = []
    handle = TaskHandle(lambda: 42)
    handle.subscribe(lambda task: phases.append(task.phase))
    handle.start().wait(1)
    assert handle.phase == TaskPhase.SUCCESS and handle.result == 42
    assert phases == [TaskPhase.RUNNING, TaskPhase.SUCCESS]


def test_task_handle_runs_async_action():
    async def work():
        await asyncio.sleep(0)
        return "done"
    handle = TaskHandle(work).start().wait(1)
    assert handle.phase == TaskPhase.SUCCESS and handle.result == "done"


def test_task_failure_is_captured():
    def fail(): raise RuntimeError("boom")
    handle = TaskHandle(fail).start().wait(1)
    assert handle.phase == TaskPhase.FAILURE
    assert isinstance(handle.error, RuntimeError)


def test_running_task_can_be_cancelled_cooperatively():
    release = threading.Event()
    handle = TaskHandle(lambda: release.wait(1) or "late").start()
    handle.cancel(); release.set(); handle.wait(1)
    assert handle.phase == TaskPhase.CANCELLED and handle.is_cancelled


def test_task_priority_validation():
    with pytest.raises(ValueError): TaskHandle(lambda: None, "immediate")
    with pytest.raises(TypeError): TaskHandle(None)


def test_start_tasks_reuses_same_id_and_restarts_changed_id():
    calls = []
    first = Text("A").task(lambda: calls.append("one"), task_id=1, key="loader")
    registry = start_tasks(first)
    registry["loader"][1].wait(1)
    start_tasks(first, registry)
    assert calls == ["one"]

    second = Text("A").task(lambda: calls.append("two"), task_id=2, key="loader")
    start_tasks(second, registry)
    registry["loader"][1].wait(1)
    assert calls == ["one", "two"]


def test_multiple_unkeyed_tasks_use_tree_positions():
    calls = []
    root = VStack([
        Text("A").task(lambda: calls.append("A")),
        Text("B").task(lambda: calls.append("B")),
    ])
    registry = start_tasks(root)
    for _, handle in registry.values(): handle.wait(1)
    assert sorted(calls) == ["A", "B"]
    assert len(registry) == 2


def test_refreshable_action_and_helper():
    calls = []
    view = Text("Inbox").refreshable(lambda: calls.append("refresh") or 7)
    handle = refresh(view).wait(1)
    assert calls == ["refresh"] and handle.result == 7
    with pytest.raises(LookupError): refresh(Text("plain"))


def test_refresh_action_reports_running_and_latest():
    release = threading.Event()
    action = RefreshAction(lambda: release.wait(1))
    handle = action()
    assert action.latest is handle and action.is_refreshing
    release.set(); handle.wait(1)
    assert not action.is_refreshing


def test_cancel_tasks_cancels_registry():
    handles = {"a": (1, TaskHandle(lambda: None))}
    cancel_tasks(handles)
    assert handles["a"][1].phase == TaskPhase.CANCELLED
