from aui import Capability
from aui.backends.appkit import AppKitBackend
from aui.backends.ascii import AsciiBackend
from aui.backends.curses import CursesBackend
from aui.backends.standard import StandardBackend


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
