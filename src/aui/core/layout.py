"""Layout containers for aUI.

Mirrors SwiftUI's core layout containers: ``VStack``, ``HStack``, ``ZStack``
and ``Spacer``. Layout is computed in pure Python (no GUI needed), so it can be
unit-tested without a display.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from .geometry import EdgeInsets, Point, Size
from .view import View


class _Stack(View):
    """Base class for VStack/HStack with flexible spacer handling."""

    axis: str = "vertical"  # "vertical" or "horizontal"

    def __init__(self, children: Sequence[View], spacing: float = 8.0, alignment: str = "center"):
        self._children = list(children)
        self._spacing = spacing
        self._alignment = alignment

    @property
    def _main(self) -> str:
        return "height" if self.axis == "vertical" else "width"

    @property
    def _cross(self) -> str:
        return "width" if self.axis == "vertical" else "height"

    def size_that_fits(self, proposal: Size) -> Size:
        main = getattr(proposal, self._main)
        cross = getattr(proposal, self._cross)

        # First pass: measure non-spacer children with a proposal that is
        # unlimited along the main axis.
        sizes: List[Size] = []
        has_spacer = False
        for child in self._children:
            if isinstance(child, Spacer):
                has_spacer = True
                sizes.append(Size())
                continue
            child_proposal = Size(**{self._main: float("inf"), self._cross: cross})
            sizes.append(child.size_that_fits(child_proposal))

        spacers = sum(1 for c in self._children if isinstance(c, Spacer))
        n_non_spacer = len(self._children) - spacers
        spacing_total = self._spacing * max(0, len(self._children) - 1)

        if has_spacer:
            # Spacers absorb all remaining space along the main axis.
            used_main = sum(getattr(s, self._main) for s in sizes) + spacing_total
            main_size = max(main, used_main)
        else:
            main_size = sum(getattr(s, self._main) for s in sizes) + spacing_total

        cross_size = max((getattr(s, self._cross) for s in sizes), default=0.0)
        if not has_spacer:
            cross_size = max(cross_size, cross) if cross != float("inf") else cross_size

        return Size(**{self._main: main_size, self._cross: cross_size})

    def place(self, origin: Point, size: Size) -> None:
        main = getattr(size, self._main)
        cross = getattr(size, self._cross)

        # Measure children (unlimited main axis).
        sizes: List[Size] = []
        for child in self._children:
            if isinstance(child, Spacer):
                sizes.append(Size())
                continue
            proposal = Size(**{self._main: float("inf"), self._cross: cross})
            sizes.append(child.size_that_fits(proposal))

        spacers = [i for i, c in enumerate(self._children) if isinstance(c, Spacer)]
        spacing_total = self._spacing * max(0, len(self._children) - 1)
        fixed_main = sum(getattr(s, self._main) for i, s in enumerate(sizes) if i not in spacers)
        free_main = max(0.0, main - fixed_main - spacing_total)
        spacer_main = free_main / len(spacers) if spacers else 0.0

        cursor = 0.0
        for i, child in enumerate(self._children):
            child_size = sizes[i]
            if i in spacers:
                child_size = Size(**{self._main: spacer_main, self._cross: cross})
            child_main = getattr(child_size, self._main)
            child_cross = getattr(child_size, self._cross)
            offset = (cross - child_cross) * self._cross_alignment()
            if self.axis == "vertical":
                pos = Point(origin.x + offset, origin.y + cursor)
            else:
                pos = Point(origin.x + cursor, origin.y + offset)
            child.place(pos, child_size)
            cursor += child_main + self._spacing

    def _cross_alignment(self) -> float:
        return {
            "leading": 0.0, "top": 0.0,
            "center": 0.5,
            "trailing": 1.0, "bottom": 1.0,
        }.get(self._alignment, 0.5)

    def children(self) -> Sequence[View]:
        return self._children


class VStack(_Stack):
    """Arranges children vertically (top to bottom)."""

    axis = "vertical"

    def __init__(self, children: Sequence[View] = (), spacing: float = 8.0, alignment: str = "center"):
        super().__init__(children, spacing, alignment)


class HStack(_Stack):
    """Arranges children horizontally (leading to trailing)."""

    axis = "horizontal"

    def __init__(self, children: Sequence[View] = (), spacing: float = 8.0, alignment: str = "center"):
        super().__init__(children, spacing, alignment)


class ZStack(View):
    """Overlays children on top of each other (back to front)."""

    def __init__(self, children: Sequence[View] = (), alignment: str = "center"):
        self._children = list(children)
        self._alignment = alignment

    def size_that_fits(self, proposal: Size) -> Size:
        width = 0.0
        height = 0.0
        for child in self._children:
            s = child.size_that_fits(proposal)
            width = max(width, s.width)
            height = max(height, s.height)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        for child in self._children:
            child_size = child.size_that_fits(size)
            from .view import _aligned_offset
            dx, dy = _aligned_offset(size, child_size, self._alignment)
            child.place(Point(origin.x + dx, origin.y + dy), child_size)

    def children(self) -> Sequence[View]:
        return self._children


class Spacer(View):
    """A flexible empty space that expands along the stack's main axis."""

    def __init__(self, min_length: float = 0.0):
        self.min_length = min_length
        self._children = []

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(0.0, 0.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children
