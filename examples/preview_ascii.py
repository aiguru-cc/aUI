"""Example: a complete app previewed headlessly with the ASCII backend.

Renders a full app (settings screen) as plain text with no display, terminal
or GUI required. Great for documentation, CI and quick visual checks.

Run:  python3 examples/preview_ascii.py
"""

from aui.backends.ascii import AsciiBackend
from aui.core.components import Button, Divider, Form, Picker, Slider, Stepper, Text, TextField, Toggle
from aui.core.layout import HStack, VStack
from aui.core.state import State


def main():
    name = State("Ada")
    notify = State(True)
    volume = State(0.6)
    theme = State("Dark")
    retries = State(3.0)

    def make_view():
        return VStack(
            [
                Text("Settings"),
                Form(
                    [
                        TextField(name.binding(), placeholder="Name"),
                        Toggle("Notifications", is_on=notify.binding()),
                        Text(f"Volume: {volume.wrapped_value:.0%}"),
                        Slider(value=volume.binding(), in_range=(0.0, 1.0)),
                        Stepper("Retries", value=retries.binding(), in_range=(0.0, 10.0)),
                        Picker("Theme", selection=theme.binding(), options=["System", "Light", "Dark"]),
                        Divider(),
                        HStack([Button("Save", action=lambda: None), Button("Cancel", action=lambda: None)], spacing=2),
                    ],
                    spacing=1,
                ),
            ],
            spacing=1,
        )

    backend = AsciiBackend(width=46, height=20)
    print(backend.render(make_view()))


if __name__ == "__main__":
    main()
