import pytest

from aui import AttributedString, AttributeRun, Size, Text, VStack
from aui.backends.ascii import AsciiBackend
from aui.core.text import TextStyleModifier, resolve_text_style_tree, text_style_value


def test_attributed_string_validates_runs():
    value = AttributedString("Hello", [AttributeRun(0, 5, {"bold": True})])
    assert str(value) == "Hello"
    assert value.runs[0].attributes["bold"]
    with pytest.raises(ValueError):
        AttributedString("Hi", [AttributeRun(0, 9, {})])


def test_markdown_parser_preserves_plain_text_and_ranges():
    value = AttributedString.markdown("**Bold** and *italic*, `code`, [site](https://example.com)")
    assert value.text == "Bold and italic, code, site"
    assert [run.attributes for run in value.runs] == [
        {"bold": True}, {"italic": True}, {"code": True},
        {"link": "https://example.com"},
    ]
    assert value.text[value.runs[-1].start:value.runs[-1].end] == "site"


def test_text_accepts_attributed_string():
    attributed = AttributedString.markdown("Hello **world**")
    text = Text(attributed)
    assert text.content == "Hello world"
    assert text.attributed_string is attributed


def test_text_modifiers_resolve_and_preserve_layout():
    base = Text("Typography")
    view = (base.kerning(1.2).tracking(0.4).baseline_offset(2)
            .multiline_text_alignment("center").truncation_mode("middle")
            .minimum_scale_factor(0.5).allows_tightening().monospaced_digit()
            .text_selection())
    resolve_text_style_tree(view)
    leaf = view.find(lambda item: isinstance(item, Text))
    assert text_style_value(leaf, "kerning") == pytest.approx(1.2)
    assert text_style_value(leaf, "truncation_mode") == "middle"
    assert text_style_value(leaf, "text_selection") is True
    assert view.size_that_fits(Size(200, 100)).height == base.size_that_fits(Size(200, 100)).height


def test_text_style_container_inheritance_and_child_override():
    child = Text("Mixed Case").text_case("lowercase")
    root = VStack([child]).text_case("uppercase")
    resolve_text_style_tree(root)
    leaf = root.find(lambda item: isinstance(item, Text))
    assert leaf.display_content == "mixed case"


def test_ascii_applies_text_case():
    assert "HELLO" in AsciiBackend(20, 2).render(Text("Hello").text_case("uppercase"))


def test_text_style_validation_and_clamping():
    with pytest.raises(ValueError): Text("x").text_case("title")
    with pytest.raises(ValueError): Text("x").multiline_text_alignment("justify")
    with pytest.raises(ValueError): Text("x").truncation_mode("clip")
    view = Text("x").minimum_scale_factor(4)
    assert isinstance(view.modifiers[-1], TextStyleModifier)
    assert view.modifiers[-1].value == 1.0
