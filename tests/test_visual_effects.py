import pytest

from aui import (
    AngularGradient, Capsule, Circle, Color, Ellipse, EllipticalGradient, GradientStop, LinearGradient, Material,
    RadialGradient, RoundedRectangle, Size, Text, describe_accessibility,
)
from aui.backends.ascii import AsciiBackend
from aui.core.visual_effects import (
    MaterialBackgroundModifier, OverlayModifier, ShadowModifier,
)


def test_gradient_builds_evenly_spaced_stops():
    gradient = LinearGradient([Color.red, Color.green, Color.blue], size=Size(300, 80))
    assert [stop.location for stop in gradient.stops] == [0.0, 0.5, 1.0]
    assert gradient.size_that_fits(Size(500, 500)) == Size(300, 80)
    assert describe_accessibility(gradient).role == "image"


def test_gradient_sorts_and_clamps_explicit_stops():
    gradient = RadialGradient(stops=[
        GradientStop(Color.blue, 1.2),
        GradientStop(Color.red, -0.2),
    ])
    assert [stop.location for stop in gradient.stops] == [0.0, 1.0]
    with pytest.raises(ValueError):
        LinearGradient([Color.red])


def test_visual_modifiers_are_layout_transparent():
    base = Text("Card")
    size = Size(200, 100)
    material = base.material_background(Material.THIN)
    shadow = material.shadow(radius=10, y=4)
    overlay = shadow.overlay(Text("New"), alignment="topTrailing")
    assert overlay.size_that_fits(size) == base.size_that_fits(size)
    assert isinstance(material._modifier, MaterialBackgroundModifier)
    assert isinstance(shadow._modifier, ShadowModifier)
    assert isinstance(overlay._modifier, OverlayModifier)


def test_additional_shapes_and_ascii_fallback():
    views = [Capsule(size=Size(80, 30)), Ellipse(size=Size(80, 40)), Circle()]
    rendered = "\n".join(AsciiBackend().render(view) for view in views)
    assert "▰" in rendered and "⬭" in rendered and "○" in rendered
    assert RoundedRectangle(corner_radius=8).corner_radius_value == 8


def test_angular_gradient_angles_sampling_and_accessibility():
    gradient = AngularGradient(
        [Color.red, Color.blue], center=(0.4, 0.6),
        start_angle=-90, end_angle=270, size=Size(160, 160),
    )
    middle = gradient.color_at(0.5)
    assert gradient.center == (0.4, 0.6)
    assert gradient.sweep_angle == 360
    assert middle.red == pytest.approx(0.5)
    assert middle.blue == pytest.approx(0.5)
    assert describe_accessibility(gradient).role == "image"
    assert "angular" in AsciiBackend(width=30, height=3).render(gradient)


def test_gradient_sampling_clamps_and_angular_gradient_validates():
    gradient = LinearGradient([Color.red, Color.blue])
    assert gradient.color_at(-1) is Color.red
    assert gradient.color_at(2) is Color.blue
    with pytest.raises(ValueError, match="exceed"):
        AngularGradient([Color.red, Color.blue], start_angle=90, end_angle=45)
    with pytest.raises(ValueError, match="finite"):
        AngularGradient([Color.red, Color.blue], center=(float("inf"), 0.5))


def test_radial_gradient_start_and_end_radii_map_stops():
    gradient = RadialGradient(
        [Color.red, Color.blue], start_radius=20, end_radius=100
    )
    assert gradient.radius == 100
    assert gradient.mapped_locations() == pytest.approx([0.2, 1.0])
    with pytest.raises(ValueError, match="smaller"):
        RadialGradient([Color.red, Color.blue], start_radius=20, end_radius=10)


def test_radial_gradient_preserves_legacy_positional_size_argument():
    gradient = RadialGradient(
        [Color.red, Color.blue], (), (0.5, 0.5), 0.4, Size(90, 70)
    )
    assert gradient.size_that_fits(Size(500, 500)) == Size(90, 70)


def test_elliptical_gradient_radius_fractions_and_fallback():
    gradient = EllipticalGradient(
        [Color.red, Color.blue], center=(0.4, 0.6),
        start_radius_fraction=0.1, end_radius_fraction=0.5,
    )
    assert gradient.mapped_locations() == pytest.approx([0.2, 1.0])
    assert describe_accessibility(gradient).role == "image"
    assert "elliptical" in AsciiBackend(width=30, height=3).render(gradient)
    with pytest.raises(ValueError, match="smaller"):
        EllipticalGradient([Color.red, Color.blue], start_radius_fraction=0.8,
                           end_radius_fraction=0.2)
