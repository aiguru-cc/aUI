"""Gradients, materials and visual-effect view modifiers."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .geometry import Color, Point, Size
from .view import View, ViewModifier, _apply


@dataclass(frozen=True)
class GradientStop:
    color: Color
    location: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "location", max(0.0, min(1.0, float(self.location))))


class Gradient(View):
    def __init__(self, colors: Sequence[Color] = (), stops: Sequence[GradientStop] = (),
                 size: Size = Size(240.0, 120.0)):
        if stops:
            self.stops = sorted(stops, key=lambda stop: stop.location)
        else:
            palette = list(colors)
            if len(palette) < 2:
                raise ValueError("a gradient requires at least two colors or stops")
            denominator = max(1, len(palette) - 1)
            self.stops = [GradientStop(color, index / denominator)
                          for index, color in enumerate(palette)]
        self._size = size
        self._children = []

    def size_that_fits(self, proposal: Size) -> Size:
        return self._size

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self):
        return self._children

    def color_at(self, location: float) -> Color:
        """Interpolate a color at a normalized position for backend-neutral use."""
        value = max(0.0, min(1.0, float(location)))
        if value <= self.stops[0].location:
            return self.stops[0].color
        if value >= self.stops[-1].location:
            return self.stops[-1].color
        for left, right in zip(self.stops, self.stops[1:]):
            if value <= right.location:
                span = right.location - left.location
                amount = 0.0 if span == 0 else (value - left.location) / span
                return Color(
                    left.color.red + (right.color.red - left.color.red) * amount,
                    left.color.green + (right.color.green - left.color.green) * amount,
                    left.color.blue + (right.color.blue - left.color.blue) * amount,
                    left.color.alpha + (right.color.alpha - left.color.alpha) * amount,
                )
        return self.stops[-1].color


class LinearGradient(Gradient):
    def __init__(self, colors: Sequence[Color] = (), stops: Sequence[GradientStop] = (),
                 start_point: tuple = (0.0, 0.5), end_point: tuple = (1.0, 0.5),
                 size: Size = Size(240.0, 120.0)):
        super().__init__(colors, stops, size)
        self.start_point = tuple(map(float, start_point))
        self.end_point = tuple(map(float, end_point))


class RadialGradient(Gradient):
    def __init__(self, colors: Sequence[Color] = (), stops: Sequence[GradientStop] = (),
                 center: tuple = (0.5, 0.5), radius: float = 0.5,
                 size: Size = Size(240.0, 120.0), start_radius: float = 0.0,
                 end_radius: float | None = None):
        super().__init__(colors, stops, size)
        self.center = tuple(map(float, center))
        if len(self.center) != 2 or not all(isfinite(value) for value in self.center):
            raise ValueError("radial gradient center must contain two finite values")
        self.start_radius = max(0.0, float(start_radius))
        self.end_radius = max(0.0, float(radius if end_radius is None else end_radius))
        if self.end_radius < self.start_radius:
            raise ValueError("radial gradient end_radius cannot be smaller than start_radius")
        self.radius = self.end_radius

    def mapped_locations(self) -> list[float]:
        if self.end_radius == 0:
            return [stop.location for stop in self.stops]
        start = min(1.0, self.start_radius / self.end_radius)
        return [start + stop.location * (1.0 - start) for stop in self.stops]


class EllipticalGradient(Gradient):
    """A radial gradient expressed as fractions of an elliptical view bounds."""

    def __init__(self, colors: Sequence[Color] = (), stops: Sequence[GradientStop] = (),
                 center: tuple = (0.5, 0.5), start_radius_fraction: float = 0.0,
                 end_radius_fraction: float = 0.5,
                 size: Size = Size(240.0, 120.0)):
        super().__init__(colors, stops, size)
        self.center = tuple(map(float, center))
        if len(self.center) != 2 or not all(isfinite(value) for value in self.center):
            raise ValueError("elliptical gradient center must contain two finite values")
        self.start_radius_fraction = max(0.0, float(start_radius_fraction))
        self.end_radius_fraction = max(0.0, float(end_radius_fraction))
        if self.end_radius_fraction < self.start_radius_fraction:
            raise ValueError("elliptical gradient end radius cannot be smaller than start radius")

    def mapped_locations(self) -> list[float]:
        if self.end_radius_fraction == 0:
            return [stop.location for stop in self.stops]
        start = min(1.0, self.start_radius_fraction / self.end_radius_fraction)
        return [start + stop.location * (1.0 - start) for stop in self.stops]


class AngularGradient(Gradient):
    """A conic gradient rotating around ``center`` using degree angles."""

    def __init__(self, colors: Sequence[Color] = (), stops: Sequence[GradientStop] = (),
                 center: tuple = (0.5, 0.5), start_angle: float = 0.0,
                 end_angle: float = 360.0, size: Size = Size(240.0, 120.0)):
        super().__init__(colors, stops, size)
        self.center = tuple(map(float, center))
        if len(self.center) != 2 or not all(isfinite(value) for value in self.center):
            raise ValueError("angular gradient center must contain two finite values")
        self.start_angle = float(start_angle)
        self.end_angle = float(end_angle)
        if not isfinite(self.start_angle) or not isfinite(self.end_angle):
            raise ValueError("angular gradient angles must be finite")
        if self.end_angle <= self.start_angle:
            raise ValueError("angular gradient end_angle must exceed start_angle")

    @property
    def sweep_angle(self) -> float:
        return self.end_angle - self.start_angle


class Material:
    ULTRA_THIN = "ultraThin"
    THIN = "thin"
    REGULAR = "regular"
    THICK = "thick"
    ULTRA_THICK = "ultraThick"
    SIDEBAR = "sidebar"
    VALUES = {ULTRA_THIN, THIN, REGULAR, THICK, ULTRA_THICK, SIDEBAR}


class MaterialBackgroundModifier(ViewModifier):
    def __init__(self, material: str):
        if material not in Material.VALUES:
            raise ValueError(f"unsupported material: {material}")
        self.material = material

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class ShadowModifier(ViewModifier):
    def __init__(self, color: Color = Color(0, 0, 0, 0.25), radius: float = 6.0,
                 x: float = 0.0, y: float = 2.0):
        self.color = color
        self.radius = max(0.0, float(radius))
        self.x = float(x)
        self.y = float(y)

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class OverlayModifier(ViewModifier):
    def __init__(self, overlay: View, alignment: str = "center"):
        if not isinstance(overlay, View):
            raise TypeError("overlay must be a View")
        self.overlay = overlay
        self.alignment = alignment

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)
        overlay_size = self.overlay.size_that_fits(size)
        from .view import _aligned_offset
        dx, dy = _aligned_offset(size, overlay_size, self.alignment)
        self.overlay.place(Point(origin.x + dx, origin.y + dy), overlay_size)


def material_background(view: View, material: str = Material.REGULAR) -> View:
    return _apply(view, MaterialBackgroundModifier(material))


def shadow(view: View, color: Color = Color(0, 0, 0, 0.25), radius: float = 6.0,
           x: float = 0.0, y: float = 2.0) -> View:
    return _apply(view, ShadowModifier(color, radius, x, y))


def overlay(view: View, overlay_view: View, alignment: str = "center") -> View:
    return _apply(view, OverlayModifier(overlay_view, alignment))


__all__ = [
    "Gradient", "GradientStop", "LinearGradient", "Material",
    "MaterialBackgroundModifier", "OverlayModifier", "RadialGradient",
    "ShadowModifier", "material_background", "overlay", "shadow",
]
