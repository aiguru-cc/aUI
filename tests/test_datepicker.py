"""Tests for the DatePicker component and its backend rendering."""
import sys
from datetime import datetime

sys.path.insert(0, "src")

from aui import DatePicker, State
from aui.backends.ascii import AsciiBackend
from aui.backends.curses import CursesBackend


def test_datepicker_defaults():
    dp = DatePicker()
    assert dp.title == ""
    assert dp.selection is None
    assert dp.displayed_components == "date"
    assert dp.in_range is None


def test_datepicker_current_date_format():
    dp = DatePicker("Due", State(datetime(2026, 8, 26)).binding())
    assert dp._current() == "2026-08-26"


def test_datepicker_current_time_format():
    dp = DatePicker(
        "Alarm",
        State(datetime(2026, 8, 26, 14, 30)).binding(),
        displayed_components="hourAndMinute",
    )
    assert dp._current() == "14:30"


def test_datepicker_current_both_format():
    dp = DatePicker(
        "When",
        State(datetime(2026, 8, 26, 14, 30)).binding(),
        displayed_components="date hourAndMinute",
    )
    assert dp._current() == "2026-08-26 14:30"


def test_datepicker_no_selection_current_empty():
    dp = DatePicker("Due")
    assert dp._current() == ""


def test_datepicker_size():
    dp = DatePicker("Due", State(datetime(2026, 8, 26)).binding())
    size = dp.size_that_fits(__import__("aui").Size(200, 100))
    assert size.width == 160.0
    assert size.height == 28.0


def test_datepicker_ascii_render():
    dp = DatePicker("Due", State(datetime(2026, 8, 26)).binding())
    out = AsciiBackend(width=40, height=3).render(dp)
    assert "[ Due 2026-08-26 ]" in out


def test_datepicker_curses_render():
    dp = DatePicker("Due", State(datetime(2026, 8, 26)).binding())
    cb = CursesBackend(lambda: dp)
    out = cb.render_to_string(40, 3)
    assert "[ Due 2026-08-26 ]" in out


def test_datepicker_exported():
    from aui import __all__
    assert "DatePicker" in __all__
