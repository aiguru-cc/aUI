"""Compact SwiftUI-like groups of related native controls."""

from aui import (
    Button, ControlGroup, ControlGroupStyle, ControlSize, Size, Text, VStack,
    Window,
)
from aui.backends.appkit import AppKitApplication


def make_view():
    history = ControlGroup([
        Button("‹", lambda: print("Back")),
        Button("›", lambda: print("Forward")),
    ], label="History").control_group_style(
        ControlGroupStyle.NAVIGATION
    ).control_size(ControlSize.SMALL)
    editing = ControlGroup([
        Button("Bold", lambda: None),
        Button("Italic", lambda: None),
        Button("Underline", lambda: None),
    ], label="Formatting").control_group_style(ControlGroupStyle.AUTOMATIC)
    return VStack([Text("Control Groups"), history, editing],
                  spacing=18, alignment="leading").padding(length=24)


if __name__ == "__main__":
    AppKitApplication(Window(
        "aUI · ControlGroup", make_view, default_size=Size(520, 300)
    )).run()
