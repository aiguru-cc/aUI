import math

import pytest

from aui import (
    Animation, Namespace, Text, Transaction, VStack, with_transaction,
)
from aui.core.animation import current_animation, current_transaction
from aui.core.animation_modifiers import (
    animations_disabled,
    MatchedGeometryEffectModifier, TransactionModifier,
    resolve_transaction_tree, resolved_animation,
)
from aui.core.environment import resolve_environment_tree


def test_animation_timing_composition_is_non_mutating():
    base = Animation.ease_in_out(0.4)
    composed = base.delay(0.2).speed(2).repeat_count(3, autoreverses=False)
    assert base.delay_seconds == 0
    assert composed.delay_seconds == pytest.approx(0.2)
    assert composed.speed_factor == pytest.approx(2)
    assert composed.repetitions == 3
    assert not composed.autoreverses
    assert composed.effective_duration == pytest.approx(0.8)


def test_repeat_forever_has_infinite_duration():
    animation = Animation.linear(1).repeat_forever()
    assert animation.repetitions is None
    assert math.isinf(animation.effective_duration)


def test_animation_speed_is_safely_clamped():
    assert Animation.linear(1).speed(0).speed_factor > 0


def test_with_transaction_sets_animation_and_restores_context():
    tx = Transaction(Animation.spring(), is_continuous=True)
    with with_transaction(tx):
        assert current_transaction() is tx
        assert current_animation() is tx.animation
    assert current_transaction() is None
    assert current_animation() is None


def test_disabled_transaction_suppresses_current_animation():
    tx = Transaction(Animation.linear(), disables_animations=True)
    with with_transaction(tx):
        assert current_animation() is None


def test_transaction_modifier_can_mutate_or_return_transaction():
    mutate = Text("x").transaction(lambda tx: setattr(tx, "disables_animations", True))
    modifier = mutate.modifiers[-1]
    assert isinstance(modifier, TransactionModifier)
    assert modifier.resolve(Transaction(Animation.linear())).disables_animations

    replace = Text("x").transaction(lambda tx: Transaction(Animation.spring()))
    assert replace.modifiers[-1].resolve().animation.curve == "spring"


def test_matched_geometry_namespace_and_pairing_key():
    namespace = Namespace.create()
    source = Text("Small").matched_geometry_effect("card", namespace)
    target = Text("Large").matched_geometry_effect(
        "card", namespace, properties="position", is_source=False
    )
    left = source.modifiers[-1]
    right = target.modifiers[-1]
    assert isinstance(left, MatchedGeometryEffectModifier)
    assert left.key == right.key
    assert left.is_source and not right.is_source


def test_invalid_matched_geometry_properties():
    with pytest.raises(ValueError):
        Text("x").matched_geometry_effect("x", Namespace.create(), properties="color")
    with pytest.raises(ValueError, match="anchor"):
        Text("x").matched_geometry_effect("x", Namespace.create(), anchor="baseline")


def test_matched_geometry_anchor_fraction_is_deterministic():
    modifier = Text("x").matched_geometry_effect(
        "x", Namespace.create(), anchor="bottomTrailing").modifiers[-1]
    assert modifier.anchor_fraction == (1.0, 1.0)


def test_reduce_motion_environment_disables_descendant_animation():
    child = Text("Moving").transaction(lambda tx: setattr(tx, "animation", Animation.spring()))
    root = VStack([child]).accessibility_reduce_motion()
    resolve_environment_tree(root)
    resolve_transaction_tree(root)
    text = root.find(lambda view: isinstance(view, Text))
    assert text._resolved_transaction.disables_animations
    assert text._resolved_transaction.animation is None
    assert animations_disabled(text) is True
    assert resolved_animation(text, Animation.linear()) is None


def test_resolved_animation_prefers_scoped_transaction_animation():
    scoped = Animation.spring()
    root = Text("Scoped").transaction(lambda tx: setattr(tx, "animation", scoped))
    resolve_environment_tree(root)
    resolve_transaction_tree(root)
    text = root.find(lambda view: isinstance(view, Text))
    assert resolved_animation(text, Animation.linear()) is scoped
