import pytest

from aui import (
    CommandMenu, Commands, KeyboardShortcut, Menu, Divider, Button, Size,
    Text, ToolbarItem, describe_accessibility,
)
from aui.backends.ascii import AsciiBackend
from aui.core.commands import ToolbarModifier


def test_menu_selection_and_activation():
    calls = []
    menu = Menu("Actions", [
        Button("Open", lambda: calls.append("open")),
        Button("Delete", lambda: calls.append("delete"), role="destructive"),
    ])
    menu.move_selection(1)
    assert menu.selected_item.title == "Delete"
    menu.activate_selected()
    assert calls == ["delete"]
    assert describe_accessibility(menu).role == "menu"
    assert "Actions" in AsciiBackend().render(menu)


def test_disabled_menu_item_does_not_activate():
    calls = []
    menu = Menu("Menu", [Button("Disabled", lambda: calls.append(1)).disabled()])
    menu.activate_selected()
    assert calls == []


def test_menu_and_toolbar_items_reject_enabled_constructor_argument():
    with pytest.raises(TypeError):
        Button("Old", lambda: None, enabled=False)
    with pytest.raises(TypeError):
        ToolbarItem("old", Button("Old", lambda: None), enabled=False)
    with pytest.raises(TypeError):
        Menu("Old", [], enabled=False)


def test_menu_divider_is_non_selectable():
    menu = Menu("Menu", [
        Button("First", lambda: None),
        Divider(),
        Button("Second", lambda: None),
    ])

    menu.move_selection(1)
    assert menu.selected_item.title == "Second"
    menu.move_selection(-1)
    assert menu.selected_item.title == "First"


def test_toolbar_modifier_is_layout_transparent():
    shortcut = KeyboardShortcut("a")
    item = ToolbarItem(
        "add", Button("Add", lambda: None).keyboard_shortcut(shortcut).disabled()
    )
    assert item.label == "Add"
    assert item.shortcut == shortcut
    assert item.is_enabled is False
    base = Text("Content")
    wrapped = base.toolbar([item])
    assert isinstance(wrapped._modifier, ToolbarModifier)
    assert wrapped.size_that_fits(Size(200, 100)) == base.size_that_fits(Size(200, 100))


def test_toolbar_item_accepts_an_optional_system_symbol_name():
    item = ToolbarItem("help", Button("Help", lambda: None), system_name="questionmark.circle")
    assert item.system_name == "questionmark.circle"
    with pytest.raises(TypeError):
        ToolbarItem("help", Button("Help", lambda: None), system_name=1)


def test_toolbar_and_shortcut_validation():
    with pytest.raises(ValueError):
        KeyboardShortcut("AB")
    with pytest.raises(ValueError):
        KeyboardShortcut("x", ("hyper",))
    with pytest.raises(TypeError):
        ToolbarItem("old", "Old", lambda: None)
    with pytest.raises(TypeError, match="Button"):
        ToolbarItem("invalid", Text("Not a button"))
    with pytest.raises(ValueError):
        Text("x").toolbar([
            ToolbarItem("same", Button("A", lambda: None)),
            ToolbarItem("same", Button("B", lambda: None)),
        ])


def test_commands_validate_top_level_application_menus():
    file_menu = CommandMenu("File", [
        Button("New", lambda: None).keyboard_shortcut(KeyboardShortcut("n")),
        Divider(),
        Button("Close", lambda: None),
    ])
    commands = Commands([file_menu])

    assert list(commands) == [file_menu]
    assert file_menu.id == "file"
    assert file_menu.items[0].shortcut == KeyboardShortcut("n")
    assert file_menu.items[1].__class__.__name__ == "MenuDivider"
    with pytest.raises(ValueError, match="title cannot be empty"):
        CommandMenu("", [])
    with pytest.raises(TypeError, match="Button or Divider"):
        CommandMenu("Invalid", ["item"])
    with pytest.raises(ValueError, match="ids must be unique"):
        Commands([file_menu, CommandMenu("Other", [], id="file")])
    with pytest.raises(TypeError, match="CommandMenu"):
        Commands(["File"])
