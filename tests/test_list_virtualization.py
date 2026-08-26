"""Tests for List lazy virtualisation and scrolling (T21 / ADR-0008).

Covers the core viewport window logic and the Tk backend's scrollable
container with lazy row creation.
"""
import sys
import types

import pytest

from aui.core.components import List, Text
from aui.core.layout import VStack
from aui.core.state import State


# -- Core viewport logic ----------------------------------------------------

def test_visible_rows_window():
    """Only rows inside the viewport are returned (lazy)."""
    rows = [Text(f"row {i}") for i in range(10)]
    lst = List(rows, spacing=2.0, row_height=20.0)
    visible = lst.visible_rows(viewport_height=60, proposal_width=200)
    # 60 / (20+2) = 2.7 -> 3 rows (int + 1)
    assert len(visible) == 3
    assert [r.content for r in visible] == ["row 0", "row 1", "row 2"]


def test_visible_rows_scrolled():
    """Scrolling moves the viewport window."""
    rows = [Text(f"row {i}") for i in range(10)]
    lst = List(rows, spacing=2.0, row_height=20.0)
    lst.scroll_to(4)
    visible = lst.visible_rows(viewport_height=60, proposal_width=200)
    assert [r.content for r in visible] == ["row 4", "row 5", "row 6"]


def test_scroll_offset_binding():
    """scroll_offset binding is written through on scroll_to."""
    state = State(0)
    rows = [Text(f"row {i}") for i in range(5)]
    lst = List(rows, scroll_offset=state.binding(), row_height=20.0)
    lst.scroll_to(2)
    assert state.wrapped_value == 2
    assert lst.current_offset() == 2


def test_scroll_to_clamps():
    """scroll_to clamps to valid row indices."""
    rows = [Text(f"row {i}") for i in range(5)]
    lst = List(rows, row_height=20.0)
    lst.scroll_to(99)
    assert lst.current_offset() == 4  # last valid index
    lst.scroll_to(-5)
    assert lst.current_offset() == 0


def test_visible_rows_empty_viewport():
    """Zero-height viewport yields no rows."""
    lst = List([Text("a"), Text("b")], row_height=20.0)
    assert lst.visible_rows(0, 200) == []


def test_effective_row_height_measured():
    """row_height falls back to measuring the first row."""
    lst = List([Text("hello")])
    h = lst.effective_row_height(200)
    assert h > 0


def test_visible_rows_does_not_exceed_rows():
    """The window never returns more rows than exist."""
    rows = [Text(f"row {i}") for i in range(3)]
    lst = List(rows, row_height=20.0)
    visible = lst.visible_rows(viewport_height=1000, proposal_width=200)
    assert len(visible) == 3


# -- Tk backend lazy scroll container ---------------------------------------

# Mock tkinter so these run headless (same approach as test_tk_diff.py).
class FakeWidget:
    _counter = 0

    def __init__(self, parent=None, **kwargs):
        FakeWidget._counter += 1
        self.id = FakeWidget._counter
        self.parent = parent
        self.options = dict(kwargs)
        self.packed = False
        self.destroyed = False
        self.children = []
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
        return self.options.get("value", "")

    def set(self, value):
        self.options["value"] = value

    def bind(self, *args, **kwargs):
        return None

    def winfo_children(self):
        return self.children

    def winfo_height(self):
        return 200

    @property
    def master(self):
        return self.parent


class FakeTk(FakeWidget):
    def title(self, text):
        pass

    def mainloop(self):
        return None


def _make_widget_class(name):
    return type(name, (FakeWidget,), {})


def _install_mock_tkinter():
    tk_mod = types.ModuleType("tkinter")
    tk_mod.Tk = FakeTk
    tk_mod.Widget = FakeWidget
    tk_mod.Label = _make_widget_class("Label")
    tk_mod.Frame = _make_widget_class("Frame")
    tk_mod.Canvas = _make_widget_class("Canvas")

    ttk_mod = types.ModuleType("tkinter.ttk")
    for name in ("Button", "Checkbutton", "Combobox", "Entry", "Frame", "Label",
                 "LabelFrame", "Progressbar", "Scale", "Scrollbar", "Separator"):
        setattr(ttk_mod, name, _make_widget_class(name))

    sys.modules["tkinter"] = tk_mod
    sys.modules["tkinter.ttk"] = ttk_mod
    return tk_mod


# The mock tkinter is installed lazily inside the ``backend`` fixture (not at
# module import time) so that other test modules (e.g. test_tk_animation.py)
# see the real tkinter availability during collection and skip correctly.
_ORIG_TKINTER = sys.modules.get("tkinter")
_ORIG_TTK = sys.modules.get("tkinter.ttk")
_TK_BACKEND_MOD = None


@pytest.fixture
def backend():
    global _TK_BACKEND_MOD
    # Install mock tkinter (if not already installed by a previous call).
    if "tkinter" not in sys.modules or sys.modules["tkinter"].__name__ != "tkinter":
        _install_mock_tkinter()
        # Import the backend against the mock and cache the module.
        import importlib

        _TK_BACKEND_MOD = importlib.import_module("aui.backends.tk")
    elif _TK_BACKEND_MOD is None:
        import importlib

        _TK_BACKEND_MOD = importlib.import_module("aui.backends.tk")
    yield _TK_BACKEND_MOD.TkBackend()
    # Restore original tkinter so we don't leak into other test modules.
    if _ORIG_TKINTER is not None:
        sys.modules["tkinter"] = _ORIG_TKINTER
    else:
        sys.modules.pop("tkinter", None)
    if _ORIG_TTK is not None:
        sys.modules["tkinter.ttk"] = _ORIG_TTK
    else:
        sys.modules.pop("tkinter.ttk", None)


def test_tk_list_creates_scroll_container(backend):
    """A List renders into a scroll container with canvas + scrollbar."""
    lst = List([Text(f"row {i}") for i in range(50)], row_height=20.0)
    backend.render(VStack([lst]))
    # Container at root/0, canvas at root/0/canvas, scrollbar at root/0/scrollbar
    assert "root/0/canvas" in backend._widgets
    assert "root/0/scrollbar" in backend._widgets


def test_tk_list_lazy_creates_only_visible_rows(backend):
    """Only rows in the viewport window are created as widgets."""
    lst = List([Text(f"row {i}") for i in range(50)], row_height=20.0)
    backend.render(VStack([lst]))
    # Viewport 200px / (20+2) = 9.09 -> ~10 rows created
    row_paths = [p for p in backend._widgets if "/row/" in p]
    assert len(row_paths) <= 12, f"expected ~10 rows, got {len(row_paths)}"
    assert len(row_paths) >= 5


def test_tk_list_scroll_rerenders_new_window(backend):
    """Scrolling updates the offset and re-renders a new viewport."""
    state = State(0)
    rows = [Text(f"row {i}") for i in range(50)]
    lst = List(rows, scroll_offset=state.binding(), row_height=20.0)
    backend.render(VStack([lst]))
    first_paths = {p for p in backend._widgets if "/row/" in p}

    # Scroll down 20 rows -> viewport moves.
    lst.scroll_to(20)
    backend.render(VStack([lst]))
    assert state.wrapped_value == 20
    new_paths = {p for p in backend._widgets if "/row/" in p}
    # Rows left the window (destroyed) and new ones entered.
    assert first_paths != new_paths
    # Some old rows are gone.
    assert len(first_paths - new_paths) > 0
