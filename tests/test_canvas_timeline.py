from datetime import datetime, timezone

import pytest

from aui import (
    Canvas, Color, GraphicsContext, Path, Point, Rect, Size, StrokeStyle,
    Text, TimelineView,
)
from aui.backends.ascii import AsciiBackend


def test_path_records_vector_commands():
    path = (Path().move(Point(0, 0)).line(Point(10, 0))
            .quad_curve(Point(20, 10), Point(15, 0))
            .curve(Point(30, 0), Point(22, 10), Point(28, 10)).close())
    assert [command[0] for command in path.commands] == [
        "move", "line", "quad", "curve", "close"
    ]


def test_path_shape_factories():
    rect = Rect(Point(1, 2), Size(30, 40))
    assert Path.rectangle(rect).commands == [("rect", rect)]
    assert Path.ellipse(rect).commands == [("ellipse", rect)]


def test_graphics_context_records_fill_and_stroke_with_opacity():
    context = GraphicsContext()
    context.opacity = 0.5
    path = Path.rectangle(Rect(Point(), Size(20, 20)))
    context.fill(path, Color.red)
    context.stroke(path, Color.blue, StrokeStyle(2, "round", "bevel", dash=(3, 2)))
    assert [item.operation for item in context.commands] == ["fill", "stroke"]
    assert context.commands[0].color.alpha == pytest.approx(0.5)
    assert context.commands[1].style.dash == (3, 2)


def test_stroke_style_validation():
    with pytest.raises(ValueError): StrokeStyle(-1)
    with pytest.raises(ValueError): StrokeStyle(line_cap="triangle")
    with pytest.raises(ValueError): StrokeStyle(line_join="curve")


def test_canvas_resolves_at_proposed_size():
    seen = []
    canvas = Canvas(lambda context, size: (
        seen.append(size), context.fill(Path.ellipse(Rect(Point(), size)), Color.green)
    ), width=100, height=80)
    assert canvas.size_that_fits(Size(60, 200)) == Size(60, 80)
    context = canvas.resolve(Size(60, 80))
    assert seen == [Size(60, 80)]
    assert len(context.commands) == 1


def test_canvas_ascii_summary():
    canvas = Canvas(lambda context, size: context.fill(
        Path.rectangle(Rect(Point(), size)), Color.orange
    ))
    assert "canvas 1 commands" in AsciiBackend(30, 2).render(canvas)


def test_timeline_view_is_deterministic_and_tickable():
    first = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    second = datetime(2026, 1, 2, 3, 5, tzinfo=timezone.utc)
    timeline = TimelineView(lambda context: Text(context.date.strftime("%H:%M")),
                            cadence="minutes", date=first)
    assert timeline.content.content == "03:04"
    assert timeline.tick(second).content == "03:05"
    assert "03:05" in AsciiBackend(20, 2).render(timeline)


def test_timeline_validation():
    with pytest.raises(ValueError): TimelineView(lambda context: Text("x"), cadence="daily")
    with pytest.raises(TypeError): TimelineView(lambda context: "not a view")
