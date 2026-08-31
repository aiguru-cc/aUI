from aui import (
    Animation, Button, ContentTransition, Picker, ProgressView, State, Text,
    Namespace, NavigationSplitView, Spacer, SymbolEffect, Transition, VStack,
)
from aui.core.animation_runtime import AnimationDriver
from aui.backends import appkit as appkit_module
from aui.backends.appkit import AppKitBackend
from aui.core.geometry import Point, Size


class _ButtonControl:
    def __init__(self):
        self.title = None
        self.enabled = None
        self.frame = None
        self.alpha = None
        self.removed = False

    def setTitle_(self, value):
        self.title = value

    def setEnabled_(self, value):
        self.enabled = value

    def setAlphaValue_(self, value):
        self.alpha = value

    def setFrame_(self, value):
        self.frame = value

    def removeFromSuperview(self):
        self.removed = True


def test_appkit_reuses_compatible_native_leaf(monkeypatch):
    old_button = Button("Before", lambda: None)
    new_button = Button("After", lambda: None)
    old = VStack([old_button])
    new = VStack([new_button])
    native = _ButtonControl()
    backend = AppKitBackend(lambda: new)
    backend._frames = {id(new_button): (Point(4, 6), Size(90, 24))}
    monkeypatch.setattr(appkit_module, "NSMakeRect", lambda *values: values, raising=False)

    assert backend._update_native_tree(old, new, {id(old_button): native}) is True
    assert native.title == "After"
    assert native.frame == (4, 6, 90, 24)
    assert backend._controls == {id(new_button): native}


def test_appkit_rebuilds_when_structure_changes():
    old_button = Button("Before", lambda: None)
    old = VStack([old_button])
    new = VStack([Button("After", lambda: None), Text("Added")])
    backend = AppKitBackend(lambda: new)
    assert backend._update_native_tree(old, new, {id(old_button): _ButtonControl()}) is False


class _IncrementalBackend(AppKitBackend):
    def _build_leaf(self, view, parent, x, y, size):
        native = _ButtonControl()
        native.setTitle_(view.title)
        native.setFrame_((x, y, size.width, size.height))
        self._controls[id(view)] = native


def test_appkit_inserts_and_removes_identified_leaves_locally(monkeypatch):
    first_old = Button("First", lambda: None)
    old = VStack([first_old.id("first")])
    first_new = Button("First updated", lambda: None)
    second_new = Button("Second", lambda: None)
    new = VStack([first_new.id("first"), second_new.id("second")])
    native_first = _ButtonControl()
    backend = _IncrementalBackend(lambda: new)
    backend._content = object()
    backend._frames = {
        id(first_new): (Point(0, 0), Size(80, 24)),
        id(second_new): (Point(0, 30), Size(80, 24)),
    }
    monkeypatch.setattr(appkit_module, "NSMakeRect", lambda *values: values, raising=False)

    assert backend._update_native_tree(old, new, {id(first_old): native_first}) is True
    assert native_first.title == "First updated"
    assert len(backend._controls) == 2

    newer_first = Button("Only", lambda: None)
    newer = VStack([newer_first.id("first")])
    backend._frames = {id(newer_first): (Point(0, 0), Size(80, 24))}
    second_native = backend._controls[id(second_new)]
    assert backend._update_native_tree(new, newer, dict(backend._controls)) is True
    assert second_native.removed is True
    assert backend._controls == {id(newer_first): native_first}


class _PopupControl:
    def __init__(self):
        self.items = []
        self.selected = None
        self.enabled = None

    def removeAllItems(self):
        self.items.clear()

    def addItemWithTitle_(self, value):
        self.items.append(value)

    def selectItemWithTitle_(self, value):
        self.selected = value

    def setEnabled_(self, value):
        self.enabled = value


def test_appkit_updates_picker_options_and_selection_without_rebuild():
    selection = State("B")
    picker = Picker("Choice", selection.binding(), ["A", "B", "C"])
    native = _PopupControl()
    AppKitBackend(lambda: picker)._update_native_leaf(picker, native)
    assert native.items == ["A", "B", "C"]
    assert native.selected == "B"
    assert native.enabled is True


def test_appkit_split_divider_width_persists_across_view_rebuilds():
    def make_split():
        return NavigationSplitView(Text("Sidebar"), content=Text("Content"), detail=Text("Detail"))

    split = make_split()
    backend = AppKitBackend(make_split)
    backend._view = split
    backend._layout(split, 1000, 600)
    initial = split.column_widths(1000)[0]
    backend.resizeSplitDivider_(0, 0, 70)

    rebuilt = make_split()
    backend._layout(rebuilt, 1000, 600)
    assert rebuilt.column_widths(1000)[0] == initial + 70


def test_appkit_window_resize_relayouts_content_and_emits_size(monkeypatch):
    class Native:
        def __init__(self, width, height): self.size = type("Size", (), {"width": width, "height": height})()
        def frame(self): return type("Frame", (), {"size": self.size})()
        def contentView(self): return self

    class Content(Native):
        def __init__(self): super().__init__(600, 400); self.frame_value = None
        def setFrame_(self, value): self.frame_value = value

    sizes = []
    backend = AppKitBackend(lambda: Text("Hello"), on_resize=sizes.append)
    backend._window, backend._content = Native(900, 700), Content()
    backend._content_h = 400
    monkeypatch.setattr(appkit_module, "NSMakeRect", lambda *values: values)
    backend._refresh_content = lambda: setattr(backend, "refreshed", True)
    backend.windowDidResize_(None)
    assert backend._content.frame_value == (0, 0, 900.0, 700.0)
    assert backend.refreshed is True
    assert sizes == [Size(900, 700)]


class _ProgressControl:
    def __init__(self):
        self.indeterminate = None
        self.value = None
        self.stopped = False

    def setIndeterminate_(self, value):
        self.indeterminate = value

    def setDoubleValue_(self, value):
        self.value = value

    def stopAnimation_(self, _sender):
        self.stopped = True


def test_appkit_updates_determinate_progress_in_place():
    progress = ProgressView(0.42)
    native = _ProgressControl()
    AppKitBackend(lambda: progress)._update_native_leaf(progress, native)
    assert native.indeterminate is False
    assert native.value == 42.0
    assert native.stopped is True


def test_appkit_native_frame_animation_interpolates_on_injected_driver(monkeypatch):
    now = [0.0]
    pending = []
    backend = AppKitBackend(lambda: Text("Frame"))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)
    monkeypatch.setattr(appkit_module, "NSMakeRect", lambda *values: values, raising=False)

    class Native:
        frames = []
        def setFrame_(self, value): self.frames.append(value)

    native = Native()
    backend._animate_native_frame(
        native, (Point(0, 0), Size(20, 10)), (Point(100, 40), Size(40, 30)),
        Animation.linear(0.2),
    )
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert native.frames[0] == (0, 0, 20, 10)
    assert native.frames[-1] == (100, 40, 40, 30)
    assert backend._animation_handles == {}


def test_appkit_transition_animates_alpha_and_scaled_frame(monkeypatch):
    now = [0.0]
    pending = []
    backend = AppKitBackend(lambda: Text("Transition"))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)
    monkeypatch.setattr(appkit_module, "NSMakeRect", lambda *values: values, raising=False)

    class Native:
        def __init__(self): self.frames = []; self.alpha = []
        def setFrame_(self, value): self.frames.append(value)
        def setAlphaValue_(self, value): self.alpha.append(value)

    native = Native()
    transition = Transition.opacity().combined(Transition.scale())
    backend._animate_native_transition(
        native, (Point(10, 20), Size(100, 40)), transition, Animation.linear(0.2))
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert native.alpha[0] == 0
    assert native.alpha[-1] == 1
    assert native.frames[0] == (60, 40, 0, 0)
    assert native.frames[-1] == (10, 20, 100, 40)


def test_appkit_removal_uses_asymmetric_removal_transition(monkeypatch):
    now = [0.0]
    pending = []
    old_button = Button("Old", lambda: None)
    old = VStack([old_button.transition(Transition.asymmetric(
        Transition.scale(), Transition.opacity())).id("old")])
    new = VStack([])
    native = _ButtonControl()
    backend = AppKitBackend(lambda: new)
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)
    backend._frames = {}
    monkeypatch.setattr(appkit_module, "NSMakeRect", lambda *values: values, raising=False)

    assert backend._update_native_tree(
        old, new, {id(old_button): native},
        {id(old_button): (Point(0, 0), Size(80, 24))}, Animation.linear(0.2)) is True
    assert native.removed is False
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert native.alpha == 0
    assert native.frame == (0, 0, 80, 24)
    assert native.removed is True


def test_appkit_numeric_content_transition_interpolates_text():
    now = [0.0]
    pending = []
    backend = AppKitBackend(lambda: Text("10"))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)

    class Native:
        def __init__(self): self.values = []
        def setStringValue_(self, value): self.values.append(value)

    native = Native()
    backend._animate_native_text_content(
        native, "10", "20", ContentTransition.NUMERIC_TEXT, Animation.linear(0.2))
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert native.values[0] == "10"
    assert "15" in native.values
    assert native.values[-1] == "20"
    assert backend._animation_handles == {}


def test_appkit_opacity_content_transition_crossfades_non_numeric_text():
    now = [0.0]
    pending = []
    backend = AppKitBackend(lambda: Text("New"))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)

    class Native:
        def __init__(self): self.values = []; self.alpha = []
        def setStringValue_(self, value): self.values.append(value)
        def setAlphaValue_(self, value): self.alpha.append(value)

    native = Native()
    backend._animate_native_text_content(
        native, "Old", "New", ContentTransition.OPACITY, Animation.linear(0.2))
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert native.values[0] == "Old"
    assert native.values[-1] == "New"
    assert 0 in native.alpha
    assert native.alpha[-1] == 1


def test_appkit_symbol_effect_restores_native_geometry(monkeypatch):
    now = [0.0]
    pending = []
    backend = AppKitBackend(lambda: Text("★"))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)
    monkeypatch.setattr(appkit_module, "NSMakeRect", lambda *values: values, raising=False)

    class Native:
        def __init__(self): self.frames = []; self.alpha = []
        def setFrame_(self, value): self.frames.append(value)
        def setAlphaValue_(self, value): self.alpha.append(value)

    native = Native()
    backend._animate_native_symbol(
        native, (Point(10, 20), Size(100, 40)), SymbolEffect.BOUNCE,
        Animation.linear(0.2))
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert any(frame[1] < 20 for frame in native.frames)
    assert native.frames[-1] == (10, 20, 100, 40)
    assert native.alpha[-1] == 1


def test_appkit_repeating_symbol_effect_uses_infinite_animation(monkeypatch):
    old_text = Text("★")
    new_text = Text("★")
    old = old_text.symbol_effect(SymbolEffect.PULSE, value=1)
    new = new_text.symbol_effect(SymbolEffect.PULSE, value=2, repeating=True)
    native = _ButtonControl()
    backend = AppKitBackend(lambda: new)
    frame = (Point(0, 0), Size(24, 24))
    backend._frames = {id(new_text): frame}
    captured = []
    monkeypatch.setattr(backend, "_update_native_leaf", lambda *_args: None)
    monkeypatch.setattr(
        backend, "_animate_native_symbol",
        lambda _native, _frame, effect, animation: captured.append((effect, animation)))
    monkeypatch.setattr(appkit_module, "NSMakeRect", lambda *values: values, raising=False)

    assert backend._update_native_tree(
        old, new, {id(old_text): native}, {id(old_text): frame}) is True
    assert captured[0][0] == SymbolEffect.PULSE
    assert captured[0][1].repetitions is None


def test_appkit_matched_geometry_reuses_native_control_across_paths(monkeypatch):
    namespace = Namespace.create()
    old_text = Text("Card")
    new_text = Text("Card")
    old = VStack([
        old_text.matched_geometry_effect("card", namespace), Spacer(),
    ])
    new = VStack([
        Spacer(), new_text.matched_geometry_effect(
            "card", namespace, properties="position", is_source=False),
    ])
    native = _ButtonControl()
    backend = AppKitBackend(lambda: new)
    old_frame = (Point(0, 0), Size(80, 24))
    new_frame = (Point(120, 40), Size(100, 30))
    backend._frames = {id(new_text): new_frame}
    captured = []
    monkeypatch.setattr(backend, "_update_native_leaf", lambda *_args: None)
    monkeypatch.setattr(
        backend, "_animate_native_matched_frame",
        lambda control, start, end, animation, modifier:
        captured.append((control, start, end, modifier.properties)))

    assert backend._update_native_tree(
        old, new, {id(old_text): native}, {id(old_text): old_frame},
        Animation.linear(0.2)) is True
    assert backend._controls == {id(new_text): native}
    assert native.removed is False
    assert captured == [(native, old_frame, new_frame, "position")]


def test_appkit_matched_position_preserves_selected_anchor(monkeypatch):
    now = [0.0]
    pending = []
    namespace = Namespace.create()
    modifier = Text("Card").matched_geometry_effect(
        "card", namespace, properties="position", anchor="bottomTrailing",
        is_source=False).modifiers[-1]
    backend = AppKitBackend(lambda: Text("Card"))
    backend._animation_driver = AnimationDriver(
        lambda delay, callback: pending.append((delay, callback)), lambda: now[0], fps=10)
    monkeypatch.setattr(appkit_module, "NSMakeRect", lambda *values: values, raising=False)

    class Native:
        def __init__(self): self.frames = []
        def setFrame_(self, value): self.frames.append(value)

    native = Native()
    backend._animate_native_matched_frame(
        native, (Point(0, 0), Size(80, 24)),
        (Point(120, 40), Size(100, 30)), Animation.linear(0.2), modifier)
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert native.frames[0] == (-20, -6, 100, 30)
    assert native.frames[-1] == (120, 40, 100, 30)
