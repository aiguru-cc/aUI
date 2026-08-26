"""Example: a gallery of every aUI component (curses backend).

Demonstrates Text, Button, TextField, Toggle, Slider, Picker, Stepper,
ProgressView, Divider, Image, List and NavigationStack together.

Run:  python3 examples/gallery_curses.py

Controls:
    Tab / Up / Down : move focus between text fields
    Type            : edit the focused text field
    Backspace       : delete last char
    Enter           : confirm current text field
    q / Q           : quit
"""
import _bootstrap  # noqa: F401
from aui.backends.curses import CursesBackend
from aui.core.components import (
    Button,
    Divider,
    Image,
    List,
    NavigationStack,
    Picker,
    ProgressView,
    Slider,
    Stepper,
    Text,
    TextField,
    Toggle,
)
from aui.core.layout import HStack, VStack
from aui.core.state import State


def main():
    text = State("")
    flag = State(True)
    level = State(0.6)
    pick = State("B")
    qty = State(2.0)

    def make_view():
        return NavigationStack(
            "Component Gallery",
            VStack(
                [
                    Text("Text component", font=None),
                    Button("Button", action=lambda: None),
                    TextField(text.binding(), placeholder="TextField"),
                    Toggle("Toggle", is_on=flag.binding()),
                    Text(f"Slider: {level.wrapped_value:.0%}"),
                    Slider(value=level.binding(), in_range=(0.0, 1.0)),
                    Stepper("Stepper", value=qty.binding(), in_range=(0.0, 10.0), step=1.0),
                    Picker("Picker", selection=pick.binding(), options=["A", "B", "C"]),
                    ProgressView(value=0.75, label="ProgressView"),
                    Divider(),
                    HStack([Image(system_name="star"), Text("Image + HStack")], spacing=1),
                    List([Text("List row 1"), Text("List row 2")]),
                ],
                spacing=1,
            ),
        )

    CursesBackend(make_view).run()


if __name__ == "__main__":
    main()
