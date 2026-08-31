from datetime import datetime

import pytest

from aui import (
    Animation, Button, ColorPicker, CommandMenu, Commands, ContentTransition, DatePicker, Font,
    KeyboardShortcut,
    Gauge, LazyHStack, LazyVStack, List, Picker, ProgressView, Settings, Slider, State,
    Stepper, SymbolEffect, Text,
    NavigationSplitView, Window, WindowGroup, with_animation,
)
from aui.core.async_image import AsyncImage
from aui.core.canvas import Canvas, TimelineView
from aui.core.inspector import InspectorView
from aui.core.structural import OutlineGroup, ViewThatFits
from aui.core.table import Table, TableColumn
from aui.core.visual_effects import LinearGradient
from aui.core.animation_runtime import AnimationDriver
from aui.backends.standard import StandardApplication
from aui.core.presentation import AlertModifier
from aui.core.system_environment import ScenePhase
from aui.backends import standard as standard_module
from aui.backends.standard import StandardBackend, platform_family
from aui.backends.standard_theme import StandardTheme, color_hex
from aui.core.geometry import Color, Size
from aui.core.modifiers import resolve_visual_style_tree


@pytest.mark.parametrize(("value", "expected"), [
    ("darwin", "macos"), ("win32", "windows"), ("linux", "linux"),
    ("freebsd14", "linux"),
])
def test_platform_family_is_stable(value, expected):
    assert platform_family(value) == expected


def test_standard_theme_uses_cross_platform_fixed_metrics():
    theme = StandardTheme()
    assert theme.control_height == 28
    assert theme.corner_radius == 8
    assert theme.content_padding == 16


def test_color_hex_clamps_and_rounds_channels():
    assert color_hex(Color(-1, 0.5, 2)) == "#0080ff"


def test_standard_backend_validates_factory_and_reports_platform():
    with pytest.raises(TypeError, match="view_factory"):
        StandardBackend(None)
    backend = StandardBackend(lambda: Text("Hello"))
    assert backend.platform in {"macos", "linux", "windows"}
    assert isinstance(backend.available(), bool)


def test_standard_backend_starts_and_cancels_view_tasks():
    calls = []
    backend = StandardBackend(lambda: Text("Load").task(
        lambda: calls.append("ran"), task_id="one", key="load"
    ))

    backend._make_view()
    backend._tasks["load"][1].wait(1)
    assert calls == ["ran"]

    backend._async_image_cancels = [lambda: calls.append("image-unsubscribed")]
    backend._images = [object()]
    backend.close()
    assert backend._tasks == {}
    assert backend._images == []
    assert calls == ["ran", "image-unsubscribed"]


def test_standard_lifecycle_action_queues_are_one_shot():
    calls = []
    backend = StandardBackend(lambda: Text("x"))
    backend._appear_actions = [lambda: calls.append("appear")]
    backend._disappear_actions = [lambda: calls.append("disappear")]

    backend._run_appear_actions()
    backend._run_appear_actions()
    backend._run_disappear_actions()
    backend._run_disappear_actions()

    assert calls == ["appear", "disappear"]


def test_standard_routes_extended_public_views_to_native_renderers(monkeypatch):
    """Extended SwiftUI views must not fall through to a type-name placeholder."""
    backend = StandardBackend(lambda: Text("Hello"))
    backend._window_width, backend._window_height = 800, 600
    rendered = []
    backend._build_inspector = lambda view, parent: rendered.append(("inspector", view))
    backend._build_async_image = lambda view, parent: rendered.append(("async", view))
    backend._build_canvas = lambda view, parent: rendered.append(("canvas", view))
    backend._build_gradient = lambda view, parent: rendered.append(("gradient", view))
    backend._build_table = lambda view, parent: rendered.append(("table", view))

    shown = State(True)
    backend._build(InspectorView(Text("main"), shown.binding(), Text("panel")), object())
    backend._build(AsyncImage("memory://image", loader=lambda _url: b"image"), object())
    backend._build(Canvas(lambda _context, _size: None), object())
    backend._build(LinearGradient(colors=[Color.red, Color.blue]), object())
    backend._build(Table([], [TableColumn("Name", "name")]), object())

    assert [name for name, _view in rendered] == [
        "inspector", "async", "canvas", "gradient", "table",
    ]

    selected = []
    backend._build = lambda view, parent: selected.append(view)
    adaptive = ViewThatFits([Text("fits"), Text("fallback")])
    backend._build(adaptive.selected(Size(800, 600)), object())
    assert selected[0].display_content == "fits"

    outline = OutlineGroup(
        [{"id": "root", "children": []}], "children",
        lambda item: Text(item["id"]), id="id",
    )
    backend._build(outline.content_view(), object())
    assert selected[-1] is outline.content_view()


def test_standard_timeline_installs_declared_cadence_and_refreshes():
    scheduled = []

    class Root:
        def after(self, delay, callback):
            scheduled.append((delay, callback))
            return "timeline"

        def after_cancel(self, token):
            assert token == "timeline"

    timeline = TimelineView(lambda context: Text(context.date.isoformat()), cadence="seconds")
    backend = StandardBackend(lambda: timeline)
    backend._root = Root()
    backend._view = timeline
    refreshed = []
    backend._request_refresh = lambda: refreshed.append(True)

    backend._install_timeline_timer()

    assert scheduled[0][0] == 1000
    scheduled[0][1]()
    assert refreshed == [True]


def test_standard_backend_reports_a_missing_tk_runtime_clearly(monkeypatch):
    monkeypatch.setattr(standard_module, "_TK_AVAILABLE", False)
    monkeypatch.setattr(standard_module, "_TK_IMPORT_ERROR", "No module named '_tkinter'")
    backend = StandardBackend(lambda: Text("Hello"))

    assert "_tkinter" in backend.availability_reason()
    with pytest.raises(RuntimeError, match="_tkinter"):
        backend.run()


def test_standard_split_width_overrides_are_reapplied_after_rebuild():
    backend = StandardBackend(lambda: Text("Hello"))
    split = NavigationSplitView(Text("Side"), content=Text("Content"), detail=Text("Detail"))
    backend._split_width_overrides[0] = {0: 290.0, 1: 340.0}
    backend._apply_split_width_overrides(split, 0)
    assert split.sidebar_width[1] == 290.0
    assert split.content_width[1] == 340.0


def test_standard_numeric_content_transition_uses_same_runtime():
    now = [0.0]
    pending = []
    backend = StandardBackend(lambda: Text("20"))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)

    class Widget:
        def __init__(self): self.values = []
        def configure(self, **values): self.values.append(values["text"])

    widget = Widget()
    backend._animate_text_content(
        widget, "10", "20", ContentTransition.NUMERIC_TEXT, Animation.linear(0.2))
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert widget.values[0] == "10"
    assert "15" in widget.values
    assert widget.values[-1] == "20"
    assert backend._animation_handles == {}


def test_standard_symbol_effect_uses_portable_padding_motion():
    now = [0.0]
    pending = []
    backend = StandardBackend(lambda: Text("★"))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=20)

    class Widget:
        def __init__(self): self.padding = []
        def winfo_width(self): return 100
        def winfo_height(self): return 40
        def configure(self, **values): self.padding.append(values["padding"])

    widget = Widget()
    backend._animate_widget_symbol(widget, SymbolEffect.WIGGLE, Animation.linear(0.2))
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert any(left or right for left, _top, right, _bottom in widget.padding)
    assert widget.padding[-1] == (0, 0, 0, 0)


def test_standard_reconciles_safe_animation_modifiers_without_rebuild():
    old_text = Text("10")
    new_text = Text("20")
    old = old_text.content_transition(ContentTransition.NUMERIC_TEXT).id("score")
    new = new_text.content_transition(ContentTransition.NUMERIC_TEXT).id("score")

    class Widget:
        def __init__(self): self.values = []
        def configure(self, **values): self.values.append(values)

    backend = StandardBackend(lambda: new)
    widget = Widget()
    assert backend._update_widget_tree(
        old, new, {id(old_text): (widget, None)}) is True
    assert backend._widgets == {id(new_text): (widget, None)}
    assert any(values.get("text") == "20" for values in widget.values)


def test_visual_text_modifiers_propagate_to_native_text_configuration():
    root = Text("Headline").font(Font.title()).foreground_color(Color(1, 0, 0))
    resolve_visual_style_tree(root)
    text = root.find(lambda view: isinstance(view, Text))
    assert text.effective_font.size == 28
    assert color_hex(text.effective_color) == "#ff0000"

    class Widget:
        def __init__(self): self.options = None
        def configure(self, **values): self.options = values

    widget = Widget()
    StandardBackend._configure_text_widget(widget, text)
    assert widget.options["font"] == ("TkDefaultFont", 28, "bold")
    assert widget.options["foreground"] == "#ff0000"


def test_standard_updates_composite_control_widgets_in_place():
    backend = StandardBackend(lambda: Text("Controls"))

    class Widget:
        def __init__(self): self.options = []; self.bindings = []
        def configure(self, **values): self.options.append(values)
        def bind(self, event, callback): self.bindings.append(event)

    class Variable:
        def __init__(self): self.value = None
        def set(self, value): self.value = value
        def get(self): return self.value

    value = State(3)
    stepper = Stepper("Count", value.binding(), in_range=(0, 10))
    decrement, increment, value_label = Widget(), Widget(), Widget()
    backend._update_widget(stepper, Widget(), {
        "decrement": decrement, "increment": increment, "value_label": value_label,
    })
    assert decrement.options[-1]["state"] == "normal"
    assert increment.options[-1]["state"] == "normal"
    assert value_label.options[-1]["text"] == "3"

    date = DatePicker("Date", State(datetime(2026, 1, 2)).binding())
    variable, date_widget = Variable(), Widget()
    backend._update_widget(date, date_widget, {"variable": variable})
    assert variable.value == "2026-01-02"
    assert set(date_widget.bindings) == {"<Return>", "<FocusOut>"}

    color_widget, color_label = Widget(), Widget()
    color = ColorPicker("Tint", State(Color(1, 0, 0)).binding())
    backend._update_widget(color, color_widget, {"value_label": color_label})
    assert color_label.options[-1]["text"] == "#ff0000"

    gauge_widget, gauge_label = Widget(), Widget()
    gauge = Gauge(14, in_range=(10, 20), label="Capacity")
    backend._update_widget(gauge, gauge_widget, {"label": gauge_label})
    assert gauge_widget.options[-1] == {"maximum": 10.0, "value": 4.0}
    assert gauge_label.options[-1]["text"] == "Capacity"


def test_root_resize_requests_responsive_rebuild():
    backend = StandardBackend(lambda: Text("Hello"))
    root = object()
    backend._root = root
    requests = []
    backend._request_refresh = lambda: requests.append(True)
    event = type("Resize", (), {"widget": root, "width": 900, "height": 600})()
    backend._window_resized(event)
    assert (backend._window_width, backend._window_height) == (900, 600)
    assert requests == [True]
    backend._window_resized(event)
    assert requests == [True]


def test_root_resize_ignores_tk_pre_layout_dimensions():
    backend = StandardBackend(lambda: Text("Hello"))
    root = object()
    backend._root = root
    events = []
    backend._on_resize = lambda size: events.append(size)
    backend._request_refresh = lambda: events.append("refresh")

    backend._window_resized(type("Resize", (), {"widget": root, "width": 1, "height": 1})())
    backend._window_resized(type("Resize", (), {"widget": root, "width": 200, "height": 200})())

    assert events == []


def test_picker_writes_original_typed_option():
    selection = State(1)
    picker = Picker("Number", selection.binding(), [1, 2, 3])
    StandardBackend._picker_selected(picker, 2)
    assert selection.wrapped_value == 3
    assert isinstance(selection.wrapped_value, int)


def test_date_editor_parses_and_clamps_without_corrupting_invalid_input():
    selection = State(datetime(2026, 1, 1))
    picker = DatePicker("Date", selection.binding(), in_range=(
        datetime(2026, 1, 10), datetime(2026, 1, 20)))
    assert StandardBackend._date_changed(picker, "2026-01-15") is True
    assert selection.wrapped_value == datetime(2026, 1, 15)
    assert StandardBackend._date_changed(picker, "2026-01-30") is True
    assert selection.wrapped_value == datetime(2026, 1, 20)
    assert StandardBackend._date_changed(picker, "not-a-date") is False
    assert selection.wrapped_value == datetime(2026, 1, 20)


def test_standard_color_parser_and_symbol_fallbacks():
    color = StandardBackend._color_from_hex("#0080ff")
    assert color.red == 0
    assert color.green == pytest.approx(128 / 255)
    assert color.blue == 1
    with pytest.raises(ValueError, match="RRGGBB"):
        StandardBackend._color_from_hex("invalid")
    assert StandardBackend._symbol_text("gear.fill") == "⚙"


def test_presentation_binding_is_queued_only_once_until_dismissed():
    presented = State(True)
    modifier = AlertModifier("Notice", presented.binding())
    backend = StandardBackend(lambda: Text("Root"))
    backend._queue_presentation(modifier)
    backend._queue_presentation(modifier)
    assert len(backend._pending_presentations) == 1
    assert len(backend._active_presentations) == 1
    presented.wrapped_value = False
    backend._queue_presentation(modifier)
    assert backend._active_presentations == set()


def test_alert_button_dismisses_before_running_action():
    presented = State(True)
    calls = []
    button = Button("OK", lambda: calls.append(presented.wrapped_value))
    modifier = AlertModifier("Notice", presented.binding(), buttons=[button])
    backend = StandardBackend(lambda: Text("Root"))
    key = (type(modifier), id(modifier.is_presented))
    backend._active_presentations.add(key)

    class Window:
        destroyed = False
        def winfo_exists(self): return True
        def destroy(self): self.destroyed = True

    window = Window()
    backend._run_alert_button(key, modifier, window, button)
    assert calls == [False]
    assert window.destroyed is True
    assert key not in backend._active_presentations


def test_standard_application_window_registry_and_settings_singleton():
    main = Window("Main", Text("Main"), id="main", initially_presented=False)
    settings = Settings(Text("Settings"))
    app = StandardApplication(WindowGroup([main, settings]))
    launches = []

    class Root:
        def __init__(self): self.focuses = 0
        def deiconify(self): self.focuses += 1
        def lift(self): self.focuses += 1
        def focus_force(self): self.focuses += 1

    def launch(scene):
        backend = StandardBackend(scene.make_view)
        backend._root = Root()
        launches.append((scene.id, backend))
        return backend

    app._launch = launch
    assert app.open_window("missing") is False
    assert app.open_window("main") is True
    assert app.open_window("main") is True
    assert [item[0] for item in launches] == ["main"]
    assert app._window_backends["main"]._root.focuses == 3
    assert app.open_settings() is True
    assert app.open_settings() is True
    assert [item[0] for item in launches] == ["main", "settings"]


def test_standard_application_rejects_multiple_settings():
    with pytest.raises(ValueError, match="one Settings"):
        StandardApplication(WindowGroup([Settings(Text("A"), id="a"),
                                         Settings(Text("B"), id="b")]))


def test_standard_backend_scene_phase_changes_are_coalesced():
    backend = StandardBackend(lambda: Text("Phase"))
    requests = []
    backend._request_refresh = lambda: requests.append(backend._scene_phase)
    backend._set_scene_phase(ScenePhase.INACTIVE)
    backend._set_scene_phase(ScenePhase.INACTIVE)
    backend._set_scene_phase(ScenePhase.BACKGROUND)
    assert requests == [ScenePhase.INACTIVE, ScenePhase.BACKGROUND]


def test_shortcut_sequences_map_command_by_platform():
    shortcut = KeyboardShortcut("s", ("command", "shift"))
    assert StandardBackend._shortcut_sequence(shortcut, "macos") == "<Command-Shift-s>"
    assert StandardBackend._shortcut_sequence(shortcut, "windows") == "<Control-Shift-s>"
    assert StandardBackend._shortcut_sequence(shortcut, "linux") == "<Control-Shift-s>"
    assert StandardBackend._shortcut_sequence(KeyboardShortcut.default_action(), "linux") == "<Return>"
    assert StandardBackend._shortcut_sequence(KeyboardShortcut.cancel_action(), "linux") == "<Escape>"


def test_standard_application_accepts_shared_commands_model():
    commands = Commands([CommandMenu("File", [Button("Save", lambda: None).keyboard_shortcut("s")])])
    app = StandardApplication(Window("Main", Text("Root")), commands=commands)
    assert app.commands is commands


def test_standard_reconciliation_reuses_compatible_widgets():
    old_text, old_button = Text("Before"), Button("Old", lambda: None)
    new_text, new_button = Text("After"), Button("New", lambda: None)
    old = __import__("aui").VStack([old_text, old_button])
    new = __import__("aui").VStack([new_text, new_button])

    class Widget:
        def __init__(self): self.options = {}
        def configure(self, **values): self.options.update(values)

    text_widget, button_widget = Widget(), Widget()
    backend = StandardBackend(lambda: new)
    assert backend._update_widget_tree(old, new, {
        id(old_text): (text_widget, None), id(old_button): (button_widget, None),
    }) is True
    assert text_widget.options["text"] == "After"
    assert button_widget.options["text"] == "New"
    assert backend._widgets[id(new_text)][0] is text_widget


def test_standard_reconciliation_rebuilds_after_structure_change():
    old = __import__("aui").VStack([Text("One")])
    new = __import__("aui").VStack([Text("One"), Text("Two")])
    backend = StandardBackend(lambda: new)
    assert backend._update_widget_tree(old, new, {}) is False


def test_standard_list_scroll_fraction_updates_virtual_offset_once():
    offset = State(0)
    view = List([Text(str(index)) for index in range(100)],
                scroll_offset=offset.binding(), row_height=24)
    backend = StandardBackend(lambda: view)
    requests = []
    backend._request_refresh = lambda: requests.append(view.current_offset())
    backend._list_scrolled(view, 0.5)
    backend._list_scrolled(view, 0.5)
    assert offset.wrapped_value == 50
    assert requests == [50]


def test_lazy_scroll_offsets_are_isolated_by_stable_container_index():
    vertical = LazyVStack(range(1000), lambda value: Text(str(value)))
    horizontal = LazyHStack(range(1000), lambda value: Text(str(value)))
    backend = StandardBackend(lambda: Text("Root"))
    requests = []
    backend._request_refresh = lambda: requests.append(True)
    vertical_key = (LazyVStack, 0)
    horizontal_key = (LazyHStack, 1)
    backend._lazy_scrolled(vertical, vertical_key, 0.5)
    backend._lazy_scrolled(horizontal, horizontal_key, 0.25)
    assert backend._lazy_offsets[vertical_key] == 14_000
    assert backend._lazy_offsets[horizontal_key] == 20_000
    assert requests == [True, True]


def test_standard_backend_captures_animation_during_state_notification():
    backend = StandardBackend(lambda: Text("Root"))
    animation = Animation.linear(0.2)
    with with_animation(animation):
        backend._request_refresh()
    assert backend._pending_animation is animation


def test_standard_progress_uses_animation_driver_for_incremental_value():
    now = [0.0]
    pending = []
    backend = StandardBackend(lambda: ProgressView(1.0))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)

    class Progress:
        def __init__(self): self.value = 0.0
        def stop(self): pass
        def configure(self, **values):
            if "value" in values: self.value = values["value"]
        def cget(self, key): return self.value

    widget = Progress()
    backend._update_widget(ProgressView(1.0), widget, animation=Animation.linear(0.2))
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert widget.value == 100.0
    assert backend._animation_handles == {}


def test_standard_slider_restores_binding_callback_after_animation():
    now = [0.0]
    pending = []
    value = State(1.0)
    backend = StandardBackend(lambda: Slider(value.binding()))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)

    class Scale:
        def __init__(self): self.value = 0.0; self.options = {}
        def get(self): return self.value
        def set(self, value): self.value = value
        def configure(self, **values): self.options.update(values)

    widget = Scale()
    backend._update_widget(Slider(value.binding()), widget, animation=Animation.linear(0.2))
    assert widget.options["command"] is None
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert widget.value == 1.0
    assert callable(widget.options["command"])
    assert backend._animation_handles == {}
