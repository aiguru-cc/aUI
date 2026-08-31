"""SwiftUI-like upward data flow through PreferenceKey values."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Dict, Type

from .view import View, ViewModifier, _ModifiedContent, _apply


class PreferenceKey:
    """Subclass and override ``default_value`` / ``reduce``."""

    default_value: Any = None

    @classmethod
    def reduce(cls, value, next_value):
        return next_value


def _validate_key(key):
    if not isinstance(key, type) or not issubclass(key, PreferenceKey):
        raise TypeError("preference key must be a PreferenceKey subclass")


@dataclass(frozen=True)
class PreferenceModifier(ViewModifier):
    key: Type[PreferenceKey]
    value: Any

    def __post_init__(self): _validate_key(self.key)
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class TransformPreferenceModifier(ViewModifier):
    key: Type[PreferenceKey]
    transform: Callable[[Any], Any]

    def __post_init__(self):
        _validate_key(self.key)
        if not callable(self.transform): raise TypeError("preference transform must be callable")
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


class OnPreferenceChangeModifier(ViewModifier):
    def __init__(self, key: Type[PreferenceKey], action: Callable[[Any], None]):
        _validate_key(key)
        if not callable(action): raise TypeError("preference action must be callable")
        self.key, self.action = key, action
        self._has_value = False
        self._last_value = None

    def notify(self, value):
        if not self._has_value or value != self._last_value:
            self._has_value = True
            self._last_value = deepcopy(value)
            self.action(value)

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def preference(view: View, key: Type[PreferenceKey], value: Any) -> View:
    return _apply(view, PreferenceModifier(key, value))


def transform_preference(view: View, key: Type[PreferenceKey],
                         transform: Callable[[Any], Any]) -> View:
    return _apply(view, TransformPreferenceModifier(key, transform))


def on_preference_change(view: View, key: Type[PreferenceKey],
                         action: Callable[[Any], None]) -> View:
    return _apply(view, OnPreferenceChangeModifier(key, action))


def _merge(target: Dict[type, Any], source: Dict[type, Any]) -> None:
    for key, next_value in source.items():
        current = target.get(key, deepcopy(key.default_value))
        target[key] = key.reduce(current, next_value)


def collect_preferences(root: View, notify: bool = True) -> Dict[type, Any]:
    """Collect each subtree bottom-up and optionally notify observers."""
    def visit(node: View) -> Dict[type, Any]:
        if isinstance(node, _ModifiedContent):
            values = visit(node._content)
            mod = node._modifier
            if isinstance(mod, PreferenceModifier):
                current = values.get(mod.key, deepcopy(mod.key.default_value))
                values[mod.key] = mod.key.reduce(current, mod.value)
            elif isinstance(mod, TransformPreferenceModifier):
                current = values.get(mod.key, deepcopy(mod.key.default_value))
                result = mod.transform(current)
                values[mod.key] = current if result is None else result
            elif isinstance(mod, OnPreferenceChangeModifier) and notify:
                mod.notify(values.get(mod.key, deepcopy(mod.key.default_value)))
            node._preferences = dict(values)
            return values
        values: Dict[type, Any] = {}
        for child in node.children():
            _merge(values, visit(child))
        node._preferences = dict(values)
        return values

    return visit(root)


def preference_value(view: View, key: Type[PreferenceKey]):
    _validate_key(key)
    return getattr(view, "_preferences", {}).get(key, deepcopy(key.default_value))
