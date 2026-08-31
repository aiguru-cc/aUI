import pytest

from aui import (
    CommandMenu, Commands, DismissWindowAction, DismissWindowLink,
    KeyboardShortcut, MenuBarExtra, Divider, Button, NavigationSplitView,
    NavigationSplitViewColumn, NavigationSplitViewStyle,
    NavigationSplitViewVisibility, OpenWindowAction, Settings, State,
    Point, SettingsLink, Size, Text, Window, WindowGroup, WindowLevel, WindowLink,
    WindowResizability, WindowRestorationBehavior, WindowStyle,
    describe_accessibility,
)
from aui.backends.appkit import AppKitApplication
from aui.backends.ascii import AsciiBackend


def make_split():
    return NavigationSplitView(
        Text("Sidebar"), content=Text("Content"), detail=Text("Detail")
    )


def test_three_column_split_resolves_widths():
    split = make_split()
    widths = split.column_widths(1000)
    assert split.column_count == 3
    assert sum(widths) + split.divider_width * 2 == pytest.approx(1000)
    assert widths[0] >= split.sidebar_width[0]
    assert widths[1] >= split.content_width[0]


def test_two_column_split_and_validation():
    split = NavigationSplitView(Text("Side"), detail=Text("Detail"))
    assert split.column_count == 2
    assert sum(split.column_widths(700)) + split.divider_width == pytest.approx(700)
    with pytest.raises(ValueError):
        NavigationSplitView(Text("S"), Text("D"), sidebar_width=(300, 200, 400))


def test_split_adapts_to_compact_widths():
    split = make_split()
    assert split.column_widths(480)[:2] == [0.0, 0.0]
    medium = split.column_widths(700)
    assert medium[0] > 0 and medium[1] == 0 and medium[2] > 0


def test_split_accessibility_and_ascii_fallback():
    split = make_split()
    info = describe_accessibility(split)
    assert info.role == "splitview"
    assert len(info.children) == 3
    rendered = AsciiBackend(width=1000, height=4).render(split)
    assert "Sidebar" in rendered and "Content" in rendered and "Detail" in rendered
    assert "|" in rendered


def test_split_visibility_binding_controls_columns():
    visibility = State(NavigationSplitViewVisibility.ALL)
    split = NavigationSplitView(
        Text("Side"), content=Text("Content"), detail=Text("Detail"),
        column_visibility=visibility.binding(),
    )
    assert all(width > 0 for width in split.column_widths(1000))
    split.set_column_visibility(NavigationSplitViewVisibility.DETAIL_ONLY)
    assert split.column_widths(1000) == [0.0, 0.0, 1000.0]
    split.set_column_visibility(NavigationSplitViewVisibility.DOUBLE_COLUMN)
    widths = split.column_widths(1000)
    assert widths[0] > 0 and widths[1] == 0 and widths[2] > 0


def test_split_sidebar_visibility_hides_only_the_leading_column():
    sidebar_visible = State(True)
    split = NavigationSplitView(
        Text("Side"), content=Text("Content"), detail=Text("Detail"),
        sidebar_visibility=sidebar_visible.binding(),
    )
    sidebar_visible._set(False)
    widths = split.column_widths(1000)
    assert widths[0] == 0 and widths[1] > 0 and widths[2] > 0


def test_split_preferred_compact_column_and_ascii_collapse():
    preferred = State(NavigationSplitViewColumn.SIDEBAR)
    split = NavigationSplitView(
        Text("Sidebar"), content=Text("Content"), detail=Text("Detail"),
        preferred_compact_column=preferred.binding(),
    )
    assert split.column_widths(480) == [480.0, 0.0, 0.0]
    rendered = AsciiBackend(width=60, height=4).render(split)
    assert "Sidebar" in rendered
    assert "Content" not in rendered and "Detail" not in rendered


def test_prominent_detail_style_and_per_column_width():
    balanced = make_split().navigation_split_view_style(NavigationSplitViewStyle.BALANCED)
    prominent = make_split().navigation_split_view_style(
        NavigationSplitViewStyle.PROMINENT_DETAIL
    ).navigation_split_view_column_width(
        NavigationSplitViewColumn.SIDEBAR, 140, 180, 240
    )
    assert prominent.column_widths(1000)[-1] > balanced.column_widths(1000)[-1]
    assert prominent.sidebar_width == (140.0, 180.0, 240.0)


def test_split_configuration_validation():
    with pytest.raises(TypeError):
        NavigationSplitView(Text("S"), Text("D"), column_visibility="all")
    with pytest.raises(TypeError):
        NavigationSplitView(Text("S"), Text("D"), sidebar_visibility=True)
    with pytest.raises(ValueError):
        make_split().navigation_split_view_style("overlay")
    with pytest.raises(ValueError):
        make_split().navigation_split_view_column_width("inspector", 100, 200, 300)


def test_window_group_requires_unique_ids():
    window = Window("Main", lambda: Text("Hello"), default_size=Size(800, 600))
    assert window.make_view().content == "Hello"
    with pytest.raises(ValueError):
        WindowGroup([window, Window("Duplicate", Text("x"), id="main")])


def test_window_lifecycle_callbacks_are_validated_and_retained():
    resized, focused, closed = [], [], []
    window = Window(
        "Main", Text("Hello"),
        on_resize=resized.append,
        on_focus_changed=focused.append,
        on_close=lambda: closed.append(True),
    )
    assert callable(window.on_resize)
    assert callable(window.on_focus_changed)
    assert callable(window.on_close)
    with pytest.raises(TypeError):
        Window("Invalid", Text("x"), on_resize="not callable")


def test_window_scene_configuration_and_effective_resizability():
    window = Window(
        "Inspector", Text("Details"), id="inspector",
        window_resizability=WindowResizability.CONTENT_SIZE,
        style=WindowStyle.HIDDEN_TITLE_BAR,
        default_position=Point(40, 80), min_size=Size(240, 180),
        max_size=Size(640, 720), level=WindowLevel.FLOATING,
        restoration_behavior=WindowRestorationBehavior.DISABLED,
        restoration_id="inspector-frame",
    )
    assert window.effective_resizable is False
    assert window.default_position == Point(40, 80)
    with pytest.raises(ValueError):
        Window("Bad", Text("x"), style="glass")
    with pytest.raises(ValueError):
        Window("Bad", Text("x"), min_size=Size(500, 500), max_size=Size(200, 200))


def test_appkit_scene_configuration_without_opening_gui():
    calls = []

    class Native:
        def setContentMinSize_(self, value): calls.append(("min", value))
        def setContentMaxSize_(self, value): calls.append(("max", value))
        def setFrameAutosaveName_(self, value): calls.append(("restore", value))
        def setFrameOrigin_(self, value): calls.append(("origin", value))

    backend = type("Backend", (), {"_window": Native()})()
    scene = Window(
        "Panel", Text("x"), id="panel", default_position=Point(12, 34),
        min_size=Size(200, 150), max_size=Size(800, 600),
        restoration_id="panel-frame",
    )
    AppKitApplication._apply_scene_configuration(scene, backend)
    assert ("min", (200.0, 150.0)) in calls
    assert ("max", (800.0, 600.0)) in calls
    assert ("restore", "panel-frame") in calls
    assert ("origin", (12, 34)) in calls


def test_settings_is_a_lazy_scene_description():
    built = []
    settings = Settings(lambda: built.append(True) or Text("Preferences"))

    assert built == []
    assert settings.id == "settings"
    assert settings.make_view().content == "Preferences"
    assert built == [True]


def test_settings_link_receives_application_action():
    opened = []
    link = SettingsLink()
    link.action()
    assert opened == []
    link.connect(lambda: opened.append("settings"))
    link.action()
    assert opened == ["settings"]
    assert describe_accessibility(link).role == "button"


def test_window_group_includes_one_unique_settings_scene():
    scenes = WindowGroup([Window("Main", Text("Main")), Settings(Text("Settings"))])
    app = AppKitApplication(scenes)

    assert len(list(scenes)) == 2
    assert app._settings_scene.title == "Settings"
    assert app._settings_backend is None


def test_application_rejects_multiple_settings_scenes():
    scenes = WindowGroup([
        Settings(Text("First"), id="first"),
        Settings(Text("Second"), id="second"),
    ])
    with pytest.raises(ValueError, match="one Settings scene"):
        AppKitApplication(scenes)


def test_open_window_action_validates_and_forwards_id():
    opened = []
    action = OpenWindowAction(lambda window_id: opened.append(window_id) or True)

    assert action("inspector") is True
    assert opened == ["inspector"]
    with pytest.raises(ValueError, match="cannot be empty"):
        action("")
    with pytest.raises(TypeError, match="callable"):
        OpenWindowAction(None)


def test_window_link_receives_open_window_action():
    opened = []
    link = WindowLink("Show Inspector", "inspector")
    link.connect(lambda window_id: opened.append(window_id) or True)

    link.action()
    assert opened == ["inspector"]
    assert describe_accessibility(link).role == "button"
    with pytest.raises(ValueError, match="cannot be empty"):
        WindowLink("Invalid", "")


def test_application_indexes_lazy_windows_without_launching_them():
    inspector = Window(
        "Inspector", Text("Details"), id="inspector", initially_presented=False
    )
    app = AppKitApplication(WindowGroup([Window("Main", Text("Main")), inspector]))

    assert app._windows["inspector"] is inspector
    assert app._window_backends == {}
    assert inspector.initially_presented is False


def test_open_window_launches_once_then_focuses(monkeypatch):
    import aui.backends.appkit as appkit_module

    class NativeWindow:
        def __init__(self):
            self.focus_count = 0

        def makeKeyAndOrderFront_(self, sender):
            self.focus_count += 1

    class Backend:
        def __init__(self):
            self._window = NativeWindow()

    class Application:
        activations = 0

        @classmethod
        def sharedApplication(cls):
            return cls

        @classmethod
        def activateIgnoringOtherApps_(cls, active):
            cls.activations += 1

    app = AppKitApplication(Window(
        "Inspector", Text("Details"), id="inspector", initially_presented=False
    ))
    launched = []
    monkeypatch.setattr(app, "_launch", lambda window: launched.append(window.id) or Backend())
    monkeypatch.setattr(appkit_module, "NSApplication", Application, raising=False)

    assert app.open_window("missing") is False
    assert app.open_window("inspector") is True
    backend = app._window_backends["inspector"]
    assert app.open_window("inspector") is True
    assert launched == ["inspector"]
    assert backend._window.focus_count == 1
    assert app.backends == [backend]


def test_dismiss_window_action_uses_explicit_or_current_scene():
    dismissed = []
    action = DismissWindowAction(
        lambda window_id: dismissed.append(window_id) or True,
        current_id="inspector",
    )

    assert action() is True
    assert action("activity") is True
    assert dismissed == ["inspector", "activity"]
    assert DismissWindowAction(lambda window_id: True)() is False
    with pytest.raises(TypeError, match="callable"):
        DismissWindowAction(None)


def test_dismiss_window_link_receives_action_and_keeps_button_semantics():
    dismissed = []
    link = DismissWindowLink(window_id="inspector")
    link.connect(DismissWindowAction(lambda value: dismissed.append(value) or True))

    link.action()
    assert dismissed == ["inspector"]
    assert describe_accessibility(link).role == "button"


def test_application_dismisses_only_open_windows():
    class NativeWindow:
        def __init__(self):
            self.close_count = 0

        def performClose_(self, sender):
            self.close_count += 1

    class Backend:
        def __init__(self):
            self._window = NativeWindow()

    app = AppKitApplication(Window("Main", Text("Main"), id="main"))
    backend = Backend()
    app._window_backends["main"] = backend

    assert app.dismiss_window("unknown") is False
    assert app.dismiss_window("main") is True
    assert backend._window.close_count == 1
    assert app._window_backends["main"] is backend


def test_menu_bar_extra_validates_content_and_is_registered_by_application():
    extra = MenuBarExtra(
        "aUI",
        [
            Button("Open", lambda: None).keyboard_shortcut(KeyboardShortcut("o")),
            Divider(),
            Button("Quit", lambda: None),
        ],
        system_name="sparkles",
    )
    scenes = WindowGroup([Window("Main", Text("Main")), extra])
    app = AppKitApplication(scenes)

    assert app._menu_bar_extras == [extra]
    assert app._status_items == []
    with pytest.raises(ValueError, match="title or system_name"):
        MenuBarExtra("", [])
    with pytest.raises(TypeError, match="Button or Divider"):
        MenuBarExtra("Invalid", ["item"])


def test_application_accepts_commands_collection_or_sequence():
    menu = CommandMenu("View", [Button("Inspector", lambda: None)])
    scene = Window("Main", Text("Main"))

    assert AppKitApplication(scene, commands=[menu]).commands.menus == (menu,)
    commands = Commands([menu])
    assert AppKitApplication(scene, commands=commands).commands is commands
