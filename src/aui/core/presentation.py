"""Declarative modal presentation modifiers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from .geometry import Size
from .components import Button
from .state import Binding
from .view import View, ViewModifier, _apply


class PresentationModifier(ViewModifier):
    """Layout-transparent base class for presentation modifiers."""

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin, size) -> None:
        content.place(origin, size)


@dataclass(frozen=True)
class PresentationDetent:
    kind: str
    value: Optional[float] = None

    def __post_init__(self):
        if self.kind not in ("medium", "large", "height", "fraction"):
            raise ValueError("unsupported presentation detent")
        if self.kind in ("height", "fraction") and self.value is None:
            raise ValueError(f"{self.kind} presentation detent requires a value")

    @classmethod
    def medium(cls): return cls("medium")

    @classmethod
    def large(cls): return cls("large")

    @classmethod
    def height(cls, value: float):
        if float(value) <= 0: raise ValueError("presentation detent height must be positive")
        return cls("height", float(value))

    @classmethod
    def fraction(cls, value: float):
        if not 0 < float(value) <= 1: raise ValueError("presentation detent fraction must be in (0, 1]")
        return cls("fraction", float(value))

    def resolve(self, maximum: float) -> float:
        if self.kind == "medium": return maximum * 0.5
        if self.kind == "large": return maximum
        if self.kind == "fraction": return maximum * self.value
        return min(maximum, self.value)


@dataclass(frozen=True)
class PresentationConfiguration:
    detents: tuple[PresentationDetent, ...] = ()
    selection: Optional[Binding] = None
    drag_indicator: str = "automatic"
    interactive_dismiss_disabled: bool = False
    background_interaction: str = "automatic"
    corner_radius: Optional[float] = None


class PresentationConfigurationModifier(PresentationModifier):
    def __init__(self, kind: str, value):
        self.kind = kind
        self.value = value


class SheetModifier(PresentationModifier):
    def __init__(self, is_presented: Binding[bool], content: Callable[..., View],
                 title: str = "", size: Size = Size(520.0, 360.0)):
        if not isinstance(is_presented, Binding):
            raise TypeError("sheet is_presented must be a Binding[bool]")
        if not callable(content):
            raise TypeError("sheet content must be callable")
        self.is_presented = is_presented
        self.content = content
        self.title = title
        self.size = size
        self.configuration = PresentationConfiguration()
        self.full_screen = False


class FullScreenCoverModifier(SheetModifier):
    def __init__(self, is_presented: Binding[bool], content: Callable[..., View],
                 title: str = ""):
        super().__init__(is_presented, content, title, Size())
        self.full_screen = True


class AlertModifier(PresentationModifier):
    def __init__(self, title: str, is_presented: Binding[bool], message: str = "",
                 buttons: Sequence[Button] = (Button("OK", lambda: None),)):
        if not isinstance(is_presented, Binding):
            raise TypeError("alert is_presented must be a Binding[bool]")
        self.title = str(title)
        self.is_presented = is_presented
        self.message = str(message)
        self.buttons = tuple(buttons) or (Button("OK", lambda: None),)
        if not all(isinstance(button, Button) for button in self.buttons):
            raise TypeError("alert buttons must be Button instances")


class ConfirmationDialogModifier(AlertModifier):
    """A choice-oriented confirmation dialog with optional destructive actions."""


class PopoverModifier(PresentationModifier):
    def __init__(self, is_presented: Binding[bool], content: Callable[..., View],
                 size: Size = Size(320.0, 240.0), edge: str = "bottom"):
        if not isinstance(is_presented, Binding):
            raise TypeError("popover is_presented must be a Binding[bool]")
        if not callable(content):
            raise TypeError("popover content must be callable")
        if edge not in ("top", "bottom", "leading", "trailing"):
            raise ValueError("popover edge must be top, bottom, leading, or trailing")
        self.is_presented = is_presented
        self.content = content
        self.size = size
        self.edge = edge


class SnackBarModifier(PresentationModifier):
    """A non-modal, time-limited status message inspired by Flet SnackBar."""

    def __init__(self, message: str, is_presented: Binding[bool], *,
                 action: Optional[Button] = None, duration: float = 4.0):
        if not isinstance(is_presented, Binding):
            raise TypeError("snack_bar is_presented must be a Binding[bool]")
        if action is not None and not isinstance(action, Button):
            raise TypeError("snack_bar action must be a Button")
        if float(duration) <= 0:
            raise ValueError("snack_bar duration must be positive")
        self.message, self.is_presented = str(message), is_presented
        self.action, self.duration = action, float(duration)


def sheet(view: View, is_presented: Binding[bool], content: Callable[..., View],
          title: str = "", size: Size = Size(520.0, 360.0)) -> View:
    return _apply(view, SheetModifier(is_presented, content, title, size))


def full_screen_cover(view: View, is_presented: Binding[bool],
                      content: Callable[..., View], title: str = "") -> View:
    return _apply(view, FullScreenCoverModifier(is_presented, content, title))


def presentation_detents(view: View, detents, selection: Optional[Binding] = None) -> View:
    values = tuple(detents)
    if not values or not all(isinstance(item, PresentationDetent) for item in values):
        raise TypeError("presentation detents must contain PresentationDetent values")
    if selection is not None and not isinstance(selection, Binding):
        raise TypeError("presentation detent selection must be a Binding")
    return _apply(view, PresentationConfigurationModifier("detents", (values, selection)))


def presentation_drag_indicator(view: View, visibility: str) -> View:
    if visibility not in ("automatic", "visible", "hidden"):
        raise ValueError("presentation drag indicator must be automatic, visible, or hidden")
    return _apply(view, PresentationConfigurationModifier("drag_indicator", visibility))


def interactive_dismiss_disabled(view: View, disabled: bool = True) -> View:
    return _apply(view, PresentationConfigurationModifier(
        "interactive_dismiss_disabled", bool(disabled)
    ))


def presentation_background_interaction(view: View, behavior: str) -> View:
    if behavior not in ("automatic", "enabled", "disabled"):
        raise ValueError("presentation background interaction must be automatic, enabled, or disabled")
    return _apply(view, PresentationConfigurationModifier("background_interaction", behavior))


def presentation_corner_radius(view: View, radius: float) -> View:
    if float(radius) < 0: raise ValueError("presentation corner radius cannot be negative")
    return _apply(view, PresentationConfigurationModifier("corner_radius", float(radius)))


def collect_presentation_configurations(view: View) -> View:
    """Attach outer presentation configuration modifiers to their nearest sheet."""
    def visit(node: View, values: dict) -> None:
        if hasattr(node, "_modifier") and hasattr(node, "_content"):
            modifier = node._modifier
            current = dict(values)
            if isinstance(modifier, PresentationConfigurationModifier):
                if modifier.kind == "detents":
                    current["detents"], current["selection"] = modifier.value
                else:
                    current[modifier.kind] = modifier.value
            elif isinstance(modifier, SheetModifier):
                modifier.configuration = PresentationConfiguration(**current)
                current = {}
            visit(node._content, current)
            return
        for child in node.children(): visit(child, values)
    visit(view, {})
    return view


def alert(view: View, title: str, is_presented: Binding[bool], message: str = "",
          buttons: Sequence[Button] = (Button("OK", lambda: None),)) -> View:
    return _apply(view, AlertModifier(title, is_presented, message, buttons))


def confirmation_dialog(view: View, title: str, is_presented: Binding[bool],
                        message: str = "", buttons: Sequence[Button] = ()) -> View:
    return _apply(
        view,
        ConfirmationDialogModifier(
            title, is_presented, message,
            buttons or (Button("Cancel", lambda: None, role="cancel"),),
        ),
    )


def popover(view: View, is_presented: Binding[bool], content: Callable[..., View],
            size: Size = Size(320.0, 240.0), edge: str = "bottom") -> View:
    return _apply(view, PopoverModifier(is_presented, content, size, edge))


def snack_bar(view: View, message: str, is_presented: Binding[bool], *,
              action: Optional[Button] = None, duration: float = 4.0) -> View:
    return _apply(view, SnackBarModifier(message, is_presented, action=action, duration=duration))


__all__ = [
    "AlertModifier", "ConfirmationDialogModifier",
    "FullScreenCoverModifier", "PopoverModifier", "PresentationConfiguration",
    "PresentationConfigurationModifier", "PresentationDetent", "PresentationModifier",
    "SheetModifier", "alert", "collect_presentation_configurations",
    "confirmation_dialog", "full_screen_cover", "interactive_dismiss_disabled", "popover",
    "presentation_background_interaction", "presentation_corner_radius",
    "presentation_detents", "presentation_drag_indicator", "sheet", "SnackBarModifier", "snack_bar",
]
