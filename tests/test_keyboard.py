import pytest

from aui import (
    Button, FocusState, KeyPress, KeyPressResult, KeyboardShortcut, Size, Text,
    TextField, VStack,
)
from aui.core.keyboard import FocusSectionModifier, OnKeyPressModifier


def test_keyboard_shortcut_roles_and_validation():
    assert KeyboardShortcut.default_action().key == "\r"
    assert KeyboardShortcut.default_action().modifiers == ()
    assert KeyboardShortcut.cancel_action().key == "\x1b"
    wrapped = Button("Save", lambda: None).keyboard_shortcut("s")
    assert wrapped._modifier.shortcut == KeyboardShortcut("s")


def test_key_press_filter_and_result_normalization():
    events = []
    modifier = Text("x").on_key_press("x", lambda event: events.append(event) or True)._modifier
    assert isinstance(modifier, OnKeyPressModifier)
    assert modifier.dispatch(KeyPress("y")) is KeyPressResult.IGNORED
    assert modifier.dispatch(KeyPress("x")) is KeyPressResult.HANDLED
    assert events[0].key == "x"
    with pytest.raises(ValueError):
        KeyPress("", phase="down")


def test_default_focus_initializes_empty_binding_but_preserves_selection():
    focus = FocusState(None)
    modifier = TextField(FocusState("").binding()).default_focus(
        focus.binding(), equals="email"
    )._modifier
    modifier.activate_if_needed()
    assert focus.value == "email"
    focus.value = "password"
    modifier.activate_if_needed()
    assert focus.value == "password"


def test_focus_section_is_layout_transparent():
    text = Text("Section")
    wrapped = text.focus_section("account")
    assert isinstance(wrapped._modifier, FocusSectionModifier)
    assert wrapped.size_that_fits(Size(100, 100)) == text.size_that_fits(Size(100, 100))


def test_curses_dispatches_key_handler_before_default_editing():
    from aui.backends.curses import CursesBackend
    events = []
    backend = CursesBackend(lambda: Text("keys").on_key_press(
        "x", lambda event: events.append(event.key) or KeyPressResult.HANDLED
    ))
    backend.render_to_string(30, 4)
    backend._handle_key(ord("x"))
    assert events == ["x"]


def test_curses_default_action_shortcut_activates_button():
    from aui.backends.curses import CursesBackend
    calls = []
    backend = CursesBackend(lambda: VStack([
        Button("Save", lambda: calls.append("save")).keyboard_shortcut(
            KeyboardShortcut.default_action()
        )
    ]))
    backend.render_to_string(30, 4)
    backend._handle_key(10)
    assert calls == ["save"]
