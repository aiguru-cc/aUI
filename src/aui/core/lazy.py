"""Identity-preserving lazy stacks and grids."""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor
from typing import Any, Callable, Optional, Sequence

from .geometry import Point, Size
from .layout import HStack, VStack
from .structural import ForEach
from .view import View
from .measurement import measure


class _LazyStackMixin:
    def _prepare(self) -> None:
        self._children = list(self._foreach.children())

    def children(self):
        self._prepare()
        return self._children

    def size_that_fits(self, proposal: Size) -> Size:
        self._prepare()
        return super().size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        self._prepare()
        super().place(origin, size)

    def visible_children(self, offset: float, viewport: float,
                         item_extent: float = 28.0, overscan: int = 2):
        extent = max(1.0, float(item_extent) + float(getattr(self, "_spacing", 0.0)))
        margin = max(0, int(overscan))
        start = max(0, int(float(offset) // extent) - margin)
        count = max(1, int(ceil(max(0.0, float(viewport)) / extent)) + 2 * margin)
        end = min(len(self._foreach.data), start + count)
        return start, self._foreach.children_range(start, end)


class LazyVStack(_LazyStackMixin, VStack):
    """A vertical stack that builds identified child views on first layout."""

    def __init__(self, data: Sequence[Any], content: Callable[[Any], View],
                 id: Optional[Callable[[Any], Any] | str] = None,
                 spacing: float = 8.0, alignment: str = "center"):
        self._foreach = ForEach(data, content, id=id)
        super().__init__([], spacing=spacing, alignment=alignment)


class LazyHStack(_LazyStackMixin, HStack):
    """A horizontal stack that builds identified child views on first layout."""

    def __init__(self, data: Sequence[Any], content: Callable[[Any], View],
                 id: Optional[Callable[[Any], Any] | str] = None,
                 spacing: float = 8.0, alignment: str = "center"):
        self._foreach = ForEach(data, content, id=id)
        super().__init__([], spacing=spacing, alignment=alignment)


@dataclass(frozen=True)
class GridItem:
    kind: str = "flexible"
    size: float = 120.0
    minimum: float = 80.0
    maximum: float = float("inf")
    spacing: Optional[float] = None
    alignment: str = "center"

    def __post_init__(self) -> None:
        if self.kind not in ("fixed", "flexible", "adaptive"):
            raise ValueError("GridItem kind must be fixed, flexible, or adaptive")
        if self.size <= 0 or self.minimum <= 0 or self.maximum < self.minimum:
            raise ValueError("GridItem dimensions must be positive and ordered")
        if self.spacing is not None and self.spacing < 0:
            raise ValueError("GridItem spacing cannot be negative")
        if self.alignment not in ("automatic", "leading", "center", "trailing",
                                  "top", "bottom"):
            raise ValueError("unsupported GridItem alignment")

    @classmethod
    def fixed(cls, size: float, spacing: Optional[float] = None,
              alignment: str = "center") -> "GridItem":
        return cls("fixed", size=float(size), minimum=float(size), maximum=float(size),
                   spacing=spacing, alignment=alignment)

    @classmethod
    def flexible(cls, minimum: float = 80.0,
                 maximum: float = float("inf"), spacing: Optional[float] = None,
                 alignment: str = "center") -> "GridItem":
        return cls("flexible", size=minimum, minimum=minimum, maximum=maximum,
                   spacing=spacing, alignment=alignment)

    @classmethod
    def adaptive(cls, minimum: float = 100.0,
                 maximum: float = float("inf"), spacing: Optional[float] = None,
                 alignment: str = "center") -> "GridItem":
        return cls("adaptive", size=minimum, minimum=minimum, maximum=maximum,
                   spacing=spacing, alignment=alignment)


class LazyVGrid(View):
    """A vertically scrolling-style grid with fixed/flexible/adaptive columns."""

    def __init__(self, data: Sequence[Any], columns: Sequence[GridItem],
                 content: Callable[[Any], View], id=None,
                 spacing: float = 12.0, row_spacing: float = 12.0):
        self.columns = list(columns)
        if not self.columns or not all(isinstance(item, GridItem) for item in self.columns):
            raise ValueError("LazyVGrid requires at least one GridItem")
        self._foreach = ForEach(data, content, id=id)
        self.spacing = max(0.0, float(spacing))
        self.row_spacing = max(0.0, float(row_spacing))

    def children(self):
        return self._foreach.children()

    def visible_children(self, offset: float, viewport: float, available_width: float,
                         row_extent: float = 40.0, overscan: int = 2):
        columns = max(1, len(self.resolved_columns(available_width)))
        extent = max(1.0, float(row_extent) + self.row_spacing)
        margin = max(0, int(overscan))
        start_row = max(0, int(float(offset) // extent) - margin)
        row_count = max(1, int(ceil(max(0.0, float(viewport)) / extent)) + 2 * margin)
        start = start_row * columns
        end = min(len(self._foreach.data), (start_row + row_count) * columns)
        return start, self._foreach.children_range(start, end)

    def resolved_columns(self, available_width: float) -> list[GridItem]:
        available_width = max(0.0, float(available_width))
        expanded: list[GridItem] = []
        for item in self.columns:
            if item.kind == "adaptive":
                gap = self.spacing if item.spacing is None else item.spacing
                count = max(1, floor((available_width + gap) / (item.minimum + gap)))
                expanded.extend([GridItem.flexible(item.minimum, item.maximum,
                                                    item.spacing, item.alignment)] * count)
            else:
                expanded.append(item)
        return expanded

    def column_spacings(self, available_width: float) -> list[float]:
        tracks = self.resolved_columns(available_width)
        return [self.spacing if item.spacing is None else item.spacing
                for item in tracks[:-1]]

    def column_widths(self, available_width: float) -> list[float]:
        expanded = self.resolved_columns(available_width)
        spacing_total = sum(self.column_spacings(available_width))
        fixed = sum(item.size for item in expanded if item.kind == "fixed")
        flexible = [item for item in expanded if item.kind == "flexible"]
        remaining = max(0.0, available_width - spacing_total - fixed)
        share = remaining / len(flexible) if flexible else 0.0
        return [item.size if item.kind == "fixed" else
                min(item.maximum, max(item.minimum, share)) for item in expanded]

    def metrics(self, proposal: Size) -> tuple[list[float], list[float]]:
        widths = self.column_widths(proposal.width)
        views = self.children()
        heights = []
        for row_start in range(0, len(views), len(widths)):
            row = views[row_start:row_start + len(widths)]
            heights.append(max((measure(view, Size(widths[index], float("inf"))).height
                                for index, view in enumerate(row)), default=0.0))
        return widths, heights

    def size_that_fits(self, proposal: Size) -> Size:
        widths, heights = self.metrics(proposal)
        return Size(sum(widths) + sum(self.column_spacings(proposal.width)),
                    sum(heights) + self.row_spacing * max(0, len(heights) - 1))

    def placements(self, origin: Point, size: Size):
        widths, heights = self.metrics(size)
        tracks = self.resolved_columns(size.width)
        gaps = self.column_spacings(size.width)
        views = self.children()
        result = []
        y = origin.y
        index = 0
        for row_height in heights:
            x = origin.x
            for column, width in enumerate(widths):
                if index >= len(views):
                    break
                child = views[index]
                natural = measure(child, Size(width, row_height))
                child_width = min(width, natural.width)
                alignment = tracks[column].alignment
                dx = width - child_width if alignment == "trailing" else (
                    (width - child_width) / 2 if alignment in ("center", "automatic") else 0.0)
                result.append((child, Point(x + dx, y), Size(child_width, row_height)))
                x += width + (gaps[column] if column < len(gaps) else 0.0)
                index += 1
            y += row_height + self.row_spacing
        return result

    def place(self, origin: Point, size: Size) -> None:
        for child, point, child_size in self.placements(origin, size):
            child.place(point, child_size)


class LazyHGrid(View):
    """A horizontal grid whose fixed/flexible/adaptive tracks are rows.

    Items fill each column from top to bottom, matching SwiftUI's
    ``LazyHGrid`` ordering. Views are created by ``ForEach`` so stable IDs
    preserve their identity when the input sequence changes.
    """

    def __init__(self, data: Sequence[Any], rows: Sequence[GridItem],
                 content: Callable[[Any], View], id=None,
                 spacing: float = 12.0, column_spacing: float = 12.0):
        self.rows = list(rows)
        if not self.rows or not all(isinstance(item, GridItem) for item in self.rows):
            raise ValueError("LazyHGrid requires at least one GridItem")
        self._foreach = ForEach(data, content, id=id)
        self.spacing = max(0.0, float(spacing))
        self.column_spacing = max(0.0, float(column_spacing))

    def children(self):
        return self._foreach.children()

    def visible_children(self, offset: float, viewport: float, available_height: float,
                         column_extent: float = 120.0, overscan: int = 2):
        rows = max(1, len(self.resolved_rows(available_height)))
        extent = max(1.0, float(column_extent) + self.column_spacing)
        margin = max(0, int(overscan))
        start_column = max(0, int(float(offset) // extent) - margin)
        column_count = max(1, int(ceil(max(0.0, float(viewport)) / extent)) + 2 * margin)
        start = start_column * rows
        end = min(len(self._foreach.data), (start_column + column_count) * rows)
        return start, self._foreach.children_range(start, end)

    def resolved_rows(self, available_height: float) -> list[GridItem]:
        available_height = float(available_height)
        finite_height = available_height != float("inf")
        available_height = max(0.0, available_height) if finite_height else 0.0
        expanded: list[GridItem] = []
        for item in self.rows:
            if item.kind == "adaptive":
                gap = self.spacing if item.spacing is None else item.spacing
                count = (max(1, floor((available_height + gap) /
                                      (item.minimum + gap)))
                         if finite_height else 1)
                expanded.extend([GridItem.flexible(item.minimum, item.maximum,
                                                    item.spacing, item.alignment)] * count)
            else:
                expanded.append(item)
        return expanded

    def row_spacings(self, available_height: float) -> list[float]:
        tracks = self.resolved_rows(available_height)
        return [self.spacing if item.spacing is None else item.spacing
                for item in tracks[:-1]]

    def row_heights(self, available_height: float) -> list[float]:
        finite_height = available_height != float("inf")
        expanded = self.resolved_rows(available_height)
        available_height = max(0.0, float(available_height)) if finite_height else 0.0
        spacing_total = sum(self.row_spacings(available_height if finite_height else float("inf")))
        fixed = sum(item.size for item in expanded if item.kind == "fixed")
        flexible = [item for item in expanded if item.kind == "flexible"]
        remaining = max(0.0, available_height - spacing_total - fixed)
        share = remaining / len(flexible) if flexible and finite_height else 0.0
        return [item.size if item.kind == "fixed" else
                min(item.maximum, max(item.minimum, share)) for item in expanded]

    def metrics(self, proposal: Size) -> tuple[list[float], list[float]]:
        heights = self.row_heights(proposal.height)
        views = self.children()
        widths = []
        for column_start in range(0, len(views), len(heights)):
            column = views[column_start:column_start + len(heights)]
            widths.append(max((measure(view, Size(float("inf"), heights[index])).width
                               for index, view in enumerate(column)), default=0.0))
        return widths, heights

    def size_that_fits(self, proposal: Size) -> Size:
        widths, heights = self.metrics(proposal)
        return Size(sum(widths) + self.column_spacing * max(0, len(widths) - 1),
                    sum(heights) + sum(self.row_spacings(proposal.height)))

    def placements(self, origin: Point, size: Size):
        widths, heights = self.metrics(size)
        tracks = self.resolved_rows(size.height)
        gaps = self.row_spacings(size.height)
        views = self.children()
        result = []
        index = 0
        x = origin.x
        for column_width in widths:
            y = origin.y
            for row, row_height in enumerate(heights):
                if index >= len(views):
                    break
                child = views[index]
                natural = measure(child, Size(column_width, row_height))
                child_height = min(row_height, natural.height)
                alignment = tracks[row].alignment
                dy = row_height - child_height if alignment == "bottom" else (
                    (row_height - child_height) / 2 if alignment in ("center", "automatic") else 0.0)
                result.append((child, Point(x, y + dy), Size(column_width, child_height)))
                index += 1
                y += row_height + (gaps[row] if row < len(gaps) else 0.0)
            x += column_width + self.column_spacing
        return result

    def place(self, origin: Point, size: Size) -> None:
        for child, point, child_size in self.placements(origin, size):
            child.place(point, child_size)


__all__ = ["GridItem", "LazyHGrid", "LazyHStack", "LazyVGrid", "LazyVStack"]
