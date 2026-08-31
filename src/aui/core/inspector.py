"""SwiftUI-like trailing inspector presentation and layout."""
from __future__ import annotations

from typing import Callable

from .geometry import Color, Point, Size
from .state import Binding
from .view import View


class InspectorView(View):
    def __init__(self, content: View, is_presented: Binding[bool], inspector,
                 minimum: float = 220.0, ideal: float = 280.0,
                 maximum: float = 420.0, compact_threshold: float = 600.0,
                 background: Color | None = None):
        if not isinstance(content, View):
            raise TypeError("inspector content must be a View")
        if not isinstance(is_presented, Binding):
            raise TypeError("inspector is_presented must be a Binding")
        panel = inspector() if callable(inspector) else inspector
        if not isinstance(panel, View):
            raise TypeError("inspector builder must produce a View")
        self.content = content
        self.inspector_content = panel
        self.is_presented = is_presented
        self.minimum, self.ideal, self.maximum = self._validate_widths(
            minimum, ideal, maximum
        )
        self.compact_threshold = max(1.0, float(compact_threshold))
        self.background = background
        self.divider_width = 1.0
        self._children = [content, panel]

    @staticmethod
    def _validate_widths(minimum, ideal, maximum):
        values = tuple(map(float, (minimum, ideal, maximum)))
        if values[0] <= 0 or not values[0] <= values[1] <= values[2]:
            raise ValueError("inspector widths must satisfy 0 < minimum <= ideal <= maximum")
        return values

    @property
    def presented(self) -> bool:
        return bool(self.is_presented.wrapped_value)

    def dismiss(self) -> None:
        self.is_presented.wrapped_value = False

    def column_widths(self, available: float) -> tuple[float, float]:
        width = max(0.0, float(available))
        if not self.presented:
            return width, 0.0
        if width < self.compact_threshold:
            return 0.0, width
        panel = min(self.maximum, max(self.minimum, self.ideal))
        panel = min(panel, max(0.0, width - self.minimum - self.divider_width))
        return max(0.0, width - panel - self.divider_width), panel

    def inspector_column_width(self, minimum: float, ideal: float,
                               maximum: float) -> "InspectorView":
        self.minimum, self.ideal, self.maximum = self._validate_widths(
            minimum, ideal, maximum
        )
        return self

    def inspector_background(self, color: Color | None) -> "InspectorView":
        if color is not None and not isinstance(color, Color):
            raise TypeError("inspector background must be a Color or None")
        self.background = color
        return self

    def size_that_fits(self, proposal: Size) -> Size:
        width = proposal.width
        if width == float("inf"):
            content_size = self.content.size_that_fits(proposal)
            width = content_size.width + (self.ideal + self.divider_width if self.presented else 0)
        main, panel = self.column_widths(width)
        heights = [self.content.size_that_fits(Size(main, proposal.height)).height]
        if panel:
            heights.append(self.inspector_content.size_that_fits(Size(panel, proposal.height)).height)
        height = max(heights, default=0.0)
        if proposal.height != float("inf"):
            height = max(height, proposal.height)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        main, panel = self.column_widths(size.width)
        if main:
            self.content.place(origin, Size(main, size.height))
        if panel:
            x = origin.x if main == 0 else origin.x + main + self.divider_width
            self.inspector_content.place(Point(x, origin.y), Size(panel, size.height))


def inspector(view: View, is_presented: Binding[bool], content,
              minimum: float = 220.0, ideal: float = 280.0,
              maximum: float = 420.0, compact_threshold: float = 600.0) -> InspectorView:
    return InspectorView(view, is_presented, content, minimum, ideal, maximum,
                         compact_threshold)


__all__ = ["InspectorView", "inspector"]
