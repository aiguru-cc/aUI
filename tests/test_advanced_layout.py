import pytest

from aui import (
    AnyLayout, HStackLayout, Layout, LayoutPlacement, Point, Rect, Size, Text,
    VStackLayout, ZStack, ZStackLayout,
)
from aui.backends.ascii import AsciiBackend
from aui.backends.appkit import AppKitBackend
from aui.backends.curses import CursesBackend
from aui.core.layout_modifiers import (
    AspectRatioModifier, FixedSizeModifier, IgnoresSafeAreaModifier,
    LayoutPriorityModifier, OffsetModifier, PositionModifier,
    SafeAreaInsetModifier, ZIndexModifier, z_ordered,
)


def test_advanced_layout_chained_modifiers_are_typed():
    assert isinstance(Text("x").layout_priority(2)._modifier, LayoutPriorityModifier)
    assert isinstance(Text("x").fixed_size()._modifier, FixedSizeModifier)
    assert isinstance(Text("x").offset(x=4)._modifier, OffsetModifier)
    assert isinstance(Text("x").position(10, 20)._modifier, PositionModifier)
    assert isinstance(Text("x").z_index(3)._modifier, ZIndexModifier)
    assert isinstance(Text("x").aspect_ratio(2)._modifier, AspectRatioModifier)
    assert isinstance(Text("x").safe_area_inset("top", 8)._modifier,
                      SafeAreaInsetModifier)
    assert isinstance(Text("x").ignores_safe_area()._modifier, IgnoresSafeAreaModifier)


def test_fixed_size_uses_natural_dimensions():
    text = Text("a fairly long label")
    constrained = text.size_that_fits(Size(30, 30))
    fixed = text.fixed_size(horizontal=True, vertical=False).size_that_fits(Size(30, 30))

    assert fixed.width > constrained.width


def test_aspect_ratio_fit_and_fill():
    content = Text("x")
    assert content.aspect_ratio(2, "fit").size_that_fits(Size(100, 100)) == Size(100, 50)
    assert content.aspect_ratio(2, "fill").size_that_fits(Size(100, 100)) == Size(200, 100)
    with pytest.raises(ValueError, match="positive"):
        content.aspect_ratio(0)
    with pytest.raises(ValueError, match="fit or fill"):
        content.aspect_ratio(1, "stretch")


def test_safe_area_inset_changes_size_and_validates_edges():
    base = Text("safe")
    original = base.size_that_fits(Size(200, 100))
    inset = base.safe_area_inset("top", 12).size_that_fits(Size(200, 100))
    assert inset.height == pytest.approx(original.height + 12)
    with pytest.raises(ValueError, match="safe area edge"):
        base.safe_area_inset("center", 4)
    with pytest.raises(ValueError, match="cannot be negative"):
        base.safe_area_inset("top", -1)


def test_offset_changes_ascii_draw_location_without_changing_measurement():
    base = Text("X")
    moved = base.offset(x=4, y=1)
    assert moved.size_that_fits(Size(20, 4)) == base.size_that_fits(Size(20, 4))
    lines = AsciiBackend(width=12, height=3).render(moved).splitlines()
    assert lines[1].startswith("    X")


def test_z_index_orders_equal_layout_siblings_stably():
    back = Text("back").z_index(-1)
    middle = Text("middle")
    front = Text("front").z_index(4)
    ordered = [view for _, view in z_ordered([front, back, middle])]
    assert ordered == [back, middle, front]


def test_hstack_layout_exposes_priority_during_compression():
    low = Text("low priority content").layout_priority(0)
    high = Text("important").layout_priority(10)
    layout = HStackLayout(spacing=0)([low, high])
    placements = layout.placements(Point(), Size(80, 30))

    assert placements[1].subview.priority == 10
    assert placements[1].size.width >= placements[0].size.width
    assert sum(item.size.width for item in placements) == pytest.approx(80)


def test_any_layout_switches_concrete_algorithm():
    children = [Text("A"), Text("B")]
    horizontal = AnyLayout(HStackLayout(spacing=2))(children)
    vertical = AnyLayout(VStackLayout(spacing=2))(children)

    assert horizontal.size_that_fits(Size(200, 200)).width > vertical.size_that_fits(
        Size(200, 200)
    ).width
    assert vertical.size_that_fits(Size(200, 200)).height > horizontal.size_that_fits(
        Size(200, 200)
    ).height


def test_zstack_layout_places_children_and_ascii_renders_custom_container():
    container = ZStackLayout(alignment="topLeading")([Text("Bottom"), Text("Top")])
    placements = container.placements(Point(5, 7), Size(100, 40))
    assert all(item.origin == Point(5, 7) for item in placements)
    assert "Top" in AsciiBackend(width=20, height=3).render(container)


class DiagonalLayout(Layout):
    def size_that_fits(self, proposal, subviews):
        return Size(120, 60)

    def place_subviews(self, bounds, proposal, subviews):
        return [
            LayoutPlacement(subview, Point(bounds.origin.x + index * 20,
                                           bounds.origin.y + index),
                            subview.size_that_fits(Size(40, 20)))
            for index, subview in enumerate(subviews)
        ]


def test_custom_layout_protocol_returns_shared_placements():
    container = DiagonalLayout()([Text("One"), Text("Two")])
    assert container.size_that_fits(Size(300, 200)) == Size(120, 60)
    placements = container.placements(Point(10, 5), Size(120, 60))
    assert placements[0].origin == Point(10, 5)
    assert placements[1].origin == Point(30, 6)
    rendered = CursesBackend(lambda: container).render_to_string(width=40, height=5)
    assert "One" in rendered and "Two" in rendered


def test_layout_api_validation():
    with pytest.raises(TypeError, match="AnyLayout requires"):
        AnyLayout(object())
    with pytest.raises(TypeError, match="View instances"):
        HStackLayout()([Text("ok"), "bad"])


def test_appkit_layout_records_advanced_modifier_and_custom_placements():
    moved_text = Text("Moved")
    moved = moved_text.offset(x=12, y=7)
    backend = AppKitBackend(lambda: moved)
    backend._layout(moved, 200, 80)
    origin, _ = backend._frames[id(moved_text)]
    assert origin == Point(12, 7)

    first = Text("First")
    second = Text("Second")
    custom = DiagonalLayout()([first, second])
    backend._layout(custom, 120, 60)
    assert backend._frames[id(first)][0] == Point(0, 0)
    assert backend._frames[id(second)][0] == Point(20, 1)
