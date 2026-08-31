import pytest

from aui import State, Text, TextField, VStack
from aui.backends.curses import CursesBackend
from aui.core.events import (
    OnAppearModifier, OnDisappearModifier, OnSubmitModifier, SubmitLabelModifier,
)
from aui.core.geometry import Size


def test_event_modifiers_are_layout_transparent_and_validate():
    base = Text("Content")
    appeared = base.on_appear(lambda: None)
    disappeared = base.on_disappear(lambda: None)
    assert isinstance(appeared._modifier, OnAppearModifier)
    assert isinstance(disappeared._modifier, OnDisappearModifier)
    assert appeared.size_that_fits(Size(200, 100)) == base.size_that_fits(Size(200, 100))
    with pytest.raises(TypeError):
        base.on_appear("not callable")


def test_submit_modifier_and_label_validation():
    field = TextField(State("").binding())
    submitted = field.on_submit(lambda: None).submit_label("search")
    assert isinstance(submitted._modifier, SubmitLabelModifier)
    assert isinstance(submitted._content._modifier, OnSubmitModifier)
    with pytest.raises(ValueError):
        field.submit_label("invalid")


def test_curses_enter_runs_submit_action():
    value = State("")
    calls = []

    def make_view():
        return VStack([
            TextField(value.binding(), "Query")
            .on_submit(lambda: calls.append(value.wrapped_value))
            .submit_label("search")
        ])

    backend = CursesBackend(make_view)
    backend.render_to_string(40, 5)
    value._set("swiftui")
    backend._activate()
    assert calls == ["swiftui"]
    assert "search" in backend._status


def test_curses_on_appear_runs_once_across_renders():
    calls = []

    def appeared():
        calls.append("appear")

    backend = CursesBackend(lambda: Text("Hello").on_appear(appeared))
    backend.render_to_string()
    backend.render_to_string()
    assert calls == ["appear"]
