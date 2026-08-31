import pytest

from aui import Button, State, Text
from aui.core.presentation import SnackBarModifier


def test_snack_bar_is_a_non_modal_binding_modifier():
    shown = State(False)
    view = Text("Workspace").snack_bar("Saved", shown.binding(), duration=2)
    modifier = view._modifier
    assert isinstance(modifier, SnackBarModifier)
    assert modifier.message == "Saved" and modifier.duration == 2


def test_snack_bar_validates_state_action_and_duration():
    shown = State(False)
    with pytest.raises(TypeError):
        SnackBarModifier("Saved", shown.binding(), action=Text("Undo"))
    with pytest.raises(ValueError):
        SnackBarModifier("Saved", shown.binding(), duration=0)
