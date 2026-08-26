"""Example: an interactive Tkinter app built with aUI (SwiftUI-style).

Run:  python3 examples/counter_tk.py

The Tk backend uses incremental (diff) rendering (ADR-0004): calling
``backend.render(make_view())`` again reuses existing widgets and only updates
the changed ones, so focus/scroll position is preserved and there is no
flicker.
"""
import _bootstrap  # noqa: F401
from aui.backends.tk import TkBackend
from aui.core.components import Button, Text
from aui.core.layout import VStack
from aui.core.state import State


def main():
    state = State(0)

    def make_view():
        return VStack(
            [
                Text(f"Count: {state.wrapped_value}"),
                Button("Increment", action=lambda: state._set(state.wrapped_value + 1)),
                Button("Reset", action=lambda: state._set(0)),
            ],
            spacing=8,
        )

    backend = TkBackend()
    backend.render(make_view())

    def on_state_change():
        backend.render(make_view())

    state._owner = type("Owner", (), {"_invalidate": on_state_change})()
    backend.mainloop()


if __name__ == "__main__":
    main()
