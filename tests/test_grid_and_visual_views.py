import pytest

from aui import (
    Circle, Color, ContentUnavailableView, Grid, GridRow, LabeledContent,
    Rectangle, RoundedRectangle, Size, Text, describe_accessibility,
)
from aui.backends.ascii import AsciiBackend


def test_grid_aligns_columns_across_rows():
    grid = Grid([
        GridRow([Text("A"), Text("long value")]),
        GridRow([Text("long label"), Text("B")]),
    ], horizontal_spacing=10, vertical_spacing=6)
    columns, heights = grid.metrics(Size(500, 300))
    assert len(columns) == 2
    assert columns[0] > Text("A").size_that_fits(Size(500, 300)).width
    measured = grid.size_that_fits(Size(500, 300))
    assert measured.width == pytest.approx(sum(columns) + 10)
    assert measured.height == pytest.approx(sum(heights) + 6)


def test_grid_rejects_non_rows():
    with pytest.raises(TypeError):
        Grid([Text("not a row")])


def test_shapes_support_swiftui_style_fill_and_stroke():
    circle = Circle(size=Size(60, 40)).fill(Color.blue).stroke(Color.white, 2)
    assert circle.size_that_fits(Size(100, 100)) == Size(40, 40)
    assert circle.fill_color is Color.blue
    assert circle.stroke_color is Color.white
    rounded = RoundedRectangle(corner_radius=14).fill(Color.indigo)
    assert rounded.corner_radius_value == 14


def test_labeled_and_unavailable_views_are_semantic_containers():
    labeled = LabeledContent("Version", "1.0")
    assert len(labeled.children()) == 2
    unavailable = ContentUnavailableView("No results", "magnifyingglass", "Try another term")
    info = describe_accessibility(unavailable)
    assert info.role == "group"
    assert info.label == "No results"
    assert len(info.children) == 3


def test_ascii_grid_and_shapes_render():
    view = Grid([GridRow([Rectangle(), Circle(), RoundedRectangle()])])
    rendered = AsciiBackend(width=30, height=3).render(view)
    assert "□" in rendered and "○" in rendered and "▢" in rendered
