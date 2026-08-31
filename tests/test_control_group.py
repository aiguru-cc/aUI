import pytest

from aui import (
    Button, ControlGroup, ControlGroupStyle, ControlSize, Size,
)
from aui.backends.ascii import AsciiBackend
from aui.core.styles import resolve_style_tree, style_value


def test_control_group_layout_and_label():
    group = ControlGroup([
        Button("Back", lambda: None), Button("Forward", lambda: None),
    ], label="History")
    assert group.label == "History"
    assert group._spacing == 0
    assert group.size_that_fits(Size(400, 100)).width > 0
    with pytest.raises(ValueError): ControlGroup([])
    with pytest.raises(TypeError): ControlGroup(["button"])


def test_control_group_style_and_control_size_inherit():
    group = ControlGroup([
        Button("One", lambda: None), Button("Two", lambda: None),
    ]).control_group_style(ControlGroupStyle.NAVIGATION).control_size(ControlSize.SMALL)
    resolve_style_tree(group)
    leaf = group.find(lambda view: isinstance(view, Button))
    assert style_value(leaf, "control_group_style") == ControlGroupStyle.NAVIGATION
    assert style_value(leaf, "control_size") == ControlSize.SMALL
    with pytest.raises(ValueError):
        ControlGroup([Button("x", lambda: None)]).control_group_style("palette")


def test_ascii_marks_control_group_boundaries():
    group = ControlGroup([
        Button("A", lambda: None), Button("B", lambda: None),
    ])
    rendered = AsciiBackend(width=30, height=3).render(group)
    assert "{" in rendered and "}" in rendered
    assert "A" in rendered and "B" in rendered
