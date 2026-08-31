"""SwiftUI-style badge modifier for list rows, tabs, and labels."""
from __future__ import annotations

from typing import Any

from .geometry import Point, Size
from .view import View, ViewModifier, _ModifiedContent, _apply


class BadgeModifier(ViewModifier):
    def __init__(self, value: Any):
        if value is None:
            raise ValueError("badge value cannot be None")
        self.value = value

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        base = content.size_that_fits(proposal)
        width = max(18.0, len(str(self.value)) * 7.0 + 10.0)
        return Size(base.width + 6.0 + width, max(base.height, 18.0))

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


def badge(view: View, value: Any) -> View:
    return _apply(view, BadgeModifier(value))


def badge_value(view: View):
    node = view
    while isinstance(node, _ModifiedContent):
        if isinstance(node._modifier, BadgeModifier):
            return node._modifier.value
        node = node._content
    return None


__all__ = ["BadgeModifier", "badge", "badge_value"]
