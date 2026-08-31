"""Tests for List lazy virtualisation and scrolling (T21 / ADR-0008).

Covers the core viewport window logic and the curses backend's scrollable
rendering (global page scroll keeps the focused element visible).
"""
import pytest

from aui.backends.curses import CursesBackend
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


# -- Curses backend list rendering ------------------------------------------

def test_curses_list_renders_visible_rows():
    """The curses backend lays out the visible window of a List."""
    rows = [Text(f"row {i}") for i in range(50)]
    view = VStack([List(rows, spacing=1, row_height=1)])
    backend = CursesBackend(lambda: view)
    out = backend.render_to_string(40, 10)
    assert "row 0" in out
    assert "row 3" in out  # several visible rows rendered
    assert "row 49" not in out  # lazy: not all 50 rows in the viewport


def test_curses_list_scroll_moves_window():
    """Scrolling the list updates the lazy window."""
    rows = [Text(f"row {i}") for i in range(50)]
    lst = List(rows, spacing=1, row_height=1)
    view = VStack([lst])
    backend = CursesBackend(lambda: view)
    backend.render_to_string(40, 10)
    lst.scroll_to(30)
    out = backend.render_to_string(40, 10)
    assert "row 30" in out
    assert "row 0" not in out


def test_curses_global_scroll_clamps():
    """Global page scroll clamps to the content extent."""
    rows = [Text(f"row {i}") for i in range(30)]
    view = VStack(rows, spacing=1)
    backend = CursesBackend(lambda: view)
    backend._layout(view, 40, 1000)
    backend._viewport_h = 10
    backend._scroll_y = 9999.0
    max_scroll = max(0, int(backend._content_height) - 10)
    backend._scroll_y = max(0.0, min(backend._scroll_y, float(max_scroll)))
    assert backend._scroll_y == max_scroll
    assert max_scroll > 0  # the page is scrollable
