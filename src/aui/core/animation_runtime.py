"""Deterministic animation timelines and backend frame driving."""
from __future__ import annotations

import time
import math
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Optional

from .animation import Animation
from .geometry import Point, Size
from .transitions import SymbolEffect, Transition


@dataclass(frozen=True)
class AnimationSample:
    value: Any
    progress: float
    cycle: int
    finished: bool


class AnimationTimeline:
    """Pure time-to-value mapping for one Animation."""

    def __init__(self, animation: Animation, start: Any, end: Any,
                 start_time: float = 0.0):
        if not isinstance(animation, Animation):
            raise TypeError("animation must be Animation")
        self.animation = animation
        self.start = start
        self.end = end
        self.start_time = float(start_time)

    def sample(self, now: float) -> AnimationSample:
        animation = self.animation
        elapsed = max(0.0, float(now) - self.start_time)
        if elapsed < animation.delay_seconds:
            return AnimationSample(self.start, 0.0, 0, False)
        active = (elapsed - animation.delay_seconds) * animation.speed_factor
        duration = animation.duration
        repetitions = animation.repetitions
        if duration <= 0:
            return AnimationSample(self.end, 1.0, 0, True)
        finished = repetitions is not None and active >= duration * repetitions
        if finished:
            cycle = repetitions - 1
            progress = 0.0 if animation.autoreverses and cycle % 2 else 1.0
            return AnimationSample(animation.interpolate(self.start, self.end, progress),
                                   progress, cycle, True)
        cycle = int(active // duration)
        progress = (active - cycle * duration) / duration
        if animation.autoreverses and cycle % 2:
            progress = 1.0 - progress
        return AnimationSample(animation.interpolate(self.start, self.end, progress),
                               progress, cycle, False)


class AnimationHandle:
    def __init__(self):
        self._cancelled = False
        self._lock = RLock()

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled


class AnimationDriver:
    """Advance timelines using an injected UI-loop scheduler."""

    def __init__(self, scheduler: Callable[[float, Callable[[], None]], object],
                 clock: Callable[[], float] = time.monotonic, fps: float = 60.0):
        if not callable(scheduler) or not callable(clock):
            raise TypeError("scheduler and clock must be callable")
        self.scheduler = scheduler
        self.clock = clock
        self.frame_interval = 1.0 / max(1.0, float(fps))

    def animate(self, animation: Optional[Animation], start: Any, end: Any,
                update: Callable[[Any], None], completion: Optional[Callable[[], None]] = None
                ) -> AnimationHandle:
        if not callable(update):
            raise TypeError("animation update must be callable")
        handle = AnimationHandle()
        if animation is None:
            update(end)
            if completion is not None:
                completion()
            return handle
        timeline = AnimationTimeline(animation, start, end, self.clock())

        def tick() -> None:
            if handle.is_cancelled:
                return
            sample = timeline.sample(self.clock())
            update(sample.value)
            if sample.finished:
                if completion is not None:
                    completion()
                return
            self.scheduler(self.frame_interval, tick)

        self.scheduler(0.0, tick)
        return handle


@dataclass(frozen=True)
class TransitionSample:
    opacity: float = 1.0
    scale: float = 1.0
    offset: Point = Point()


@dataclass(frozen=True)
class SymbolEffectSample:
    opacity: float = 1.0
    scale: float = 1.0
    offset: Point = Point()


def sample_symbol_effect(effect: str, progress: float,
                         size: Size = Size()) -> SymbolEffectSample:
    """Return deterministic visual properties for a SwiftUI-style symbol effect."""
    if effect not in {SymbolEffect.APPEAR, SymbolEffect.BOUNCE, SymbolEffect.PULSE,
                      SymbolEffect.SCALE, SymbolEffect.VARIABLE_COLOR,
                      SymbolEffect.WIGGLE}:
        raise ValueError(f"unsupported symbol effect: {effect!r}")
    t = max(0.0, min(1.0, float(progress)))
    envelope = math.sin(math.pi * t)
    if effect == SymbolEffect.APPEAR:
        return SymbolEffectSample(opacity=t, scale=0.75 + 0.25 * t)
    if effect == SymbolEffect.BOUNCE:
        return SymbolEffectSample(
            scale=1.0 + 0.12 * envelope,
            offset=Point(0.0, -max(2.0, size.height * 0.18) * envelope))
    if effect in (SymbolEffect.PULSE, SymbolEffect.VARIABLE_COLOR):
        return SymbolEffectSample(opacity=1.0 - 0.35 * envelope,
                                  scale=1.0 + 0.04 * envelope)
    if effect == SymbolEffect.SCALE:
        return SymbolEffectSample(scale=1.0 + 0.18 * envelope)
    if effect == SymbolEffect.WIGGLE:
        return SymbolEffectSample(
            offset=Point(math.sin(6.0 * math.pi * t) * max(2.0, size.width * 0.06)
                         * envelope, 0.0))
    return SymbolEffectSample()


def sample_transition(transition: Transition, progress: float, size: Size = Size(),
                      inserting: bool = True) -> TransitionSample:
    """Resolve a transition into backend-neutral visual properties."""
    if not isinstance(transition, Transition):
        raise TypeError("transition must be Transition")
    t = max(0.0, min(1.0, float(progress)))
    selected = transition
    if transition.kind == "asymmetric":
        selected = transition.insertion if inserting else transition.removal
        return sample_transition(selected, t, size, inserting)
    if transition.kind == "combined":
        first = sample_transition(transition.insertion, t, size, inserting)
        second = sample_transition(transition.removal, t, size, inserting)
        return TransitionSample(first.opacity * second.opacity,
                                first.scale * second.scale,
                                Point(first.offset.x + second.offset.x,
                                      first.offset.y + second.offset.y))
    if selected.kind == "identity":
        return TransitionSample()
    if selected.kind == "opacity":
        return TransitionSample(opacity=t)
    if selected.kind == "scale":
        return TransitionSample(scale=t)
    if selected.kind == "slide":
        return TransitionSample(offset=Point((1.0 - t) * -size.width, 0.0))
    if selected.kind == "move":
        distance = 1.0 - t
        offsets = {
            "top": Point(0.0, -size.height * distance),
            "bottom": Point(0.0, size.height * distance),
            "leading": Point(-size.width * distance, 0.0),
            "trailing": Point(size.width * distance, 0.0),
        }
        return TransitionSample(offset=offsets[selected.edge])
    return TransitionSample()


__all__ = [
    "AnimationDriver", "AnimationHandle", "AnimationSample", "AnimationTimeline",
    "SymbolEffectSample", "TransitionSample", "sample_symbol_effect", "sample_transition",
]
