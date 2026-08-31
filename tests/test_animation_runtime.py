import pytest

from aui import Animation, Size, SymbolEffect, Transition
from aui.core.animation_runtime import (
    AnimationDriver, AnimationTimeline, sample_symbol_effect, sample_transition,
)


def test_timeline_honors_delay_speed_and_easing():
    animation = Animation.linear(2).delay(1).speed(2)
    timeline = AnimationTimeline(animation, 0.0, 10.0, start_time=5.0)
    assert timeline.sample(5.5).value == 0.0
    assert timeline.sample(6.5).value == 5.0
    assert timeline.sample(7.0).value == 10.0
    assert timeline.sample(7.0).finished is True


def test_timeline_autoreverses_repeated_cycles():
    timeline = AnimationTimeline(Animation.linear(1).repeat_count(2), 0.0, 10.0)
    assert timeline.sample(0.25).value == 2.5
    assert timeline.sample(1.25).value == 7.5
    final = timeline.sample(2.0)
    assert final.value == 0.0
    assert final.finished is True


def test_repeat_forever_never_finishes():
    timeline = AnimationTimeline(Animation.linear(1).repeat_forever(False), 0.0, 1.0)
    assert timeline.sample(10_000.25).finished is False
    assert timeline.sample(10_000.25).value == 0.25


def test_driver_uses_injected_clock_and_scheduler():
    now = [0.0]
    pending = []
    values = []
    completed = []
    driver = AnimationDriver(lambda delay, callback: pending.append((delay, callback)),
                             clock=lambda: now[0], fps=10)
    driver.animate(Animation.linear(1), 0.0, 10.0, values.append,
                   lambda: completed.append(True))
    while pending:
        delay, callback = pending.pop(0)
        now[0] += delay
        callback()
    assert values[0] == 0.0
    assert values[-1] == 10.0
    assert completed == [True]


def test_cancelled_driver_stops_future_frames():
    pending = []
    values = []
    driver = AnimationDriver(lambda delay, callback: pending.append(callback), clock=lambda: 0.0)
    handle = driver.animate(Animation.linear(1), 0.0, 1.0, values.append)
    handle.cancel()
    pending.pop()()
    assert values == []


def test_none_animation_commits_immediately():
    values = []
    completed = []
    AnimationDriver(lambda _delay, _callback: None).animate(
        None, 0, 4, values.append, lambda: completed.append(True))
    assert values == [4]
    assert completed == [True]


def test_transition_sampling_covers_geometry_and_composition():
    size = Size(100, 40)
    assert sample_transition(Transition.opacity(), 0.25, size).opacity == 0.25
    assert sample_transition(Transition.scale(), 0.5, size).scale == 0.5
    assert sample_transition(Transition.move("trailing"), 0.25, size).offset.x == 75
    combined = Transition.opacity().combined(Transition.move("top"))
    sample = sample_transition(combined, 0.5, size)
    assert sample.opacity == 0.5
    assert sample.offset.y == -20


def test_asymmetric_transition_selects_insertion_or_removal():
    transition = Transition.asymmetric(Transition.scale(), Transition.opacity())
    assert sample_transition(transition, 0.3, inserting=True).scale == 0.3
    assert sample_transition(transition, 0.3, inserting=False).opacity == 0.3


def test_symbol_effect_sampling_is_stable_and_returns_to_identity():
    size = Size(100, 40)
    assert sample_symbol_effect(SymbolEffect.APPEAR, 0, size).opacity == 0
    bounce = sample_symbol_effect(SymbolEffect.BOUNCE, 0.5, size)
    assert bounce.scale > 1
    assert bounce.offset.y < 0
    assert sample_symbol_effect(SymbolEffect.SCALE, 1, size).scale == pytest.approx(1)
    assert sample_symbol_effect(SymbolEffect.WIGGLE, 1, size).offset.x == pytest.approx(0)


def test_invalid_symbol_effect_sampling_is_rejected():
    with pytest.raises(ValueError, match="unsupported symbol effect"):
        sample_symbol_effect("explode", 0.5)
