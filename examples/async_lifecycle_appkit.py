"""SwiftUI-like task and refreshable async lifecycle."""
import asyncio

from aui import Button, State, TaskHandle, Text, VStack, Window
from appkit_support import run_window


status = State("Waiting")


async def load():
    status.wrapped_value = "Loading…"
    await asyncio.sleep(0.25)
    status.wrapped_value = "Loaded"
    return status.wrapped_value


def content():
    refreshable_content = VStack([
        Text(status.wrapped_value),
        Button("Refresh", lambda: TaskHandle(load).start()),
    ]).refreshable(load)
    return refreshable_content.task(load, task_id="initial", key="initial-load")


if __name__ == "__main__":
    run_window("Async Lifecycle", content, width=500, height=280)
