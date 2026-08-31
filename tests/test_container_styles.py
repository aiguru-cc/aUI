import pytest

from aui import (
    Color, DisclosureGroupStyle, EdgeInsets, Form, FormStyle, GroupBox,
    GroupBoxStyle, List, ListStyle, Point, Section, Size, Text, VStack,
)
from aui.core.container_styles import (
    ListRowBackgroundModifier, ListRowInsetsModifier, ListRowSeparatorModifier,
)
from aui.core.environment import resolve_environment_tree
from aui.core.styles import resolve_style_tree, style_value


def test_container_style_families_resolve():
    view = (VStack([Text("x")])
            .list_style(ListStyle.SIDEBAR)
            .form_style(FormStyle.COLUMNS)
            .group_box_style(GroupBoxStyle.CARD)
            .disclosure_group_style(DisclosureGroupStyle.COMPACT))
    resolve_style_tree(view)
    leaf = view.find(lambda item: isinstance(item, Text))
    assert style_value(leaf, "list_style") == ListStyle.SIDEBAR
    assert style_value(leaf, "form_style") == FormStyle.COLUMNS


@pytest.mark.parametrize("method", [
    "list_style", "form_style", "group_box_style", "disclosure_group_style",
])
def test_invalid_container_styles(method):
    with pytest.raises(ValueError): getattr(Text("x"), method)("glass")


def test_list_row_background_and_separator_modifiers():
    row = Text("Row").list_row_background(Color.blue).list_row_separator("hidden")
    assert any(isinstance(mod, ListRowBackgroundModifier) for mod in row.modifiers)
    assert isinstance(row.modifiers[-1], ListRowSeparatorModifier)
    assert row.modifiers[-1].visibility == "hidden"
    with pytest.raises(ValueError): Text("x").list_row_separator("sometimes")
    with pytest.raises(TypeError): Text("x").list_row_background("blue")


def test_list_row_insets_change_measurement():
    base = Text("Row")
    inset = base.list_row_insets(EdgeInsets.symmetric(horizontal=12, vertical=4))
    base_size = base.size_that_fits(Size(200, 100))
    inset_size = inset.size_that_fits(Size(200, 100))
    assert inset_size.width == pytest.approx(base_size.width + 24)
    assert inset_size.height == pytest.approx(base_size.height + 8)
    with pytest.raises(TypeError): base.list_row_insets(8)


def test_section_spacing_changes_real_layout_size():
    section = Section(Text("Header"), [Text("A"), Text("B")], Text("Footer"))
    normal = section.size_that_fits(Size(300, 500))
    styled = section.section_spacing(6)
    resolve_style_tree(styled)
    leaf = styled.find(lambda item: isinstance(item, Section))
    spaced = leaf.size_that_fits(Size(300, 500))
    assert spaced.height == pytest.approx(normal.height + 18)


def test_header_prominence_validation_and_propagation():
    section = Section(Text("Header"), [Text("Row")]).header_prominence("increased")
    resolve_style_tree(section)
    header = section.find(lambda item: isinstance(item, Text) and item.content == "Header")
    assert style_value(header, "header_prominence") == "increased"
    with pytest.raises(ValueError): Text("x").header_prominence("giant")
