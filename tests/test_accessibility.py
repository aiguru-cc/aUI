"""Tests for the accessibility system (T25, ADR-0010)."""
from __future__ import annotations

import pytest

from aui import (
    CHILDREN_COMBINE,
    CHILDREN_IGNORE,
    Button,
    Form,
    HStack,
    Image,
    List,
    NavigationStack,
    Picker,
    ProgressView,
    Slider,
    State,
    Stepper,
    Text,
    TextField,
    Toggle,
    VStack,
    describe_accessibility,
)
from aui.core.accessibility import (
    accessibility_element, accessibility_hidden, accessibility_hint,
    accessibility_label, accessibility_value,
)


def _noop():
    pass


# -- Modifier API -------------------------------------------------------------

def test_accessibility_label_sets_label():
    view = accessibility_label(Button("X", action=_noop), "Close window")
    info = describe_accessibility(view)
    assert info.role == "button"
    assert info.label == "Close window"


def test_accessibility_hint_sets_hint():
    view = accessibility_hint(Button("Save", action=_noop), "Saves your changes")
    info = describe_accessibility(view)
    assert info.hint == "Saves your changes"


def test_accessibility_value_sets_value():
    view = accessibility_value(Text("50%"), "fifty percent")
    info = describe_accessibility(view)
    assert info.value == "fifty percent"


def test_accessibility_hidden_excludes():
    view = accessibility_hidden(Text("decorative"), True)
    info = describe_accessibility(view)
    assert info.hidden is True


def test_accessibility_hidden_default_true():
    view = accessibility_hidden(Text("decorative"))
    info = describe_accessibility(view)
    assert info.hidden is True


# -- Semantic roles -----------------------------------------------------------

def test_component_roles():
    view = VStack([
        Text("hi"),
        Button("Go", action=_noop),
        TextField(State("").binding()),
        Toggle("On", is_on=State(False).binding()),
        Slider(value=State(0.5).binding()),
        Picker("Pick", selection=State("a").binding(), options=["a", "b"]),
        Image(system_name="star"),
        Stepper("Steps", value=State(3.0).binding()),
        ProgressView(value=0.5, label="Loading"),
    ])
    info = describe_accessibility(view)
    roles = [c.role for c in info.children]
    assert roles == [
        "text", "button", "textfield", "toggle", "slider",
        "picker", "image", "stepper", "progress",
    ]


def test_container_roles():
    view = NavigationStack(
        Form([
            List([Text("row1"), Text("row2")]),
        ]).navigation_title("Settings"),
    )
    info = describe_accessibility(view)
    assert info.role == "navigation"
    assert info.label == "Settings"
    assert len(info.children) == 1
    form = info.children[0]
    assert form.role == "group"
    assert len(form.children) == 1
    lst = form.children[0]
    assert lst.role == "list"
    assert len(lst.children) == 2


# -- Component values ---------------------------------------------------------

def test_component_values():
    toggle = Toggle("On", is_on=State(True).binding())
    slider = Slider(value=State(0.25).binding())
    field = TextField(State("hello").binding(), placeholder="Name")
    progress = ProgressView(value=0.75)

    assert describe_accessibility(toggle).value == "on"
    assert describe_accessibility(slider).value == "0.25"
    assert describe_accessibility(field).value == "hello"
    assert describe_accessibility(progress).value == "75%"


def test_textfield_placeholder_is_label():
    field = TextField(State("").binding(), placeholder="Name")
    info = describe_accessibility(field)
    assert info.label == "Name"


# -- Element children strategies ---------------------------------------------

def test_element_combine_children():
    row = HStack([Text("Name"), Text("Alice")])
    combined = accessibility_element(row, CHILDREN_COMBINE)
    info = describe_accessibility(combined)
    assert info.role == "group"
    assert "Name" in info.label
    assert "Alice" in info.label
    assert info.children == []  # combined into one element


def test_element_ignore_children():
    row = HStack([Text("Name"), Text("Alice")])
    ignored = accessibility_element(row, CHILDREN_IGNORE)
    info = describe_accessibility(ignored)
    assert info.children == []


def test_hidden_children_not_in_summary():
    view = VStack([
        accessibility_hidden(Text("secret")),
        Text("visible"),
    ])
    info = describe_accessibility(view)
    assert len(info.children) == 2  # hidden flag is on the node
    assert info.children[0].hidden is True
    assert info.children[1].hidden is False


# -- Summary output -----------------------------------------------------------

def test_summary_format():
    view = VStack([
        accessibility_hint(Button("Save", action=_noop), "Saves your changes"),
    ])
    info = describe_accessibility(view)
    summary = info.summary()
    assert "button Save (Saves your changes)" in summary


def test_summary_indents_children():
    view = VStack([Text("a"), Text("b")])
    summary = describe_accessibility(view).summary()
    lines = summary.split("\n")
    assert lines[0] == "group"
    assert "  text a" in lines
    assert "  text b" in lines


# -- Backend integration (headless) ------------------------------------------

def test_ascii_backend_describe_accessibility():
    from aui.backends.ascii import AsciiBackend
    view = accessibility_label(Button("X", action=_noop), "Close")
    info = AsciiBackend().describe_accessibility(view)
    assert info.role == "button"
    assert info.label == "Close"


def test_curses_backend_describe_accessibility():
    from aui.backends.curses import CursesBackend
    view = accessibility_label(Button("X", action=_noop), "Close")
    backend = CursesBackend(lambda: view)
    info = backend.describe_accessibility()
    assert info.role == "button"
    assert info.label == "Close"


# -- Edge cases ---------------------------------------------------------------

def test_empty_view_is_group():
    from aui import Group
    info = describe_accessibility(Group([]))
    assert info.role == "group"
    assert info.children == []


def test_spacer_is_hidden():
    from aui import Spacer
    info = describe_accessibility(VStack([Spacer(), Text("x")]))
    assert info.children[0].role == "spacer"
    assert info.children[0].hidden is True


def test_chained_accessibility_modifiers():
    view = accessibility_hint(
        accessibility_label(Button("Del", action=_noop), "Delete"),
        "Deletes the item",
    )
    info = describe_accessibility(view)
    assert info.label == "Delete"
    assert info.hint == "Deletes the item"
