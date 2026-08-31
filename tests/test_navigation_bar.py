import pytest

from aui import (
    Color, NavigationBarTitleDisplayMode, NavigationPath, NavigationStack,
    Size, Text,
)
from aui.core.navigation import navigation_configuration
from aui.backends.ascii import AsciiBackend


def test_destination_controls_navigation_title_and_restores_root():
    path = NavigationPath()
    root = Text("Root").navigation_title("Library")
    stack = NavigationStack(root, path=path).navigation_destination(
        str, lambda value: Text(value).navigation_title("Detail")
    )
    assert stack.title == "Library"
    path.append("article")
    assert stack.title == "Detail"
    stack.go_back()
    assert stack.title == "Library"


def test_large_and_hidden_navigation_bar_affect_layout():
    large = NavigationStack(
        Text("Body").navigation_title("Title").navigation_bar_title_display_mode(
            NavigationBarTitleDisplayMode.LARGE
        )
    )
    hidden = NavigationStack(Text("Body").navigation_title("Title").navigation_bar_hidden())
    assert large.header_height == 44.0
    assert hidden.header_height == 0.0
    body_height = Text("Body").size_that_fits(Size(200, 200)).height
    assert large.size_that_fits(Size(200, 200)).height == pytest.approx(body_height + 44.0)
    assert hidden.size_that_fits(Size(200, 200)).height == pytest.approx(body_height)


def test_navigation_configuration_outer_modifier_wins():
    view = Text("Body").navigation_title("Inner").navigation_title("Outer")
    assert navigation_configuration(view).title == "Outer"


def test_navigation_bar_background_and_validation():
    color = Color.blue
    view = Text("Body").navigation_bar_background(color)
    assert navigation_configuration(view).background == color
    with pytest.raises(TypeError):
        Text("Body").navigation_bar_background("blue")
    with pytest.raises(ValueError):
        Text("Body").navigation_bar_title_display_mode("compact")


def test_ascii_backend_omits_hidden_navigation_header():
    view = NavigationStack(Text("Body").navigation_title("Secret").navigation_bar_hidden())
    rendered = AsciiBackend(width=30, height=4).render(view)
    assert "Secret" not in rendered
    assert "Body" in rendered
