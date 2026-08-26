"""The core View protocol and base view types for aUI.

This module defines the declarative contract that every aUI view implements.
It mirrors SwiftUI's `View` protocol: a view knows how to propose a size to
its children, receive a size, and render itself.
"""
from __future__ import annotations

import abc
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .geometry import EdgeInsets, Point, Size


class View(abc.ABC):
    """Base class for all aUI views.

    A view is a lightweight, immutable description of a piece of UI. It is
    evaluated (``body``) and laid out by a backend, never stored directly in a
    widget tree. This mirrors SwiftUI's value-semantics views.
    """

    #: Cached list of child views (subclasses fill this in ``__init__``).
    _children: List["View"] = []

    #: Modifiers applied to this view, in application order.
    modifiers: List["ViewModifier"] = []

    def body(self) -> "View":  # pragma: no cover - overridden by subclasses
        return self

    def _content(self) -> "View":
        """The effective content after applying modifiers."""
        content: View = self
        for mod in self.modifiers:
            content = mod.body(content)
        return content

    # -- Layout protocol (mirrors SwiftUI's proposal/response) -------------
    def size_that_fits(self, proposal: Size) -> Size:
        """Return the size this view would take given a size proposal."""
        raise NotImplementedError

    def place(self, origin: Point, size: Size) -> None:
        """Position this view within its allocated frame. No-op by default."""
        return None

    # -- Tree helpers -------------------------------------------------------
    def children(self) -> Sequence["View"]:
        return self._children

    def flatten(self) -> List["View"]:
        """Depth-first list of this view and all descendants."""
        result: List[View] = [self]
        for child in self.children():
            result.extend(child.flatten())
        return result

    def find(self, predicate: Callable[["View"], bool]) -> Optional["View"]:
        for view in self.flatten():
            if predicate(view):
                return view
        return None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__}>"


class ViewModifier(abc.ABC):
    """Base class for view modifiers (mirrors SwiftUI's ViewModifier)."""

    def body(self, content: View) -> View:
        return content


class _ModifiedContent(View):
    """Wraps a content view together with a modifier (internal)."""

    def __init__(self, content: View, modifier: ViewModifier):
        self._content = content
        self._modifier = modifier
        self.modifiers = list(content.modifiers) + [modifier]
        self._children = [content]

    def body(self) -> View:
        # Use the base View._content explicitly: subclasses (e.g. Text) store
        # their payload in a ``_content`` attribute that shadows the method.
        return View._content(self._content)

    def size_that_fits(self, proposal: Size) -> Size:
        return self._modifier.size_that_fits(self._content, proposal)

    def place(self, origin: Point, size: Size) -> None:
        self._modifier.place(self._content, origin, size)

    def children(self) -> Sequence[View]:
        return self._children


def _apply(view: View, modifier: ViewModifier) -> View:
    """Attach a modifier to a view, returning the (possibly wrapped) view."""
    if isinstance(modifier, FrameModifier):
        return modifier.apply(view)
    wrapped = _ModifiedContent(view, modifier)
    return wrapped


class FrameModifier(ViewModifier):
    """The .frame() modifier — the only modifier that must wrap structurally."""

    def __init__(
        self,
        width: Optional[float] = None,
        height: Optional[float] = None,
        alignment: str = "center",
    ):
        self.width = width
        self.height = height
        self.alignment = alignment

    def apply(self, content: View) -> View:
        return _Frame(content, self.width, self.height, self.alignment)

    def body(self, content: View) -> View:
        return _Frame(content, self.width, self.height, self.alignment)


class _Frame(View):
    """A view that proposes a fixed size to its child and aligns it."""

    def __init__(self, content: View, width: Optional[float], height: Optional[float], alignment: str):
        self._content = content
        self._width = width
        self._height = height
        self._alignment = alignment
        self._children = [content]

    def size_that_fits(self, proposal: Size) -> Size:
        w = self._width if self._width is not None else proposal.width
        h = self._height if self._height is not None else proposal.height
        return Size(w, h)

    def place(self, origin: Point, size: Size) -> None:
        child_size = self._content.size_that_fits(size)
        x, y = _aligned_offset(size, child_size, self._alignment)
        self._content.place(Point(origin.x + x, origin.y + y), child_size)

    def children(self) -> Sequence[View]:
        return self._children


def _aligned_offset(container: Size, child: Size, alignment: str) -> Tuple[float, float]:
    """Compute the offset of a child within a container for an alignment."""
    alignments = {
        "topLeading": (0.0, 0.0),
        "top": (0.5, 0.0),
        "topTrailing": (1.0, 0.0),
        "leading": (0.0, 0.5),
        "center": (0.5, 0.5),
        "trailing": (1.0, 0.5),
        "bottomLeading": (0.0, 1.0),
        "bottom": (0.5, 1.0),
        "bottomTrailing": (1.0, 1.0),
    }
    fx, fy = alignments.get(alignment, (0.5, 0.5))
    return (container.width - child.width) * fx, (container.height - child.height) * fy
