"""View-level keyboard shortcuts, key press handlers, and focus sections."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, Optional

from .commands import KeyboardShortcut
from .focus import FocusedModifier
from .geometry import Point, Size
from .state import Binding
from .view import View, ViewModifier, _apply


class KeyPressResult(str, Enum):
    HANDLED = "handled"
    IGNORED = "ignored"


@dataclass(frozen=True)
class KeyPress:
    key: str
    modifiers: frozenset[str] = frozenset()
    phase: str = "down"

    def __post_init__(self):
        if not self.key:
            raise ValueError("key press key cannot be empty")
        if self.phase not in ("down", "repeat", "up"):
            raise ValueError("key press phase must be down, repeat, or up")


class KeyboardShortcutModifier(ViewModifier):
    def __init__(self, shortcut: KeyboardShortcut):
        if not isinstance(shortcut, KeyboardShortcut):
            raise TypeError("keyboard shortcut modifier requires KeyboardShortcut")
        self.shortcut = shortcut

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class OnKeyPressModifier(ViewModifier):
    def __init__(self, keys: Optional[Iterable[str]], action: Callable[[KeyPress], object]):
        if not callable(action):
            raise TypeError("on_key_press action must be callable")
        self.keys = None if keys is None else frozenset(str(key) for key in keys)
        if self.keys is not None and any(not key for key in self.keys):
            raise ValueError("key press keys cannot be empty")
        self.action = action

    def dispatch(self, event: KeyPress) -> KeyPressResult:
        if self.keys is not None and event.key not in self.keys:
            return KeyPressResult.IGNORED
        result = self.action(event)
        if isinstance(result, KeyPressResult):
            return result
        return KeyPressResult.HANDLED if result is True else KeyPressResult.IGNORED

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class DefaultFocusModifier(FocusedModifier):
    def activate_if_needed(self) -> None:
        if self.binding.wrapped_value in (None, False):
            self.activate()


class FocusSectionModifier(ViewModifier):
    def __init__(self, section_id: object = None):
        self.section_id = section_id

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


def keyboard_shortcut(view: View, shortcut: KeyboardShortcut | str,
                      modifiers=("command",)) -> View:
    value = shortcut if isinstance(shortcut, KeyboardShortcut) else KeyboardShortcut(
        str(shortcut), tuple(modifiers)
    )
    return _apply(view, KeyboardShortcutModifier(value))


def on_key_press(view: View, keys=None, action=None) -> View:
    if action is None and callable(keys):
        action, keys = keys, None
    elif isinstance(keys, str):
        keys = (keys,)
    return _apply(view, OnKeyPressModifier(keys, action))


def default_focus(view: View, binding: Binding, equals=True) -> View:
    return _apply(view, DefaultFocusModifier(binding, equals))


def focus_section(view: View, section_id=None) -> View:
    return _apply(view, FocusSectionModifier(section_id))


__all__ = [
    "DefaultFocusModifier", "FocusSectionModifier", "KeyPress", "KeyPressResult",
    "KeyboardShortcutModifier", "OnKeyPressModifier", "default_focus", "focus_section",
    "keyboard_shortcut", "on_key_press",
]
