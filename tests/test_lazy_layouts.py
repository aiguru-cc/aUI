from dataclasses import dataclass

import pytest

from aui import (
    GridItem, LazyHGrid, LazyHStack, LazyVGrid, LazyVStack, Point, Size, Text,
    describe_accessibility,
)
from aui.backends.ascii import AsciiBackend


@dataclass(frozen=True)
class Item:
    id: int
    title: str


ITEMS = [Item(index, f"Item {index}") for index in range(7)]


def test_lazy_stack_defers_builder_until_layout():
    built = []
    stack = LazyVStack(ITEMS, lambda item: built.append(item.id) or Text(item.title), id="id")
    assert built == []
    stack.size_that_fits(Size(300, 500))
    assert built == list(range(7))
    first = stack.children()
    assert stack.children()[0] is first[0]


def test_lazy_horizontal_stack_layout():
    stack = LazyHStack(ITEMS[:3], lambda item: Text(item.title), id="id", spacing=5)
    size = stack.size_that_fits(Size(500, 100))
    assert size.width > 0 and size.height > 0


def test_grid_item_factories_and_validation():
    assert GridItem.fixed(80).kind == "fixed"
    assert GridItem.flexible(60, 180).maximum == 180
    assert GridItem.adaptive(100).kind == "adaptive"
    with pytest.raises(ValueError):
        GridItem("unknown")


def test_lazy_grid_resolves_adaptive_columns_and_rows():
    grid = LazyVGrid(
        ITEMS, [GridItem.adaptive(100)], lambda item: Text(item.title), id="id",
        spacing=10, row_spacing=8,
    )
    widths = grid.column_widths(340)
    assert len(widths) == 3
    size = grid.size_that_fits(Size(340, 500))
    assert size.width == pytest.approx(340)
    assert size.height > 0
    assert describe_accessibility(grid).role == "grid"
    assert "Item 0" in AsciiBackend(width=60, height=6).render(grid)


def test_lazy_hgrid_fills_columns_top_to_bottom():
    grid = LazyHGrid(
        ITEMS[:5], [GridItem.fixed(20), GridItem.flexible(10, 40)],
        lambda item: Text(item.title), id="id", spacing=4, column_spacing=6,
    )
    heights = grid.row_heights(64)
    widths, metric_heights = grid.metrics(Size(400, 64))

    assert heights == pytest.approx([20, 40])
    assert metric_heights == heights
    assert len(widths) == 3
    assert grid.size_that_fits(Size(400, 64)).height == pytest.approx(64)
    assert grid.children()[0] is grid.children()[0]


def test_lazy_hgrid_adaptive_rows_and_ascii_rendering():
    grid = LazyHGrid(
        ITEMS, [GridItem.adaptive(20, 30)], lambda item: Text(item.title),
        id="id", spacing=5,
    )
    assert len(grid.row_heights(70)) == 3
    assert "Item 0" in AsciiBackend(width=60, height=6).render(grid)
    assert describe_accessibility(grid).role == "grid"


def test_lazy_hgrid_validation_and_infinite_height_proposal():
    with pytest.raises(ValueError, match="at least one"):
        LazyHGrid(ITEMS, [], lambda item: Text(item.title))
    grid = LazyHGrid(ITEMS[:2], [GridItem.adaptive(24)], lambda item: Text(item.title))
    assert grid.row_heights(float("inf")) == [24]


def test_grid_item_track_spacing_and_vgrid_alignment():
    grid = LazyVGrid(
        ITEMS[:2],
        [GridItem.fixed(30, spacing=7, alignment="trailing"),
         GridItem.fixed(20, alignment="leading")],
        lambda item: Text(item.title).frame(width=10), id="id",
    )
    assert grid.column_spacings(57) == [7]
    placements = grid.placements(Point(), Size(57, 40))
    assert placements[0][1].x > 0
    assert placements[1][1].x == pytest.approx(37)


def test_hgrid_track_spacing_and_bottom_alignment():
    grid = LazyHGrid(
        ITEMS[:2],
        [GridItem.fixed(20, spacing=9, alignment="bottom"),
         GridItem.fixed(20, alignment="top")],
        lambda item: Text(item.title).frame(height=5), id="id",
    )
    assert grid.row_spacings(49) == [9]
    placements = grid.placements(Point(), Size(100, 49))
    assert placements[0][1].y > 0
    assert placements[1][1].y == pytest.approx(29)


def test_grid_item_rejects_invalid_spacing_and_alignment():
    with pytest.raises(ValueError, match="spacing"):
        GridItem.fixed(20, spacing=-1)
    with pytest.raises(ValueError, match="alignment"):
        GridItem.flexible(alignment="diagonal")
