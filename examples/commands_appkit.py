"""Native title-bar toolbar, action menu and keyboard shortcuts."""

from aui import (
    KeyboardShortcut, Menu, Button, Size, State, Text, ToolbarItem, VStack,
    Window,
)
from aui.backends.appkit import AppKitApplication

count = State(0)


def change(delta):
    count._set(count.wrapped_value + delta)


def make_view():
    menu = Menu("Actions", [
        Button("Increment", lambda: change(1)).keyboard_shortcut(KeyboardShortcut("+")),
        Button("Reset", lambda: count._set(0)),
        Button("Delete value", lambda: count._set(0), role="destructive"),
    ])
    content = VStack([
        Text("Commands & Toolbar"),
        Text(f"Value: {count.wrapped_value}"),
        menu,
    ], spacing=18, alignment="leading").padding(length=24)
    return content.toolbar([
        ToolbarItem(
            "decrement",
            Button("Decrease", lambda: change(-1)).keyboard_shortcut(KeyboardShortcut("-")),
        ),
        ToolbarItem(
            "increment",
            Button("Increase", lambda: change(1)).keyboard_shortcut(KeyboardShortcut("+")),
            placement="primaryAction",
        ),
    ])


def main():
    AppKitApplication(
        Window("aUI · Commands", make_view, default_size=Size(560, 380))
    ).run()


if __name__ == "__main__":
    main()
