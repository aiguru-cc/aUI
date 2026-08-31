"""AppStorage, SceneStorage and an explicit JSON persistence example."""

import os
from pathlib import Path

from aui import AppStorage, Font, JSONStore, LabeledContent, SceneStorage, Text, TextField, Toggle, VStack
from appkit_support import run_window


data_root = Path(os.environ.get(
    "AUI_EXAMPLE_DATA_DIR",
    Path.home() / ".local" / "share" / "aUI-examples",
))
settings_path = data_root / "aUI Storage Example" / "settings.json"
settings = JSONStore(settings_path)
display_name = AppStorage("display_name", "Guest", store=settings)
show_tips = AppStorage("show_tips", True, store=settings)
draft = SceneStorage("draft", "", scene_id="editor")


def make_view():
    return VStack([
        Text("Persistent Settings").font(Font.title()),
        LabeledContent("Display name", TextField(display_name.binding(), placeholder="Name")),
        Toggle("Show helpful tips", is_on=show_tips.binding()),
        Text("Scene Draft").font(Font.headline()),
        TextField(draft.binding(), placeholder="Kept for this scene session"),
        Text(f"Saved in {settings_path}"),
    ], spacing=14, alignment="leading").padding(length=24)


if __name__ == "__main__":
    run_window("Storage", make_view, width=560, height=330)
