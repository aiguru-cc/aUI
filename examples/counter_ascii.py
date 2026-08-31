"""Example: a small SwiftUI-style counter app rendered with the headless ASCII backend."""
from aui.backends.ascii import AsciiBackend
from aui.core.components import Button, Text
from aui.core.layout import VStack
from aui.core.state import State


def counter_view(state: State[int]) -> VStack:
    return VStack(
        [
            Text(f"Count: {state.wrapped_value}"),
            Button("Increment", action=lambda: state._set(state.wrapped_value + 1)),
            Button("Reset", action=lambda: state._set(0)),
        ],
        spacing=2,
    )


if __name__ == "__main__":
    state = State(0)
    view = counter_view(state)
    backend = AsciiBackend(width=40, height=10)
    print(backend.render(view))
    print("\n--- after increment ---")
    state._set(3)
    print(backend.render(view))
