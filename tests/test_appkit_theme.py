from aui.backends.appkit_theme import AppKitTheme, DEFAULT_APPKIT_THEME
from aui.core.geometry import Color


def test_default_theme_has_swiftui_sized_tokens():
    assert DEFAULT_APPKIT_THEME.card_radius >= 10
    assert DEFAULT_APPKIT_THEME.control_radius >= 6
    assert 0 <= DEFAULT_APPKIT_THEME.card_border_alpha <= 1


def test_theme_accent_copy_is_immutable():
    accent = Color.indigo
    changed = DEFAULT_APPKIT_THEME.with_accent(accent)
    assert changed.accent is accent
    assert DEFAULT_APPKIT_THEME.accent is not accent
