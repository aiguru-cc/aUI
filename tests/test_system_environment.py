from aui import (
    ColorScheme, ControlActiveState, DismissAction, EnvironmentReader,
    OpenURLAction, OpenURLDisposition, OpenURLResult, ScenePhase, Text,
    VStack, color_scheme, control_active_state, dismiss, open_url, scene_phase,
)
from aui.core.environment import resolve_environment_tree
from aui.core.system_environment import system_environment


def test_system_environment_reader_values():
    seen = []
    view = VStack([
        EnvironmentReader(scene_phase, lambda value: seen.append(value) or Text(value.value)),
        EnvironmentReader(color_scheme, lambda value: seen.append(value) or Text(value.value)),
        EnvironmentReader(control_active_state,
                          lambda value: seen.append(value) or Text(value.value)),
    ])
    resolve_environment_tree(view, system_environment(
        phase=ScenePhase.BACKGROUND,
        scheme=ColorScheme.DARK,
        active_state=ControlActiveState.INACTIVE,
    ))
    assert seen == [ScenePhase.BACKGROUND, ColorScheme.DARK, ControlActiveState.INACTIVE]


def test_scoped_system_environment_modifiers():
    values = []
    view = EnvironmentReader(
        color_scheme, lambda value: values.append(value) or Text("theme")
    ).preferred_color_scheme(ColorScheme.DARK)
    resolve_environment_tree(view, system_environment())
    assert values == [ColorScheme.DARK]


def test_open_url_action_policy_and_redirect():
    opened = []
    action = OpenURLAction(
        lambda url: OpenURLResult.system_action("https://example.com/redirect"),
        system_opener=lambda url: opened.append(url) or True,
    )
    result = action("https://example.com/original")
    assert result.disposition is OpenURLDisposition.HANDLED
    assert opened == ["https://example.com/redirect"]
    assert action("not a url").disposition is OpenURLDisposition.DISCARDED


def test_open_url_action_can_handle_or_discard_without_system_open():
    assert OpenURLAction(lambda _url: True)("mailto:test@example.com").disposition is OpenURLDisposition.HANDLED
    assert OpenURLAction(lambda _url: False)("https://example.com").disposition is OpenURLDisposition.DISCARDED


def test_environment_actions_are_callable_and_scoped():
    calls = []
    readers = []
    view = VStack([
        EnvironmentReader(open_url, lambda action: readers.append(action) or Text("open")),
        EnvironmentReader(dismiss, lambda action: readers.append(action) or Text("dismiss")),
    ]).open_url_action(lambda url: calls.append(url) or True).dismiss_action(
        lambda: calls.append("dismiss")
    )
    resolve_environment_tree(view, system_environment())
    assert readers[0]("https://example.com").disposition is OpenURLDisposition.HANDLED
    assert readers[1]() is True
    assert calls == ["https://example.com", "dismiss"]


def test_dismiss_action_without_host_is_noop():
    assert DismissAction()() is False


def test_appkit_backend_tracks_window_environment_without_opening_window():
    from aui.backends.appkit import AppKitBackend

    backend = AppKitBackend(lambda: EnvironmentReader(
        scene_phase, lambda phase: Text(phase.value)
    ))
    backend.windowDidResignKey_(None)
    view = backend._make_view()
    assert view.content.content == "inactive"
    backend.windowDidMiniaturize_(None)
    view = backend._make_view()
    assert view.content.content == "background"
