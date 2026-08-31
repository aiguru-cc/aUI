"""Native keyboard shortcuts, default focus, and key handling."""

from aui import (
    Button, FocusState, Font, KeyboardShortcut, Size, State, Text, TextField,
    VStack, Window,
)
from aui.backends.appkit import AppKitApplication


name = State("")
focus = FocusState(None)


def make_view():
    return VStack([
        Text("Keyboard & Focus").font(Font.title()),
        TextField(name.binding(), "Name").focused(
            focus.binding(), equals="name"
        ).default_focus(focus.binding(), equals="name"),
        Button("Save", lambda: print(f"Saved {name.value}"))
        .keyboard_shortcut(KeyboardShortcut.default_action()),
        Button("Cancel", lambda: print("Cancelled"))
        .keyboard_shortcut(KeyboardShortcut.cancel_action()),
    ], spacing=14, alignment="leading").padding(length=24).focus_section("editor")


if __name__ == "__main__":
    AppKitApplication(Window(
        "aUI · Keyboard", make_view, default_size=Size(460, 280)
    )).run()
