"""SwiftUI-inspired visual transforms, filters, clipping and compositing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .view import View, ViewModifier, _apply


class BlendMode:
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    COLOR_DODGE = "colorDodge"
    COLOR_BURN = "colorBurn"
    SOFT_LIGHT = "softLight"
    HARD_LIGHT = "hardLight"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"


@dataclass(frozen=True)
class ScaleEffectModifier(ViewModifier):
    x: float
    y: float
    anchor: str = "center"

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class RotationEffectModifier(ViewModifier):
    degrees: float
    anchor: str = "center"

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class Rotation3DEffectModifier(ViewModifier):
    degrees: float
    axis: tuple[float, float, float] = (0.0, 1.0, 0.0)
    perspective: float = 1.0 / 500.0

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class FilterModifier(ViewModifier):
    kind: str
    amount: float

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class BlendModeModifier(ViewModifier):
    mode: str

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class CompositingModifier(ViewModifier):
    drawing: bool = False
    opaque: bool = False
    color_mode: str = "nonLinear"

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class ClipModifier(ViewModifier):
    shape: Optional[View] = None
    antialiased: bool = True

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class MaskModifier(ViewModifier):
    mask_view: View

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def scale_effect(view: View, scale: float = 1.0, y: Optional[float] = None,
                 anchor: str = "center") -> View:
    return _apply(view, ScaleEffectModifier(float(scale), float(scale if y is None else y), anchor))


def rotation_effect(view: View, degrees: float, anchor: str = "center") -> View:
    return _apply(view, RotationEffectModifier(float(degrees), anchor))


def rotation_3d_effect(view: View, degrees: float, axis=(0.0, 1.0, 0.0),
                       perspective: float = 1.0 / 500.0) -> View:
    if len(axis) != 3:
        raise ValueError("rotation_3d_effect axis must contain x, y, z")
    return _apply(view, Rotation3DEffectModifier(float(degrees), tuple(map(float, axis)), float(perspective)))


def _filter(view: View, kind: str, amount: float) -> View:
    return _apply(view, FilterModifier(kind, float(amount)))


def blur(view: View, radius: float = 3.0) -> View: return _filter(view, "blur", max(0.0, radius))
def brightness(view: View, amount: float) -> View: return _filter(view, "brightness", amount)
def contrast(view: View, amount: float) -> View: return _filter(view, "contrast", max(0.0, amount))
def saturation(view: View, amount: float) -> View: return _filter(view, "saturation", max(0.0, amount))
def grayscale(view: View, amount: float = 1.0) -> View: return _filter(view, "grayscale", max(0.0, min(1.0, amount)))
def hue_rotation(view: View, degrees: float) -> View: return _filter(view, "hueRotation", degrees)


def blend_mode(view: View, mode: str) -> View:
    values = {value for name, value in vars(BlendMode).items() if name.isupper()}
    if mode not in values:
        raise ValueError(f"unsupported blend mode: {mode!r}")
    return _apply(view, BlendModeModifier(mode))


def compositing_group(view: View) -> View: return _apply(view, CompositingModifier())
def drawing_group(view: View, opaque: bool = False, color_mode: str = "nonLinear") -> View:
    if color_mode not in {"nonLinear", "linear", "extendedLinear"}:
        raise ValueError(f"unsupported color mode: {color_mode!r}")
    return _apply(view, CompositingModifier(True, bool(opaque), color_mode))
def clipped(view: View, antialiased: bool = True) -> View: return _apply(view, ClipModifier(None, antialiased))
def clip_shape(view: View, shape: View, antialiased: bool = True) -> View:
    if not isinstance(shape, View): raise TypeError("clip_shape expects a View shape")
    return _apply(view, ClipModifier(shape, antialiased))
def mask(view: View, mask_view: View) -> View:
    if not isinstance(mask_view, View): raise TypeError("mask expects a View")
    return _apply(view, MaskModifier(mask_view))
