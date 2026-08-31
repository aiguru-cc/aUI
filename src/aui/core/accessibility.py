"""Accessibility support for aUI.

Mirrors SwiftUI's accessibility model:

* ``accessibilityLabel``  — a short, human-readable name for the element.
* ``accessibilityHint``  — a description of the result of performing an action.
* ``accessibilityValue`` — the current value of the element (e.g. a slider's
  position, a toggle's state).
* ``accessibilityHidden`` — exclude an element (and its children) from the
  accessibility tree.
* ``accessibilityElement(children=...)`` — control whether children are
  combined into a single element or kept separate (``.contain`` / ``.combine`` /
  ``.ignore``).

These are declarative value objects attached via modifiers; the render backend
exposes them to the platform's assistive technology (e.g. Tk ``-accessible``
attributes) or generates a textual description (ASCII/curses).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .view import View, ViewModifier, _apply


#: Accessibility element children strategies (mirrors SwiftUI).
CHILDREN_CONTAIN = "contain"   # children remain separate elements
CHILDREN_COMBINE = "combine"   # children are combined into this element
CHILDREN_IGNORE = "ignore"     # children are excluded from the tree


class AccessibilityModifier(ViewModifier):
    """Base class for accessibility modifiers (layout-transparent)."""

    def size_that_fits(self, content: View, proposal) -> Any:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin, size) -> None:
        content.place(origin, size)


class LabelModifier(AccessibilityModifier):
    def __init__(self, label: str):
        self.label = label


class HintModifier(AccessibilityModifier):
    def __init__(self, hint: str):
        self.hint = hint


class ValueModifier(AccessibilityModifier):
    def __init__(self, value: str):
        self.value = value


class HiddenModifier(AccessibilityModifier):
    def __init__(self, hidden: bool = True):
        self.hidden = hidden


class ElementModifier(AccessibilityModifier):
    def __init__(self, children: str = CHILDREN_CONTAIN):
        self.children = children


class TraitsModifier(AccessibilityModifier):
    def __init__(self, traits, remove: bool = False):
        self.traits = frozenset((traits,) if isinstance(traits, str) else traits)
        self.remove = remove


class SortPriorityModifier(AccessibilityModifier):
    def __init__(self, priority: float): self.priority = float(priority)


class IdentifierModifier(AccessibilityModifier):
    def __init__(self, identifier: str): self.identifier = str(identifier)


class HeadingModifier(AccessibilityModifier):
    def __init__(self, level: int):
        if not 1 <= int(level) <= 6: raise ValueError("heading level must be 1...6")
        self.level = int(level)


class InputLabelsModifier(AccessibilityModifier):
    def __init__(self, labels): self.labels = tuple(map(str, labels))


class CustomContentModifier(AccessibilityModifier):
    def __init__(self, key: str, value: str, importance: str = "default"):
        if importance not in {"default", "high"}: raise ValueError("importance must be default or high")
        self.key, self.value, self.importance = str(key), str(value), importance


class ActionModifier(AccessibilityModifier):
    def __init__(self, name: str, action: Callable[[], None]):
        if not callable(action): raise TypeError("accessibility action must be callable")
        self.name, self.action = str(name), action


class AdjustableActionModifier(AccessibilityModifier):
    def __init__(self, action: Callable[[str], None]):
        if not callable(action): raise TypeError("adjustable action must be callable")
        self.action = action


# Public modifier API ---------------------------------------------------------

def accessibility_label(view: View, label: str) -> View:
    """Provide a human-readable label for assistive technology.

    Usage::

        from aui import accessibility_label, Button

        view = accessibility_label(Button("X", action=close), "Close window")
    """
    return _apply(view, LabelModifier(label))


def accessibility_hint(view: View, hint: str) -> View:
    """Describe the result of performing an action on the view.

    Usage::

        from aui import accessibility_hint, Button

        view = accessibility_hint(Button("Save", action=save), "Saves your changes")
    """
    return _apply(view, HintModifier(hint))


def accessibility_value(view: View, value: str) -> View:
    """Provide the current value of the view.

    Usage::

        from aui import accessibility_value, Slider

        view = accessibility_value(slider, f"{volume:.0%}")
    """
    return _apply(view, ValueModifier(value))


def accessibility_hidden(view: View, hidden: bool = True) -> View:
    """Exclude the view (and its children) from the accessibility tree.

    Usage::

        from aui import accessibility_hidden, Text

        view = accessibility_hidden(Text("decorative"), True)
    """
    return _apply(view, HiddenModifier(hidden))


def accessibility_element(
    view: View,
    children: str = CHILDREN_CONTAIN,
) -> View:
    """Control how children are exposed to assistive technology.

    ``children`` is one of ``contain`` (default), ``combine`` or ``ignore``.
    """
    return _apply(view, ElementModifier(children))


def accessibility_add_traits(view: View, traits) -> View: return _apply(view, TraitsModifier(traits))
def accessibility_remove_traits(view: View, traits) -> View: return _apply(view, TraitsModifier(traits, True))
def accessibility_sort_priority(view: View, priority: float) -> View: return _apply(view, SortPriorityModifier(priority))
def accessibility_identifier(view: View, identifier: str) -> View: return _apply(view, IdentifierModifier(identifier))
def accessibility_heading(view: View, level: int = 1) -> View: return _apply(view, HeadingModifier(level))
def accessibility_input_labels(view: View, labels) -> View: return _apply(view, InputLabelsModifier(labels))
def accessibility_custom_content(view: View, key: str, value: str, importance: str = "default") -> View:
    return _apply(view, CustomContentModifier(key, value, importance))
def accessibility_action(view: View, name: str, action: Callable[[], None]) -> View:
    return _apply(view, ActionModifier(name, action))
def accessibility_adjustable_action(view: View, action: Callable[[str], None]) -> View:
    return _apply(view, AdjustableActionModifier(action))


# Accessibility tree ----------------------------------------------------------

class AccessibilityInfo:
    """The accessibility metadata of a single view-tree node.

    ``role`` is the semantic role (button / text / textfield / toggle /
    slider / picker / image / group / list / ...). ``label``, ``hint`` and
    ``value`` come from the matching modifiers or the component's own state.
    ``children`` is the list of child ``AccessibilityInfo`` nodes.
    """

    def __init__(
        self,
        role: str = "unknown",
        label: str = "",
        hint: str = "",
        value: str = "",
        hidden: bool = False,
        children: Optional[List["AccessibilityInfo"]] = None,
        traits=None,
        sort_priority: float = 0.0,
        identifier: str = "",
        heading_level: Optional[int] = None,
        input_labels=(),
        custom_content=None,
        actions=None,
        adjustable_action=None,
    ):
        self.role = role
        self.label = label
        self.hint = hint
        self.value = value
        self.hidden = hidden
        self.children = sorted(list(children or []),
                               key=lambda child: child.sort_priority,
                               reverse=True)
        self.traits = set(traits or ())
        self.sort_priority = float(sort_priority)
        self.identifier = identifier
        self.heading_level = heading_level
        self.input_labels = tuple(input_labels)
        self.custom_content = dict(custom_content or {})
        self.actions = dict(actions or {})
        self.adjustable_action = adjustable_action

    def perform_action(self, name: str) -> None:
        if name not in self.actions: raise KeyError(name)
        self.actions[name]()

    def adjust(self, direction: str) -> None:
        if direction not in {"increment", "decrement"}: raise ValueError("direction must be increment or decrement")
        if self.adjustable_action is None: raise LookupError("no adjustable action")
        self.adjustable_action(direction)

    def is_leaf(self) -> bool:
        return not self.children

    def summary(self) -> str:
        """A compact human-readable description of this node and its subtree.

        Format: ``"role: label (hint) [value]"`` with children indented.
        """
        parts = []
        if self.role:
            parts.append(self.role)
        if self.label:
            parts.append(self.label)
        if self.value:
            parts.append(f"[{self.value}]")
        if self.hint:
            parts.append(f"({self.hint})")
        head = " ".join(parts) or self.role
        lines = [head]
        for child in self.children:
            for line in child.summary().split("\n"):
                lines.append("  " + line)
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"AccessibilityInfo(role={self.role!r}, label={self.label!r}, "
            f"value={self.value!r}, hidden={self.hidden}, "
            f"children={len(self.children)})"
        )


#: Semantic roles for built-in components.
_ROLES = {
    "Button": "button",
    "Text": "text",
    "TextField": "textfield",
    "SecureField": "textfield",
    "Toggle": "toggle",
    "Slider": "slider",
    "Picker": "picker",
    "Image": "image",
    "AsyncImage": "image",
    "Divider": "divider",
    "List": "list",
    "Stepper": "stepper",
    "ProgressView": "progress",
    "DatePicker": "datepicker",
    "ColorPicker": "colorpicker",
    "NavigationStack": "navigation",
    "NavigationLink": "link",
    "NavigationSplitView": "splitview",
    "Form": "group",
    "Group": "group",
    "Section": "group",
    "DisclosureGroup": "group",
    "ScrollView": "scrollview",
    "TabView": "tabview",
    "Label": "label",
    "SearchField": "searchfield",
    "TextEditor": "texteditor",
    "Link": "link",
    "Gauge": "progress",
    "Rectangle": "image",
    "RoundedRectangle": "image",
    "Circle": "image",
    "LabeledContent": "group",
    "ContentUnavailableView": "group",
    "Grid": "grid",
    "GridRow": "row",
    "Menu": "menu",
    "Table": "table",
    "LinearGradient": "image",
    "RadialGradient": "image",
    "AngularGradient": "image",
    "EllipticalGradient": "image",
    "ForEach": "group",
    "GroupBox": "group",
    "ViewThatFits": "group",
    "LazyVGrid": "grid",
    "LazyHGrid": "grid",
    "ScrollViewReader": "scrollview",
    "Spacer": "spacer",
}


def _role_for(view, default: str = "unknown") -> str:
    """Resolve semantic roles through the class hierarchy for custom controls."""
    for cls in type(view).__mro__:
        role = _ROLES.get(cls.__name__)
        if role is not None:
            return role
    return default


def _component_value(view) -> str:
    """Best-effort current value of a component for assistive technology."""
    from .components import (
        ColorPicker,
        DatePicker,
        ProgressView,
        SecureField,
        Slider,
        Stepper,
        TextField,
        Toggle,
    )

    if isinstance(view, TextField):
        return str(view.text.wrapped_value)
    if isinstance(view, SecureField):
        return "•" * len(str(view.text.wrapped_value or ""))
    if isinstance(view, Toggle):
        return "on" if (view.is_on and view.is_on.wrapped_value) else "off"
    if isinstance(view, Slider):
        if view.value is not None:
            return f"{view.value.wrapped_value:.2f}"
        return ""
    if isinstance(view, Stepper):
        if view.value is not None:
            return str(view.value.wrapped_value)
        return ""
    if isinstance(view, ProgressView):
        if view.value is not None:
            return f"{view.value:.0%}"
        return "indeterminate"
    if isinstance(view, DatePicker):
        return view._current()
    if isinstance(view, ColorPicker):
        if view.selection is not None:
            return view.selection.wrapped_value.to_tk()
        return ""
    return ""


def _component_label(view) -> str:
    """Best-effort default label of a component."""
    from .components import (
        Button,
        ColorPicker,
        DatePicker,
        Image,
        Label,
        Link,
        Picker,
        ProgressView,
        SecureField,
        Stepper,
        Text,
        TextField,
        Toggle,
    )
    from .commands import Menu
    from .table import Table
    from .visual_effects import Gradient
    if isinstance(view, Text):
        return view.content
    if isinstance(view, Button):
        return view.title
    if isinstance(view, TextField):
        return view.placeholder or "text field"
    if isinstance(view, SecureField):
        return view.placeholder or "secure field"
    if isinstance(view, Toggle):
        return view.title or "toggle"
    if isinstance(view, Picker):
        return view.title
    if isinstance(view, Stepper):
        return view.title or "stepper"
    if isinstance(view, ProgressView):
        return view.label or "progress"
    if isinstance(view, DatePicker):
        return view.title or "date"
    if isinstance(view, ColorPicker):
        return view.title or "color"
    if isinstance(view, Label):
        return view.title
    if isinstance(view, Link):
        return view.title
    if isinstance(view, Image):
        if view.label:
            return view.label
        if view.system_name:
            return view.system_name
        if view.path is not None:
            from pathlib import Path
            return Path(view.path).name
    if isinstance(view, Menu):
        return view.title
    if isinstance(view, Table):
        return "table"
    return ""


def _apply_metadata(info: AccessibilityInfo, view: View) -> AccessibilityInfo:
    """Fold the accessibility modifiers attached to ``view`` into ``info``."""
    for mod in view.modifiers:
        from .modifiers import HiddenModifier as _LayoutHidden  # not used here
        if isinstance(mod, LabelModifier):
            info.label = mod.label
        elif isinstance(mod, HintModifier):
            info.hint = mod.hint
        elif isinstance(mod, ValueModifier):
            info.value = mod.value
        elif isinstance(mod, HiddenModifier):
            info.hidden = mod.hidden
        else:
            _apply_extended_metadata(info, mod)
    return info


def _apply_extended_metadata(info: AccessibilityInfo, mod) -> None:
    if isinstance(mod, TraitsModifier):
        info.traits.difference_update(mod.traits) if mod.remove else info.traits.update(mod.traits)
    elif isinstance(mod, SortPriorityModifier): info.sort_priority = mod.priority
    elif isinstance(mod, IdentifierModifier): info.identifier = mod.identifier
    elif isinstance(mod, HeadingModifier): info.heading_level = mod.level; info.traits.add("header")
    elif isinstance(mod, InputLabelsModifier): info.input_labels = mod.labels
    elif isinstance(mod, CustomContentModifier): info.custom_content[mod.key] = (mod.value, mod.importance)
    elif isinstance(mod, ActionModifier): info.actions[mod.name] = mod.action
    elif isinstance(mod, AdjustableActionModifier): info.adjustable_action = mod.action


def describe_accessibility(view: View) -> AccessibilityInfo:
    """Build the accessibility tree for ``view`` (mirrors SwiftUI's tree).

    Recursively walks the view tree, assigning each node a semantic role,
    label, hint and value, and folding in any accessibility modifiers. The
    result is a pure data structure that any backend can consume.
    """
    from .view import _Frame, _ModifiedContent

    # Unwrap modifier wrappers, folding accessibility metadata as we go.
    if isinstance(view, _ModifiedContent):
        inner = describe_accessibility(view.body())
        # The modifier may itself carry accessibility info; apply it to the
        # wrapped node's info.
        mod = view._modifier
        from .badges import BadgeModifier
        if isinstance(mod, BadgeModifier):
            inner.value = f"{inner.value}, badge {mod.value}" if inner.value else f"badge {mod.value}"
        elif isinstance(mod, LabelModifier):
            inner.label = mod.label
        elif isinstance(mod, HintModifier):
            inner.hint = mod.hint
        elif isinstance(mod, ValueModifier):
            inner.value = mod.value
        elif isinstance(mod, HiddenModifier):
            inner.hidden = mod.hidden
        elif isinstance(mod, ElementModifier):
            if mod.children == CHILDREN_COMBINE:
                combined = _combine_children(inner)
                return combined
            if mod.children == CHILDREN_IGNORE:
                inner.children = []
                return inner
        else:
            _apply_extended_metadata(inner, mod)
        return inner
    if isinstance(view, _Frame):
        return describe_accessibility(view._content)

    # Leaf components.
    from .components import (
        Button,
        ColorPicker,
        DatePicker,
        DisclosureGroup,
        Divider,
        Form,
        Group,
        Image,
        Label,
        LabeledContent,
        Link,
        List,
        NavigationStack,
        Picker,
        ProgressView,
        ScrollView,
        Section,
        SecureField,
        Slider,
        Stepper,
        TabView,
        Text,
        TextField,
        Toggle,
        Shape,
        ContentUnavailableView,
    )
    from .layout import Grid, GridRow, HStack, NavigationSplitView, Spacer, VStack, ZStack
    from .commands import Menu
    from .table import Table
    from .visual_effects import Gradient
    from .structural import AnyView, EmptyView, ForEach, GroupBox, ViewThatFits
    from .lazy import LazyHGrid, LazyVGrid
    from .scrolling import ScrollViewReader
    from .async_image import AsyncImage

    if isinstance(view, EmptyView):
        return AccessibilityInfo(role="empty", hidden=True)
    if isinstance(view, AnyView):
        return describe_accessibility(view.content)
    if isinstance(view, ScrollViewReader):
        info = AccessibilityInfo(
            role="scrollview", children=[describe_accessibility(view.content)]
        )
        return _apply_metadata(info, view)

    if isinstance(
        view,
        (Text, Button, TextField, SecureField, Toggle, Slider, Picker, Image, AsyncImage,
         Divider, Stepper, ProgressView, DatePicker, ColorPicker, Label,
         Link, Shape, Menu, Table, Gradient),
    ):
        if isinstance(view, Image) and view.decorative:
            return AccessibilityInfo(role="image", hidden=True)
        role = _role_for(view)
        info = AccessibilityInfo(
            role=role,
            label=_component_label(view),
            value=_component_value(view),
        )
        return _apply_metadata(info, view)

    # Containers.
    if isinstance(view, (VStack, HStack, ZStack)):
        info = AccessibilityInfo(
            role="group",
            children=[describe_accessibility(c) for c in view.children()],
        )
        return _apply_metadata(info, view)
    if isinstance(view, NavigationSplitView):
        info = AccessibilityInfo(
            role="splitview",
            children=[describe_accessibility(c) for c in view.children()],
        )
        return _apply_metadata(info, view)
    if isinstance(view, (Grid, GridRow, LabeledContent, ContentUnavailableView)):
        info = AccessibilityInfo(
            role=_role_for(view, "group"),
            label=getattr(view, "title", ""),
            children=[describe_accessibility(c) for c in view.children()],
        )
        return _apply_metadata(info, view)
    if isinstance(view, (ForEach, GroupBox, ViewThatFits, LazyHGrid, LazyVGrid)):
        info = AccessibilityInfo(
            role=_role_for(view, "group"),
            children=[describe_accessibility(c) for c in view.children()],
        )
        return _apply_metadata(info, view)
    if isinstance(view, (Form, Group, Section, DisclosureGroup)):
        info = AccessibilityInfo(
            role=_role_for(view, "group"),
            children=[describe_accessibility(c) for c in view.children()],
        )
        return _apply_metadata(info, view)
    if isinstance(view, NavigationStack):
        info = AccessibilityInfo(
            role="navigation",
            label=view.title,
            children=[describe_accessibility(view.content)],
        )
        return _apply_metadata(info, view)
    if isinstance(view, ScrollView):
        info = AccessibilityInfo(
            role="scrollview",
            children=[describe_accessibility(view.content)],
        )
        return _apply_metadata(info, view)
    if isinstance(view, TabView):
        info = AccessibilityInfo(
            role="tabview",
            children=[describe_accessibility(c) for c in view.children()],
        )
        return _apply_metadata(info, view)
    if isinstance(view, List):
        info = AccessibilityInfo(
            role="list",
            children=[describe_accessibility(r) for r in view.rows],
        )
        return _apply_metadata(info, view)
    if isinstance(view, Spacer):
        return AccessibilityInfo(role="spacer", hidden=True)

    # Generic container.
    info = AccessibilityInfo(
        role="group",
        children=[describe_accessibility(c) for c in view.children()],
    )
    return _apply_metadata(info, view)


def _combine_children(info: AccessibilityInfo) -> AccessibilityInfo:
    """Combine a node's children into a single accessibility element.

    The label/value of the combined element is the concatenation of the
    children's labels and values (mirrors SwiftUI's ``.combine`` strategy).
    """
    parts: List[str] = []
    values: List[str] = []
    for child in info.children:
        if child.hidden:
            continue
        if child.label:
            parts.append(child.label)
        if child.value:
            values.append(child.value)
    combined = AccessibilityInfo(
        role=info.role or "group",
        label=info.label or " ".join(parts),
        value=info.value or " ".join(values),
        hint=info.hint,
    )
    return combined


def accessibility_children(info: AccessibilityInfo) -> List[AccessibilityInfo]:
    """Return the non-hidden children of an accessibility node."""
    return [c for c in info.children if not c.hidden]
