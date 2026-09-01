from aui import Capability
from aui.backends.appkit import AppKitBackend
from aui.backends.ascii import AsciiBackend
from aui.backends.curses import CursesBackend
from aui.backends.standard import StandardBackend
from aui.backends.standard_theme import StandardTheme
from aui.backends.appkit_theme import AppKitTheme


def test_backends_package_exposes_all_builtin_renderers():
    from aui.backends import (
        AppKitBackend as ExportedAppKitBackend,
        AsciiBackend as ExportedAsciiBackend,
        CursesBackend as ExportedCursesBackend,
        StandardBackend as ExportedStandardBackend,
    )

    assert ExportedAppKitBackend is AppKitBackend
    assert ExportedAsciiBackend is AsciiBackend
    assert ExportedCursesBackend is CursesBackend
    assert ExportedStandardBackend is StandardBackend


def test_theme_dynamic_type_scale_is_validated_and_shared():
    assert StandardTheme(font_scale=1.5).scaled_font_size(13) == 20
    assert AppKitTheme(font_scale=1.5).scaled_font_size(13) == 19.5
    for theme_type in (StandardTheme, AppKitTheme):
        import pytest
        with pytest.raises(ValueError):
            theme_type(font_scale=4.0)


def test_all_builtin_backends_expose_availability_contract():
    assert AsciiBackend.available()
    assert isinstance(AsciiBackend.availability_reason(), str)
    assert isinstance(CursesBackend.available(), bool)
    assert isinstance(CursesBackend.availability_reason(), str)
    assert isinstance(StandardBackend.available(), bool)
    assert isinstance(AppKitBackend.available(), bool)
    assert isinstance(AppKitBackend.availability_reason(), str)

    from aui.backends import appkit_available, standard_available
    assert appkit_available() == AppKitBackend.available()
    assert standard_available() == StandardBackend.available()


def test_appkit_unavailable_reason_is_safe_without_pyobjc(monkeypatch):
    import aui.backends.appkit as appkit
    monkeypatch.setattr(appkit, "_PYOBJC", False)
    monkeypatch.setattr(appkit, "_PYOBJC_IMPORT_ERROR", "simulated missing bridge", raising=False)
    reason = appkit.AppKitBackend.availability_reason()
    assert "unavailable" in reason
    assert "simulated missing bridge" in reason


def test_backend_capabilities_are_explicit_and_queryable():
    assert AppKitBackend.supports(Capability.NATIVE_SYMBOLS)
    assert AppKitBackend.supports(Capability.SPLIT_DIVIDER_DRAG)
    assert not AppKitBackend.supports(Capability.DRAG_AND_DROP)
    assert StandardBackend.supports(Capability.SNACK_BAR_ACTION)
    assert StandardBackend.supports(Capability.RESPONSIVE_ROW)
    assert StandardBackend.supports(Capability.SPLIT_DIVIDER_DRAG)
    assert not StandardBackend.supports(Capability.NATIVE_SYMBOLS)
    assert AsciiBackend.supports(Capability.NAVIGATION_RAIL)
    assert not AsciiBackend.supports(Capability.TOOLBAR)
    assert not CursesBackend.supports(Capability.TOOLBAR)


def test_capability_sets_are_complete_and_do_not_overclaim():
    expected = {
        AppKitBackend: {
            Capability.NATIVE_SYMBOLS, Capability.TOOLBAR,
            Capability.SPLIT_DIVIDER_DRAG, Capability.SNACK_BAR,
            Capability.SNACK_BAR_ACTION, Capability.WINDOW_EVENTS,
            Capability.RESPONSIVE_ROW, Capability.NAVIGATION_RAIL,
            Capability.APP_BAR, Capability.FILE_DIALOGS,
        },
        StandardBackend: {
            Capability.TOOLBAR, Capability.SPLIT_DIVIDER_DRAG,
            Capability.SNACK_BAR, Capability.SNACK_BAR_ACTION,
            Capability.WINDOW_EVENTS, Capability.RESPONSIVE_ROW,
            Capability.NAVIGATION_RAIL, Capability.APP_BAR,
            Capability.FILE_DIALOGS,
        },
        AsciiBackend: {
            Capability.RESPONSIVE_ROW, Capability.NAVIGATION_RAIL,
            Capability.APP_BAR,
        },
        CursesBackend: set(),
    }
    for backend, capabilities in expected.items():
        assert backend.CAPABILITIES == frozenset(capabilities)
        assert backend.CAPABILITIES <= Capability.ALL
