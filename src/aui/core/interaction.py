"""Context menus, hover behavior, hit testing, and sensory feedback."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .commands import Menu
from .view import View, ViewModifier, _apply


class HoverEffect:
    AUTOMATIC = "automatic"
    HIGHLIGHT = "highlight"
    LIFT = "lift"


@dataclass(frozen=True)
class SensoryFeedback:
    kind: str
    weight: str = "medium"
    intensity: float = 1.0

    def __post_init__(self):
        valid = {"success", "warning", "error", "selection", "impact",
                 "increase", "decrease", "start", "stop", "alignment", "levelChange"}
        if self.kind not in valid: raise ValueError(f"unsupported sensory feedback: {self.kind!r}")
        if self.weight not in {"light", "medium", "heavy", "soft", "rigid"}: raise ValueError("invalid feedback weight")
        object.__setattr__(self, "intensity", max(0.0, min(1.0, float(self.intensity))))

    @classmethod
    def success(cls): return cls("success")
    @classmethod
    def warning(cls): return cls("warning")
    @classmethod
    def error(cls): return cls("error")
    @classmethod
    def selection(cls): return cls("selection")
    @classmethod
    def impact(cls, weight="medium", intensity=1.0): return cls("impact", weight, intensity)


@dataclass(frozen=True)
class ContextMenuModifier(ViewModifier):
    menu: Menu | Callable[[], Menu]
    def resolve(self):
        value = self.menu() if callable(self.menu) else self.menu
        if not isinstance(value, Menu): raise TypeError("context_menu content must be a Menu")
        return value
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class OnHoverModifier(ViewModifier):
    action: Callable[[bool], None]
    def __post_init__(self):
        if not callable(self.action): raise TypeError("on_hover action must be callable")
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class HoverEffectModifier(ViewModifier):
    effect: str
    def __post_init__(self):
        if self.effect not in {HoverEffect.AUTOMATIC, HoverEffect.HIGHLIGHT, HoverEffect.LIFT}:
            raise ValueError(f"unsupported hover effect: {self.effect!r}")
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class HitTestingModifier(ViewModifier):
    enabled: bool
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class ContentShapeModifier(ViewModifier):
    shape: View
    kind: str = "interaction"
    def __post_init__(self):
        if not isinstance(self.shape, View): raise TypeError("content_shape expects a View")
        if self.kind not in {"interaction", "hoverEffect", "dragPreview", "contextMenuPreview"}:
            raise ValueError(f"unsupported content shape kind: {self.kind!r}")
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class SensoryFeedbackModifier(ViewModifier):
    feedback: SensoryFeedback
    trigger: Any
    condition: Optional[Callable[[Any, Any], bool]] = None
    key: str = ""
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def context_menu(view, menu): return _apply(view, ContextMenuModifier(menu))
def on_hover(view, action): return _apply(view, OnHoverModifier(action))
def hover_effect(view, effect=HoverEffect.AUTOMATIC): return _apply(view, HoverEffectModifier(effect))
def allows_hit_testing(view, enabled=True): return _apply(view, HitTestingModifier(bool(enabled)))
def content_shape(view, shape, kind="interaction"): return _apply(view, ContentShapeModifier(shape, kind))
def sensory_feedback(view, feedback, trigger, condition=None, key=""):
    if not isinstance(feedback, SensoryFeedback): raise TypeError("sensory_feedback expects SensoryFeedback")
    if condition is not None and not callable(condition): raise TypeError("feedback condition must be callable")
    return _apply(view, SensoryFeedbackModifier(feedback, trigger, condition, str(key)))
