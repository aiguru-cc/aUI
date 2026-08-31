import pytest

from aui import PreferenceKey, Text, VStack
from aui.core.preferences import collect_preferences, preference_value
from aui.backends.ascii import AsciiBackend


class TotalKey(PreferenceKey):
    default_value = 0

    @classmethod
    def reduce(cls, value, next_value):
        return value + next_value


class TitlesKey(PreferenceKey):
    default_value = []

    @classmethod
    def reduce(cls, value, next_value):
        return [*value, *next_value]


def test_preferences_reduce_across_siblings():
    root = VStack([
        Text("A").preference(TotalKey, 2),
        Text("B").preference(TotalKey, 3),
        Text("C").preference(TotalKey, 5),
    ])
    values = collect_preferences(root)
    assert values[TotalKey] == 10
    assert preference_value(root, TotalKey) == 10


def test_mutable_defaults_are_not_shared():
    first = Text("A").preference(TitlesKey, ["A"])
    second = Text("B")
    collect_preferences(first)
    collect_preferences(second)
    assert preference_value(second, TitlesKey) == []


def test_transform_preference_return_value():
    root = (Text("A").preference(TotalKey, 4)
            .transform_preference(TotalKey, lambda value: value * 10))
    assert collect_preferences(root)[TotalKey] == 40


def test_transform_preference_can_mutate_in_place():
    root = (Text("A").preference(TitlesKey, ["A"])
            .transform_preference(TitlesKey, lambda value: value.append("B")))
    assert collect_preferences(root)[TitlesKey] == ["A", "B"]


def test_on_preference_change_notifies_only_for_changes():
    received = []
    root = (Text("A").preference(TotalKey, 7)
            .on_preference_change(TotalKey, received.append))
    collect_preferences(root)
    collect_preferences(root)
    assert received == [7]
    object.__setattr__(root._content._modifier, "value", 8)
    collect_preferences(root)
    assert received == [7, 8]


def test_observer_receives_default_when_no_child_emits():
    received = []
    root = Text("A").on_preference_change(TotalKey, received.append)
    collect_preferences(root)
    assert received == [0]


def test_preference_key_validation():
    with pytest.raises(TypeError): Text("x").preference(str, "bad")
    with pytest.raises(TypeError): Text("x").transform_preference(TotalKey, None)
    with pytest.raises(TypeError): Text("x").on_preference_change(TotalKey, None)


def test_backend_automatically_collects_and_notifies():
    received = []
    root = (Text("Visible").preference(TotalKey, 12)
            .on_preference_change(TotalKey, received.append))
    output = AsciiBackend(20, 2).render(root)
    assert "Visible" in output
    assert received == [12]
