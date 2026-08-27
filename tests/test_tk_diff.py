"""Tests for the Tk backend's incremental (diff) rendering.

These tests mock the ``tkinter`` / ``tkinter.ttk`` modules so they run in
headless environments (no display, no real Tk). They verify the core diff
behaviour: widget reuse across re-renders, property updates, incompatible-type
rebuilds, and destruction of removed widgets.
"""
import sys
import types

import pytest


# -- Mock tkinter layer ------------------------------------------------------
class FakeWidget:
    """Minimal fake Tk widget recording config/pack/destroy calls."""

    _counter = 0

    def __init__(self, parent=None, **kwargs):
        FakeWidget._counter += 1
        self.id = FakeWidget._counter
        self.parent = parent
        self.options = dict(kwargs)
        self.packed = False
        self.destroyed = False
        self.children = []
        self._value = kwargs.get("value", "")
        self._selected = False
        if parent is not None and hasattr(parent, "children"):
            parent.children.append(self)

    def config(self, **kwargs):
        self.options.update(kwargs)

    def configure(self, **kwargs):
        self.options.update(kwargs)

    def pack(self, **kwargs):
        self.packed = True
        self.pack_options = kwargs

    def destroy(self):
        self.destroyed = True

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def delete(self, *args):
        self._value = ""

    def insert(self, index, value):
        self._value = value

    def state(self, states=None):
        if states:
            self._selected = "selected" in states
        return self._selected

    def instate(self, states):
        return self._selected

    def trace_add(self, *args):
        return "trace1"

    def trace_remove(self, *args):
        return None

    def bind(self, *args, **kwargs):
        return None

    def winfo_children(self):
        return self.children

    def winfo_height(self):
        return 200

    def start(self, *args):
        return None

    @property
    def master(self):
        return self.parent


class FakeTk(FakeWidget):
    def __init__(self):
        super().__init__()
        self.title_calls = []

    def title(self, text):
        self.title_calls.append(text)

    def winfo_children(self):
        return self.children

    def mainloop(self):
        return None


class FakeStringVar:
    """Minimal fake of ``tk.StringVar`` with ``textvariable`` trace support."""

    _counter = 0

    def __init__(self, master=None, value=""):
        FakeStringVar._counter += 1
        self.master = master
        self._value = value
        self._traces = {}

    def set(self, value):
        self._value = value
        for cb in list(self._traces.values()):
            cb()

    def get(self):
        return self._value

    def trace_add(self, mode, callback):
        name = f"trace{FakeStringVar._counter}"
        self._traces[name] = callback
        return name

    def trace_remove(self, mode, name):
        self._traces.pop(name, None)


def _make_widget_class(name):
    cls = type(name, (FakeWidget,), {})
    return cls


def _install_mock_tkinter():
    """Install fake tkinter/ttk modules into sys.modules and return the tk module."""
    tk_mod = types.ModuleType("tkinter")
    tk_mod.Tk = FakeTk
    tk_mod.Widget = FakeWidget
    tk_mod.Label = _make_widget_class("Label")
    tk_mod.Frame = _make_widget_class("Frame")
    tk_mod.Canvas = _make_widget_class("Canvas")
    tk_mod.StringVar = FakeStringVar
    tk_mod.BooleanVar = types.SimpleNamespace
    tk_mod.DoubleVar = types.SimpleNamespace

    ttk_mod = types.ModuleType("tkinter.ttk")
    for name in ("Button", "Checkbutton", "Combobox", "Entry", "Frame", "Label",
                 "LabelFrame", "Progressbar", "Scale", "Scrollbar", "Separator"):
        setattr(ttk_mod, name, _make_widget_class(name))

    sys.modules["tkinter"] = tk_mod
    sys.modules["tkinter.ttk"] = ttk_mod
    return tk_mod


_install_mock_tkinter()

from aui.backends.tk import TkBackend  # noqa: E402
from aui.core.components import Button, Text, TextField  # noqa: E402
from aui.core.layout import VStack  # noqa: E402
from aui.core.state import State  # noqa: E402


@pytest.fixture
def backend():
    return TkBackend()


def _widget_count(backend):
    return len(backend._widgets)


# -- Diff behaviour ----------------------------------------------------------

def test_reuse_text_widget_across_rerender(backend):
    """Same structural path + same type => widget is reused, only text updated."""
    v1 = VStack([Text("hello")])
    backend.render(v1)
    first = backend._widgets["root/0"][1]
    assert first.options.get("text") == "hello"

    v2 = VStack([Text("world")])
    backend.render(v2)
    second = backend._widgets["root/0"][1]
    assert second is first, "widget should be reused, not recreated"
    assert second.options.get("text") == "world"
    assert not second.destroyed


def test_unchanged_tree_keeps_widgets(backend):
    v1 = VStack([Text("a"), Text("b")])
    backend.render(v1)
    w_a = backend._widgets["root/0"][1]
    w_b = backend._widgets["root/1"][1]

    v2 = VStack([Text("a"), Text("b")])
    backend.render(v2)
    assert backend._widgets["root/0"][1] is w_a
    assert backend._widgets["root/1"][1] is w_b


def test_incompatible_type_rebuilds(backend):
    """Same path but different view type => old widget destroyed, new created."""
    backend.render(VStack([Text("x")]))
    old = backend._widgets["root/0"][1]

    backend.render(VStack([Button("x", action=lambda: None)]))
    new = backend._widgets["root/0"][1]
    assert new is not old
    assert old.destroyed


def test_removed_view_destroys_widget(backend):
    backend.render(VStack([Text("a"), Text("b")]))
    w_a = backend._widgets["root/0"][1]
    w_b = backend._widgets["root/1"][1]

    backend.render(VStack([Text("a")]))
    assert backend._widgets["root/0"][1] is w_a
    assert "root/1" not in backend._widgets
    assert w_b.destroyed


def test_button_command_updated(backend):
    calls = []

    def act():
        calls.append(1)

    backend.render(VStack([Button("go", action=act)]))
    btn = backend._widgets["root/0"][1]
    btn.options["command"]()
    assert calls == [1]

    def act2():
        calls.append(2)

    backend.render(VStack([Button("go", action=act2)]))
    btn2 = backend._widgets["root/0"][1]
    assert btn2 is btn
    btn2.options["command"]()
    assert calls == [1, 2], "command should be rebound to the new action"


def test_textfield_keeps_focus_widget(backend):
    """TextField widget is reused across re-renders (focus preserved)."""
    state = State("abc")
    v1 = VStack([TextField(state.binding())])
    backend.render(v1)
    entry1 = backend._widgets["root/0"][1]
    entry1.set("abc")

    v2 = VStack([TextField(state.binding())])
    backend.render(v2)
    entry2 = backend._widgets["root/0"][1]
    assert entry2 is entry1


def test_textfield_edits_write_back_to_binding(backend):
    """User edits on the Tk Entry propagate to the aUI Binding (Tk backend).

    Regression test: the old implementation called ``entry.trace_add`` which
    does not exist on ``ttk.Entry`` (it is a ``StringVar`` method), so a real
    Tk window crashed when it contained a TextField. The backend now binds a
    ``tk.StringVar`` via ``textvariable`` and traces that instead.
    """
    state = State("abc")
    backend.render(VStack([TextField(state.binding())]))
    entry = backend._widgets["root/0"][1]
    var = entry._aui_var
    assert var is not None, "entry should carry a StringVar"

    var.set("xyz")
    assert state.wrapped_value == "xyz", "typing should write through to the binding"

    # Re-render keeps the same StringVar (focus / partial-edit preserved).
    backend.render(VStack([TextField(state.binding())]))
    assert backend._widgets["root/0"][1]._aui_var is var


def test_state_change_diff_updates_only_text(backend):
    """Simulating a state change: only the changed Text widget is reconfigured."""
    state = State(0)

    def make_view():
        return VStack(
            [
                Text(f"count: {state.wrapped_value}"),
                Button("+", action=lambda: state._set(state.wrapped_value + 1)),
            ]
        )

    backend.render(make_view())
    text_w = backend._widgets["root/0"][1]
    btn_w = backend._widgets["root/1"][1]

    state._set(5)
    backend.render(make_view())
    assert backend._widgets["root/0"][1] is text_w
    assert backend._widgets["root/1"][1] is btn_w
    assert text_w.options.get("text") == "count: 5"
