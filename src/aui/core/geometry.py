"""Geometry primitives for aUI.

These are lightweight, immutable value objects used by the layout engine.
They mirror the core value types in SwiftUI (CGSize / CGPoint / EdgeInsets).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

Number = Union[int, float]


@dataclass(frozen=True)
class Size:
    width: float = 0.0
    height: float = 0.0

    def __post_init__(self) -> None:
        # Normalize negative sizes to zero (SwiftUI clamps proposals to >= 0).
        object.__setattr__(self, "width", max(0.0, float(self.width)))
        object.__setattr__(self, "height", max(0.0, float(self.height)))

    def __add__(self, other: "Size") -> "Size":
        return Size(self.width + other.width, self.height + other.height)

    def __sub__(self, other: "Size") -> "Size":
        return Size(self.width - other.width, self.height - other.height)

    def expanded_by(self, insets: "EdgeInsets") -> "Size":
        return Size(
            self.width + insets.horizontal,
            self.height + insets.vertical,
        )

    def deflated_by(self, insets: "EdgeInsets") -> "Size":
        return Size(
            max(0.0, self.width - insets.horizontal),
            max(0.0, self.height - insets.vertical),
        )


@dataclass(frozen=True)
class Point:
    x: float = 0.0
    y: float = 0.0


@dataclass(frozen=True)
class EdgeInsets:
    """Insets for each edge, mirroring SwiftUI EdgeInsets."""

    top: float = 0.0
    leading: float = 0.0
    bottom: float = 0.0
    trailing: float = 0.0

    @classmethod
    def all(cls, value: float) -> "EdgeInsets":
        return cls(top=value, leading=value, bottom=value, trailing=value)

    @classmethod
    def symmetric(cls, horizontal: float = 0.0, vertical: float = 0.0) -> "EdgeInsets":
        return cls(top=vertical, leading=horizontal, bottom=vertical, trailing=horizontal)

    @property
    def horizontal(self) -> float:
        return self.leading + self.trailing

    @property
    def vertical(self) -> float:
        return self.top + self.bottom


class Color:
    """A simple RGBA color, plus a small palette of SwiftUI-like named colors."""

    def __init__(self, red: float, green: float, blue: float, alpha: float = 1.0):
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha

    @classmethod
    def rgb(cls, red: int, green: int, blue: int, alpha: float = 1.0) -> "Color":
        return cls(red / 255.0, green / 255.0, blue / 255.0, alpha)

    @classmethod
    def hex(cls, value: str) -> "Color":
        """Parse '#RRGGBB' or 'RRGGBB'."""
        h = value.lstrip("#")
        if len(h) != 6:
            raise ValueError(f"Invalid hex color: {value!r}")
        return cls.rgb(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def to_tk(self) -> str:
        """Convert to a '#rrggbb' string for the Tkinter backend."""
        def channel(v: float) -> int:
            return max(0, min(255, int(round(v * 255))))
        return "#%02x%02x%02x" % (channel(self.red), channel(self.green), channel(self.blue))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Color({self.red:.2f},{self.green:.2f},{self.blue:.2f},{self.alpha:.2f})"


# SwiftUI-inspired named colors
Color.clear = Color(0, 0, 0, 0)
Color.black = Color(0, 0, 0)
Color.white = Color(1, 1, 1)
Color.red = Color(1, 0, 0)
Color.green = Color(0, 1, 0)
Color.blue = Color(0, 0, 1)
Color.gray = Color(0.5, 0.5, 0.5)
Color.orange = Color.rgb(255, 149, 0)
Color.yellow = Color.rgb(255, 204, 0)
Color.purple = Color.rgb(175, 82, 222)
Color.pink = Color.rgb(255, 45, 85)
Color.teal = Color.rgb(48, 176, 199)
Color.indigo = Color.rgb(88, 86, 214)
Color.primary = Color.black
Color.secondary = Color(0.45, 0.45, 0.45)


class Font:
    """Font descriptor. Size presets mirror SwiftUI's dynamic type sizes."""

    __slots__ = ("size", "weight", "family")

    WEIGHTS = {"regular": "normal", "medium": "bold", "bold": "bold", "semibold": "bold", "light": "normal"}

    def __init__(self, size: float = 14.0, weight: str = "regular", family: str = "TkDefaultFont"):
        self.size = float(size)
        self.weight = weight
        self.family = family

    @classmethod
    def system(cls, size: float = 14.0, weight: str = "regular") -> "Font":
        return cls(size=size, weight=weight)

    @classmethod
    def title(cls) -> "Font":
        return cls(size=28.0, weight="bold")

    @classmethod
    def headline(cls) -> "Font":
        return cls(size=17.0, weight="semibold")

    @classmethod
    def subheadline(cls) -> "Font":
        return cls(size=15.0, weight="regular")

    @classmethod
    def body(cls) -> "Font":
        return cls(size=14.0)

    @classmethod
    def caption(cls) -> "Font":
        return cls(size=11.0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Font(size={self.size}, weight={self.weight})"
