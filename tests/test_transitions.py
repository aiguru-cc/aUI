import pytest

from aui import (
    Animation, ContentTransition, Keyframe, KeyframeAnimator, PhaseAnimator,
    Size, SymbolEffect, Text, Transition,
)
from aui.backends.ascii import AsciiBackend
from aui.core.transitions import (
    ContentTransitionModifier, SymbolEffectModifier, TransitionModifier,
)


def test_transition_factories_and_composition():
    move = Transition.move("trailing")
    combined = move.combined(Transition.opacity())
    asymmetric = Transition.asymmetric(Transition.scale(), move)
    assert move.edge == "trailing"
    assert combined.kind == "combined"
    assert asymmetric.insertion.kind == "scale"
    assert asymmetric.removal is move


def test_invalid_transition_edge():
    with pytest.raises(ValueError):
        Transition.move("center")


def test_transition_modifiers_attach_and_preserve_layout():
    base = Text("42")
    view = (base.transition(Transition.opacity())
            .content_transition(ContentTransition.NUMERIC_TEXT)
            .symbol_effect(SymbolEffect.BOUNCE, value=1))
    assert any(isinstance(mod, TransitionModifier) for mod in view.modifiers)
    assert any(isinstance(mod, ContentTransitionModifier) for mod in view.modifiers)
    assert isinstance(view.modifiers[-1], SymbolEffectModifier)
    assert view.size_that_fits(Size(100, 20)).width == base.size_that_fits(Size(100, 20)).width


def test_invalid_effect_values_are_rejected():
    with pytest.raises(ValueError):
        Text("x").content_transition("morph")
    with pytest.raises(ValueError):
        Text("x").symbol_effect("explode")


def test_phase_animator_advances_and_wraps():
    animator = PhaseAnimator(
        ["small", "large"], lambda phase: Text(phase),
        animation=lambda phase: Animation.spring() if phase == "large" else Animation.linear(),
    )
    assert animator.phase == "small"
    assert animator.advance() == "large"
    assert animator.content.content == "large"
    assert animator.current_animation.curve == "spring"
    assert animator.advance() == "small"


def test_phase_animator_requires_phases():
    with pytest.raises(ValueError):
        PhaseAnimator([], lambda phase: Text(str(phase)))


def test_keyframe_timeline_interpolates_by_duration():
    animator = KeyframeAnimator(
        0.0,
        [Keyframe(10.0, 1.0), Keyframe(30.0, 3.0)],
        lambda value: Text(f"{value:.1f}"),
    )
    assert animator.value_at(0.125) == pytest.approx(5.0)
    assert animator.value_at(0.25) == pytest.approx(10.0)
    assert animator.value_at(0.625) == pytest.approx(20.0)
    assert animator.value_at(1.0) == pytest.approx(30.0)


def test_keyframe_seek_rebuilds_content_and_clamps():
    animator = KeyframeAnimator(0.0, [Keyframe(1.0, 1.0)], lambda v: Text(f"{v:.1f}"))
    assert animator.seek(0.5).content.content == "0.5"
    assert animator.seek(9).progress == 1.0


def test_animators_render_headlessly():
    phase = PhaseAnimator(["Ready", "Go"], Text)
    assert "Ready" in AsciiBackend(20, 2).render(phase)
    phase.advance()
    assert "Go" in AsciiBackend(20, 2).render(phase)
    keyframes = KeyframeAnimator(0.0, [Keyframe(10.0)], lambda v: Text(str(round(v))))
    keyframes.seek(1.0)
    assert "10" in AsciiBackend(20, 2).render(keyframes)
