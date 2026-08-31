import pytest

from aui import (
    Environment, EnvironmentObject, EnvironmentReader, EnvironmentValue,
    ObservedObject, StateObject, Text, VStack, observable,
)
from aui.backends.ascii import AsciiBackend
from aui.core.environment import resolve_environment_tree
from aui.core.state import observation_tracking


@observable
class Model:
    count = 0
    name = "Guest"


def test_observed_object_tracks_reads_and_binding_writes():
    model = Model()
    observed = ObservedObject(model)
    invalidations = []

    with observation_tracking(lambda: invalidations.append(True)) as cleanups:
        assert observed.value.count == 0
    observed.binding("count").value = 2
    assert invalidations == [True]

    for cleanup in cleanups:
        cleanup()
    model.count = 3
    assert invalidations == [True]


def test_state_object_creates_owned_model_once():
    creations = []
    state = StateObject(lambda: creations.append(True) or Model())

    assert creations == []
    assert state.value is state.value
    assert creations == [True]
    state.binding("name").value = "Taylor"
    assert state.value.name == "Taylor"


def test_object_wrappers_validate_models_and_binding_attributes():
    with pytest.raises(TypeError, match="add_listener"):
        ObservedObject(object())
    with pytest.raises(TypeError, match="add_listener"):
        StateObject(object())
    with pytest.raises(ValueError, match="cannot be empty"):
        ObservedObject(Model()).binding("")


def test_environment_value_inherits_and_inner_scope_overrides():
    request = EnvironmentValue("accent", "blue")
    outer = EnvironmentReader(request, lambda value: Text(f"outer={value}"))
    inner = EnvironmentReader(request, lambda value: Text(f"inner={value}"))
    tree = VStack([outer, inner.environment("accent", "orange")]).environment(
        "accent", "purple"
    )

    rendered = AsciiBackend(width=40, height=6).render(tree)
    assert "outer=purple" in rendered
    assert "inner=orange" in rendered


def test_environment_object_resolves_by_type_and_tracks_model():
    model = Model()
    request = EnvironmentObject(Model)
    reader = EnvironmentReader(request, lambda value: Text(f"count={value.count}"))
    tree = reader.environment_object(model)
    invalidations = []

    with observation_tracking(lambda: invalidations.append(True)) as cleanups:
        resolve_environment_tree(tree)
    assert reader.content.content == "count=0"
    model.count = 1
    assert invalidations == [True]
    for cleanup in cleanups:
        cleanup()


def test_missing_environment_object_is_explicit():
    reader = EnvironmentReader(EnvironmentObject(Model), lambda value: Text(value.name))
    with pytest.raises(LookupError, match="no environment object"):
        resolve_environment_tree(reader)


def test_environment_reader_validates_request_and_content():
    with pytest.raises(TypeError, match="EnvironmentValue or EnvironmentObject"):
        EnvironmentReader("accent", lambda value: Text(value))
    reader = EnvironmentReader(EnvironmentValue("value"), lambda value: "not a view")
    with pytest.raises(TypeError, match="return a View"):
        resolve_environment_tree(reader)


def test_environment_object_helper_on_plain_environment():
    model = Model()
    environment = Environment().object(model)
    assert EnvironmentObject(Model).resolve(environment) is model
