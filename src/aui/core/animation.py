"""Animation values and interpolation for aUI.

Mirrors SwiftUI's ``Animation`` value type. ``Animation`` is a pure value
object describing *how* a change should be animated (duration + curve); it
carries no GUI state, so it can be unit-tested without a display.

The Tk backend consumes ``Animation`` to drive frame-by-frame interpolation
(see ADR-0006). ``with_animation`` / ``animate`` wrap state changes so the
backend can detect that a change should be animated.
"""
from __future__ import annotations

import math
import threading
from contextlib import contextmanager
from typing import Any, Callable, Optional

from .geometry import Color, Point, Size

#: Thread-local "current animation" context, set by ``with_animation``.
_animation_context = threading.local()


def current_animation() -> Optional["Animation"]:
    """Return the animation in effect for the current thread, if any."""
    return getattr(_animation_context, "value", None)


@contextmanager
def with_animation(animation: Optional["Animation"]):
    """Context manager: run a state change inside an animation scope.

    Usage::

        with with_animation(Animation.ease_in_out(0.3)):
            state.wrapped_value = new_value

    The Tk backend reads ``current_animation()`` when diffing to decide whether
    a change should be animated.
    """
    previous = getattr(_animation_context, "value", None)
    _animation_context.value = animation
    try:
        yield
    finally:
        _animation_context.value = previous


def animate(animation: Optional["Animation"], fn: Callable[[], Any]) -> Any:
    """Functional form of ``with_animation``: run ``fn`` inside an animation scope."""
    with with_animation(animation):
        return fn()


class Animation:
    """A value object describing an animation (duration + easing curve)."""

    def __init__(self, duration: float, curve: str = "easeInOut"):
        self.duration = max(0.0, float(duration))
        self.curve = curve

    # -- Factories (SwiftUI-style) -----------------------------------------
    @classmethod
    def linear(cls, duration: float = 0.25) -> "Animation":
        return cls(duration, "linear")

    @classmethod
    def ease_in(cls, duration: float = 0.25) -> "Animation":
        return cls(duration, "easeIn")

    @classmethod
    def ease_out(cls, duration: float = 0.25) -> "Animation":
        return cls(duration, "easeOut")

    @classmethod
    def ease_in_out(cls, duration: float = 0.35) -> "Animation":
        return cls(duration, "easeInOut")

    @classmethod
    def spring(cls, duration: float = 0.4, damping: float = 0.6) -> "Animation":
        return cls(duration, "spring")

    # -- Easing ------------------------------------------------------------
    def ease(self, t: float) -> float:
        """Map a linear progress ``t`` in [0, 1] through the easing curve."""
        t = max(0.0, min(1.0, t))
        if self.curve == "linear":
            return t
        if self.curve == "easeIn":
            return t * t
        if self.curve == "easeOut":
            return 1.0 - (1.0 - t) * (1.0 - t)
        if self.curve == "easeInOut":
            if t < 0.5:
                return 2.0 * t * t
            return 1.0 - 2.0 * (1.0 - t) * (1.0 - t)
        if self.curve == "spring":
            # Simple damped spring approximation.
            decay = math.exp(-3.0 * t)
            return 1.0 - decay * math.cos(6.0 * t)
        return t

    def interpolate(self, start: Any, end: Any, t: float) -> Any:
        """Interpolate between ``start`` and ``end`` at progress ``t``."""
        eased = self.ease(t)
        return interpolate(start, end, eased)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Animation({self.duration}, {self.curve!r})"


def interpolate(start: Any, end: Any, t: float) -> Any:
    """Interpolate two values at linear progress ``t`` in [0, 1].

    Supports floats/ints, ``Color``, ``Size`` and ``Point``. Other types fall
    back to ``end`` (no interpolation).
    """
    t = max(0.0, min(1.0, t))
    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
        return start + (end - start) * t
    if isinstance(start, Color) and isinstance(end, Color):
        return Color(
            red=start.red + (end.red - start.red) * t,
            green=start.green + (end.green - start.green) * t,
            blue=start.blue + (end.blue - start.blue) * t,
            alpha=start.alpha + (end.alpha - start.alpha) * t,
        )
    if isinstance(start, Size) and isinstance(end, Size):
        return Size(
            width=start.width + (end.width - start.width) * t,
            height=start.height + (end.height - start.height) * t,
        )
    if isinstance(start, Point) and isinstance(end, Point):
        return Point(
            x=start.x + (end.x - start.x) * t,
            y=start.y + (end.y - start.y) * t,
        )
    return end
