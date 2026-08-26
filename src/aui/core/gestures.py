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
from typing import Callable, Optional

from .geometry import Point, Size
from .view import View, ViewModifier, _apply


@dataclass(frozen=True)
class LongPressGesture:
    """A long-press gesture with a minimum duration (seconds)."""

    minimum_duration: float = 0.5


@dataclass(frozen=True)
class DragGesture:
    """A drag gesture. ``minimum_distance`` is in layout points."""

    minimum_distance: float = 10.0


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
