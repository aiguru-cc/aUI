"""Transitions, content effects, phase animation and keyframe animation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Sequence

from .animation import Animation, interpolate
from .geometry import Point, Size
from .view import View, ViewModifier, _apply


@dataclass(frozen=True)
class Transition:
    kind: str
    edge: Optional[str] = None
    insertion: Optional["Transition"] = None
    removal: Optional["Transition"] = None

    @classmethod
    def identity(cls): return cls("identity")
    @classmethod
    def opacity(cls): return cls("opacity")
    @classmethod
    def scale(cls): return cls("scale")
    @classmethod
    def slide(cls): return cls("slide")
    @classmethod
    def move(cls, edge: str):
        if edge not in {"top", "bottom", "leading", "trailing"}:
            raise ValueError(f"unsupported transition edge: {edge!r}")
        return cls("move", edge=edge)
    @classmethod
    def asymmetric(cls, insertion: "Transition", removal: "Transition"):
        return cls("asymmetric", insertion=insertion, removal=removal)

    def combined(self, other: "Transition") -> "Transition":
        return Transition("combined", insertion=self, removal=other)


class ContentTransition:
    IDENTITY = "identity"
    INTERPOLATE = "interpolate"
    NUMERIC_TEXT = "numericText"
    OPACITY = "opacity"


class SymbolEffect:
    APPEAR = "appear"
    BOUNCE = "bounce"
    PULSE = "pulse"
    SCALE = "scale"
    VARIABLE_COLOR = "variableColor"
    WIGGLE = "wiggle"


@dataclass(frozen=True)
class TransitionModifier(ViewModifier):
    transition: Transition

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class ContentTransitionModifier(ViewModifier):
    transition: str

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class SymbolEffectModifier(ViewModifier):
    effect: str
    value: Any = None
    repeating: bool = False

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def transition(view: View, value: Transition) -> View:
    if not isinstance(value, Transition):
        raise TypeError("transition expects a Transition")
    return _apply(view, TransitionModifier(value))


def content_transition(view: View, value: str) -> View:
    if value not in {ContentTransition.IDENTITY, ContentTransition.INTERPOLATE,
                     ContentTransition.NUMERIC_TEXT, ContentTransition.OPACITY}:
        raise ValueError(f"unsupported content transition: {value!r}")
    return _apply(view, ContentTransitionModifier(value))


def symbol_effect(view: View, effect: str, value=None, repeating: bool = False) -> View:
    if effect not in {SymbolEffect.APPEAR, SymbolEffect.BOUNCE, SymbolEffect.PULSE,
                      SymbolEffect.SCALE, SymbolEffect.VARIABLE_COLOR, SymbolEffect.WIGGLE}:
        raise ValueError(f"unsupported symbol effect: {effect!r}")
    return _apply(view, SymbolEffectModifier(effect, value, repeating))


class PhaseAnimator(View):
    """A deterministic phase-driven view; call ``advance`` to move phases."""

    def __init__(self, phases: Sequence[Any], content: Callable[[Any], View],
                 animation: Optional[Callable[[Any], Animation] | Animation] = None,
                 trigger: Any = None):
        if not phases:
            raise ValueError("PhaseAnimator requires at least one phase")
        self.phases = tuple(phases)
        self.content_builder = content
        self.animation_for_phase = animation
        self.trigger = trigger
        self.phase_index = 0
        self._content = content(self.phases[0])
        self._children = [self._content]

    @property
    def phase(self): return self.phases[self.phase_index]

    @property
    def content(self): return self._content

    @property
    def current_animation(self):
        value = self.animation_for_phase
        return value(self.phase) if callable(value) else value

    def advance(self) -> Any:
        self.phase_index = (self.phase_index + 1) % len(self.phases)
        self._content = self.content_builder(self.phase)
        self._children = [self._content]
        return self.phase

    def size_that_fits(self, proposal): return self._content.size_that_fits(proposal)
    def place(self, origin, size): self._content.place(origin, size)


@dataclass(frozen=True)
class Keyframe:
    value: Any
    duration: float = 0.25
    curve: str = "linear"


class KeyframeAnimator(View):
    """A keyframe timeline rendered at an explicit normalized progress value."""

    def __init__(self, initial_value: Any, keyframes: Iterable[Keyframe],
                 content: Callable[[Any], View], progress: float = 0.0,
                 trigger: Any = None):
        self.initial_value = initial_value
        self.keyframes = tuple(keyframes)
        if not self.keyframes:
            raise ValueError("KeyframeAnimator requires at least one keyframe")
        self.content_builder = content
        self.trigger = trigger
        self.progress = max(0.0, min(1.0, float(progress)))
        self._content = content(self.value_at(self.progress))
        self._children = [self._content]

    @property
    def content(self): return self._content

    def value_at(self, progress: float):
        total = sum(max(0.0, frame.duration) for frame in self.keyframes)
        if total <= 0:
            return self.keyframes[-1].value
        cursor = max(0.0, min(1.0, progress)) * total
        start = self.initial_value
        for frame in self.keyframes:
            duration = max(0.0, frame.duration)
            if cursor <= duration or frame is self.keyframes[-1]:
                local = 1.0 if duration == 0 else cursor / duration
                return interpolate(start, frame.value, Animation(duration, frame.curve).ease(local))
            cursor -= duration
            start = frame.value
        return self.keyframes[-1].value

    def seek(self, progress: float):
        self.progress = max(0.0, min(1.0, float(progress)))
        self._content = self.content_builder(self.value_at(self.progress))
        self._children = [self._content]
        return self

    def size_that_fits(self, proposal): return self._content.size_that_fits(proposal)
    def place(self, origin, size): self._content.place(origin, size)
