"""Value-driven navigation primitives inspired by SwiftUI."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .geometry import Color, Point, Size
from .view import View, ViewModifier, _ModifiedContent, _apply


class NavigationBarTitleDisplayMode:
    AUTOMATIC = "automatic"
    INLINE = "inline"
    LARGE = "large"


@dataclass(frozen=True)
class NavigationConfiguration:
    title: Optional[str] = None
    display_mode: str = NavigationBarTitleDisplayMode.AUTOMATIC
    visible: bool = True
    background: Optional[Color] = None


class NavigationModifier(ViewModifier):
    def __init__(self, kind: str, value: Any):
        self.kind = kind
        self.value = value

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


def navigation_title(view: View, title: str) -> View:
    return _apply(view, NavigationModifier("title", str(title)))


def navigation_bar_title_display_mode(view: View, mode: str) -> View:
    if mode not in (NavigationBarTitleDisplayMode.AUTOMATIC,
                    NavigationBarTitleDisplayMode.INLINE,
                    NavigationBarTitleDisplayMode.LARGE):
        raise ValueError("navigation title display mode must be automatic, inline, or large")
    return _apply(view, NavigationModifier("display_mode", mode))


def navigation_bar_hidden(view: View, hidden: bool = True) -> View:
    return _apply(view, NavigationModifier("visible", not bool(hidden)))


def navigation_bar_background(view: View, color: Optional[Color]) -> View:
    if color is not None and not isinstance(color, Color):
        raise TypeError("navigation bar background must be a Color or None")
    return _apply(view, NavigationModifier("background", color))


def navigation_configuration(view: View) -> NavigationConfiguration:
    """Read the effective destination-level navigation metadata."""
    values: dict[str, Any] = {}
    node = view
    while isinstance(node, _ModifiedContent):
        modifier = node._modifier
        if isinstance(modifier, NavigationModifier) and modifier.kind not in values:
            values[modifier.kind] = modifier.value
        node = node._content
    return NavigationConfiguration(**values)


class NavigationPath:
    """A mutable stack of hashable navigation values.

    Views describe destinations for value types; pushing a value chooses the
    matching destination.  The path itself contains no backend-specific code.
    """

    def __init__(self, values: Iterable[Any] = ()):
        self._values = list(values)
        self._listeners: list[Callable[["NavigationPath"], None]] = []

    def append(self, value: Any) -> None:
        try:
            hash(value)
        except TypeError as exc:
            raise TypeError("NavigationPath values must be hashable") from exc
        self._values.append(value)
        self._notify()

    def remove_last(self, count: int = 1) -> None:
        count = int(count)
        if count < 0:
            raise ValueError("count must be non-negative")
        if count > len(self._values):
            raise IndexError("cannot remove more navigation values than the path contains")
        if count:
            del self._values[-count:]
            self._notify()

    def clear(self) -> None:
        if self._values:
            self._values.clear()
            self._notify()

    @property
    def last(self) -> Any:
        return self._values[-1] if self._values else None

    def subscribe(self, listener: Callable[["NavigationPath"], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def cancel() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return cancel

    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener(self)

    def __len__(self) -> int:
        return len(self._values)

    def __iter__(self) -> Iterator[Any]:
        return iter(tuple(self._values))

    def __getitem__(self, index):
        return self._values[index]

    def __repr__(self) -> str:
        return f"NavigationPath({self._values!r})"


__all__ = [
    "NavigationBarTitleDisplayMode", "NavigationConfiguration", "NavigationModifier",
    "NavigationPath", "navigation_bar_background", "navigation_bar_hidden",
    "navigation_bar_title_display_mode", "navigation_configuration", "navigation_title",
]
