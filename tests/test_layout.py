"""Tests for aUI layout containers."""
from aui.core.components import Text
from aui.core.geometry import Point, Size
from aui.core.layout import HStack, Spacer, VStack, ZStack


def test_vstack_vertical_sum():
    stack = VStack([Text("a"), Text("b")], spacing=10)
    size = stack.size_that_fits(Size(200, 200))
    # Each text ~ 14*1.4 = 19.6 high; two + 10 spacing.
    assert size.height == pytest.approx(19.6 * 2 + 10)


def test_hstack_horizontal_sum():
    stack = HStack([Text("hi"), Text("yo")], spacing=5)
    size = stack.size_that_fits(Size(300, 100))
    assert size.width == pytest.approx(len("hi") * 14 * 0.55 + len("yo") * 14 * 0.55 + 5)


def test_spacer_expands():
    stack = HStack([Text("x"), Spacer(), Text("y")], spacing=0)
    size = stack.size_that_fits(Size(300, 50))
    assert size.width == 300.0


def test_zstack_max_size():
    stack = ZStack([Text("aaaa"), Text("bb")])
    size = stack.size_that_fits(Size(100, 100))
    assert size.width == pytest.approx(len("aaaa") * 14 * 0.55)
    assert size.height == pytest.approx(19.6)


def test_stack_place_positions_children():
    stack = VStack([Text("a"), Text("b")], spacing=0)
    size = stack.size_that_fits(Size(200, 200))
    positions = []
    for child in stack.children():
        positions.append(child.size_that_fits(Size(200, float("inf"))).height)
    assert sum(positions) == pytest.approx(size.height)


import pytest
