from pathlib import Path

import pytest

from aui import (
    Color, EdgeInsets, Image, ImageInterpolation, ImageResizingMode, ImageScale,
    Size, SymbolRenderingMode,
    describe_accessibility,
)
from aui.backends.ascii import AsciiBackend


def test_image_accepts_symbol_file_and_byte_sources():
    symbol = Image(system_name="star.fill", label="Favorite")
    file_image = Image.from_file(Path("/tmp/photo.png"), size=Size(200, 100))
    data_image = Image.from_data(b"image bytes", size=32)

    assert symbol.system_name == "star.fill"
    assert file_image.path == Path("/tmp/photo.png")
    assert data_image.data == b"image bytes"
    assert data_image.size_that_fits(Size(500, 500)) == Size(32, 32)


def test_image_rejects_ambiguous_or_invalid_sources():
    with pytest.raises(ValueError, match="only one"):
        Image(system_name="star", path="star.png")
    with pytest.raises(TypeError, match="bytes-like"):
        Image(data="not bytes")
    with pytest.raises(ValueError, match="cannot be empty"):
        Image(data=b"")


def test_resizable_image_fit_and_fill_modes_are_immutable():
    original = Image.from_data(b"pixels", size=Size(200, 100))
    fitted = original.scaled_to_fit()
    filled = original.scaled_to_fill()

    assert original.size_that_fits(Size(100, 100)) == Size(200, 100)
    assert fitted.size_that_fits(Size(100, 100)) == Size(100, 50)
    assert filled.size_that_fits(Size(100, 100)) == Size(100, 100)
    assert fitted.content_mode == "fit"
    assert filled.content_mode == "fill"


def test_image_rendering_mode_and_accessibility():
    original = Image.from_file("portrait.png", label="Portrait")
    template = original.rendering_mode("template")

    assert original._rendering_mode == "original"
    assert template._rendering_mode == "template"
    assert describe_accessibility(original).label == "Portrait"
    decorative = Image(system_name="sparkles", decorative=True, color=Color.purple)
    assert describe_accessibility(decorative).hidden
    with pytest.raises(ValueError, match="original or template"):
        original.rendering_mode("automatic")


def test_file_image_uses_filename_as_default_accessibility_label():
    info = describe_accessibility(Image.from_file("/tmp/cover-art.png"))
    assert info.role == "image"
    assert info.label == "cover-art.png"


def test_image_interpolation_and_antialiasing_are_immutable():
    original = Image.from_data(b"pixels")
    configured = original.interpolation(ImageInterpolation.HIGH).antialiased(False)
    assert original.interpolation_quality == ImageInterpolation.MEDIUM
    assert original.is_antialiased is True
    assert configured.interpolation_quality == ImageInterpolation.HIGH
    assert configured.is_antialiased is False
    with pytest.raises(ValueError, match="interpolation"):
        original.interpolation("ultra")


def test_symbol_variants_compose_and_render_in_ascii():
    symbol = Image(system_name="star").symbol_variant("circle").symbol_variant("fill")
    assert symbol.resolved_system_name == "star.circle.fill"
    assert "star.circle.fill" in AsciiBackend(width=30, height=3).render(symbol)
    assert symbol.symbol_variant("none").resolved_system_name == "star"
    with pytest.raises(ValueError, match="system image"):
        Image.from_data(b"pixels").symbol_variant("fill")
    with pytest.raises(ValueError, match="variant"):
        Image(system_name="star").symbol_variant("diamond")


def test_symbol_rendering_modes_and_palette_validation():
    symbol = Image(system_name="cloud.sun")
    palette = symbol.symbol_rendering_mode(
        SymbolRenderingMode.PALETTE, [Color.blue, Color.yellow]
    )
    assert palette.palette_colors == (Color.blue, Color.yellow)
    assert palette.symbol_rendering_mode_value == SymbolRenderingMode.PALETTE
    assert symbol.symbol_rendering_mode(SymbolRenderingMode.MULTICOLOR).palette_colors == ()
    with pytest.raises(ValueError, match="requires colors"):
        symbol.symbol_rendering_mode(SymbolRenderingMode.PALETTE)
    with pytest.raises(TypeError, match="Color"):
        symbol.symbol_rendering_mode(SymbolRenderingMode.PALETTE, ["blue"])


def test_resizable_cap_insets_and_modes_are_preserved():
    insets = EdgeInsets(4, 6, 8, 10)
    image = Image.from_data(b"nine-patch").resizable(
        cap_insets=insets, resizing_mode=ImageResizingMode.TILE
    )
    assert image.cap_insets == insets
    assert image.resizing_mode == ImageResizingMode.TILE
    with pytest.raises(TypeError, match="EdgeInsets"):
        Image.from_data(b"pixels").resizable(cap_insets=(1, 2, 3, 4))
    with pytest.raises(ValueError, match="stretch or tile"):
        Image.from_data(b"pixels").resizable(resizing_mode="repeat")


def test_symbol_image_scale_changes_intrinsic_size_only_for_symbols():
    symbol = Image(system_name="star", size=20)
    assert symbol.image_scale(ImageScale.SMALL).size_that_fits(Size(100, 100)) == Size(16, 16)
    assert symbol.image_scale(ImageScale.LARGE).size_that_fits(Size(100, 100)) == Size(27, 27)
    bitmap = Image.from_data(b"pixels", size=20).image_scale(ImageScale.LARGE)
    assert bitmap.size_that_fits(Size(100, 100)) == Size(20, 20)
    with pytest.raises(ValueError, match="small, medium, or large"):
        symbol.image_scale("huge")


def test_symbol_weight_validation_and_copying():
    symbol = Image(system_name="star").symbol_weight("semibold")
    assert symbol.symbol_weight_value == "semibold"
    assert symbol.symbol_variant("fill").symbol_weight_value == "semibold"
    with pytest.raises(ValueError, match="system image"):
        Image.from_data(b"pixels").symbol_weight("bold")
    with pytest.raises(ValueError, match="weight"):
        Image(system_name="star").symbol_weight("extraBold")


def test_variable_symbol_values_and_terminal_fallback():
    symbol = Image(system_name="speaker.wave.3", variable_value=0.625)
    configured = symbol.symbol_variant("fill").symbol_weight("bold")
    assert configured.variable_value == pytest.approx(0.625)
    assert "62%" in AsciiBackend(width=40, height=3).render(configured)
    assert configured.variable_symbol(0).variable_value == 0
    assert configured.variable_symbol(1).variable_value == 1
    assert configured.variable_symbol(None).variable_value is None


def test_variable_symbol_validation():
    with pytest.raises(ValueError, match="system image"):
        Image.from_data(b"pixels", variable_value=0.5)
    with pytest.raises(ValueError, match="between 0 and 1"):
        Image(system_name="wifi", variable_value=1.1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        Image(system_name="wifi").variable_symbol(-0.1)
    with pytest.raises(ValueError, match="system image"):
        Image.from_data(b"pixels").variable_symbol(0.5)
