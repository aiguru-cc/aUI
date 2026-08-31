"""Adaptive SwiftUI-like inspector panel on AppKit."""

from aui import Button, Color, Form, Size, State, Text, TextField, VStack, Window
from aui.backends.appkit import AppKitApplication


show_inspector = State(True)
title = State("Design Review")


def make_view():
    document = VStack([
        Button("Toggle Inspector", lambda: setattr(
            show_inspector, "value", not show_inspector.value
        )),
        Text("Document canvas"),
    ], spacing=18, alignment="leading").padding(length=24)
    properties = Form([
        Text("Inspector"),
        TextField(title.binding(), "Title"),
        Button("Done", lambda: setattr(show_inspector, "value", False)),
    ], spacing=14).padding(length=18)
    return document.inspector(
        show_inspector.binding(), properties, minimum=240, ideal=300, maximum=380
    ).inspector_background(Color(0.95, 0.96, 0.98))


if __name__ == "__main__":
    AppKitApplication(Window(
        "aUI · Inspector", make_view, default_size=Size(920, 620)
    )).run()
