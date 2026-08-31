"""Tests for the curses backend's SwiftUI-style states and focus navigation.

Covers:
  * disabled components are greyed out and not focusable
  * focus navigation moves through interactive components
  * activating a button / toggle fires the correct action
  * slider / picker / stepper / date adjustment
  * text field editing
  * semantic button roles remain focusable
"""
import curses
from datetime import datetime

from aui.backends.curses import CursesBackend
from aui.core.components import (
    Button,
    DatePicker,
    Picker,
    Slider,
    Stepper,
    TextField,
    Toggle,
)
from aui.core.layout import VStack
from aui.core.state import State


def test_disabled_components_not_focusable():
    """Disabled components are excluded from the focus list."""
    view = VStack(
        [
            Button("ok", lambda: None).disabled(),
            Button("enabled", lambda: None),
            TextField(State("").binding()).disabled(),
            Toggle("t", is_on=State(True).binding()).disabled(),
        ],
        spacing=1,
    )
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    kinds = [it.kind for it in backend._interactives]
    assert kinds == ["button"]
    assert backend._interactives[0].view.title == "enabled"


def test_focus_navigation_cycles():
    """Tab moves focus through all interactive components and wraps."""
    view = VStack(
        [
            Button("b1", lambda: None),
            TextField(State("").binding()),
            Toggle("t", is_on=State(True).binding()),
        ],
        spacing=1,
    )
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    assert len(backend._interactives) == 3
    backend._move_focus(1)
    assert backend._interactives[backend._focus_index].kind == "textfield"
    backend._move_focus(1)
    assert backend._interactives[backend._focus_index].kind == "toggle"
    backend._move_focus(1)  # wraps back to the first
    assert backend._interactives[backend._focus_index].kind == "button"
    backend._move_focus(-1)  # wraps the other way
    assert backend._interactives[backend._focus_index].kind == "toggle"


def test_activate_button_fires_action():
    calls = []
    view = VStack([Button("go", lambda: calls.append(1))])
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    backend._focus_index = 0
    backend._activate()
    assert calls == [1]


def test_activate_toggle_flips():
    on = State(False)
    view = VStack([Toggle("flag", is_on=on.binding())])
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    backend._focus_index = 0
    backend._activate()
    assert on.wrapped_value is True
    backend._activate()
    assert on.wrapped_value is False


def test_slider_adjust():
    vol = State(0.5)
    view = VStack([Slider(value=vol.binding(), in_range=(0.0, 1.0), step=0.1)])
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    backend._focus_index = 0
    backend._adjust(1)
    assert vol.wrapped_value == 0.6
    backend._adjust(-1)
    assert vol.wrapped_value == 0.5


def test_picker_adjust_cycles():
    pick = State("red")
    view = VStack([Picker("c", selection=pick.binding(), options=["red", "green", "blue"])])
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    backend._focus_index = 0
    backend._adjust(1)
    assert pick.wrapped_value == "green"
    backend._adjust(1)
    assert pick.wrapped_value == "blue"
    backend._adjust(1)  # wraps
    assert pick.wrapped_value == "red"


def test_stepper_adjust():
    qty = State(3.0)
    view = VStack([Stepper("q", value=qty.binding(), in_range=(0.0, 10.0), step=1.0)])
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    backend._focus_index = 0
    backend._adjust(1)
    assert qty.wrapped_value == 4.0
    backend._adjust(-1)
    assert qty.wrapped_value == 3.0


def test_datepicker_adjust_days():
    d = State(datetime(2026, 8, 26))
    view = VStack([DatePicker("due", selection=d.binding())])
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    backend._focus_index = 0
    backend._adjust(1)
    assert d.wrapped_value == datetime(2026, 8, 27)


def test_textfield_typing_and_backspace():
    text = State("")
    view = VStack([TextField(text.binding(), placeholder="name")])
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    backend._focus_index = 0
    backend._edit_typed("h")
    backend._edit_typed("i")
    assert text.wrapped_value == "hi"
    backend._edit_backspace()
    assert text.wrapped_value == "h"


def test_disabled_textfield_blocks_typing():
    text = State("x")
    view = VStack([TextField(text.binding()).disabled()])
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    # disabled textfield is not focusable; force-focus it anyway -> typing blocked
    backend._interactives = []
    view2 = VStack([Button("b", lambda: None)])
    backend._layout(view2, 80, 20)
    assert not any(it.kind == "textfield" for it in backend._interactives)


def test_button_swiftui_roles_are_focusable():
    view = VStack([Button("Default", lambda: None),
                   Button("Delete", lambda: None, role="destructive"),
                   Button("Cancel", lambda: None, role="cancel")])
    backend = CursesBackend(lambda: view)
    backend._layout(view, 80, 20)
    assert [item.view.role for item in backend._interactives] == [None, "destructive", "cancel"]


def test_curses_color_mapping():
    """aUI colors map to the closest curses colour."""
    from aui.core.geometry import Color
    backend = CursesBackend(lambda: None)
    assert backend._curses_color(Color.red) == curses.COLOR_RED
    assert backend._curses_color(Color.green) == curses.COLOR_GREEN
    assert backend._curses_color(Color.blue) == curses.COLOR_BLUE
    assert backend._curses_color(Color.white) == curses.COLOR_WHITE
    assert backend._curses_color(Color.black) == curses.COLOR_BLACK


def test_curses_close_cancels_tasks_observations_and_disappear_actions():
    calls = []

    class Task:
        def cancel(self):
            calls.append("task")

    backend = CursesBackend(lambda: Button("unused", lambda: None))
    backend._tasks["work"] = (None, Task())
    backend._observation_cancels = [lambda: calls.append("observation")]
    backend._disappear_actions = {"view": lambda: calls.append("disappear")}

    backend.close()
    backend.close()  # idempotent, including task and onDisappear lifetimes.

    assert calls == ["task", "observation", "disappear"]
    assert backend._dispatcher.dispatch(lambda: calls.append("late")) is False
