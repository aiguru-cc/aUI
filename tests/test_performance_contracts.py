"""Deterministic complexity guards; timings are intentionally not asserted."""

from aui import GridItem, LazyHGrid, LazyHStack, LazyVGrid, LazyVStack, List, Size, State, Text
from aui.backends import standard as standard_module
from aui.backends.standard import StandardBackend


def test_large_list_visible_window_is_bounded():
    offset = State(50_000)
    view = List([Text(str(index)) for index in range(100_000)],
                scroll_offset=offset.binding(), row_height=24, spacing=2)
    visible = view.visible_rows(viewport_height=600, proposal_width=800)
    assert len(visible) <= 25
    assert visible[0].display_content == "50000"


def test_large_list_scroll_does_not_copy_or_rebuild_rows():
    rows = [Text(str(index)) for index in range(10_000)]
    view = List(rows, row_height=20)
    original_ids = tuple(map(id, view.rows))
    view.scroll_to(9_000)
    assert tuple(map(id, view.rows)) == original_ids
    assert view.visible_rows(200, 400)[0] is rows[9_000]


def test_unfixed_row_height_list_measurement_is_bounded_to_first_row():
    calls = []

    class CountingText(Text):
        def size_that_fits(self, proposal):
            calls.append(proposal)
            return super().size_that_fits(proposal)

    rows = [CountingText(str(index)) for index in range(100_000)]
    view = List(rows)
    measured = view.size_that_fits(Size(800, float("inf")))

    assert measured.height > 0
    assert len(calls) <= 2


def test_standard_reconciliation_does_not_snapshot_virtual_list(monkeypatch):
    view = List([Text(str(index)) for index in range(10_000)], row_height=20)
    monkeypatch.setattr(standard_module, "snapshot",
                        lambda _view: (_ for _ in ()).throw(AssertionError("snapshot traversed list")))
    backend = StandardBackend(lambda: view)
    assert backend._update_widget_tree(view, view, {}) is False


def test_lazy_stacks_build_only_visible_ranges():
    data = range(100_000)
    vertical_built = []
    horizontal_built = []
    vertical = LazyVStack(data, lambda value: vertical_built.append(value) or Text(str(value)))
    horizontal = LazyHStack(data, lambda value: horizontal_built.append(value) or Text(str(value)))
    start_v, visible_v = vertical.visible_children(50_000 * 38, 600, item_extent=30)
    start_h, visible_h = horizontal.visible_children(40_000 * 88, 800, item_extent=80)
    assert start_v <= 50_000 < start_v + len(visible_v)
    assert start_h <= 40_000 < start_h + len(visible_h)
    assert len(vertical_built) < 30
    assert len(horizontal_built) < 20


def test_lazy_grids_build_only_visible_tracks():
    data = range(100_000)
    vertical_built = []
    horizontal_built = []
    vertical = LazyVGrid(data, [GridItem.fixed(100)] * 4,
                         lambda value: vertical_built.append(value) or Text(str(value)))
    horizontal = LazyHGrid(data, [GridItem.fixed(30)] * 3,
                           lambda value: horizontal_built.append(value) or Text(str(value)))
    _, visible_v = vertical.visible_children(10_000, 600, 460, row_extent=40)
    _, visible_h = horizontal.visible_children(10_000, 800, 120, column_extent=120)
    assert len(visible_v) == len(vertical_built) < 80
    assert len(visible_h) == len(horizontal_built) <= 33
