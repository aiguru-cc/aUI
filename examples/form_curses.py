"""Example: a settings form built with aUI (curses backend).

Demonstrates Form, TextField, Toggle, Slider, Stepper, Picker and Button
working together in an interactive terminal UI.

Run:  python3 examples/form_curses.py

Controls:
    Tab / Up / Down : move focus between text fields
    Type            : edit the focused text field
    Backspace       : delete last char
    Enter           : confirm current text field
    q / Q           : quit
"""
from aui.backends.curses import CursesBackend
from aui.core.components import Button, Form, Picker, Slider, Stepper, Text, TextField, Toggle
from aui.core.layout import VStack
from aui.core.state import State


def main():
    name = State("")
    email = State("")
    notify = State(True)
    volume = State(0.7)
    theme = State("System")
    retries = State(3.0)

    def make_view():
        return VStack(
            [
                Text("Settings (q: quit)"),
                Form(
                    [
                        TextField(name.binding(), placeholder="Name"),
                        TextField(email.binding(), placeholder="Email"),
                        Toggle("Notifications", is_on=notify.binding()),
                        Text(f"Volume: {volume.wrapped_value:.0%}"),
                        Slider(value=volume.binding(), in_range=(0.0, 1.0), step=0.1),
                        Stepper("Retries", value=retries.binding(), in_range=(0.0, 10.0), step=1.0),
                        Picker("Theme", selection=theme.binding(), options=["System", "Light", "Dark"]),
                        Button("Save", action=lambda: None),
                    ],
                    spacing=1,
                ),
            ],
            spacing=1,
        )

    CursesBackend(make_view).run()


if __name__ == "__main__":
    main()
