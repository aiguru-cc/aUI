"""SwiftUI-style control styling showcase (macOS AppKit)."""
from aui import (
    Button, ButtonStyle, Color, ControlSize, HStack, Label, LabelStyle,
    ProgressView, ProgressViewStyle, Toggle, VStack, Window,
)
from appkit_support import run_window
from aui.core.state import State


enabled = State(True)


def content():
    return VStack([
        Label("Control styles", "paintpalette.fill"),
        HStack([
            Button("Prominent", lambda: None)
            .button_style(ButtonStyle.BORDERED_PROMINENT),
            Button("Plain", lambda: None).button_style(ButtonStyle.PLAIN),
        ]),
        Toggle("Live updates", enabled.binding()),
        ProgressView(0.68, "Progress").progress_view_style(ProgressViewStyle.LINEAR),
        Label("Favorites", "star.fill").label_style(LabelStyle.TITLE_AND_ICON),
    ]).tint(Color.rgb(41, 121, 255)).control_size(ControlSize.LARGE)


if __name__ == "__main__":
    run_window("SwiftUI Styles", content, width=520, height=320)
