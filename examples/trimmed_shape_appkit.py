"""SwiftUI-style trimmed shape used as a native circular progress ring."""
from aui import Circle, Color, Size, StrokeStyle, Text, VStack, Window, ZStack
from appkit_support import run_window


progress = 0.72


def content():
    track = Circle(size=Size(150, 150)).stroke(Color.gray, line_width=14)
    value = Circle(size=Size(150, 150)).trim(0, progress).stroke(
        Color.blue, style=StrokeStyle(14, "round", "round")
    )
    return VStack([
        Text("Trimmed Shape"),
        ZStack([track, value, Text(f"{progress:.0%}")]),
    ], spacing=18)


if __name__ == "__main__":
    run_window("Shape Progress", content, width=320, height=270)
