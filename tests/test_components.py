"""Tests for aUI components and modifiers."""
from aui.core.components import Button, Text, TextField
from aui.core.geometry import Color, EdgeInsets, Size
from aui.core.modifiers import background, border, corner_radius, font, foreground_color, frame, hidden, padding
from aui.core.state import State


def test_text_measures():
    t = Text("hello")
    size = t.size_that_fits(Size(100, 100))
    assert size.width > 0
    assert size.height > 0


def test_button_has_action():
    calls = []
    btn = Button("Go", action=lambda: calls.append(1))
    btn.action()
    assert calls == [1]


def test_padding_expands_size():
    t = Text("x")
    padded = padding(t, EdgeInsets.all(10))
    base = t.size_that_fits(Size(100, 100))
    grown = padded.size_that_fits(Size(100, 100))
    assert grown.width == pytest.approx(base.width + 20)
    assert grown.height == pytest.approx(base.height + 20)


def test_frame_fixes_size():
    t = Text("hello")
    framed = frame(t, width=200, height=50)
    size = framed.size_that_fits(Size(1000, 1000))
    assert size.width == 200.0
    assert size.height == 50.0


def test_hidden_has_zero_size():
    t = Text("secret")
    h = hidden(t)
    assert h.size_that_fits(Size(100, 100)) == Size(0, 0)


def test_modifier_chain_builds():
    t = Text("hi")
    styled = foreground_color(font(border(corner_radius(background(t, Color.blue), 4), Color.red), None), Color.green)
    # Chain should not crash and should keep measuring.
    assert styled.size_that_fits(Size(100, 100)).width > 0


def test_textfield_binding():
    state = State("initial")
    field = TextField(state.binding(), placeholder="type here")
    assert field.text.wrapped_value == "initial"
    field.text.wrapped_value = "updated"
    assert state.wrapped_value == "updated"


import pytest
