"""Tests for aUI state management."""
from aui.core.state import Binding, ObservableObject, State, observable


def test_state_value_and_binding():
    state = State(0)
    binding = state.binding()
    assert binding.wrapped_value == 0
    binding.wrapped_value = 42
    assert state.wrapped_value == 42


def test_observable_object_notifies():
    obj = ObservableObject()
    fired = []
    obj.add_listener(lambda: fired.append(1))
    obj.object_will_change()
    assert fired == [1]


def test_observable_decorator():
    @observable
    class Counter:
        count = 0

    c = Counter()
    fired = []
    c.add_listener(lambda: fired.append(True))
    c.count = 5
    assert c.count == 5
    assert fired == [True]
    # No notification when value unchanged.
    c.count = 5
    assert fired == [True]


def test_binding_writes_through():
    state = State("hello")
    binding = Binding(getter=lambda: state.wrapped_value, setter=state._set)
    binding.wrapped_value = "world"
    assert state.wrapped_value == "world"
