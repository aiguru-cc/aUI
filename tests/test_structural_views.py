from dataclasses import dataclass

import pytest

from aui import (
    AnyView, EmptyView, ForEach, GroupBox, Size, Text, ViewThatFits,
    describe_accessibility,
)
from aui.backends.ascii import AsciiBackend


@dataclass(frozen=True)
class Item:
    id: int
    title: str


def test_foreach_preserves_view_identity_by_data_id():
    items = [Item(1, "One"), Item(2, "Two")]
    views = ForEach(items, lambda item: Text(item.title), spacing=4)
    first = views.children()
    views.data = [items[1], items[0]]
    second = views.children()
    assert second[0] is first[1]
    assert second[1] is first[0]
    assert views.size_that_fits(Size(300, 200)).height > 0


def test_foreach_validates_identity_and_builder():
    with pytest.raises(ValueError):
        ForEach([{"id": 1}, {"id": 1}], lambda item: Text("x"), id="id")
    with pytest.raises(TypeError):
        ForEach([1], lambda item: "not a view").children()


def test_view_that_fits_selects_first_fitting_candidate():
    wide = Text("This is a long horizontal label")
    compact = Text("Short")
    adaptive = ViewThatFits([wide, compact], axis="horizontal")
    assert adaptive.selected(Size(60, 100)) is compact
    assert adaptive.selected(Size(400, 100)) is wide


def test_empty_any_and_groupbox_semantics():
    empty = EmptyView()
    assert empty.size_that_fits(Size(100, 100)) == Size()
    assert describe_accessibility(empty).hidden
    erased = AnyView(Text("Erased"))
    assert describe_accessibility(erased).label == "Erased"
    group = GroupBox("Settings", Text("Content"))
    assert describe_accessibility(group).role == "group"
    rendered = AsciiBackend(width=40, height=5).render(group)
    assert "Settings" in rendered and "Content" in rendered
