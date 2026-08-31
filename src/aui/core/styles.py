"""SwiftUI-inspired control styles and environment-like style modifiers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .geometry import Color
from .view import View, ViewModifier, _ModifiedContent, _apply


class ButtonStyle:
    AUTOMATIC = "automatic"
    PLAIN = "plain"
    BORDERED = "bordered"
    BORDERED_PROMINENT = "borderedProminent"
    BORDERLESS = "borderless"
    LINK = "link"


class ToggleStyle:
    AUTOMATIC = "automatic"
    SWITCH = "switch"
    CHECKBOX = "checkbox"
    BUTTON = "button"


class PickerStyle:
    AUTOMATIC = "automatic"
    MENU = "menu"
    SEGMENTED = "segmented"
    RADIO_GROUP = "radioGroup"


class LabelStyle:
    AUTOMATIC = "automatic"
    TITLE_AND_ICON = "titleAndIcon"
    TITLE_ONLY = "titleOnly"
    ICON_ONLY = "iconOnly"


class ProgressViewStyle:
    AUTOMATIC = "automatic"
    LINEAR = "linear"
    CIRCULAR = "circular"


class TextFieldStyle:
    AUTOMATIC = "automatic"
    PLAIN = "plain"
    ROUNDED_BORDER = "roundedBorder"
    SQUARE_BORDER = "squareBorder"


class ControlGroupStyle:
    AUTOMATIC = "automatic"
    NAVIGATION = "navigation"
    COMPACT_MENU = "compactMenu"


class ControlSize:
    MINI = "mini"
    SMALL = "small"
    REGULAR = "regular"
    LARGE = "large"
    EXTRA_LARGE = "extraLarge"


_VALID = {
    "button_style": {ButtonStyle.AUTOMATIC, ButtonStyle.PLAIN, ButtonStyle.BORDERED,
                     ButtonStyle.BORDERED_PROMINENT, ButtonStyle.BORDERLESS, ButtonStyle.LINK},
    "toggle_style": {ToggleStyle.AUTOMATIC, ToggleStyle.SWITCH, ToggleStyle.CHECKBOX, ToggleStyle.BUTTON},
    "picker_style": {PickerStyle.AUTOMATIC, PickerStyle.MENU, PickerStyle.SEGMENTED, PickerStyle.RADIO_GROUP},
    "label_style": {LabelStyle.AUTOMATIC, LabelStyle.TITLE_AND_ICON, LabelStyle.TITLE_ONLY, LabelStyle.ICON_ONLY},
    "progress_view_style": {ProgressViewStyle.AUTOMATIC, ProgressViewStyle.LINEAR, ProgressViewStyle.CIRCULAR},
    "text_field_style": {TextFieldStyle.AUTOMATIC, TextFieldStyle.PLAIN,
                         TextFieldStyle.ROUNDED_BORDER, TextFieldStyle.SQUARE_BORDER},
    "control_size": {ControlSize.MINI, ControlSize.SMALL, ControlSize.REGULAR, ControlSize.LARGE, ControlSize.EXTRA_LARGE},
    "control_group_style": {ControlGroupStyle.AUTOMATIC, ControlGroupStyle.NAVIGATION,
                            ControlGroupStyle.COMPACT_MENU},
}


@dataclass(frozen=True)
class StyleModifier(ViewModifier):
    key: str
    value: Any

    def size_that_fits(self, content: View, proposal):
        return content.size_that_fits(proposal)

    def place(self, content: View, origin, size) -> None:
        content.place(origin, size)


def _style(view: View, key: str, value: Any) -> View:
    if key in _VALID and value not in _VALID[key]:
        raise ValueError(f"unsupported {key.replace('_', ' ')}: {value!r}")
    return _apply(view, StyleModifier(key, value))


def button_style(view: View, style: str) -> View:
    return _style(view, "button_style", style)


def toggle_style(view: View, style: str) -> View:
    return _style(view, "toggle_style", style)


def picker_style(view: View, style: str) -> View:
    return _style(view, "picker_style", style)


def label_style(view: View, style: str) -> View:
    return _style(view, "label_style", style)


def progress_view_style(view: View, style: str) -> View:
    return _style(view, "progress_view_style", style)


def text_field_style(view: View, style: str) -> View:
    return _style(view, "text_field_style", style)


def control_group_style(view: View, style: str) -> View:
    return _style(view, "control_group_style", style)


def tint(view: View, color: Color) -> View:
    if not isinstance(color, Color):
        raise TypeError("tint expects a Color")
    return _style(view, "tint", color)


def control_size(view: View, size: str) -> View:
    return _style(view, "control_size", size)


def disabled(view: View, value: bool = True) -> View:
    return _style(view, "disabled", bool(value))


def labels_hidden(view: View, hidden: bool = True) -> View:
    return _style(view, "labels_hidden", bool(hidden))


def style_value(view: View, key: str, default=None):
    return getattr(view, "_resolved_style", {}).get(key, default)


def is_enabled(view: View) -> bool:
    return bool(getattr(view, "enabled", True)) and not bool(style_value(view, "disabled", False))


def resolve_style_tree(root: View) -> View:
    """Resolve inherited styles onto leaf descriptions before rendering."""
    seen: set[int] = set()

    def walk(view: View, inherited: Dict[str, Any], locked=frozenset()) -> None:
        if id(view) in seen:
            return
        seen.add(id(view))
        context = dict(inherited)
        if isinstance(view, _ModifiedContent) and isinstance(view._modifier, StyleModifier):
            # The outermost (last-applied) modifier wins across a wrapper chain.
            if view._modifier.key not in locked:
                context[view._modifier.key] = view._modifier.value
            locked = locked | {view._modifier.key}
        view._resolved_style = dict(context)
        for child in view.children():
            # Locks only describe ordering inside one modifier wrapper chain;
            # an explicitly styled descendant overrides its container style.
            child_locks = locked if isinstance(view, _ModifiedContent) else frozenset()
            walk(child, context, child_locks)

    walk(root, {})
    return root
