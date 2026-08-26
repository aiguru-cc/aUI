"""Example: an interactive terminal app built with aUI (curses backend).

Run:  python3 examples/counter_curses.py

Controls:
    Tab / Up / Down : move focus between text fields
    Type            : edit the focused text field
    Backspace       : delete last char
    Enter           : confirm current text field
    q / Q           : quit
"""
import _bootstrap  # noqa: F401
from aui.backends.curses import CursesBackend
from aui.core.components import Button, Slider, Text, TextField, Toggle
from aui.core.layout import VStack
from aui.core.state import State


def main():
    count = State(0)
    name = State("")
    enabled = State(True)
    volume = State(0.5)

    def make_view():
        return VStack(
            [
                Text("aUI terminal demo (q: quit)"),
                Text(f"Count: {count.wrapped_value}"),
                Button("Increment", action=lambda: count._set(count.wrapped_value + 1)),
                Button("Reset", action=lambda: count._set(0)),
                TextField(name.binding(), placeholder="your name"),
                Toggle("Enable", is_on=enabled.binding()),
                Slider(value=volume.binding(), in_range=(0.0, 1.0)),
            ],
            spacing=1,
        )

    CursesBackend(make_view).run()


if __name__ == "__main__":
    main()
