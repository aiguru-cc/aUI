import pytest

from aui import FocusState, Size, TextField, VStack
from aui.backends.curses import CursesBackend
from aui.core.focus import FocusedModifier


def test_focus_state_with_typed_field_identifier():
    focus = FocusState(None)
    field = TextField(FocusState("").binding(), placeholder="Name").focused(
        focus.binding(), equals="name"
    )
    modifier = field._modifier
    assert isinstance(modifier, FocusedModifier)
    assert not modifier.is_focused
    modifier.activate()
    assert focus.wrapped_value == "name"
    modifier.deactivate()
    assert focus.wrapped_value is None


def test_boolean_focus_state_deactivates_to_false():
    focus = FocusState(True)
    modifier = TextField(FocusState("").binding()).focused(focus.binding())._modifier
    assert modifier.is_focused
    modifier.deactivate()
    assert focus.wrapped_value is False


def test_focused_modifier_is_layout_transparent_and_validates():
    text = FocusState("")
    focus = FocusState("field")
    base = TextField(text.binding())
    wrapped = base.focused(focus.binding(), equals="field")
    assert wrapped.size_that_fits(Size(300, 100)) == base.size_that_fits(Size(300, 100))
    with pytest.raises(TypeError):
        base.focused(True)
    with pytest.raises(TypeError):
        base.focused(focus.binding(), equals=[])


def test_curses_uses_declarative_initial_focus():
    first = FocusState("")
    second = FocusState("")
    focus = FocusState("second")

    def make_view():
        return VStack([
            TextField(first.binding(), "First").focused(focus.binding(), "first"),
            TextField(second.binding(), "Second").focused(focus.binding(), "second"),
        ])

    backend = CursesBackend(make_view)
    backend.render_to_string(40, 8)
    assert backend._interactives[backend._focus_index].view.placeholder == "Second"
