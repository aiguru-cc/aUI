"""Tests for aUI geometry primitives."""
import pytest

from aui.core.geometry import Color, EdgeInsets, Font, Size


def test_size_clamps_negative():
    s = Size(-5, 10)
    assert s.width == 0.0
    assert s.height == 10.0


def test_size_expand_deflate():
    s = Size(100, 50)
    insets = EdgeInsets.all(10)
    assert s.expanded_by(insets) == Size(120, 70)
    assert s.deflated_by(insets) == Size(80, 30)


def test_edge_insets_symmetric():
    e = EdgeInsets.symmetric(horizontal=5, vertical=3)
    assert e.horizontal == 10
    assert e.vertical == 6


def test_color_hex_and_tk():
    c = Color.hex("#ff8000")
    assert c.to_tk() == "#ff8000"
    assert Color.rgb(255, 0, 0).to_tk() == "#ff0000"


def test_named_colors():
    assert Color.red.to_tk() == "#ff0000"
    assert Color.clear.alpha == 0.0


def test_invalid_hex_raises():
    with pytest.raises(ValueError):
        Color.hex("xyz")


def test_font_presets():
    assert Font.title().size == 28.0
    assert Font.caption().size == 11.0
