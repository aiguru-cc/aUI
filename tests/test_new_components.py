"""Tests for the new SwiftUI-style components (Stepper, ProgressView, Form, NavigationStack)."""
import pytest

from aui import (
    Button,
    Form,
    NavigationStack,
    ProgressView,
    Slider,
    Stepper,
    Text,
    TextField,
    Toggle,
    VStack,
)
from aui.backends.ascii import AsciiBackend
from aui.backends.curses import CursesBackend
from aui.core.geometry import Size
from aui.core.state import State


# -- Stepper ----------------------------------------------------------------
def test_stepper_increment_decrement_binding():
    state = State(5.0)
    stepper = Stepper("Qty", value=state.binding(), in_range=(0.0, 10.0), step=1.0)
    stepper.increment()
    assert state.wrapped_value == 6.0
    stepper.decrement()
    assert state.wrapped_value == 5.0


def test_stepper_clamps_to_range():
    state = State(9.5)
    stepper = Stepper("Qty", value=state.binding(), in_range=(0.0, 10.0), step=1.0)
    stepper.increment()
    assert state.wrapped_value == 10.0  # clamped at max
    stepper.decrement()
    stepper.decrement()
    assert state.wrapped_value == 8.0


def test_stepper_callbacks():
    calls = []
    stepper = Stepper("X", on_increment=lambda: calls.append("+"), on_decrement=lambda: calls.append("-"))
    stepper.increment()
    stepper.decrement()
    assert calls == ["+", "-"]


def test_stepper_size():
    s = Stepper("Qty")
    size = s.size_that_fits(Size(200, 50))
    assert size.width > 0 and size.height > 0


# -- ProgressView -----------------------------------------------------------
def test_progress_view_determinate():
    p = ProgressView(value=0.5, label="Loading")
    assert p.value == 0.5
    assert p.label == "Loading"
    size = p.size_that_fits(Size(200, 50))
    assert size.width > 0


def test_progress_view_indeterminate():
    p = ProgressView()
    assert p.value is None


# -- Form -------------------------------------------------------------------
def test_form_stacks_children():
    form = Form([Text("a"), Text("b")], spacing=2)
    size = form.size_that_fits(Size(200, 200))
    assert size.height > 0
    assert len(form.children()) == 2


def test_form_place_positions_children():
    form = Form([Text("row1"), Text("row2")], spacing=0)
    size = form.size_that_fits(Size(200, 200))
    heights = [c.size_that_fits(Size(200, float("inf"))).height for c in form.children()]
    assert size.height == pytest.approx(sum(heights))


# -- NavigationStack --------------------------------------------------------
def test_navigation_stack_header_offset():
    nav = NavigationStack("Home", Text("body"))
    size = nav.size_that_fits(Size(200, 200))
    # Header (24) + body height.
    assert size.height > 24.0


def test_navigation_stack_children():
    nav = NavigationStack("Home", Text("body"))
    assert len(nav.children()) == 1
    assert nav.title == "Home"


# -- Backend integration ----------------------------------------------------
def test_ascii_renders_new_components():
    view = VStack(
        [
            Stepper("Qty", value=State(3.0).binding(), in_range=(0.0, 10.0)),
            ProgressView(value=0.5, label="Loading"),
            Text("body"),
        ],
        spacing=1,
    )
    out = AsciiBackend(width=40, height=10).render(view)
    assert "Qty" in out
    assert "#" in out  # progress filled marker


def test_ascii_renders_navigation_and_form():
    view = NavigationStack("Settings", Form([Toggle("WiFi"), Button("Save", action=lambda: None)]))
    out = AsciiBackend(width=40, height=10).render(view)
    assert "Settings" in out
    assert "WiFi" in out
    assert "Save" in out


def test_curses_renders_new_components():
    state = State(3.0)
    view = VStack(
        [
            Stepper("Qty", value=state.binding(), in_range=(0.0, 10.0)),
            ProgressView(value=0.25),
            Text("done"),
        ],
        spacing=1,
    )
    backend = CursesBackend(lambda: view)
    out = backend.render_to_string(60, 10)
    assert "Qty" in out
    assert "#" in out  # progress filled
    assert "done" in out


def test_curses_renders_navigation():
    view = NavigationStack("Home", Text("welcome"))
    backend = CursesBackend(lambda: view)
    out = backend.render_to_string(60, 10)
    assert "Home" in out
    assert "welcome" in out
