"""Tests for the aUI gesture system (T20)."""
import pytest

from aui import (
    DragGesture,
    LongPressGesture,
    Text,
)
from aui.core.geometry import Point, Size
from aui.core.modifiers import TapGestureModifier
from aui.core.gestures import DragGestureModifier, LongPressGestureModifier
from aui.core.view import _ModifiedContent


# -- Core gesture value objects ---------------------------------------------

def test_long_press_gesture_defaults():
    g = LongPressGesture()
    assert g.minimum_duration == 0.5


def test_long_press_gesture_custom():
    g = LongPressGesture(minimum_duration=1.5)
    assert g.minimum_duration == 1.5


def test_drag_gesture_defaults():
    g = DragGesture()
    assert g.minimum_distance == 10.0


def test_drag_gesture_custom():
    g = DragGesture(minimum_distance=5.0)
    assert g.minimum_distance == 5.0


# -- Modifiers wrap views ---------------------------------------------------

def test_on_long_press_wraps_view():
    calls = []
    v = Text("hold").on_long_press_gesture(lambda: calls.append(1))
    assert isinstance(v, _ModifiedContent)
    assert isinstance(v._modifier, LongPressGestureModifier)
    assert v._modifier.action is not None
    assert v._modifier.gesture.minimum_duration == 0.5


def test_on_long_press_custom_duration():
    v = Text("hold").on_long_press_gesture(lambda: None, minimum_duration=2.0)
    assert v._modifier.gesture.minimum_duration == 2.0


def test_on_drag_wraps_view():
    v = Text("drag").on_drag_gesture(lambda s, c: None)
    assert isinstance(v, _ModifiedContent)
    assert isinstance(v._modifier, DragGestureModifier)


def test_gesture_modifiers_do_not_change_layout():
    """Gesture modifiers must be transparent to the layout engine."""
    base = Text("hello")
    held = base.on_long_press_gesture(lambda: None)
    dragged = base.on_drag_gesture(lambda s, c: None)
    proposal = Size(100, 100)
    assert held.size_that_fits(proposal) == base.size_that_fits(proposal)
    assert dragged.size_that_fits(proposal) == base.size_that_fits(proposal)


# -- Drag callback signature ------------------------------------------------

def test_drag_callback_receives_points():
    """The drag action receives (start, current) Point values."""
    received = []
    v = Text("x").on_drag_gesture(lambda s, c: received.append((s, c)))
    mod = v._modifier
    mod.action(Point(1, 2), Point(5, 6))
    assert received == [(Point(1, 2), Point(5, 6))]


# -- onTapGesture modifier (existing) ---------------------------------------

def test_tap_gesture_modifier_exists():
    calls = []
    v = Text("tap").on_tap_gesture(lambda: calls.append("tap"))
    assert isinstance(v, _ModifiedContent)
    assert isinstance(v._modifier, TapGestureModifier)
    v._modifier.action()
    assert calls == ["tap"]


# -- Public API exports -----------------------------------------------------

def test_gesture_exports():
    import aui
    for name in ("DragGesture", "LongPressGesture"):
        assert hasattr(aui, name), f"missing export {name}"
    for name in ("gesture", "high_priority_gesture", "on_drag_gesture",
                 "on_long_press_gesture", "simultaneous_gesture"):
        assert not hasattr(aui, name)
