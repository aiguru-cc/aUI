"""Native macOS menu-bar extra scene with SF Symbol and commands."""

from aui import (
    KeyboardShortcut, MenuBarExtra, Divider, Button, Settings,
    SettingsLink, Size, Text, VStack, Window, WindowGroup,
)
from aui.backends.appkit import AppKitApplication


def main_view():
    return VStack([
        Text("Menu Bar Extra"),
        Text("Use the sparkles item in the macOS menu bar."),
        SettingsLink(),
    ], spacing=16, alignment="leading").padding(length=24)


def main():
    app = None

    extra = MenuBarExtra("aUI", [
        Button("Show Main Window", lambda: app.open_window("main")).keyboard_shortcut(
            KeyboardShortcut("1")
        ),
        Button("Settings…", lambda: app.open_settings()).keyboard_shortcut(
            KeyboardShortcut(",")
        ),
        Divider(),
        Button("Hide Main Window", lambda: app.dismiss_window("main")),
    ], system_name="sparkles")

    app = AppKitApplication(WindowGroup([
        Window("aUI · Menu Bar", main_view, id="main", default_size=Size(560, 360)),
        Settings(lambda: Text("Menu bar preferences").padding(length=24)),
        extra,
    ]))
    app.run()


if __name__ == "__main__":
    main()
