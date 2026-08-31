import pytest

from aui import Button, PresentationDetent, Size, State, Text
from aui.core.presentation import (
    AlertModifier, ConfirmationDialogModifier, FullScreenCoverModifier,
    PopoverModifier, SheetModifier, collect_presentation_configurations,
)
from aui.core.view import _ModifiedContent


def test_sheet_modifier_is_layout_transparent_and_keeps_binding():
    presented = State(False)
    base = Text("Base")
    view = base.sheet(presented.binding(), lambda dismiss: Button("Done", dismiss),
                      title="Editor", size=Size(640, 480))
    assert isinstance(view, _ModifiedContent)
    assert isinstance(view._modifier, SheetModifier)
    assert view.size_that_fits(Size(300, 200)) == base.size_that_fits(Size(300, 200))
    assert view._modifier.size == Size(640, 480)


def test_alert_modifier_buttons_and_roles():
    presented = State(True)
    destructive = Button("Delete", lambda: None, role="destructive")
    cancel = Button("Cancel", lambda: None, role="cancel")
    view = Text("Document").alert(
        "Delete document?", presented.binding(), "This cannot be undone.",
        [destructive, cancel],
    )
    assert isinstance(view._modifier, AlertModifier)
    assert view._modifier.buttons == (destructive, cancel)
    with pytest.raises(ValueError):
        Button("Invalid", lambda: None, role="warning")


def test_presentation_requires_bindings_and_callable_content():
    with pytest.raises(TypeError):
        Text("x").sheet(True, lambda: Text("sheet"))
    with pytest.raises(TypeError):
        Text("x").sheet(State(True).binding(), Text("not callable"))
    with pytest.raises(TypeError):
        Text("x").alert("Alert", True)


def test_popover_modifier_validates_anchor_edge_and_content():
    presented = State(True)
    view = Button("Info", lambda: None).popover(
        presented.binding(), lambda dismiss: Button("Close", dismiss),
        size=Size(360, 220), edge="trailing",
    )
    assert isinstance(view._modifier, PopoverModifier)
    assert view._modifier.edge == "trailing"
    with pytest.raises(ValueError):
        Text("x").popover(presented.binding(), lambda: Text("y"), edge="center")


def test_confirmation_dialog_uses_alert_buttons():
    presented = State(False)
    dialog = Text("File").confirmation_dialog(
        "Choose an action", presented.binding(), buttons=[
            Button("Delete", lambda: None, role="destructive"),
            Button("Cancel", lambda: None, role="cancel"),
        ],
    )
    assert isinstance(dialog._modifier, ConfirmationDialogModifier)
    assert dialog._modifier.buttons[0].role == "destructive"


def test_presentation_detents_resolve_and_validate():
    assert PresentationDetent.medium().resolve(800) == 400
    assert PresentationDetent.large().resolve(800) == 800
    assert PresentationDetent.height(320).resolve(800) == 320
    assert PresentationDetent.fraction(0.25).resolve(800) == 200
    with pytest.raises(ValueError): PresentationDetent.height(0)
    with pytest.raises(ValueError): PresentationDetent.fraction(1.2)


def test_sheet_collects_chained_presentation_configuration():
    presented = State(True)
    selection = State(None)
    view = (
        Text("Host").sheet(presented.binding(), lambda: Text("Sheet"))
        .presentation_detents(
            [PresentationDetent.medium(), PresentationDetent.large()],
            selection.binding(),
        )
        .presentation_drag_indicator("visible")
        .interactive_dismiss_disabled()
        .presentation_background_interaction("enabled")
        .presentation_corner_radius(18)
    )
    collect_presentation_configurations(view)
    node = view
    while not isinstance(node._modifier, SheetModifier):
        node = node._content
    configuration = node._modifier.configuration
    assert len(configuration.detents) == 2
    assert configuration.selection is not None
    assert configuration.drag_indicator == "visible"
    assert configuration.interactive_dismiss_disabled is True
    assert configuration.background_interaction == "enabled"
    assert configuration.corner_radius == 18


def test_full_screen_cover_and_configuration_validation():
    presented = State(False)
    view = Text("Host").full_screen_cover(
        presented.binding(), lambda dismiss: Button("Close", dismiss)
    )
    assert isinstance(view._modifier, FullScreenCoverModifier)
    assert view._modifier.full_screen is True
    with pytest.raises(TypeError): Text("x").presentation_detents([])
    with pytest.raises(ValueError): Text("x").presentation_drag_indicator("sometimes")
    with pytest.raises(ValueError): Text("x").presentation_background_interaction("partial")
    with pytest.raises(ValueError): Text("x").presentation_corner_radius(-1)
