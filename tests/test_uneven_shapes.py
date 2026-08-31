import pytest

from aui import Circle, Color, FillStyle, Rectangle, Size, StrokeStyle, UnevenRoundedRectangle
from aui.backends.ascii import AsciiBackend


def test_uneven_rounded_rectangle_preserves_geometry_through_styles():
    shape = UnevenRoundedRectangle(
        4, 8, 12, 16, style="continuous", size=Size(120, 60)
    ).fill(Color.blue).stroke(Color.white, 3)

    assert isinstance(shape, UnevenRoundedRectangle)
    assert shape.corner_radii == (4, 8, 12, 16)
    assert shape.style == "continuous"
    assert shape.fill_color == Color.blue
    assert shape.stroke_color == Color.white
    assert shape.line_width == 3


def test_inset_and_stroke_border_accumulate_inside_shape():
    shape = Rectangle(size=Size(80, 40)).inset(3).stroke_border(Color.red, 6)
    assert shape.inset_amount == pytest.approx(6)
    assert shape.line_width == 6
    assert shape.stroke_color == Color.red
    assert shape.size_that_fits(Size(500, 500)) == Size(80, 40)


def test_uneven_shape_validation_and_ascii_marker():
    with pytest.raises(ValueError, match="style"):
        UnevenRoundedRectangle(style="squircle")

    shape = UnevenRoundedRectangle(8, 2, 12, 4).fill(Color.blue)
    assert "◩" in AsciiBackend(width=12, height=3).render(shape)


def test_negative_corner_radii_and_insets_are_clamped():
    shape = UnevenRoundedRectangle(-2, 3, -4, 5).inset(-10)
    assert shape.corner_radii == (0, 3, 0, 5)
    assert shape.inset_amount == 0


def test_shape_stroke_accepts_full_stroke_style_and_preserves_it():
    style = StrokeStyle(5, "round", "bevel", dash=(8, 3), dash_phase=2)
    shape = UnevenRoundedRectangle(4, 8, 12, 16).stroke(Color.blue, style=style)
    copied = shape.fill(Color.teal).inset(2)

    assert copied.stroke_style == style
    assert copied.line_width == 5
    assert copied.corner_radii == (4, 8, 12, 16)


def test_stroke_border_uses_style_width_for_inset():
    style = StrokeStyle(line_width=8, line_cap="square", dash=(2, 1))
    shape = Rectangle().stroke_border(Color.red, style=style)
    assert shape.inset_amount == 4
    assert shape.stroke_style is style
    positional = Rectangle().stroke(Color.blue, style)
    assert positional.stroke_style is style


def test_shape_stroke_style_type_validation():
    with pytest.raises(TypeError, match="StrokeStyle"):
        Rectangle(stroke_style="dashed")
    with pytest.raises(TypeError, match="StrokeStyle"):
        Rectangle().stroke(Color.blue, style="dashed")


def test_stroke_style_rejects_negative_dash_and_miter_limit():
    with pytest.raises(ValueError, match="dash"):
        StrokeStyle(dash=(2, -1))
    with pytest.raises(ValueError, match="miter"):
        StrokeStyle(miter_limit=-1)


def test_shape_trim_and_fill_style_survive_chained_copies():
    fill_style = FillStyle(eo_fill=True, antialiased=False)
    shape = Circle().trim(0.15, 0.8).fill(Color.blue, fill_style).stroke(
        Color.white, 3
    ).inset(2)
    assert shape.trim_range == (0.15, 0.8)
    assert shape.fill_style is fill_style
    assert "◔" in AsciiBackend(width=8, height=2).render(shape)


def test_shape_trim_and_fill_style_validation():
    for values in ((-0.1, 0.5), (0.8, 0.2), (0.2, 1.1)):
        with pytest.raises(ValueError, match="trim range"):
            Circle().trim(*values)
    with pytest.raises(TypeError, match="FillStyle"):
        Circle().fill(Color.blue, style="even-odd")
