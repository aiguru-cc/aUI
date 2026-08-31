"""Native asymmetric corners and inset strokes."""
from aui import (
    Color, HStack, Rectangle, Size, StrokeStyle, Text, UnevenRoundedRectangle,
    VStack, Window,
)
from appkit_support import run_window


def content():
    asymmetric = UnevenRoundedRectangle(
        top_leading=28,
        top_trailing=8,
        bottom_leading=8,
        bottom_trailing=28,
        size=Size(180, 110),
    ).fill(Color.blue).stroke_border(
        Color.white, style=StrokeStyle(4, "round", "round", dash=(10, 4))
    )
    inset_border = Rectangle(size=Size(180, 110)).fill(Color.clear).stroke_border(
        Color.teal, 8
    )
    return VStack([
        Text("Insettable Shapes"),
        HStack([asymmetric, inset_border], spacing=24),
    ], spacing=18)


if __name__ == "__main__":
    run_window("Uneven Shapes", content, width=460, height=240)
