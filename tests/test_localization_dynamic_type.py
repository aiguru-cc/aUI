import pytest

from aui import (
    DynamicTypeSize, HStack, Locale, LocalizedStringKey, Size, Text, VStack,
)
from aui.backends.ascii import AsciiBackend
from aui.core.environment import resolve_environment_tree
from aui.core.localization import resolve_semantic_tree, semantic_value


def test_locale_language_code_normalization():
    assert Locale("zh-Hans-CN").language_code == "zh"
    assert Locale("en_US").language_code == "en"


def test_localized_string_exact_language_and_default_fallback():
    key = LocalizedStringKey("welcome", "Welcome, {name}", {
        "zh": "欢迎，{name}", "fr-FR": "Bienvenue, {name}",
    }, name="Ada")
    assert key.resolve(Locale("zh-CN")) == "欢迎，Ada"
    assert key.resolve(Locale("fr-FR")) == "Bienvenue, Ada"
    assert key.resolve(Locale("de")) == "Welcome, Ada"


def test_text_resolves_locale_from_environment():
    text = Text(LocalizedStringKey("save", "Save", {"zh": "保存"}))
    root = VStack([text]).locale("zh-CN")
    output = AsciiBackend(20, 2).render(root)
    assert "保存" in output and "Save" not in output


def test_dynamic_type_changes_measurement_and_inherits():
    text = Text("Readable")
    normal = text.size_that_fits(Size(500, 500))
    root = VStack([text]).dynamic_type_size(DynamicTypeSize.ACCESSIBILITY3)
    resolve_environment_tree(root)
    enlarged = text.size_that_fits(Size(500, 500))
    assert enlarged.width > normal.width
    assert enlarged.height > normal.height


def test_dynamic_type_and_layout_direction_validation():
    with pytest.raises(ValueError): Text("x").dynamic_type_size("huge")
    with pytest.raises(ValueError): Text("x").layout_direction("vertical")


def test_rtl_reverses_horizontal_stack_visual_order():
    root = HStack([Text("First"), Text("Second")], spacing=1).layout_direction("rightToLeft")
    output = AsciiBackend(30, 2).render(root)
    assert output.index("Second") < output.index("First")


def test_redacted_content_is_rendered_as_placeholder():
    output = AsciiBackend(30, 2).render(Text("Secret value").redacted())
    assert "Secret value" not in output
    assert "███" in output


def test_semantic_privacy_and_help_propagate():
    root = VStack([Text("Account")]).privacy_sensitive().help("Private account")
    resolve_semantic_tree(root)
    leaf = root.find(lambda view: isinstance(view, Text))
    assert semantic_value(leaf, "privacy_sensitive") is True
    assert semantic_value(leaf, "help") == "Private account"


def test_invalid_redaction_reason():
    with pytest.raises(ValueError): Text("x").redacted("blur")
