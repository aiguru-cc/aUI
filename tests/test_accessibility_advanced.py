import pytest

from aui import Button, Text, VStack, describe_accessibility


def test_traits_can_be_added_and_removed():
    view = (Text("Important")
            .accessibility_add_traits({"header", "selected"})
            .accessibility_remove_traits("selected"))
    info = describe_accessibility(view)
    assert info.traits == {"header"}


def test_identifier_priority_heading_and_input_labels():
    view = (Text("Search")
            .accessibility_identifier("search.title")
            .accessibility_sort_priority(10)
            .accessibility_heading(2)
            .accessibility_input_labels(["Search", "Find"]))
    info = describe_accessibility(view)
    assert info.identifier == "search.title"
    assert info.sort_priority == 10
    assert info.heading_level == 2
    assert "header" in info.traits
    assert info.input_labels == ("Search", "Find")


def test_heading_level_validation():
    with pytest.raises(ValueError): Text("x").accessibility_heading(0)
    with pytest.raises(ValueError): Text("x").accessibility_heading(7)


def test_custom_content_preserves_importance():
    view = (Text("Flight")
            .accessibility_custom_content("Gate", "A12", importance="high")
            .accessibility_custom_content("Terminal", "2"))
    info = describe_accessibility(view)
    assert info.custom_content == {
        "Gate": ("A12", "high"), "Terminal": ("2", "default")
    }
    with pytest.raises(ValueError):
        Text("x").accessibility_custom_content("key", "value", "urgent")


def test_named_accessibility_action_is_executable():
    calls = []
    info = describe_accessibility(
        Button("Message", lambda: None).accessibility_action(
            "Archive", lambda: calls.append("archive")
        )
    )
    info.perform_action("Archive")
    assert calls == ["archive"]
    with pytest.raises(KeyError): info.perform_action("Delete")


def test_adjustable_accessibility_action_is_executable():
    directions = []
    info = describe_accessibility(
        Text("Rating").accessibility_adjustable_action(directions.append)
    )
    info.adjust("increment")
    info.adjust("decrement")
    assert directions == ["increment", "decrement"]
    with pytest.raises(ValueError): info.adjust("left")


def test_missing_adjustable_action_reports_error():
    with pytest.raises(LookupError): describe_accessibility(Text("x")).adjust("increment")


def test_sort_priority_orders_sibling_accessibility_nodes():
    info = describe_accessibility(VStack([
        Text("Later"), Text("First").accessibility_sort_priority(5), Text("Also later")
    ]))
    assert [child.label for child in info.children] == ["First", "Later", "Also later"]
