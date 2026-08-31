"""Attributed strings, Markdown parsing, and SwiftUI-like text modifiers."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict

from .geometry import Color
from .view import View, ViewModifier, _ModifiedContent, _apply


@dataclass(frozen=True)
class AttributeRun:
    start: int
    end: int
    attributes: Dict[str, Any] = field(default_factory=dict)


class AttributedString:
    def __init__(self, text: str, runs=()):
        self.text = str(text)
        self.runs = tuple(runs)
        for run in self.runs:
            if not isinstance(run, AttributeRun) or not (0 <= run.start <= run.end <= len(self.text)):
                raise ValueError("attribute run is outside the string")

    def __str__(self): return self.text

    @classmethod
    def markdown(cls, source: str) -> "AttributedString":
        """Parse bold, italic, code and Markdown links using the standard library."""
        pattern = re.compile(r"\[([^]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`|(?<!\*)\*([^*]+)\*(?!\*)")
        output, runs, cursor, source_pos = [], [], 0, 0
        for match in pattern.finditer(source):
            prefix = source[source_pos:match.start()]
            output.append(prefix); cursor += len(prefix)
            if match.group(1) is not None:
                text, attrs = match.group(1), {"link": match.group(2)}
            elif match.group(3) is not None:
                text, attrs = match.group(3), {"bold": True}
            elif match.group(4) is not None:
                text, attrs = match.group(4), {"code": True}
            else:
                text, attrs = match.group(5), {"italic": True}
            output.append(text)
            runs.append(AttributeRun(cursor, cursor + len(text), attrs))
            cursor += len(text); source_pos = match.end()
        output.append(source[source_pos:])
        return cls("".join(output), runs)


@dataclass(frozen=True)
class TextStyleModifier(ViewModifier):
    key: str
    value: Any

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def _text_style(view, key, value): return _apply(view, TextStyleModifier(key, value))
def kerning(view, value): return _text_style(view, "kerning", float(value))
def tracking(view, value): return _text_style(view, "tracking", float(value))
def baseline_offset(view, value): return _text_style(view, "baseline_offset", float(value))
def text_case(view, value):
    if value not in {None, "uppercase", "lowercase"}: raise ValueError(f"unsupported text case: {value!r}")
    return _text_style(view, "text_case", value)
def multiline_text_alignment(view, value):
    if value not in {"leading", "center", "trailing"}: raise ValueError(f"unsupported text alignment: {value!r}")
    return _text_style(view, "multiline_alignment", value)
def truncation_mode(view, value):
    if value not in {"head", "middle", "tail"}: raise ValueError(f"unsupported truncation mode: {value!r}")
    return _text_style(view, "truncation_mode", value)
def minimum_scale_factor(view, value): return _text_style(view, "minimum_scale_factor", max(0.0, min(1.0, float(value))))
def allows_tightening(view, value=True): return _text_style(view, "allows_tightening", bool(value))
def monospaced_digit(view): return _text_style(view, "monospaced_digit", True)
def text_selection(view, enabled=True): return _text_style(view, "text_selection", bool(enabled))


def resolve_text_style_tree(root: View) -> View:
    seen = set()
    def visit(node, inherited, locked=frozenset()):
        if id(node) in seen: return
        seen.add(id(node)); values = dict(inherited)
        if isinstance(node, _ModifiedContent) and isinstance(node._modifier, TextStyleModifier):
            if node._modifier.key not in locked: values[node._modifier.key] = node._modifier.value
            locked = locked | {node._modifier.key}
        node._resolved_text_style = values
        for child in node.children():
            visit(child, values, locked if isinstance(node, _ModifiedContent) else frozenset())
    visit(root, {})
    return root


def text_style_value(view, key, default=None):
    return getattr(view, "_resolved_text_style", {}).get(key, default)
