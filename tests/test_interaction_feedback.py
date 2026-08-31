import pytest

from aui import (
    Circle, HoverEffect, Menu, Divider, Button, SensoryFeedback, Text,
)
from aui.core.interaction import (
    ContentShapeModifier, ContextMenuModifier, HitTestingModifier, HoverEffectModifier,
    OnHoverModifier, SensoryFeedbackModifier,
)


def test_context_menu_static_and_lazy_resolution():
    menu = Menu("Actions", [Button("Copy", lambda: None), Divider()])
    static = Text("Item").context_menu(menu).modifiers[-1]
    lazy = Text("Item").context_menu(lambda: menu).modifiers[-1]
    assert isinstance(static, ContextMenuModifier)
    assert static.resolve() is menu and lazy.resolve() is menu
    with pytest.raises(TypeError): Text("x").context_menu(lambda: "not menu").modifiers[-1].resolve()


def test_hover_callback_and_effect_validation():
    calls = []
    modifier = Text("Hover").on_hover(calls.append).modifiers[-1]
    assert isinstance(modifier, OnHoverModifier)
    modifier.action(True); modifier.action(False)
    assert calls == [True, False]
    assert isinstance(Text("x").hover_effect(HoverEffect.LIFT).modifiers[-1], HoverEffectModifier)
    with pytest.raises(ValueError): Text("x").hover_effect("glow")


def test_hit_testing_and_content_shape():
    hit = Text("x").allows_hit_testing(False).modifiers[-1]
    shape = Text("x").content_shape(Circle(), "hoverEffect").modifiers[-1]
    assert isinstance(hit, HitTestingModifier) and not hit.enabled
    assert isinstance(shape, ContentShapeModifier)
    with pytest.raises(TypeError): Text("x").content_shape("circle")
    with pytest.raises(ValueError): Text("x").content_shape(Circle(), "focus")


def test_sensory_feedback_factories_and_clamping():
    assert SensoryFeedback.success().kind == "success"
    assert SensoryFeedback.impact("heavy", 9).intensity == 1.0
    assert SensoryFeedback.impact("soft", -1).intensity == 0.0
    with pytest.raises(ValueError): SensoryFeedback("sparkle")
    with pytest.raises(ValueError): SensoryFeedback.impact("huge")


def test_sensory_feedback_modifier_trigger_condition_and_key():
    condition = lambda old, new: new > old
    modifier = Text("Saved").sensory_feedback(
        SensoryFeedback.success(), trigger=2, condition=condition, key="save"
    ).modifiers[-1]
    assert isinstance(modifier, SensoryFeedbackModifier)
    assert modifier.trigger == 2 and modifier.key == "save"
    assert modifier.condition(1, 2) and not modifier.condition(2, 1)
    with pytest.raises(TypeError): Text("x").sensory_feedback("success", 1)
    with pytest.raises(TypeError): Text("x").sensory_feedback(SensoryFeedback.success(), 1, condition=True)
