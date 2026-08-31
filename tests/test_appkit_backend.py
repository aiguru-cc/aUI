"""Tests for the native AppKit backend and the shared showcase view tree.

These tests never open a window or enter the AppKit event loop (that would
require an interactive macOS desktop session). They verify:

* ``AppKitBackend.available()`` correctly reports PyObjC availability;
* the off-screen window build maps every aUI component to a native Cocoa
  control with the right type and a recorded layout frame;
* the shared ``make_view()`` builds a tree usable by every backend.

Native window construction requires a graphical macOS session.  The tests are
therefore opt-in through ``AUI_APPKIT_TESTS=1``; PyObjC-only bridge tests stay
safe to run without a window server.
"""
import os
import sys

import pytest

from aui.core.components import (
    Button,
    ColorPicker,
    DatePicker,
    Divider,
    Image,
    Label,
    List,
    NavigationStack,
    Picker,
    ProgressView,
    SecureField,
    Slider,
    Stepper,
    Text,
    TextField,
    Toggle,
)
from aui.core.geometry import Point, Size
from aui.core.canvas import TimelineView
from aui.core.view import View
from aui.core.scenes import Window
from aui.core.state import State
from aui.core.table import Table, TableColumn

SHOWCASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "showcase_view.py")
sys.path.insert(0, os.path.dirname(SHOWCASE))

from aui.backends import appkit as appkit_mod  # noqa: E402


_APPKIT_WINDOW_TESTS = (
    appkit_mod._PYOBJC and os.environ.get("AUI_APPKIT_TESTS") == "1"
)
_WINDOW_TEST_REASON = "requires PyObjC and AUI_APPKIT_TESTS=1 in a graphical macOS session"


# ---------------------------------------------------------------------------
# Backend availability detection (runs everywhere)
# ---------------------------------------------------------------------------
def test_available_matches_pyobjc_import():
    import importlib
    try:
        importlib.import_module("objc")
        importlib.import_module("AppKit")
        expect = True
    except Exception:
        expect = False
    assert appkit_mod.available() is expect
    assert appkit_mod.AppKitBackend.available() is expect


def test_run_raises_without_pyobjc(monkeypatch):
    monkeypatch.setattr(appkit_mod, "_PYOBJC", False)
    backend = appkit_mod.AppKitBackend(lambda: Text("x"))
    with pytest.raises(RuntimeError, match="PyObjC"):
        backend.run()


def test_application_uses_standard_scene_runner_when_appkit_is_unavailable(monkeypatch):
    """Native-first examples still have a usable Windows/Linux launch path."""
    from aui.backends import standard as standard_mod

    calls = []

    class FakeStandardApplication:
        def __init__(self, scene, *, commands):
            calls.append((scene, commands))

        def run(self):
            calls.append("run")

    monkeypatch.setattr(appkit_mod, "_PYOBJC", False)
    monkeypatch.setattr(standard_mod.StandardBackend, "available", staticmethod(lambda: True))
    monkeypatch.setattr(standard_mod, "StandardApplication", FakeStandardApplication)
    scene = Window("Portable", lambda: Text("x"))
    appkit_mod.AppKitApplication(scene).run()

    assert calls[0][0] is scene
    assert calls[-1] == "run"


def test_appkit_timeline_uses_main_queue_animation_scheduler(monkeypatch):
    """Timeline lifecycle is renderer-owned rather than a one-time build."""
    scheduled = []

    class Timer:
        def __init__(self): self.cancelled = False
        def cancel(self): self.cancelled = True

    timeline = TimelineView(lambda context: Text(context.date.isoformat()), cadence="seconds")
    backend = appkit_mod.AppKitBackend(lambda: timeline)
    backend._view = timeline
    backend._window = object()
    timer = Timer()
    monkeypatch.setattr(backend, "_schedule_animation_frame",
                        lambda delay, callback: (scheduled.append((delay, callback)) or timer))
    refreshed = []
    monkeypatch.setattr(backend, "_observed_value_changed", lambda: refreshed.append(True))

    backend._install_timeline_timer()

    assert scheduled[0][0] == 1.0
    scheduled[0][1]()
    assert refreshed == [True]


def test_appkit_close_cancels_and_releases_task_registry():
    calls = []

    class Task:
        def cancel(self):
            calls.append("task")

    backend = appkit_mod.AppKitBackend(lambda: Text("x"))
    backend._tasks["work"] = (None, Task())
    backend.windowWillClose_(None)

    assert calls == ["task"]
    assert backend._tasks == {}


def test_appkit_table_selection_requests_a_sibling_refresh():
    selected = State(None)
    model = Table([{"id": "row", "title": "Row"}], [TableColumn("Title", "title")],
                  selection=selected.binding())

    class NativeTable:
        def selectedRow(self): return 0

    native = NativeTable()
    notification = type("Notification", (), {"object": lambda self: native})()
    backend = appkit_mod.AppKitBackend(lambda: Text("x"))
    backend._tables = [(native, model)]
    refreshes = []
    backend._refresh_content = lambda: refreshes.append(True)

    backend.tableViewSelectionDidChange_(notification)

    assert selected.wrapped_value == "row"
    assert refreshes == [True]


@pytest.mark.skipif(not appkit_mod._PYOBJC, reason="PyObjC not installed")
def test_native_actions_are_exposed_by_the_objc_bridge():
    """Regression guard for assigning a pure Python backend as a Cocoa target."""
    backend = appkit_mod.AppKitBackend(lambda: Text("x"))
    bridge = appkit_mod._BackendBridge.alloc().initWithBackend_(backend)

    for selector in (
        b"toolbarItemPressed:", b"buttonPressed:", b"fieldChanged:",
        b"sliderChanged:", b"navigationRailSelected:", b"snackBarAction:",
    ):
        assert bridge.respondsToSelector_(selector)


@pytest.mark.skipif(not appkit_mod._PYOBJC, reason="PyObjC not installed")
def test_application_menu_actions_are_exposed_by_an_objc_bridge():
    """Application commands must not install a pure Python object as target."""
    application = appkit_mod.AppKitApplication(Window("Bridge", lambda: Text("x")))
    bridge = application._bridge
    assert bridge is not None
    for selector in (b"openSettings:", b"appCommandPressed:", b"menuBarItemPressed:"):
        assert bridge.respondsToSelector_(selector)


@pytest.mark.skipif(not _APPKIT_WINDOW_TESTS, reason=_WINDOW_TEST_REASON)
def test_appkit_initial_build_has_no_prior_view_requirement():
    """Initial native construction must not reference refresh-only state."""
    backend = appkit_mod.AppKitBackend(lambda: Text("x"))
    backend._build_window(160, 100, "initial build")
    assert backend._view is not None
    assert backend._content is not None
    backend._window.close()


# ---------------------------------------------------------------------------
# Shared showcase view tree builds and measures
# ---------------------------------------------------------------------------
def test_showcase_view_builds():
    mod = __import__("showcase_view")
    view = mod.make_view()
    assert isinstance(view, View)
    flat = view.flatten()
    assert len(flat) > 50
    # All major component families present.
    types = {type(v) for v in flat}
    for cls in (Button, Text, TextField, Toggle, Slider, Picker, Stepper,
                DatePicker, ProgressView, Divider, Image, Label, List,
                NavigationStack):
        assert cls in types, f"{cls.__name__} missing from showcase tree"


# ---------------------------------------------------------------------------
# AppKit off-screen build (skipped without PyObjC)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _APPKIT_WINDOW_TESTS, reason=_WINDOW_TEST_REASON)
def test_appkit_offscreen_build_creates_native_controls():
    sys.path.insert(0, os.path.dirname(SHOWCASE))
    mod = __import__("showcase_view")
    backend = appkit_mod.AppKitBackend(mod.make_view)
    backend._build_window(620, 480, "aUI Test")

    window = backend._window
    assert window.title() == "aUI Test"
    # Controls are hosted in the NSScrollView's document view (the window's
    # content view only contains the scroll view).
    content = backend._content
    subviews = list(content.subviews())
    assert len(subviews) >= 40, f"expected many native controls, got {len(subviews)}"

    names = [type(sv).__name__ for sv in subviews]
    # Spot-check the native control mapping. NSSwitch is created as its
    # KVO-observing subclass NSKVONotifying_NSSwitch in PyObjC.
    assert "NSButton" in names
    assert any("NSSwitch" in n for n in names)
    assert "NSSlider" in names
    assert "NSStepper" in names
    assert "NSPopUpButton" in names
    assert "NSProgressIndicator" in names
    assert any("NSSecureTextField" in n for n in names)
    # Layout frames were recorded for the components.
    assert len(backend._frames) > 80
    # A handful of components legitimately collapse to zero size (hidden()
    # elements and Spacers with no free space), but the vast majority must
    # carry a real frame so native controls are positioned correctly.
    empty = sum(1 for (o, s) in backend._frames.values() if s.width == 0 and s.height == 0)
    assert empty <= 3, f"expected at most a few zero-size frames, got {empty}"
    assert len(backend._frames) - empty > 80


@pytest.mark.skipif(not _APPKIT_WINDOW_TESTS, reason=_WINDOW_TEST_REASON)
def test_appkit_offscreen_build_handles_text_layout():
    sys.path.insert(0, os.path.dirname(SHOWCASE))
    mod = __import__("showcase_view")
    backend = appkit_mod.AppKitBackend(mod.make_view)
    backend._build_window(620, 480, "aUI Test")

    # The root is a NavigationStack: its content frame must be inside the window
    # and the title header text control must exist.
    view = backend._view
    assert isinstance(view, NavigationStack)
    content = backend._content
    text_controls = [sv for sv in content.subviews() if type(sv).__name__ == "NSTextField"]
    assert text_controls, "expected NSTextField labels for Text components"


@pytest.mark.skipif(not _APPKIT_WINDOW_TESTS, reason=_WINDOW_TEST_REASON)
def test_appkit_binding_roundtrip_state():
    from aui.core.state import State

    value = State(0.5)

    def make():
        return Slider(value=value.binding(), in_range=(0.0, 1.0))

    backend = appkit_mod.AppKitBackend(make)
    backend._build_window(200, 100, "t")
    # Find the NSSlider control and simulate the native action callback.
    content = backend._content
    slider = next(sv for sv in content.subviews() if type(sv).__name__ == "NSSlider")
    slider.setDoubleValue_(0.75)
    backend.sliderChanged_(slider)
    assert value.wrapped_value == pytest.approx(0.75)


@pytest.mark.skipif(not _APPKIT_WINDOW_TESTS, reason=_WINDOW_TEST_REASON)
def test_appkit_all_controls_inside_document():
    """Every native control must sit inside the scrollable document view.

    Regression guard for the layout rewrite: components used to be placed with
    un-flipped y coordinates that pushed them outside the window. The document
    is a flipped NSView sized to the laid-out content, so every subview frame
    must be fully contained in it.
    """
    sys.path.insert(0, os.path.dirname(SHOWCASE))
    mod = __import__("showcase_view")
    backend = appkit_mod.AppKitBackend(mod.make_view)
    backend._build_window(620, 480, "aUI Test")
    doc = backend._content
    W = doc.frame().size.width
    H = doc.frame().size.height
    assert H > 480.0, "document must be taller than the window (scrollable content)"
    assert W == pytest.approx(620.0)

    def walk(v):
        f = v.frame()
        x, y, w, h = f.origin.x, f.origin.y, f.size.width, f.size.height
        assert x >= -1 and y >= -1, f"control out of bounds: {type(v).__name__} @({x:.1f},{y:.1f})"
        assert x + w <= W + 1 and y + h <= H + 1, \
            f"control spills outside document: {type(v).__name__} " \
            f"frame=({x:.1f},{y:.1f},{w:.1f},{h:.1f}) doc={W:.0f}x{H:.0f}"
        for c in v.subviews():
            walk(c)

    walk(doc)


@pytest.mark.skipif(not _APPKIT_WINDOW_TESTS, reason=_WINDOW_TEST_REASON)
def test_appkit_first_viewport_has_controls():
    """The first visible viewport (top 480pt) must contain real controls."""
    sys.path.insert(0, os.path.dirname(SHOWCASE))
    mod = __import__("showcase_view")
    backend = appkit_mod.AppKitBackend(mod.make_view)
    backend._build_window(620, 480, "aUI Test")
    doc = backend._content
    visible = [sv for sv in doc.subviews() if 0 <= sv.frame().origin.y < 480]
    assert len(visible) >= 20, f"expected controls in first viewport, got {len(visible)}"
    # The title header from NavigationStack must be present.
    assert any(type(sv).__name__ == "NSTextField" for sv in visible)


@pytest.mark.skipif(not _APPKIT_WINDOW_TESTS, reason=_WINDOW_TEST_REASON)
def test_appkit_stack_with_spacer_no_infinite_height():
    """A VStack/HStack containing a Spacer must not explode on natural-height
    measurement (its size_that_fits returns inf on an unlimited proposal)."""
    from aui import HStack, Spacer, VStack

    v = VStack([Text("a"), Spacer(), Text("b")], spacing=6)
    backend = appkit_mod.AppKitBackend(lambda: v)
    backend._build_window(300, 200, "spacer")
    assert len(backend._content.subviews()) == 2
    # Text labels end up at the top and bottom of the 2000pt document.
    ys = sorted(sv.frame().origin.y for sv in backend._content.subviews())
    assert ys[1] - ys[0] > 1000

    h = HStack([Text("L"), Spacer(), Text("R")], spacing=4)
    backend2 = appkit_mod.AppKitBackend(lambda: h)
    backend2._build_window(300, 100, "hspacer")
    xs = sorted(sv.frame().origin.x for sv in backend2._content.subviews())
    assert xs[1] - xs[0] > 200
