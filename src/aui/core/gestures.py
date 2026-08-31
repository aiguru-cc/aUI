"""Gesture system for aUI.

Mirrors SwiftUI's gesture modifiers: ``onTapGesture`` already exists in
``modifiers``; this module adds ``LongPressGesture`` and ``DragGesture`` as
value objects plus the ``onLongPressGesture`` / ``onDragGesture`` modifiers.

Gestures are declarative value objects attached to views via modifiers. The
render backend (Tk / curses) is responsible for detecting the corresponding
native events and invoking the attached callbacks. Layout semantics are
unaffected: a gesture modifier simply passes through size and placement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar

from .geometry import Point, Size
from .view import View, ViewModifier, _apply


@dataclass(frozen=True)
class LongPressGesture:
    """A long-press gesture with a minimum duration (seconds)."""

    minimum_duration: float = 0.5

    def on_changed(self, action): return GestureHandler(self, on_changed=action)
    def on_ended(self, action): return GestureHandler(self, on_ended=action)
    def updating(self, state, action=None): return GestureHandler(self, state=state, updating=action)
    def simultaneously(self, other): return SimultaneousGesture(self, other)
    def sequenced(self, other): return SequenceGesture(self, other)
    def exclusively(self, other): return ExclusiveGesture(self, other)


@dataclass(frozen=True)
class DragGesture:
    """A drag gesture. ``minimum_distance`` is in layout points."""

    minimum_distance: float = 10.0

    def on_changed(self, action): return GestureHandler(self, on_changed=action)
    def on_ended(self, action): return GestureHandler(self, on_ended=action)
    def updating(self, state, action=None): return GestureHandler(self, state=state, updating=action)
    def simultaneously(self, other): return SimultaneousGesture(self, other)
    def sequenced(self, other): return SequenceGesture(self, other)
    def exclusively(self, other): return ExclusiveGesture(self, other)


T = TypeVar("T")


class GestureState(Generic[T]):
    """Transient state reset automatically when a gesture ends."""

    def __init__(self, initial: T):
        self.initial_value = initial
        self.value = initial

    def update(self, value: T) -> None: self.value = value
    def reset(self) -> None: self.value = self.initial_value


class Gesture:
    def on_changed(self, action): return GestureHandler(self, on_changed=action)
    def on_ended(self, action): return GestureHandler(self, on_ended=action)
    def updating(self, state: GestureState, action=None):
        return GestureHandler(self, state=state, updating=action)
    def simultaneously(self, other): return SimultaneousGesture(self, other)
    def sequenced(self, other): return SequenceGesture(self, other)
    def exclusively(self, other): return ExclusiveGesture(self, other)


@dataclass(frozen=True)
class TapGesture(Gesture):
    count: int = 1

    def __post_init__(self):
        if self.count < 1: raise ValueError("tap count must be positive")


@dataclass(frozen=True)
class SpatialTapGesture(Gesture):
    count: int = 1


@dataclass(frozen=True)
class MagnifyGesture(Gesture):
    minimum_scale_delta: float = 0.01


@dataclass(frozen=True)
class RotateGesture(Gesture):
    minimum_angle_delta: float = 0.01


@dataclass(frozen=True)
class MagnifyGestureValue:
    magnification: float
    velocity: float = 0.0
    start_anchor: Point = Point(0.5, 0.5)


@dataclass(frozen=True)
class RotateGestureValue:
    rotation: float
    velocity: float = 0.0
    start_anchor: Point = Point(0.5, 0.5)


class GestureHandler(Gesture):
    def __init__(self, gesture, on_changed=None, on_ended=None,
                 state: GestureState | None = None, updating=None):
        self.gesture, self.changed_action, self.ended_action = gesture, on_changed, on_ended
        self.state, self.updating_action = state, updating

    def on_changed(self, action):
        self.changed_action = action; return self

    def on_ended(self, action):
        self.ended_action = action; return self

    def updating(self, state, action=None):
        self.state, self.updating_action = state, action; return self

    def emit_changed(self, value):
        if self.state is not None:
            if self.updating_action is None: self.state.update(value)
            else:
                result = self.updating_action(value, self.state)
                if result is not None: self.state.update(result)
        if self.changed_action is not None: self.changed_action(value)

    def emit_ended(self, value):
        if self.ended_action is not None: self.ended_action(value)
        if self.state is not None: self.state.reset()


class ComposedGesture(Gesture):
    kind = "composed"
    def __init__(self, first, second): self.first, self.second = first, second


class SimultaneousGesture(ComposedGesture): kind = "simultaneous"
class SequenceGesture(ComposedGesture): kind = "sequence"
class ExclusiveGesture(ComposedGesture): kind = "exclusive"


class GestureModifier(ViewModifier):
    def __init__(self, gesture: Gesture, priority: str = "normal", including: str = "all"):
        if not isinstance(gesture, (Gesture, DragGesture, LongPressGesture)):
            raise TypeError("gesture expects a Gesture")
        if priority not in {"normal", "high", "simultaneous"}: raise ValueError("invalid gesture priority")
        if including not in {"all", "gesture", "subviews", "none"}: raise ValueError("invalid gesture mask")
        self.gesture, self.priority, self.including = gesture, priority, including

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def gesture(view: View, value: Gesture, including: str = "all") -> View:
    return _apply(view, GestureModifier(value, "normal", including))


def high_priority_gesture(view: View, value: Gesture, including: str = "all") -> View:
    return _apply(view, GestureModifier(value, "high", including))


def simultaneous_gesture(view: View, value: Gesture, including: str = "all") -> View:
    return _apply(view, GestureModifier(value, "simultaneous", including))


#: A callback for drag gestures: (start, current) points.
DragCallback = Callable[[Point, Point], None]


class LongPressGestureModifier(ViewModifier):
    """Attaches a long-press handler to a view."""

    def __init__(self, action: Callable[[], None], gesture: LongPressGesture):
        self.action = action
        self.gesture = gesture

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class DragGestureModifier(ViewModifier):
    """Attaches a drag handler to a view.

    The callback receives ``(start_point, current_point)`` in view-local
    coordinates (the top-left of the view is the origin).
    """

    def __init__(self, action: DragCallback, gesture: DragGesture):
        self.action = action
        self.gesture = gesture

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


def on_long_press_gesture(
    view: View,
    action: Callable[[], None],
    minimum_duration: float = 0.5,
) -> View:
    """Attach a long-press handler (minimum duration in seconds).

    Usage::

        from aui import on_long_press_gesture

        view = on_long_press_gesture(Text("Hold me"), on_hold, minimum_duration=1.0)
    """
    return _apply(view, LongPressGestureModifier(action, LongPressGesture(minimum_duration)))


def on_drag_gesture(
    view: View,
    action: DragCallback,
    minimum_distance: float = 10.0,
) -> View:
    """Attach a drag handler receiving ``(start_point, current_point)``.

    Usage::

        from aui import on_drag_gesture

        def moved(start, current):
            print(f"dragged {current.x - start.x}pt")

        view = on_drag_gesture(Text("Drag me"), moved)
    """
    return _apply(view, DragGestureModifier(action, DragGesture(minimum_distance)))
