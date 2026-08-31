"""Menus, toolbar items and keyboard command descriptions."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Optional, Sequence

from .geometry import Point, Size
from .view import View, ViewModifier, _ModifiedContent, _apply


@dataclass(frozen=True)
class KeyboardShortcut:
    key: str
    modifiers: tuple[str, ...] = ("command",)

    def __post_init__(self) -> None:
        if len(self.key) != 1:
            raise ValueError("keyboard shortcut key must be one character")
        valid = {"command", "option", "control", "shift"}
        if not set(self.modifiers) <= valid:
            raise ValueError("unsupported keyboard shortcut modifier")

    @classmethod
    def default_action(cls) -> "KeyboardShortcut":
        return cls("\r", ())

    @classmethod
    def cancel_action(cls) -> "KeyboardShortcut":
        return cls("\x1b", ())


@dataclass(frozen=True)
class MenuItem:
    title: str
    action: Callable[[], None]
    role: str = "default"
    shortcut: Optional[KeyboardShortcut] = None
    _disabled: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if self.role not in ("default", "destructive"):
            raise ValueError("MenuItem role must be default or destructive")
        if not callable(self.action):
            raise TypeError("MenuItem action must be callable")

    @property
    def is_enabled(self) -> bool:
        return not self._disabled

    def disabled(self, value: bool = True) -> "MenuItem":
        """Return a copy with SwiftUI-style disabled state applied."""
        return replace(self, _disabled=bool(value))


@dataclass(frozen=True)
class MenuDivider:
    """A non-interactive separator inside menu content."""


def normalize_menu_items(items: Sequence[View]) -> tuple[MenuItem | MenuDivider, ...]:
    """Convert SwiftUI-style Button/Divider content to backend descriptions."""
    from .components import Button, Divider

    normalized = []
    for source in items:
        if isinstance(source, Divider):
            normalized.append(MenuDivider())
            continue
        node = source
        shortcut = None
        disabled = False
        while isinstance(node, _ModifiedContent):
            modifier = node._modifier
            if modifier.__class__.__name__ == "KeyboardShortcutModifier":
                shortcut = modifier.shortcut
            if getattr(modifier, "key", None) == "disabled" and modifier.value:
                disabled = True
            node = node._content
        if not isinstance(node, Button):
            raise TypeError("menu content must contain Button or Divider views")
        item = MenuItem(node.title, node.action, node.role or "default", shortcut)
        normalized.append(item.disabled(disabled))
    return tuple(normalized)


class Menu(View):
    """A button that presents a collection of actions."""

    def __init__(self, title: str, items: Sequence[View]):
        self.title = str(title)
        self.items = list(normalize_menu_items(items))
        self._selected_index = next(
            (index for index, item in enumerate(self.items) if isinstance(item, MenuItem)), 0
        )
        self._children = []

    @property
    def selected_item(self) -> Optional[MenuItem]:
        if not self.items:
            return None
        item = self.items[self._selected_index]
        return item if isinstance(item, MenuItem) else None

    def move_selection(self, delta: int) -> None:
        if not any(isinstance(item, MenuItem) for item in self.items):
            return
        if int(delta) == 0:
            return
        direction = 1 if int(delta) > 0 else -1
        index = self._selected_index
        for _ in self.items:
            index = (index + direction) % len(self.items)
            if isinstance(self.items[index], MenuItem):
                self._selected_index = index
                return

    def activate_selected(self) -> None:
        item = self.selected_item
        from .styles import is_enabled
        if is_enabled(self) and item is not None and item.is_enabled:
            item.action()

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(max(72.0, len(self.title) * 8.0 + 30.0), 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self):
        return self._children


@dataclass(frozen=True)
class CommandMenu:
    """A top-level application command menu."""

    title: str
    items: Sequence[View]
    id: str = ""

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("CommandMenu title cannot be empty")
        object.__setattr__(self, "items", normalize_menu_items(self.items))
        if not self.id:
            object.__setattr__(self, "id", self.title.casefold().replace(" ", "-"))


class Commands:
    """A validated collection of top-level application command menus."""

    def __init__(self, menus: Sequence[CommandMenu] = ()):
        self.menus = tuple(menus)
        if not all(isinstance(menu, CommandMenu) for menu in self.menus):
            raise TypeError("Commands entries must be CommandMenu instances")
        ids = [menu.id for menu in self.menus]
        if len(ids) != len(set(ids)):
            raise ValueError("CommandMenu ids must be unique")

    def __iter__(self):
        return iter(self.menus)


@dataclass(frozen=True, init=False)
class ToolbarItem:
    id: str
    content: View
    placement: str
    label: str
    action: Callable[[], None]
    shortcut: Optional[KeyboardShortcut] = None
    _disabled: bool = field(default=False, repr=False)
    system_name: str = field(default="", repr=False)

    def __init__(self, id: str, content: View, placement: str = "automatic",
                 system_name: str = "") -> None:
        normalized = normalize_menu_items((content,))
        if not normalized or isinstance(normalized[0], MenuDivider):
            raise TypeError("ToolbarItem content must be a Button view")
        valid = {"automatic", "navigation", "primaryAction", "confirmationAction",
                 "cancellationAction"}
        if placement not in valid:
            raise ValueError(f"unsupported toolbar placement: {placement}")
        if not isinstance(system_name, str):
            raise TypeError("ToolbarItem system_name must be a string")
        item = normalized[0]
        object.__setattr__(self, "id", str(id))
        object.__setattr__(self, "content", content)
        object.__setattr__(self, "placement", placement)
        object.__setattr__(self, "label", item.title)
        object.__setattr__(self, "action", item.action)
        object.__setattr__(self, "shortcut", item.shortcut)
        object.__setattr__(self, "_disabled", not item.is_enabled)
        object.__setattr__(self, "system_name", system_name)

    @property
    def is_enabled(self) -> bool:
        return not self._disabled

class ToolbarModifier(ViewModifier):
    def __init__(self, items: Sequence[ToolbarItem]):
        self.items = tuple(items)
        if not all(isinstance(item, ToolbarItem) for item in self.items):
            raise TypeError("toolbar items must be ToolbarItem instances")
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("toolbar item ids must be unique")

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


def toolbar(view: View, items: Sequence[ToolbarItem]) -> View:
    return _apply(view, ToolbarModifier(items))


__all__ = [
    "CommandMenu", "Commands", "KeyboardShortcut", "Menu", "MenuDivider",
    "MenuItem", "ToolbarItem", "ToolbarModifier", "normalize_menu_items", "toolbar",
]
