import pytest

from aui import Color, InspectorView, Size, State, Text
from aui.backends.ascii import AsciiBackend


def test_inspector_visibility_and_adaptive_columns():
    shown = State(False)
    view = Text("Document").inspector(shown.binding(), lambda: Text("Properties"))
    assert isinstance(view, InspectorView)
    assert view.column_widths(900) == (900.0, 0.0)
    shown.value = True
    assert view.column_widths(900) == (619.0, 280.0)
    assert view.column_widths(500) == (0.0, 500.0)
    view.dismiss()
    assert shown.value is False


def test_inspector_width_and_background_configuration():
    shown = State(True)
    view = Text("Main").inspector(shown.binding(), Text("Panel"))
    result = view.inspector_column_width(200, 320, 360).inspector_background(Color.blue)
    assert result is view
    assert view.column_widths(1000) == (679.0, 320.0)
    assert view.background == Color.blue
    with pytest.raises(ValueError):
        view.inspector_column_width(400, 300, 500)
    with pytest.raises(TypeError):
        view.inspector_background("blue")


def test_inspector_validation_and_layout():
    with pytest.raises(TypeError):
        Text("Main").inspector(True, Text("Panel"))
    with pytest.raises(TypeError):
        Text("Main").inspector(State(True).binding(), lambda: "Panel")
    view = Text("Main").inspector(State(True).binding(), Text("Panel"))
    assert view.size_that_fits(Size(800, 400)) == Size(800, 400)


def test_ascii_inspector_wide_and_compact_modes():
    wide = Text("Main").inspector(
        State(True).binding(), Text("Inspector"), minimum=10, ideal=20,
        maximum=25, compact_threshold=30,
    )
    rendered = AsciiBackend(width=60, height=3).render(wide)
    assert "Main" in rendered and "Inspector" in rendered and "|" in rendered
    compact = Text("Main").inspector(State(True).binding(), Text("Inspector"))
    rendered = AsciiBackend(width=40, height=3).render(compact)
    assert "Main" not in rendered and "Inspector" in rendered
