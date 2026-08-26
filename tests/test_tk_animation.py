"""Tests for Tk backend animation driving (T19, ADR-0006).

These tests require a Python with Tkinter (system /usr/bin/python3 on macOS).
They verify that:
  1. A view marked with .animation() + a with_animation scope animates color
     changes (schedules after() frames) instead of setting directly.
  2. Without .animation() or without an animation scope, colors set directly.
  3. The frame driver interpolates and terminates.

Run:  /usr/bin/python3 -m pytest tests/test_tk_animation.py -q
"""
import sys

import pytest

tk = pytest.importorskip("tkinter")
sys.path.insert(0, "src")

from aui.backends.tk import TkBackend, _parse_tk_color, _rgb_to_tk
from aui.core.animation import Animation, with_animation
from aui.core.components import Text
from aui.core.geometry import Color
from aui.core.modifiers import animation as anim_mod


@pytest.fixture
def backend():
    root = tk.Tk()
    root.withdraw()
    b = TkBackend(root)
    yield b
    try:
        root.destroy()
    except Exception:
        pass


def test_parse_tk_color_hex():
    assert _parse_tk_color("#ff0000") == (1.0, 0.0, 0.0)
    assert _parse_tk_color("#000000") == (0.0, 0.0, 0.0)
    assert _parse_tk_color("garbage") is None


def test_rgb_to_tk():
    assert _rgb_to_tk(1.0, 0.0, 0.0) == "#ff0000"
    assert _rgb_to_tk(0.0, 0.0, 0.0) == "#000000"


def test_no_animation_sets_color_directly(backend):
    view = Text("hi", color=Color.red)
    backend.render(view)
    label = backend._widgets["root"][1]
    assert label.cget("fg") == "#ff0000"


def test_animation_scope_schedules_after(backend):
    view = anim_mod(Text("hi", color=Color.red), Animation.linear(0.1))
    backend.render(view)  # initial render, red
    label = backend._widgets["root"][1]
    assert label.cget("fg") == "#ff0000"

    # Now change color inside an animation scope.
    with with_animation(Animation.linear(0.1)):
        view2 = anim_mod(Text("hi", color=Color.blue), Animation.linear(0.1))
        backend.render(view2)

    # An after() frame job should be scheduled for this widget.
    jobs = backend._animation_jobs
    assert jobs, "expected an active animation job"
    # The widget should not yet be blue (interpolating).
    assert label.cget("fg") != "#0000ff"


def test_animation_job_terminates(backend):
    view = anim_mod(Text("hi", color=Color.red), Animation.linear(0.05))
    backend.render(view)
    label = backend._widgets["root"][1]

    with with_animation(Animation.linear(0.05)):
        backend.render(anim_mod(Text("hi", color=Color.blue), Animation.linear(0.05)))

    # Pump the event loop until the animation finishes.
    import time
    deadline = time.monotonic() + 1.0
    while backend._animation_jobs and time.monotonic() < deadline:
        backend.root.update()
        time.sleep(0.01)

    assert not backend._animation_jobs, "animation should have finished"
    assert label.cget("fg") == "#0000ff"


def test_no_scope_no_animation(backend):
    # .animation() modifier but NO with_animation scope -> direct set.
    view = anim_mod(Text("hi", color=Color.red), Animation.linear(0.1))
    backend.render(view)
    label = backend._widgets["root"][1]

    view2 = anim_mod(Text("hi", color=Color.blue), Animation.linear(0.1))
    backend.render(view2)  # no animation context
    assert label.cget("fg") == "#0000ff"
    assert not backend._animation_jobs
