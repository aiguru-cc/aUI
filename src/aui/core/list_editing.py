"""List selection, edit mode, row restrictions, and swipe actions."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Sequence
from .geometry import Point, Size
from .view import View, ViewModifier, _ModifiedContent, _apply

class EditMode:
    INACTIVE = "inactive"
    TRANSIENT = "transient"
    ACTIVE = "active"

    @classmethod
    def validate(cls, value: str) -> str:
        if value not in (cls.INACTIVE, cls.TRANSIENT, cls.ACTIVE):
            raise ValueError("edit mode must be inactive, transient, or active")
        return value

@dataclass(frozen=True)
class ListRowAction:
    title: str
    action: Callable[[], None]
    role: str = "normal"
    def __post_init__(self):
        if not self.title:
            raise ValueError("list row action title cannot be empty")
        if not callable(self.action): raise TypeError("list row action must be callable")
        if self.role not in ("normal", "destructive"):
            raise ValueError("list row action role must be normal or destructive")

class ListRowEditingModifier(ViewModifier):
    def __init__(self, kind: str, value): self.kind, self.value = kind, value
    def size_that_fits(self, content: View, proposal: Size) -> Size: return content.size_that_fits(proposal)
    def place(self, content: View, origin: Point, size: Size) -> None: content.place(origin, size)

def swipe_actions(view: View, actions: Sequence[ListRowAction], edge="trailing",
                  allows_full_swipe=True) -> View:
    values = tuple(actions)
    if not values or not all(isinstance(item, ListRowAction) for item in values):
        raise TypeError("swipe actions must contain ListRowAction values")
    if edge not in ("leading", "trailing"): raise ValueError("swipe action edge must be leading or trailing")
    return _apply(view, ListRowEditingModifier("swipe_actions", (values, edge, bool(allows_full_swipe))))

def delete_disabled(view: View, disabled=True) -> View:
    return _apply(view, ListRowEditingModifier("delete_disabled", bool(disabled)))

def move_disabled(view: View, disabled=True) -> View:
    return _apply(view, ListRowEditingModifier("move_disabled", bool(disabled)))

def list_row_editing(view: View) -> dict:
    values = {}; node = view
    while isinstance(node, _ModifiedContent):
        modifier = node._modifier
        if isinstance(modifier, ListRowEditingModifier) and modifier.kind not in values:
            values[modifier.kind] = modifier.value
        node = node._content
    return values

__all__ = ["EditMode", "ListRowAction", "ListRowEditingModifier", "delete_disabled",
           "list_row_editing", "move_disabled", "swipe_actions"]
