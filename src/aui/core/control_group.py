"""Compact groups of related controls."""
from __future__ import annotations

from typing import Sequence

from .layout import HStack
from .view import View


class ControlGroup(HStack):
    """A horizontal, semantically related group of controls."""

    def __init__(self, controls: Sequence[View] = (), label: str = "",
                 spacing: float = 0.0):
        values = list(controls)
        if not all(isinstance(item, View) for item in values):
            raise TypeError("ControlGroup controls must be Views")
        if not values:
            raise ValueError("ControlGroup requires at least one control")
        self.label = str(label)
        super().__init__(values, spacing=max(0.0, float(spacing)), alignment="center")


__all__ = ["ControlGroup"]
