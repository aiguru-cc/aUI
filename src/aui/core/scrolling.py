"""Programmatic scrolling and stable view identifiers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .geometry import EdgeInsets, Point, Size
from .state import Binding
from .view import View, ViewModifier, _ModifiedContent, _apply


class ScrollIndicatorVisibility:
    AUTOMATIC = "automatic"
    VISIBLE = "visible"
    HIDDEN = "hidden"


class ScrollTargetBehavior:
    AUTOMATIC = "automatic"
    PAGING = "paging"
    VIEW_ALIGNED = "viewAligned"


@dataclass(frozen=True)
class ScrollConfiguration:
    indicators: str = ScrollIndicatorVisibility.AUTOMATIC
    default_anchor: str = "top"
    target_behavior: str = ScrollTargetBehavior.AUTOMATIC
    clip_disabled: bool = False
    margins: EdgeInsets = EdgeInsets()
    position: Optional[Binding] = None
    position_anchor: str = "top"


class ScrollModifier(ViewModifier):
    def __init__(self, kind: str, value: Any):
        self.kind = kind
        self.value = value

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        if self.kind == "margins":
            return content.size_that_fits(proposal.deflated_by(self.value)).expanded_by(self.value)
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        if self.kind == "margins":
            content.place(Point(origin.x + self.value.leading, origin.y + self.value.top),
                          size.deflated_by(self.value))
        else:
            content.place(origin, size)


class IDModifier(ViewModifier):
    def __init__(self, value: Any):
        try:
            hash(value)
        except TypeError as exc:
            raise TypeError("view id must be hashable") from exc
        self.value = value

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class ScrollViewProxy:
    """A backend-neutral handle for requesting a scroll position."""

    def __init__(self):
        self._listeners: list[Callable[[Any, str], None]] = []
        self._last_request = None

    def scroll_to(self, view_id: Any, anchor: str = "top") -> None:
        if anchor not in ("top", "center", "bottom"):
            raise ValueError("scroll anchor must be top, center, or bottom")
        self._last_request = (view_id, anchor)
        for listener in tuple(self._listeners):
            listener(view_id, anchor)

    @property
    def last_request(self):
        return self._last_request

    def subscribe(self, listener: Callable[[Any, str], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def cancel() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return cancel


class ScrollViewReader(View):
    """Provides a ``ScrollViewProxy`` to a declarative content builder."""

    def __init__(self, content: Callable[[ScrollViewProxy], View]):
        if not callable(content):
            raise TypeError("ScrollViewReader content must be callable")
        self.proxy = ScrollViewProxy()
        self.content = content(self.proxy)
        if not isinstance(self.content, View):
            raise TypeError("ScrollViewReader content must return a View")
        self._children = [self.content]

    def size_that_fits(self, proposal: Size) -> Size:
        return self.content.size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        self.content.place(origin, size)

    def children(self):
        return self._children


def view_id(view: View, value: Any) -> View:
    return _apply(view, IDModifier(value))


def _anchor(value: str) -> str:
    if value not in ("top", "center", "bottom"):
        raise ValueError("scroll anchor must be top, center, or bottom")
    return value


def scroll_indicators(view: View, visibility: str) -> View:
    if visibility not in (ScrollIndicatorVisibility.AUTOMATIC,
                           ScrollIndicatorVisibility.VISIBLE,
                           ScrollIndicatorVisibility.HIDDEN):
        raise ValueError("scroll indicators must be automatic, visible, or hidden")
    return _apply(view, ScrollModifier("indicators", visibility))


def default_scroll_anchor(view: View, anchor: str) -> View:
    return _apply(view, ScrollModifier("default_anchor", _anchor(anchor)))


def scroll_target_behavior(view: View, behavior: str) -> View:
    if behavior not in (ScrollTargetBehavior.AUTOMATIC, ScrollTargetBehavior.PAGING,
                        ScrollTargetBehavior.VIEW_ALIGNED):
        raise ValueError("scroll target behavior must be automatic, paging, or viewAligned")
    return _apply(view, ScrollModifier("target_behavior", behavior))


def scroll_clip_disabled(view: View, disabled: bool = True) -> View:
    return _apply(view, ScrollModifier("clip_disabled", bool(disabled)))


def content_margins(view: View, margins: EdgeInsets | float) -> View:
    value = EdgeInsets.all(float(margins)) if isinstance(margins, (int, float)) else margins
    if not isinstance(value, EdgeInsets):
        raise TypeError("content margins must be EdgeInsets or a number")
    return _apply(view, ScrollModifier("margins", value))


def scroll_position(view: View, position: Binding, anchor: str = "top") -> View:
    if not isinstance(position, Binding):
        raise TypeError("scroll position must be a Binding")
    return _apply(_apply(view, ScrollModifier("position", position)),
                  ScrollModifier("position_anchor", _anchor(anchor)))


def scroll_configuration(view: View) -> ScrollConfiguration:
    values = {}
    node = view
    while isinstance(node, _ModifiedContent):
        modifier = node._modifier
        if isinstance(modifier, ScrollModifier) and modifier.kind not in values:
            values[modifier.kind] = modifier.value
        node = node._content
    return ScrollConfiguration(**values)


def find_scroll_configuration(view: View) -> Optional[ScrollConfiguration]:
    for node in view.flatten():
        if isinstance(node, _ModifiedContent) and isinstance(node._modifier, ScrollModifier):
            return scroll_configuration(node)
    return None


__all__ = [
    "IDModifier", "ScrollConfiguration", "ScrollIndicatorVisibility", "ScrollModifier",
    "ScrollTargetBehavior", "ScrollViewProxy", "ScrollViewReader", "content_margins",
    "default_scroll_anchor", "find_scroll_configuration", "scroll_clip_disabled",
    "scroll_configuration", "scroll_indicators", "scroll_position",
    "scroll_target_behavior", "view_id",
]
