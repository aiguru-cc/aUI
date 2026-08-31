"""SwiftUI-like Canvas vector drawing and TimelineView."""
from datetime import datetime, timezone

from aui import (
    Canvas, Color, Path, Point, Rect, Size, StrokeStyle, Text, TimelineView,
    VStack, Window,
)
from appkit_support import run_window


def artwork(context, size):
    bounds = Rect(Point(8, 8), Size(size.width - 16, size.height - 16))
    context.fill(Path.ellipse(bounds), Color.rgb(60, 120, 255, 0.18))
    wave = (Path().move(Point(18, size.height / 2))
            .curve(Point(size.width - 18, size.height / 2),
                   Point(size.width * .32, 10), Point(size.width * .68, size.height - 10)))
    context.stroke(wave, Color.indigo, StrokeStyle(5, "round", "round", dash=(12, 5)))


clock = TimelineView(
    lambda context: Text(context.date.astimezone().strftime("%H:%M:%S")),
    cadence="seconds", date=datetime.now(timezone.utc),
)


def content():
    return VStack([Canvas(artwork, 360, 180), clock])


if __name__ == "__main__":
    run_window("Canvas & Timeline", content, width=520, height=340)
