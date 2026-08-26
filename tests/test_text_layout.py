"""Tests for Text multi-line layout and measurement (T18)."""
import pytest

from aui.core.components import Text
from aui.core.geometry import Font, Size


def test_single_line_width():
    """ASCII text width is proportional to char count."""
    t = Text("Hello", font=Font(size=10.0))
    size = t.size_that_fits(Size(float("inf"), float("inf")))
    # 5 chars * 0.55 * 10 = 27.5
    assert size.width == pytest.approx(27.5)
    assert size.height == pytest.approx(14.0)  # 10 * 1.4


def test_empty_text_zero_size():
    t = Text("")
    assert t.size_that_fits(Size(float("inf"), float("inf"))) == Size(0.0, 0.0)


def test_cjk_double_width():
    """CJK chars measure double width vs ASCII."""
    ascii_t = Text("ab", font=Font(size=10.0))
    cjk_t = Text("中文", font=Font(size=10.0))
    ascii_w = ascii_t.size_that_fits(Size(float("inf"), float("inf"))).width
    cjk_w = cjk_t.size_that_fits(Size(float("inf"), float("inf"))).width
    # 2 CJK * 10 = 20; 2 ASCII * 5.5 = 11
    assert cjk_w == pytest.approx(20.0)
    assert ascii_w == pytest.approx(11.0)
    assert cjk_w > ascii_w


def test_explicit_newline_increases_height():
    t = Text("a\nb", font=Font(size=10.0))
    size = t.size_that_fits(Size(float("inf"), float("inf")))
    assert size.height == pytest.approx(28.0)  # 2 lines * 14


def test_word_wrap_to_proposal_width():
    """Long text wraps to multiple lines when width is constrained."""
    t = Text("hello world foo bar", font=Font(size=10.0))
    size = t.size_that_fits(Size(30.0, float("inf")))
    # 30px fits ~5 ASCII chars per line -> wraps into 4 lines
    assert size.height > 14.0
    assert size.width <= 30.0


def test_line_limit_truncates():
    t = Text("a\nb\nc\nd", font=Font(size=10.0), line_limit=2)
    size = t.size_that_fits(Size(float("inf"), float("inf")))
    assert size.height == pytest.approx(28.0)  # only 2 lines


def test_line_spacing_adds_gap():
    t = Text("a\nb", font=Font(size=10.0), line_spacing=5.0)
    size = t.size_that_fits(Size(float("inf"), float("inf")))
    # 2 lines * 14 + 1 gap * 5
    assert size.height == pytest.approx(33.0)


def test_measure_line_handles_unicode():
    """Mixed ASCII + CJK measures correctly."""
    t = Text("a中b", font=Font(size=10.0))
    size = t.size_that_fits(Size(float("inf"), float("inf")))
    # a(5.5) + 中(10) + b(5.5) = 21
    assert size.width == pytest.approx(21.0)
