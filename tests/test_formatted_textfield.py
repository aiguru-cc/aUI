import pytest

from aui import (
    NumberFormatStyle, State, TextField, TextFieldStyle, VStack,
)
from aui.core.environment import resolve_environment_tree
from aui.core.styles import resolve_style_tree, style_value


def test_formatted_textfield_formats_and_parses_binding():
    amount = State(1234.5)
    field = TextField(
        placeholder="Amount", value=amount.binding(),
        format=NumberFormatStyle.number().precision(2),
    )
    assert field.text.wrapped_value == "1,234.50"
    field.text.wrapped_value = "2,500.75"
    assert amount.wrapped_value == pytest.approx(2500.75)
    assert field.validation_error is None


def test_formatted_textfield_uses_environment_locale():
    amount = State(1234.5)
    field = TextField(value=amount.binding(), format=NumberFormatStyle.number().precision(2))
    root = VStack([field]).locale("de-DE")
    resolve_environment_tree(root)
    assert field.text.wrapped_value == "1.234,50"
    field.text.wrapped_value = "2.345,75"
    assert amount.wrapped_value == pytest.approx(2345.75)


def test_parse_error_preserves_model_and_can_recover():
    amount = State(10.0)
    field = TextField(value=amount.binding(), format=NumberFormatStyle.number())
    field.text.wrapped_value = "not a number"
    assert amount.wrapped_value == 10.0
    assert field.validation_error
    field.text.wrapped_value = "12.5"
    assert amount.wrapped_value == 12.5
    assert field.validation_error is None


def test_textfield_constructor_validation():
    with pytest.raises(ValueError): TextField()
    with pytest.raises(ValueError): TextField(State("").binding(), value=State(1).binding(), format=NumberFormatStyle.number())
    with pytest.raises(TypeError): TextField(value=State(1).binding(), format="number")
    with pytest.raises(ValueError): TextField(State("").binding(), format=NumberFormatStyle.number())


def test_textfield_style_resolves_from_container_and_child_override():
    child = TextField(State("").binding()).text_field_style(TextFieldStyle.PLAIN)
    root = VStack([child]).text_field_style(TextFieldStyle.ROUNDED_BORDER)
    resolve_style_tree(root)
    leaf = root.find(lambda view: isinstance(view, TextField))
    assert style_value(leaf, "text_field_style") == TextFieldStyle.PLAIN


def test_textfield_style_validation():
    with pytest.raises(ValueError):
        TextField(State("").binding()).text_field_style("capsule")


def test_disabled_preserves_formatted_binding():
    amount = State(42.0)
    field = TextField(value=amount.binding(), format=NumberFormatStyle.number().precision(1))
    disabled = field.disabled()
    assert disabled.body().text.wrapped_value == "42.0"
    from aui.core.styles import resolve_style_tree, is_enabled
    resolve_style_tree(disabled)
    assert not is_enabled(disabled.body())
