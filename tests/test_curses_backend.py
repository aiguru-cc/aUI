"""Tests for the curses terminal backend (layout + drawing, no terminal needed)."""
from aui.backends.curses import CursesBackend, TerminalGrid
from aui.core.components import Button, Slider, Text, TextField, Toggle
from aui.core.geometry import Point, Size
from aui.core.layout import HStack, Spacer, VStack
from aui.core.state import State


def test_terminal_grid_put_and_clip():
    grid = TerminalGrid(10, 3)
    grid.put(2, 1, "hello")
    assert grid.snapshot().splitlines()[1] == "  hello"
    # Clipping: only chars inside the canvas are written.
    grid.put(8, 1, "xx")  # cols 8-9
    assert grid.snapshot().splitlines()[1] == "  hello xx"


def test_terminal_grid_box():
    grid = TerminalGrid(10, 5)
    grid.box(1, 1, 5, 3)
    lines = grid.snapshot().splitlines()
    assert "+---+" in lines[1]
    assert "|   |" in lines[2]
    assert "+---+" in lines[3]


def test_layout_records_frames():
    state = State("hi")
    view = VStack(
        [Text("Title"), Button("Go", action=lambda: None), TextField(state.binding(), placeholder="p")],
        spacing=2,
    )
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    # Four leaf components recorded (Text + Button + TextField + ...).
    assert len(backend._frames) >= 3
    kinds = [it.kind for it in backend._interactives]
    assert "button" in kinds
    assert "textfield" in kinds


def test_layout_stack_spacing_and_positions():
    view = VStack([Text("a"), Text("b")], spacing=2)
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    frames = list(backend._frames.values())
    # Two texts stacked vertically with 2-row spacing.
    assert frames[0][0].y == 0
    assert frames[1][0].y > frames[0][0].y


def test_layout_spacer_expands():
    view = HStack([Text("x"), Spacer(), Text("y")], spacing=0)
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    frames = list(backend._frames.values())
    # 'y' should be pushed to the right edge.
    assert frames[1][0].x > 30


def test_draw_text_and_button():
    view = VStack([Text("hello"), Button("OK", action=lambda: None)], spacing=1)
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 10)
    grid = TerminalGrid(80, 10)
    backend._draw(view, grid, Point(0, 0), Size(80, 10))
    out = grid.snapshot()
    assert "hello" in out
    assert "OK" in out


def test_slider_draws_marker():
    state = State(0.5)
    view = Slider(value=state.binding(), in_range=(0.0, 1.0))
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 10)
    grid = TerminalGrid(80, 10)
    backend._draw(view, grid, Point(0, 0), Size(80, 10))
    out = grid.snapshot()
    assert "o" in out


def test_toggle_draws_state():
    on = State(True)
    off = State(False)
    view = VStack([Toggle("On", is_on=on.binding()), Toggle("Off", is_on=off.binding())], spacing=1)
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 10)
    grid = TerminalGrid(80, 10)
    backend._draw(view, grid, Point(0, 0), Size(80, 10))
    out = grid.snapshot()
    assert "[x] On" in out
    assert "[ ] Off" in out
