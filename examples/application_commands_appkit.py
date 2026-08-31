"""Top-level native macOS application menus with Commands."""

from aui import (
    CommandMenu, Commands, KeyboardShortcut, Divider, Button, Size, State,
    Text, VStack, Window,
)
from aui.backends.appkit import AppKitApplication


count = State(0)


def make_view():
    return VStack([
        Text("Application Commands"),
        Text(f"Value: {count.value}"),
        Text("Use the Counter menu in the macOS menu bar."),
    ], spacing=16, alignment="leading").padding(length=24)


commands = Commands([
    CommandMenu("Counter", [
        Button("Increment", lambda: count._set(count.value + 1)).keyboard_shortcut(
            KeyboardShortcut("+")
        ),
        Button("Decrement", lambda: count._set(count.value - 1)).keyboard_shortcut(
            KeyboardShortcut("-")
        ),
        Divider(),
        Button("Reset", lambda: count._set(0)).keyboard_shortcut(KeyboardShortcut("0")),
    ]),
])


def main():
    AppKitApplication(
        Window("aUI · Commands", make_view, default_size=Size(560, 360)),
        commands=commands,
    ).run()


if __name__ == "__main__":
    main()
