"""Extensible layout protocol modeled after SwiftUI.Layout."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Sequence

from .geometry import Point, Rect, Size
from .layout_modifiers import layout_priority_of, z_ordered
from .view import View
from .measurement import measure


class LayoutSubview:
    """Measurement proxy for one child of a custom Layout."""

    def __init__(self, view: View):
        self.view = view
        self.priority = layout_priority_of(view)

    def size_that_fits(self, proposal: Size) -> Size:
        return measure(self.view, proposal)


@dataclass(frozen=True)
class LayoutPlacement:
    subview: LayoutSubview
    origin: Point
    size: Size


class Layout(abc.ABC):
    """Protocol for measuring and placing a collection of subviews."""

    @abc.abstractmethod
    def size_that_fits(self, proposal: Size, subviews: Sequence[LayoutSubview]) -> Size:
        raise NotImplementedError

    @abc.abstractmethod
    def place_subviews(self, bounds: Rect, proposal: Size,
                       subviews: Sequence[LayoutSubview]) -> Sequence[LayoutPlacement]:
        raise NotImplementedError

    def __call__(self, children: Sequence[View]) -> "LayoutContainer":
        return LayoutContainer(self, children)


class LayoutContainer(View):
    def __init__(self, layout: Layout, children: Sequence[View]):
        if not isinstance(layout, Layout):
            raise TypeError("LayoutContainer requires a Layout")
        self.layout = layout
        self._children = list(children)
        if not all(isinstance(child, View) for child in self._children):
            raise TypeError("Layout children must be View instances")

    def _subviews(self) -> list[LayoutSubview]:
        return [LayoutSubview(child) for child in self._children]

    def size_that_fits(self, proposal: Size) -> Size:
        return self.layout.size_that_fits(proposal, self._subviews())

    def placements(self, origin: Point, size: Size) -> list[LayoutPlacement]:
        values = list(self.layout.place_subviews(
            Rect(origin, size), size, self._subviews()
        ))
        known = {id(child) for child in self._children}
        if any(id(item.subview.view) not in known for item in values):
            raise ValueError("Layout returned a placement for an unknown subview")
        return values

    def place(self, origin: Point, size: Size) -> None:
        for placement in self.placements(origin, size):
            placement.subview.view.place(placement.origin, placement.size)

    def children(self):
        return self._children

    def z_ordered_children(self):
        return [child for _, child in z_ordered(self._children)]


class AnyLayout(Layout):
    """Type-erased layout that can be replaced at runtime."""

    def __init__(self, layout: Layout):
        if not isinstance(layout, Layout):
            raise TypeError("AnyLayout requires a Layout")
        self.layout = layout

    def size_that_fits(self, proposal: Size, subviews: Sequence[LayoutSubview]) -> Size:
        return self.layout.size_that_fits(proposal, subviews)

    def place_subviews(self, bounds: Rect, proposal: Size,
                       subviews: Sequence[LayoutSubview]) -> Sequence[LayoutPlacement]:
        return self.layout.place_subviews(bounds, proposal, subviews)


class StackLayout(Layout):
    """Shared implementation for HStackLayout and VStackLayout."""

    axis = "horizontal"

    def __init__(self, spacing: float = 8.0, alignment: str = "center"):
        self.spacing = max(0.0, float(spacing))
        self.alignment = alignment

    def _natural(self, subviews):
        proposal = Size(float("inf"), float("inf"))
        return [subview.size_that_fits(proposal) for subview in subviews]

    def size_that_fits(self, proposal: Size, subviews: Sequence[LayoutSubview]) -> Size:
        sizes = self._natural(subviews)
        spacing = self.spacing * max(0, len(sizes) - 1)
        if self.axis == "horizontal":
            return Size(sum(size.width for size in sizes) + spacing,
                        max((size.height for size in sizes), default=0.0))
        return Size(max((size.width for size in sizes), default=0.0),
                    sum(size.height for size in sizes) + spacing)

    def _allocated_main(self, available: float, subviews, sizes) -> list[float]:
        natural = [size.width if self.axis == "horizontal" else size.height for size in sizes]
        if sum(natural) <= available:
            return natural
        priorities = [subview.priority for subview in subviews]
        if len(set(priorities)) == 1:
            scale = available / sum(natural) if sum(natural) else 0.0
            return [value * scale for value in natural]
        result = [0.0] * len(natural)
        remaining = available
        for index in sorted(range(len(natural)), key=lambda i: priorities[i], reverse=True):
            result[index] = min(natural[index], remaining)
            remaining -= result[index]
        return result

    def place_subviews(self, bounds: Rect, proposal: Size,
                       subviews: Sequence[LayoutSubview]) -> Sequence[LayoutPlacement]:
        sizes = self._natural(subviews)
        count = len(sizes)
        spacing_total = self.spacing * max(0, count - 1)
        main = bounds.size.width if self.axis == "horizontal" else bounds.size.height
        allocated = self._allocated_main(max(0.0, main - spacing_total), subviews, sizes)
        placements = []
        cursor = 0.0
        for subview, natural, allocated_main in zip(subviews, sizes, allocated):
            if self.axis == "horizontal":
                size = subview.size_that_fits(Size(allocated_main, bounds.size.height))
                size = Size(allocated_main, min(bounds.size.height, size.height))
                cross = bounds.size.height - size.height
                y = bounds.origin.y + cross * self._alignment_factor()
                origin = Point(bounds.origin.x + cursor, y)
            else:
                size = subview.size_that_fits(Size(bounds.size.width, allocated_main))
                size = Size(min(bounds.size.width, size.width), allocated_main)
                cross = bounds.size.width - size.width
                x = bounds.origin.x + cross * self._alignment_factor()
                origin = Point(x, bounds.origin.y + cursor)
            placements.append(LayoutPlacement(subview, origin, size))
            cursor += allocated_main + self.spacing
        return placements

    def _alignment_factor(self) -> float:
        return {
            "leading": 0.0, "top": 0.0, "center": 0.5,
            "trailing": 1.0, "bottom": 1.0,
        }.get(self.alignment, 0.5)


class HStackLayout(StackLayout):
    axis = "horizontal"


class VStackLayout(StackLayout):
    axis = "vertical"


class ZStackLayout(Layout):
    def __init__(self, alignment: str = "center"):
        self.alignment = alignment

    def size_that_fits(self, proposal: Size, subviews: Sequence[LayoutSubview]) -> Size:
        sizes = [subview.size_that_fits(proposal) for subview in subviews]
        return Size(max((size.width for size in sizes), default=0.0),
                    max((size.height for size in sizes), default=0.0))

    def place_subviews(self, bounds: Rect, proposal: Size,
                       subviews: Sequence[LayoutSubview]) -> Sequence[LayoutPlacement]:
        from .view import _aligned_offset
        result = []
        for subview in subviews:
            size = subview.size_that_fits(bounds.size)
            dx, dy = _aligned_offset(bounds.size, size, self.alignment)
            result.append(LayoutPlacement(
                subview, Point(bounds.origin.x + dx, bounds.origin.y + dy), size
            ))
        return result


__all__ = [
    "AnyLayout", "HStackLayout", "Layout", "LayoutContainer", "LayoutPlacement",
    "LayoutSubview", "VStackLayout", "ZStackLayout",
]
