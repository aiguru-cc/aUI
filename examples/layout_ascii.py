"""Example: layout containers (VStack / HStack / ZStack / Spacer).

Demonstrates how aUI's layout containers arrange children, using the
headless ASCII backend so the layout is visible without a terminal.

Run:  python3 examples/layout_ascii.py
"""
import _bootstrap  # noqa: F401
from aui.backends.ascii import AsciiBackend
from aui.core.components import Button, Divider, Text
from aui.core.layout import HStack, Spacer, VStack, ZStack
from aui.core.state import State


def main():
    count = State(0)

    # VStack: vertical arrangement, centered by default.
    vstack = VStack(
        [
            Text("VStack (vertical)"),
            Button("Increment", action=lambda: count._set(count.wrapped_value + 1)),
            Text(f"Count: {count.wrapped_value}"),
        ],
        spacing=1,
        alignment="center",
    )

    # HStack with Spacer: pushes content to the edges.
    hstack = HStack(
        [
            Text("Left"),
            Spacer(),
            Text("Right"),
        ],
        spacing=1,
    )

    # ZStack: overlapping layers (back is wider so its edges peek out).
    zstack = ZStack(
        [
            Text("ZStack-back-layer"),
            Text("front"),
        ],
        alignment="center",
    )

    view = VStack(
        [
            vstack,
            Divider(),
            hstack,
            Divider(),
            zstack,
        ],
        spacing=1,
    )

    backend = AsciiBackend(width=44, height=16)
    print(backend.render(view))


if __name__ == "__main__":
    main()
