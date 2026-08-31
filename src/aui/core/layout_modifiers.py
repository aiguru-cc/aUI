"""Advanced SwiftUI-style layout adjustment modifiers."""
from __future__ import annotations

from typing import Optional

from .geometry import EdgeInsets, Point, Size
from .view import View, ViewModifier, _ModifiedContent, _apply


class LayoutPriorityModifier(ViewModifier):
    def __init__(self, priority: float):
        self.priority = float(priority)

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class FixedSizeModifier(ViewModifier):
    def __init__(self, horizontal: bool = True, vertical: bool = True):
        self.horizontal = bool(horizontal)
        self.vertical = bool(vertical)

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        child_proposal = Size(
            float("inf") if self.horizontal else proposal.width,
            float("inf") if self.vertical else proposal.height,
        )
        return content.size_that_fits(child_proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, content.size_that_fits(size))


class OffsetModifier(ViewModifier):
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(Point(origin.x + self.x, origin.y + self.y), size)


class PositionModifier(ViewModifier):
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        child = content.size_that_fits(size)
        content.place(
            Point(origin.x + self.x - child.width / 2.0,
                  origin.y + self.y - child.height / 2.0),
            child,
        )


class ZIndexModifier(ViewModifier):
    def __init__(self, value: float):
        self.value = float(value)

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class AspectRatioModifier(ViewModifier):
    def __init__(self, ratio: Optional[float], content_mode: str = "fit"):
        if ratio is not None and float(ratio) <= 0:
            raise ValueError("aspect ratio must be positive")
        if content_mode not in ("fit", "fill"):
            raise ValueError("content_mode must be fit or fill")
        self.ratio = float(ratio) if ratio is not None else None
        self.content_mode = content_mode

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        natural = content.size_that_fits(proposal)
        ratio = self.ratio or (natural.width / natural.height if natural.height else 1.0)
        width = natural.width if proposal.width == float("inf") else proposal.width
        height = natural.height if proposal.height == float("inf") else proposal.height
        if width <= 0 or height <= 0:
            return Size(width, height)
        proposed_ratio = width / height
        if self.content_mode == "fit":
            if proposed_ratio > ratio:
                width = height * ratio
            else:
                height = width / ratio
        else:
            if proposed_ratio < ratio:
                width = height * ratio
            else:
                height = width / ratio
        return Size(width, height)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class SafeAreaInsetModifier(ViewModifier):
    EDGES = {"top", "leading", "bottom", "trailing"}

    def __init__(self, edge: str, length: float):
        if edge not in self.EDGES:
            raise ValueError("safe area edge must be top, leading, bottom, or trailing")
        if length < 0:
            raise ValueError("safe area inset length cannot be negative")
        self.edge = edge
        self.length = float(length)
        self.insets = EdgeInsets(**{edge: self.length})

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        inner = content.size_that_fits(proposal.deflated_by(self.insets))
        return inner.expanded_by(self.insets)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(
            Point(origin.x + self.insets.leading, origin.y + self.insets.top),
            size.deflated_by(self.insets),
        )


class IgnoresSafeAreaModifier(ViewModifier):
    def __init__(self, edges="all"):
        valid = {"all", "top", "leading", "bottom", "trailing"}
        values = (edges,) if isinstance(edges, str) else tuple(edges)
        if not values or not set(values) <= valid:
            raise ValueError("unsupported safe area edge")
        self.edges = values

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


def layout_priority(view: View, priority: float) -> View:
    return _apply(view, LayoutPriorityModifier(priority))


def fixed_size(view: View, horizontal: bool = True, vertical: bool = True) -> View:
    return _apply(view, FixedSizeModifier(horizontal, vertical))


def offset(view: View, x: float = 0.0, y: float = 0.0) -> View:
    return _apply(view, OffsetModifier(x, y))


def position(view: View, x: float, y: float) -> View:
    return _apply(view, PositionModifier(x, y))


def z_index(view: View, value: float) -> View:
    return _apply(view, ZIndexModifier(value))


def aspect_ratio(view: View, ratio: Optional[float] = None,
                 content_mode: str = "fit") -> View:
    return _apply(view, AspectRatioModifier(ratio, content_mode))


def safe_area_inset(view: View, edge: str, length: float) -> View:
    return _apply(view, SafeAreaInsetModifier(edge, length))


def ignores_safe_area(view: View, edges="all") -> View:
    return _apply(view, IgnoresSafeAreaModifier(edges))


def layout_priority_of(view: View) -> float:
    node = view
    while isinstance(node, _ModifiedContent):
        if isinstance(node._modifier, LayoutPriorityModifier):
            return node._modifier.priority
        node = node._content
    return 0.0


def z_index_of(view: View) -> float:
    node = view
    while isinstance(node, _ModifiedContent):
        if isinstance(node._modifier, ZIndexModifier):
            return node._modifier.value
        node = node._content
    return 0.0


def z_ordered(children):
    return sorted(enumerate(children), key=lambda pair: (z_index_of(pair[1]), pair[0]))


__all__ = [
    "AspectRatioModifier", "FixedSizeModifier", "IgnoresSafeAreaModifier",
    "LayoutPriorityModifier", "OffsetModifier", "PositionModifier",
    "SafeAreaInsetModifier", "ZIndexModifier", "aspect_ratio", "fixed_size",
    "ignores_safe_area", "layout_priority", "offset", "position",
    "safe_area_inset", "z_index",
]
