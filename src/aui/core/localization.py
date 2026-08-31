"""Localization, Dynamic Type, layout direction, and semantic presentation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from .environment import environment
from .view import View, ViewModifier, _ModifiedContent, _apply

LOCALE_KEY = "locale"
LAYOUT_DIRECTION_KEY = "layoutDirection"
DYNAMIC_TYPE_SIZE_KEY = "dynamicTypeSize"


@dataclass(frozen=True)
class Locale:
    identifier: str = "en"

    @property
    def language_code(self) -> str:
        return self.identifier.replace("_", "-").split("-")[0].lower()


class LocalizedStringKey:
    """A localization key with an optional in-memory translation table."""

    def __init__(self, key: str, default: Optional[str] = None,
                 translations: Optional[Mapping[str, str]] = None, **arguments):
        if not key: raise ValueError("localization key cannot be empty")
        self.key = key
        self.default = default if default is not None else key
        self.translations = dict(translations or {})
        self.arguments = arguments

    def resolve(self, locale: Locale | str | None = None) -> str:
        value = locale if isinstance(locale, Locale) else Locale(str(locale or "en"))
        template = (self.translations.get(value.identifier)
                    or self.translations.get(value.language_code)
                    or self.default)
        try:
            return template.format(**self.arguments)
        except (KeyError, ValueError):
            return template

    def __str__(self): return self.default


class DynamicTypeSize:
    XSMALL = "xSmall"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xLarge"
    XXLARGE = "xxLarge"
    XXXLARGE = "xxxLarge"
    ACCESSIBILITY1 = "accessibility1"
    ACCESSIBILITY2 = "accessibility2"
    ACCESSIBILITY3 = "accessibility3"
    ACCESSIBILITY4 = "accessibility4"
    ACCESSIBILITY5 = "accessibility5"


DYNAMIC_TYPE_SCALE = {
    DynamicTypeSize.XSMALL: 0.82, DynamicTypeSize.SMALL: 0.9,
    DynamicTypeSize.MEDIUM: 0.96, DynamicTypeSize.LARGE: 1.0,
    DynamicTypeSize.XLARGE: 1.12, DynamicTypeSize.XXLARGE: 1.23,
    DynamicTypeSize.XXXLARGE: 1.35, DynamicTypeSize.ACCESSIBILITY1: 1.6,
    DynamicTypeSize.ACCESSIBILITY2: 1.9, DynamicTypeSize.ACCESSIBILITY3: 2.25,
    DynamicTypeSize.ACCESSIBILITY4: 2.65, DynamicTypeSize.ACCESSIBILITY5: 3.1,
}


@dataclass(frozen=True)
class SemanticModifier(ViewModifier):
    key: str
    value: object
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def locale(view: View, value: Locale | str) -> View:
    return environment(view, LOCALE_KEY, value if isinstance(value, Locale) else Locale(value))


def layout_direction(view: View, value: str) -> View:
    if value not in {"leftToRight", "rightToLeft"}:
        raise ValueError(f"unsupported layout direction: {value!r}")
    return environment(view, LAYOUT_DIRECTION_KEY, value)


def dynamic_type_size(view: View, value: str) -> View:
    if value not in DYNAMIC_TYPE_SCALE:
        raise ValueError(f"unsupported dynamic type size: {value!r}")
    return environment(view, DYNAMIC_TYPE_SIZE_KEY, value)


def redacted(view: View, reason: str = "placeholder") -> View:
    if reason not in {"placeholder", "privacy"}: raise ValueError(f"unsupported redaction reason: {reason!r}")
    return _apply(view, SemanticModifier("redacted", reason))


def privacy_sensitive(view: View, value: bool = True) -> View:
    return _apply(view, SemanticModifier("privacy_sensitive", bool(value)))


def help(view: View, text: str) -> View:
    return _apply(view, SemanticModifier("help", str(text)))


def resolve_semantic_tree(root: View) -> View:
    def visit(node, inherited):
        values = dict(inherited)
        if isinstance(node, _ModifiedContent) and isinstance(node._modifier, SemanticModifier):
            values[node._modifier.key] = node._modifier.value
        node._resolved_semantics = values
        for child in node.children(): visit(child, values)
    visit(root, {})
    return root


def semantic_value(view, key, default=None):
    return getattr(view, "_resolved_semantics", {}).get(key, default)
