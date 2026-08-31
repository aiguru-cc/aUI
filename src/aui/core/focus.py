"""Declarative focus state and focus-binding modifier."""
from __future__ import annotations

from typing import Any

from .geometry import Point, Size
from .state import Binding, State
from .view import View, ViewModifier, _apply


class FocusState(State):
    """State specialized for the currently focused field identifier."""


class FocusedModifier(ViewModifier):
    def __init__(self, binding: Binding, equals: Any = True):
        if not isinstance(binding, Binding):
            raise TypeError("focused binding must be a Binding")
        try:
            hash(equals)
        except TypeError as exc:
            raise TypeError("focused equals value must be hashable") from exc
        self.binding = binding
        self.equals = equals

    @property
    def is_focused(self) -> bool:
        return self.binding.wrapped_value == self.equals

    def activate(self) -> None:
        self.binding.wrapped_value = self.equals

    def deactivate(self) -> None:
        current = self.binding.wrapped_value
        if current == self.equals:
            self.binding.wrapped_value = False if isinstance(current, bool) else None

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


def focused(view: View, binding: Binding, equals: Any = True) -> View:
    return _apply(view, FocusedModifier(binding, equals))


__all__ = ["FocusState", "FocusedModifier", "focused"]
