import pytest

from aui import State, Text
from aui.core.events import OnChangeModifier, run_on_change


def test_on_change_fires_only_after_value_changes():
    state = State(1)
    events = []

    def build():
        return Text(str(state.value)).on_change(
            state.value, lambda old, new: events.append((old, new)), key="count"
        )

    previous = {}
    run_on_change(build(), previous)
    run_on_change(build(), previous)
    state.value = 2
    run_on_change(build(), previous)
    assert events == [(1, 2)]


def test_on_change_supports_initial_and_callback_arities():
    events = []
    previous = {}
    run_on_change(
        Text("x").on_change("ready", lambda value: events.append(value),
                            initial=True, key="status"),
        previous,
    )
    assert events == ["ready"]

    zero = []
    run_on_change(Text("x").on_change(1, lambda: zero.append(True), key="zero"), previous)
    run_on_change(Text("x").on_change(2, lambda: zero.append(True), key="zero"), previous)
    assert zero == [True]


def test_on_change_accepts_lazy_value_and_validates_action():
    state = State("a")
    view = Text("x").on_change(lambda: state.value, lambda value: None, key="lazy")
    assert isinstance(view._modifier, OnChangeModifier)
    assert view._modifier.current_value() == "a"
    with pytest.raises(TypeError, match="must be callable"):
        Text("x").on_change(1, "invalid")
