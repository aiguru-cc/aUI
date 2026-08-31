import pytest

from aui import (
    Gauge, Link, Picker, PickerStyle, State, TextEditor,
    describe_accessibility,
)
from aui.backends.ascii import AsciiBackend
from aui.core.components import SearchField
from aui.core.geometry import Size


def test_search_and_editor_keep_bindings():
    value = State("hello")
    search = SearchField(value.binding())
    editor = TextEditor(value.binding(), min_height=80)
    search.text.wrapped_value = "changed"
    assert editor.text.wrapped_value == "changed"
    assert editor.size_that_fits(Size(300, 200)).height == 80


def test_segmented_picker_exposes_picker_contract():
    selected = State("A")
    control = Picker("", selection=selected.binding(), options=["A", "B"]).picker_style(
        PickerStyle.SEGMENTED
    )
    picker = control._content
    assert picker.options == ["A", "B"]
    assert picker.selection.wrapped_value == "A"
    assert control.size_that_fits(Size(300, 40)).height == 28


def test_gauge_normalizes_and_validates_range():
    gauge = Gauge(75, in_range=(0, 100))
    assert gauge.value == pytest.approx(0.75)
    assert gauge.raw_value == 75
    with pytest.raises(ValueError):
        Gauge(1, in_range=(2, 2))


def test_ascii_backend_renders_new_components():
    search = SearchField(State("swift").binding())
    assert "? swift" in AsciiBackend().render(search)
    assert "Python" in AsciiBackend().render(Link("Python", "https://python.org"))


@pytest.mark.parametrize(
    ("view", "role"),
    [
        (SearchField(State("").binding()), "searchfield"),
        (TextEditor(State("").binding()), "texteditor"),
        (Picker("", options=["A"]).picker_style(PickerStyle.SEGMENTED), "picker"),
        (Gauge(0.5), "progress"),
        (Link("Docs", "https://example.com"), "link"),
    ],
)
def test_new_components_have_accessibility_roles(view, role):
    assert describe_accessibility(view).role == role
