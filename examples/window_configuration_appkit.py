"""SwiftUI-like native window configuration."""

from aui import (
    Point, Size, Text, Window, WindowGroup, WindowLevel, WindowResizability,
    WindowStyle,
)
from aui.backends.appkit import AppKitApplication


scenes = WindowGroup([
    Window(
        "Workspace", Text("Main workspace").padding(length=24),
        default_size=Size(720, 480), min_size=Size(520, 320),
        restoration_id="workspace-frame",
    ),
    Window(
        "Floating Inspector", Text("Inspector").padding(length=20), id="inspector",
        default_size=Size(320, 260), default_position=Point(80, 120),
        window_resizability=WindowResizability.CONTENT_SIZE,
        style=WindowStyle.HIDDEN_TITLE_BAR, level=WindowLevel.FLOATING,
    ),
])


if __name__ == "__main__":
    AppKitApplication(scenes).run()
