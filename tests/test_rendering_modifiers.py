import pytest

from aui import BlendMode, Color, RoundedRectangle, Size, Text
from aui.backends.ascii import AsciiBackend
from aui.core.rendering import (
    BlendModeModifier, ClipModifier, CompositingModifier, FilterModifier,
    MaskModifier, Rotation3DEffectModifier, RotationEffectModifier,
    ScaleEffectModifier,
)


def test_transform_modifiers_are_chainable_and_layout_neutral():
    base = Text("Transform")
    view = base.scale_effect(1.2, y=0.8).rotation_effect(15)
    assert any(isinstance(mod, ScaleEffectModifier) for mod in view.modifiers)
    assert isinstance(view.modifiers[-1], RotationEffectModifier)
    assert view.size_that_fits(Size(200, 100)).width == base.size_that_fits(Size(200, 100)).width


def test_rotation_3d_validates_axis():
    view = Text("Card").rotation_3d_effect(60, axis=(1, 0, 0))
    assert isinstance(view.modifiers[-1], Rotation3DEffectModifier)
    with pytest.raises(ValueError):
        Text("Card").rotation_3d_effect(20, axis=(1, 0))


@pytest.mark.parametrize("builder,kind,expected", [
    (lambda v: v.blur(-2), "blur", 0.0),
    (lambda v: v.brightness(0.2), "brightness", 0.2),
    (lambda v: v.contrast(-1), "contrast", 0.0),
    (lambda v: v.saturation(1.4), "saturation", 1.4),
    (lambda v: v.grayscale(4), "grayscale", 1.0),
    (lambda v: v.hue_rotation(90), "hueRotation", 90.0),
])
def test_filter_modifiers_normalize_values(builder, kind, expected):
    modifier = builder(Text("x")).modifiers[-1]
    assert isinstance(modifier, FilterModifier)
    assert modifier.kind == kind
    assert modifier.amount == pytest.approx(expected)


def test_blend_modes_validate():
    view = Text("x").blend_mode(BlendMode.MULTIPLY)
    assert isinstance(view.modifiers[-1], BlendModeModifier)
    with pytest.raises(ValueError):
        Text("x").blend_mode("unknown")


def test_compositing_and_drawing_groups():
    assert isinstance(Text("x").compositing_group().modifiers[-1], CompositingModifier)
    modifier = Text("x").drawing_group(opaque=True, color_mode="linear").modifiers[-1]
    assert modifier.drawing and modifier.opaque and modifier.color_mode == "linear"
    with pytest.raises(ValueError):
        Text("x").drawing_group(color_mode="print")


def test_clip_shape_mask_and_clipped():
    shape = RoundedRectangle(12).fill(Color.blue)
    clip = Text("x").clip_shape(shape)
    assert isinstance(clip.modifiers[-1], ClipModifier)
    assert clip.modifiers[-1].shape is shape
    assert isinstance(Text("x").clipped().modifiers[-1], ClipModifier)
    assert isinstance(Text("x").mask(Text("mask")).modifiers[-1], MaskModifier)
    with pytest.raises(TypeError):
        Text("x").clip_shape("circle")


def test_headless_backend_safely_ignores_visual_effects():
    view = (Text("Still readable").scale_effect(1.1).rotation_effect(5)
            .blur(1).drawing_group().clipped())
    assert "Still readable" in AsciiBackend(30, 2).render(view)
