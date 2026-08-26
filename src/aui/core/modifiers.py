"""View modifiers for aUI.

Mirrors SwiftUI's modifier chain: ``padding``, ``background``, ``foregroundColor``,
``font``, ``border``, ``cornerRadius``, ``opacity``, ``hidden``, ``frame`` and
``onTapGesture`` and ``animation``. Modifiers are value objects; the render
backend interprets them.
"""
from __future__ import annotations

from typing import Callable, Optional

from .animation import Animation
from .geometry import Color, EdgeInsets, Font, Point, Size
from .view import View, ViewModifier, _apply


class PaddingModifier(ViewModifier):
    def __init__(self, insets: EdgeInsets):
        self.insets = insets

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        inner = proposal.deflated_by(self.insets)
        child_size = content.size_that_fits(inner)
        return child_size.expanded_by(self.insets)

    def place(self, content: View, origin: Point, size: Size) -> None:
        inner_size = content.size_that_fits(size.deflated_by(self.insets))
        content.place(
            Point(origin.x + self.insets.leading, origin.y + self.insets.top),
            inner_size,
        )


class BackgroundModifier(ViewModifier):
    def __init__(self, color: Color):
        self.color = color

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class ForegroundColorModifier(ViewModifier):
    def __init__(self, color: Color):
        self.color = color

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class FontModifier(ViewModifier):
    def __init__(self, font: Font):
        self.font = font

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class BorderModifier(ViewModifier):
    def __init__(self, color: Color, width: float = 1.0):
        self.color = color
        self.width = width

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class CornerRadiusModifier(ViewModifier):
    def __init__(self, radius: float):
        self.radius = radius

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class OpacityModifier(ViewModifier):
    def __init__(self, opacity: float):
        self.opacity = max(0.0, min(1.0, opacity))

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class HiddenModifier(ViewModifier):
    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return Size(0.0, 0.0)

    def place(self, content: View, origin: Point, size: Size) -> None:
        return None


class TapGestureModifier(ViewModifier):
    def __init__(self, action: Callable[[], None]):
        self.action = action

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)



class AnimationModifier(ViewModifier):
    """Marks a view so that state changes animate it (see ADR-0006).

    The render backend (Tk) reads this modifier and, when the wrapped view's
    properties change inside a ``with_animation`` scope, interpolates the
    old value to the new one over the animation duration.
    """

    def __init__(self, animation: Animation):
        self.animation = animation

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


# Public modifier API ---------------------------------------------------------

def padding(view: View, edges: Optional[EdgeInsets] = None, length: float = 8.0) -> View:
    insets = edges if edges is not None else EdgeInsets.all(length)
    return _apply(view, PaddingModifier(insets))


def background(view: View, color: Color) -> View:
    return _apply(view, BackgroundModifier(color))


def foreground_color(view: View, color: Color) -> View:
    return _apply(view, ForegroundColorModifier(color))


def font(view: View, font: Font) -> View:
    return _apply(view, FontModifier(font))


def border(view: View, color: Color, width: float = 1.0) -> View:
    return _apply(view, BorderModifier(color, width))


def corner_radius(view: View, radius: float) -> View:
    return _apply(view, CornerRadiusModifier(radius))


def opacity(view: View, value: float) -> View:
    return _apply(view, OpacityModifier(value))


def hidden(view: View) -> View:
    return _apply(view, HiddenModifier())


def frame(
    view: View,
    width: Optional[float] = None,
    height: Optional[float] = None,
    alignment: str = "center",
) -> View:
    from .view import FrameModifier
    return _apply(view, FrameModifier(width, height, alignment))


def on_tap_gesture(view: View, action: Callable[[], None]) -> View:
    return _apply(view, TapGestureModifier(action))


def animation(view: View, animation: Animation) -> View:
    """Attach an ``Animation`` so state changes on this view are animated.

    Usage::

        from aui import Text, animation, with_animation, Animation

        view = Text("hello").animation(Animation.ease_in_out(0.3))
        with with_animation(Animation.ease_in_out(0.3)):
            state.wrapped_value = new_value
    """
    return _apply(view, AnimationModifier(animation))
