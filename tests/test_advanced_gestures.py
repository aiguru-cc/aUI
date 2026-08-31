import pytest

from aui import (
    DragGesture, GestureHandler, GestureState, MagnifyGesture,
    MagnifyGestureValue, Point, RotateGesture, RotateGestureValue,
    SpatialTapGesture, TapGesture, Text,
)
from aui.core.gestures import (
    ExclusiveGesture, GestureModifier, SequenceGesture, SimultaneousGesture,
)


def test_tap_gesture_count_validation():
    assert TapGesture(2).count == 2
    with pytest.raises(ValueError): TapGesture(0)


def test_magnify_and_rotate_values():
    magnify = MagnifyGestureValue(1.5, velocity=0.2)
    rotate = RotateGestureValue(45, velocity=2)
    assert magnify.magnification == 1.5
    assert rotate.rotation == 45
    assert magnify.start_anchor == Point(0.5, 0.5)


def test_gesture_changed_ended_and_state_reset_lifecycle():
    state = GestureState(1.0)
    changed, ended = [], []
    handler = (MagnifyGesture().updating(state, lambda value, current: value.magnification)
               .on_changed(changed.append).on_ended(ended.append))
    value = MagnifyGestureValue(1.8)
    handler.emit_changed(value)
    assert state.value == 1.8 and changed == [value]
    handler.emit_ended(value)
    assert ended == [value] and state.value == 1.0


def test_default_updating_stores_whole_value():
    state = GestureState(None)
    handler = RotateGesture().updating(state)
    value = RotateGestureValue(20)
    handler.emit_changed(value)
    assert state.value is value
    handler.emit_ended(value)
    assert state.value is None


def test_gesture_composition_types_and_order():
    tap, drag = TapGesture(), DragGesture()
    simultaneous = tap.simultaneously(drag)
    sequence = tap.sequenced(drag)
    exclusive = tap.exclusively(drag)
    assert isinstance(simultaneous, SimultaneousGesture)
    assert isinstance(sequence, SequenceGesture)
    assert isinstance(exclusive, ExclusiveGesture)
    assert sequence.first is tap and sequence.second is drag


def test_view_gesture_priorities_and_masks():
    handler = TapGesture(2).on_ended(lambda value: None)
    normal = Text("Tap").gesture(handler, including="gesture")
    high = Text("Tap").high_priority_gesture(handler)
    simultaneous = Text("Tap").simultaneous_gesture(handler, including="subviews")
    assert normal.modifiers[-1].priority == "normal"
    assert high.modifiers[-1].priority == "high"
    assert simultaneous.modifiers[-1].priority == "simultaneous"
    assert simultaneous.modifiers[-1].including == "subviews"


def test_gesture_modifier_validation():
    with pytest.raises(TypeError): Text("x").gesture("tap")
    with pytest.raises(ValueError): Text("x").gesture(TapGesture(), including="ancestors")
    with pytest.raises(ValueError): GestureModifier(TapGesture(), priority="urgent")


def test_spatial_tap_and_drag_support_handlers():
    calls = []
    spatial = SpatialTapGesture(2).on_ended(calls.append)
    drag = DragGesture(4).on_changed(calls.append)
    assert isinstance(spatial, GestureHandler)
    assert isinstance(drag, GestureHandler)
