"""A UI backend that renders aUI views as plain-text ASCII art.

This backend requires no display and no third-party dependencies. It is used
for tests, documentation examples and headless rendering.

It also exposes the aUI accessibility tree via ``describe_accessibility()``
so headless tooling and documentation can inspect the semantic structure.
"""
from __future__ import annotations

from typing import List, Optional

from ..core.accessibility import AccessibilityInfo, describe_accessibility as _describe_accessibility
from ..core.components import (
    Button,
    DatePicker,
    Divider,
    Form,
    Image,
    NavigationStack,
    Picker,
    ProgressView,
    Slider,
    Stepper,
    Text,
    TextField,
    Toggle,
)
from ..core.geometry import Point, Size
from ..core.layout import HStack, Spacer, VStack, ZStack
from ..core.view import View, _Frame, _ModifiedContent


class AsciiBackend:
    """Renders a view tree to a text canvas."""

    def __init__(self, width: int = 60, height: int = 20):
        self.width = width
        self.height = height
        self._canvas: List[List[str]] = [
            [" "] * width for _ in range(height)
        ]

    # -- Public API ---------------------------------------------------------
    def render(self, view: View) -> str:
        size = Size(self.width, self.height)
        self._draw(view, 0, 0, size)
        return self._snapshot()

    def describe_accessibility(self, view: View) -> AccessibilityInfo:
        """Return the accessibility tree for ``view`` (headless inspection)."""
        return _describe_accessibility(view)

    # -- Drawing ------------------------------------------------------------
    def _draw(self, view: View, x: int, y: int, size: Size) -> None:
        if isinstance(view, _ModifiedContent):
            self._draw(view.body(), x, y, size)
            return
        if isinstance(view, _Frame):
            self._draw(view._content, x, y, size)
            return

        if isinstance(view, VStack):
            self._draw_stack(view, x, y, size, vertical=True)
        elif isinstance(view, HStack):
            self._draw_stack(view, x, y, size, vertical=False)
        elif isinstance(view, ZStack):
            for child in view.children():
                self._draw(child, x, y, size)
        elif isinstance(view, Text):
            self._put(x, y, view.content[: max(0, self.width - x)])
        elif isinstance(view, Button):
            self._box(x, y, view.title)
        elif isinstance(view, TextField):
            self._put(x, y, "[" + view.placeholder + "]"[: max(0, self.width - x)])
        elif isinstance(view, Toggle):
            self._put(x, y, "[x] " + view.title)
        elif isinstance(view, Slider):
            self._put(x, y, "-----o-----")
        elif isinstance(view, Picker):
            self._put(x, y, "< " + view.title + " >")
        elif isinstance(view, Divider):
            self._hline(x, y, min(size.width, self.width - x))
        elif isinstance(view, Image):
            self._put(x, y, "(img)")
        elif isinstance(view, DatePicker):
            self._put(x, y, "[ " + view.title + " " + view._current() + " ]")
        elif isinstance(view, Stepper):
            self._put(x, y, "[- " + view.title + " +]")
        elif isinstance(view, ProgressView):
            self._draw_progress(view, x, y, size)
        elif isinstance(view, NavigationStack):
            self._put(x, y, "== " + view.title + " ==")
            for child in view.children():
                self._draw(child, x, y + 1, size)
        elif isinstance(view, Form):
            cy = y
            for child in view.children():
                self._draw(child, x, cy, size)
                cy += 1
        elif isinstance(view, Spacer):
            return
        else:
            # Generic container: draw children.
            for child in view.children():
                self._draw(child, x, y, size)

    def _draw_stack(self, stack, x: int, y: int, size: Size, vertical: bool) -> None:
        children = stack.children()
        if not children:
            return
        # Simple fixed distribution for ASCII preview.
        if vertical:
            each = max(1, int(size.height // len(children)))
            cy = y
            for child in children:
                self._draw(child, x, cy, Size(size.width, each))
                cy += each
        else:
            each = max(1, int(size.width // len(children)))
            cx = x
            for child in children:
                self._draw(child, cx, y, Size(each, size.height))
                cx += each

    # -- Primitives ---------------------------------------------------------
    def _put(self, x: int, y: int, text: str) -> None:
        if not (0 <= y < self.height):
            return
        for i, ch in enumerate(text):
            cx = x + i
            if 0 <= cx < self.width:
                self._canvas[y][cx] = ch

    def _hline(self, x: int, y: int, length: float) -> None:
        self._put(x, y, "-" * max(0, int(length)))

    def _box(self, x: int, y: int, label: str) -> None:
        text = " " + label + " "
        self._put(x, y, "[" + text[: max(0, self.width - x - 2)] + "]")

    def _draw_progress(self, view: ProgressView, x: int, y: int, size: Size) -> None:
        total = max(1, int(min(size.width, self.width - x) - 2))
        if view.value is None:
            self._put(x, y, "[" + "?" * total + "]")
            return
        ratio = max(0.0, min(1.0, view.value))
        filled = int(round(ratio * total))
        self._put(x, y, "[" + "#" * filled + "-" * (total - filled) + "]")

    def _snapshot(self) -> str:
        return "\n".join("".join(row).rstrip() for row in self._canvas)
