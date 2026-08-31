import pytest

from aui import (
    Button, ButtonStyle, Color, ControlSize, HStack, Label, LabelStyle,
    Picker, PickerStyle, ProgressView, ProgressViewStyle, Toggle, ToggleStyle,
)
from aui.backends.ascii import AsciiBackend
from aui.core.styles import is_enabled, resolve_style_tree, style_value


def leaf(view, kind):
    return view.find(lambda item: isinstance(item, kind))


def test_all_style_modifiers_are_chainable_and_resolved():
    view = (Button("Save", lambda: None)
            .button_style(ButtonStyle.BORDERED_PROMINENT)
            .tint(Color(1, 0, 0))
            .control_size(ControlSize.LARGE)
            .disabled())
    resolve_style_tree(view)
    button = leaf(view, Button)
    assert style_value(button, "button_style") == ButtonStyle.BORDERED_PROMINENT
    assert style_value(button, "control_size") == ControlSize.LARGE
    tint = style_value(button, "tint")
    assert (tint.red, tint.green, tint.blue) == (1, 0, 0)
    assert not is_enabled(button)


def test_descendant_style_overrides_inherited_container_style():
    red = Color(1, 0, 0)
    blue = Color(0, 0, 1)
    child = Button("Child", lambda: None).tint(red)
    root = HStack([child]).tint(blue)
    resolve_style_tree(root)
    assert style_value(leaf(root, Button), "tint") is red


def test_last_modifier_wins_on_same_view():
    view = Button("Go", lambda: None).tint(Color(1, 0, 0)).tint(Color(0, 0, 1))
    resolve_style_tree(view)
    tint = style_value(leaf(view, Button), "tint")
    assert (tint.red, tint.green, tint.blue) == (0, 0, 1)


@pytest.mark.parametrize("method,value,key", [
    ("toggle_style", ToggleStyle.CHECKBOX, "toggle_style"),
    ("picker_style", PickerStyle.SEGMENTED, "picker_style"),
    ("label_style", LabelStyle.ICON_ONLY, "label_style"),
    ("progress_view_style", ProgressViewStyle.CIRCULAR, "progress_view_style"),
])
def test_component_style_families(method, value, key):
    base = Label("Inbox", "tray")
    view = getattr(base, method)(value)
    resolve_style_tree(view)
    assert style_value(leaf(view, Label), key) == value


def test_invalid_style_is_rejected():
    with pytest.raises(ValueError):
        Button("No", lambda: None).button_style("neon")


def test_ascii_reflects_plain_buttons_hidden_labels_and_icon_only_labels():
    view = HStack([
        Button("Plain", lambda: None).button_style(ButtonStyle.PLAIN),
        Toggle("Wi-Fi").labels_hidden(),
        Label("Inbox", "tray").label_style(LabelStyle.ICON_ONLY),
        ProgressView().progress_view_style(ProgressViewStyle.CIRCULAR),
    ])
    output = AsciiBackend(width=60, height=4).render(view)
    assert "Plain" in output and "+" not in output
    assert "Wi-Fi" not in output
    assert "tray" in output
    assert "◌" in output
