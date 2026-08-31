"""View lifecycle and form submission modifiers."""
from __future__ import annotations

import inspect
from typing import Callable

from .geometry import Point, Size
from .view import View, ViewModifier, _apply


class _EventModifier(ViewModifier):
    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class OnAppearModifier(_EventModifier):
    def __init__(self, action: Callable[[], None]):
        if not callable(action):
            raise TypeError("on_appear action must be callable")
        self.action = action


class OnDisappearModifier(_EventModifier):
    def __init__(self, action: Callable[[], None]):
        if not callable(action):
            raise TypeError("on_disappear action must be callable")
        self.action = action


class OnSubmitModifier(_EventModifier):
    def __init__(self, action: Callable[[], None]):
        if not callable(action):
            raise TypeError("on_submit action must be callable")
        self.action = action


class SubmitLabelModifier(_EventModifier):
    LABELS = {"return", "done", "go", "send", "search", "next", "continue", "join"}

    def __init__(self, label: str):
        if label not in self.LABELS:
            raise ValueError(f"unsupported submit label: {label}")
        self.label = label


class OnChangeModifier(_EventModifier):
    def __init__(self, value, action: Callable, initial: bool = False, key=None):
        if not callable(action):
            raise TypeError("on_change action must be callable")
        self.value = value
        self.action = action
        self.initial = bool(initial)
        self.key = key if key is not None else ("on_change", id(action))

    def current_value(self):
        return self.value() if callable(self.value) else self.value

    def call(self, old, new) -> None:
        count = len(inspect.signature(self.action).parameters)
        if count == 0:
            self.action()
        elif count == 1:
            self.action(new)
        else:
            self.action(old, new)


def on_appear(view: View, action: Callable[[], None]) -> View:
    return _apply(view, OnAppearModifier(action))


def on_disappear(view: View, action: Callable[[], None]) -> View:
    return _apply(view, OnDisappearModifier(action))


def on_submit(view: View, action: Callable[[], None]) -> View:
    return _apply(view, OnSubmitModifier(action))


def submit_label(view: View, label: str) -> View:
    return _apply(view, SubmitLabelModifier(label))


def on_change(view: View, value, action: Callable, initial: bool = False, key=None) -> View:
    return _apply(view, OnChangeModifier(value, action, initial, key))


def run_on_change(view: View, previous: dict) -> None:
    """Evaluate on-change modifiers using a backend-owned identity registry."""
    from .view import _ModifiedContent

    missing = object()

    def visit(node: View) -> None:
        if isinstance(node, _ModifiedContent):
            modifier = node._modifier
            if isinstance(modifier, OnChangeModifier):
                new = modifier.current_value()
                old = previous.get(modifier.key, missing)
                previous[modifier.key] = new
                if old is missing:
                    if modifier.initial:
                        modifier.call(None, new)
                elif old != new:
                    modifier.call(old, new)
            visit(node._content)
            return
        for child in node.children():
            visit(child)

    visit(view)


__all__ = [
    "OnAppearModifier", "OnChangeModifier", "OnDisappearModifier", "OnSubmitModifier",
    "SubmitLabelModifier", "on_appear", "on_change", "on_disappear", "on_submit",
    "run_on_change", "submit_label",
]
