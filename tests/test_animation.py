"""Tests for aUI animation (T19): Animation value type, interpolation,
with_animation context, animate() and the .animation() modifier.

These tests are GUI-free: they verify the pure value semantics of Animation
and the modifier plumbing. Tk frame-driving is covered by test_tk_animation.py
(which runs under a Python with Tkinter).
"""
import pytest

from aui import (
    Animation,
    animate,
    animation,
    current_animation,
    with_animation,
)
from aui.core.geometry import Color, Point, Size
from aui.core.modifiers import AnimationModifier


# -- Animation value type ---------------------------------------------------

def test_animation_factories():
    assert Animation.linear(0.5).duration == 0.5
    assert Animation.linear(0.5).curve == "linear"
    assert Animation.ease_in(0.3).curve == "easeIn"
    assert Animation.ease_out(0.3).curve == "easeOut"
    assert Animation.ease_in_out(0.35).curve == "easeInOut"
    assert Animation.spring(0.4).curve == "spring"


def test_animation_duration_clamped():
    a = Animation(-1.0)
    assert a.duration == 0.0


def test_ease_bounds():
    a = Animation.ease_in_out(0.3)
    assert a.ease(0.0) == pytest.approx(0.0)
    assert a.ease(1.0) == pytest.approx(1.0)
    # easeInOut is monotonic in [0, 1]
    assert 0.0 <= a.ease(0.5) <= 1.0
    # out-of-range clamped
    assert a.ease(-5) == pytest.approx(0.0)
    assert a.ease(7) == pytest.approx(1.0)


def test_ease_linear_is_identity():
    a = Animation.linear(0.2)
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        assert a.ease(t) == pytest.approx(t)


def test_ease_in_out_midpoint():
    a = Animation.ease_in_out(0.3)
    assert a.ease(0.5) == pytest.approx(0.5)


# -- Interpolation ----------------------------------------------------------

def test_interpolate_float():
    a = Animation.linear(0.3)
    assert a.interpolate(0.0, 10.0, 0.5) == pytest.approx(5.0)
    assert a.interpolate(0.0, 10.0, 0.0) == pytest.approx(0.0)
    assert a.interpolate(0.0, 10.0, 1.0) == pytest.approx(10.0)


def test_interpolate_int_returns_float():
    a = Animation.linear(0.3)
    val = a.interpolate(0, 10, 0.5)
    assert val == pytest.approx(5.0)


def test_interpolate_color():
    a = Animation.linear(0.3)
    start = Color(0, 0, 0)
    end = Color(1, 1, 1)
    mid = a.interpolate(start, end, 0.5)
    assert isinstance(mid, Color)
    assert mid.red == pytest.approx(0.5)
    assert mid.green == pytest.approx(0.5)
    assert mid.blue == pytest.approx(0.5)


def test_interpolate_size_point():
    a = Animation.linear(0.3)
    mid_size = a.interpolate(Size(0, 0), Size(100, 50), 0.5)
    assert mid_size.width == pytest.approx(50.0)
    assert mid_size.height == pytest.approx(25.0)
    mid_pt = a.interpolate(Point(0, 0), Point(10, 20), 0.5)
    assert mid_pt.x == pytest.approx(5.0)
    assert mid_pt.y == pytest.approx(10.0)


def test_interpolate_unsupported_falls_back_to_end():
    a = Animation.linear(0.3)
    assert a.interpolate("a", "b", 0.5) == "b"


# -- with_animation / animate -----------------------------------------------

def test_with_animation_sets_and_restores_context():
    assert current_animation() is None
    with with_animation(Animation.ease_in_out(0.3)):
        assert current_animation() is not None
        assert current_animation().duration == 0.3
    assert current_animation() is None


def test_with_animation_nested_restores_outer():
    outer = Animation.linear(0.5)
    with with_animation(outer):
        with with_animation(None):
            assert current_animation() is None
        assert current_animation() is outer


def test_animate_functional():
    result = animate(Animation.linear(0.2), lambda: current_animation())
    assert result is not None
    assert result.duration == 0.2
    assert current_animation() is None


def test_with_animation_restores_after_exception():
    with pytest.raises(RuntimeError):
        with with_animation(Animation.linear(0.1)):
            raise RuntimeError("boom")
    assert current_animation() is None


# -- .animation() modifier --------------------------------------------------

def test_animation_modifier_attaches():
    from aui import Text
    view = animation(Text("hi"), Animation.ease_in_out(0.5))
    mods = view.modifiers
    assert isinstance(mods[-1], AnimationModifier)
    assert mods[-1].animation.duration == 0.5


def test_animation_modifier_preserves_layout():
    from aui import Text
    base = Text("hello")
    animated = animation(base, Animation.ease_in_out(0.3))
    assert animated.size_that_fits(Size(200, 200)).width == pytest.approx(
        base.size_that_fits(Size(200, 200)).width
    )


def test_animation_exported():
    from aui import __all__
    assert "Animation" in __all__
    assert "with_animation" in __all__
    assert "animate" in __all__
    assert "animation" in __all__
