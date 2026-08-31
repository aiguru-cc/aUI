import pytest

from aui import (
    EdgeInsets, ScrollIndicatorVisibility, ScrollTargetBehavior, Size, State, Text,
)
from aui.core.scrolling import find_scroll_configuration, scroll_configuration


def test_scroll_configuration_collects_chained_options():
    position = State("row-20")
    view = (
        Text("Rows")
        .scroll_indicators(ScrollIndicatorVisibility.HIDDEN)
        .default_scroll_anchor("bottom")
        .scroll_target_behavior(ScrollTargetBehavior.VIEW_ALIGNED)
        .scroll_clip_disabled()
        .scroll_position(position.binding(), anchor="center")
    )
    configuration = scroll_configuration(view)
    assert configuration.indicators == ScrollIndicatorVisibility.HIDDEN
    assert configuration.default_anchor == "bottom"
    assert configuration.target_behavior == ScrollTargetBehavior.VIEW_ALIGNED
    assert configuration.clip_disabled is True
    assert configuration.position.wrapped_value == "row-20"
    assert configuration.position_anchor == "center"


def test_content_margins_are_layout_aware():
    plain = Text("Content")
    view = plain.content_margins(EdgeInsets.symmetric(horizontal=8, vertical=4))
    natural = plain.size_that_fits(Size(200, 200))
    measured = view.size_that_fits(Size(200, 200))
    assert measured.width == pytest.approx(natural.width + 16)
    assert measured.height == pytest.approx(natural.height + 8)


def test_find_scroll_configuration_inside_container():
    from aui import ScrollView, VStack
    view = VStack([ScrollView(Text("Rows")).default_scroll_anchor("center")])
    assert find_scroll_configuration(view).default_anchor == "center"


def test_scroll_configuration_validation():
    with pytest.raises(ValueError):
        Text("x").scroll_indicators("sometimes")
    with pytest.raises(ValueError):
        Text("x").default_scroll_anchor("leading")
    with pytest.raises(ValueError):
        Text("x").scroll_target_behavior("continuous")
    with pytest.raises(TypeError):
        Text("x").scroll_position("row")
    with pytest.raises(TypeError):
        Text("x").content_margins("wide")


def test_curses_scroll_position_uses_stable_id_headlessly():
    from aui import ScrollView, VStack
    from aui.backends.curses import CursesBackend

    position = State(8)
    backend = CursesBackend(lambda: ScrollView(VStack([
        Text(f"Row {index}").id(index) for index in range(12)
    ])).scroll_position(position.binding()))
    rendered = backend.render_to_string(width=30, height=4)
    assert "Row 8" in rendered
