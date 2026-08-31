"""A lazy Settings scene opened by SettingsLink or Command-comma."""

import os
from pathlib import Path

from aui import (
    AppStorage, JSONStore, Settings, SettingsLink, Size, Text, Toggle, VStack,
    Window, WindowGroup,
)
from appkit_support import run_scenes


data_root = Path(os.environ.get(
    "AUI_EXAMPLE_DATA_DIR",
    Path.home() / ".local" / "share" / "aUI-examples",
))
store = JSONStore(data_root / "aUI Settings Example" / "settings.json")
show_status = AppStorage("show_status", True, store=store)
compact_rows = AppStorage("compact_rows", False, store=store)


def main_view():
    return VStack([
        Text("Workspace"),
        Text("Preferences open in one reusable window."),
        SettingsLink(),
    ], spacing=18, alignment="leading").padding(length=24)


def settings_view():
    return VStack([
        Text("General"),
        Toggle("Show status", is_on=show_status.binding()),
        Toggle("Use compact rows", is_on=compact_rows.binding()),
        Text(f"Saved in {store.path}"),
    ], spacing=16, alignment="leading").padding(length=24)


def main():
    run_scenes(WindowGroup([
        Window("aUI · Workspace", main_view, default_size=Size(620, 420)),
        Settings(settings_view, title="Settings", default_size=Size(520, 340)),
    ]))


if __name__ == "__main__":
    main()
