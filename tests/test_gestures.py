"""Tests for the aUI gesture system (T20)."""
import pytest

from aui import (
    DragGesture,
    LongPressGesture,
    Text,
    on_drag_gesture,
    on_long_press_gesture,
    on_tap_gesture,
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
    v = on_long_press_gesture(Text("hold"), lambda: calls.append(1))
    assert isinstance(v, _ModifiedContent)
    assert isinstance(v._modifier, LongPressGestureModifier)
    assert v._modifier.action is not None
    assert v._modifier.gesture.minimum_duration == 0.5


def test_on_long_press_custom_duration():
    v = on_long_press_gesture(Text("hold"), lambda: None, minimum_duration=2.0)
    assert v._modifier.gesture.minimum_duration == 2.0


def test_on_drag_wraps_view():
    v = on_drag_gesture(Text("drag"), lambda s, c: None)
    assert isinstance(v, _ModifiedContent)
    assert isinstance(v._modifier, DragGestureModifier)


def test_gesture_modifiers_do_not_change_layout():
    """Gesture modifiers must be transparent to the layout engine."""
    base = Text("hello")
    held = on_long_press_gesture(base, lambda: None)
    dragged = on_drag_gesture(base, lambda s, c: None)
    proposal = Size(100, 100)
    assert held.size_that_fits(proposal) == base.size_that_fits(proposal)
    assert dragged.size_that_fits(proposal) == base.size_that_fits(proposal)


# -- Drag callback signature ------------------------------------------------

def test_drag_callback_receives_points():
    """The drag action receives (start, current) Point values."""
    received = []
    v = on_drag_gesture(Text("x"), lambda s, c: received.append((s, c)))
    mod = v._modifier
    mod.action(Point(1, 2), Point(5, 6))
    assert received == [(Point(1, 2), Point(5, 6))]


# -- onTapGesture modifier (existing) ---------------------------------------

def test_tap_gesture_modifier_exists():
    calls = []
    v = on_tap_gesture(Text("tap"), lambda: calls.append("tap"))
    assert isinstance(v, _ModifiedContent)
    assert isinstance(v._modifier, TapGestureModifier)
    v._modifier.action()
    assert calls == ["tap"]


# -- Public API exports -----------------------------------------------------

def test_gesture_exports():
    import aui
    for name in ("DragGesture", "LongPressGesture", "on_drag_gesture", "on_long_press_gesture"):
        assert hasattr(aui, name), f"missing export {name}"
