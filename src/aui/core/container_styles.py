"""SwiftUI-like list, form, group box, disclosure and row styling."""
from __future__ import annotations

from dataclasses import dataclass

from .geometry import Color, EdgeInsets
from .styles import _style
from .view import View, ViewModifier, _apply


class ListStyle:
    AUTOMATIC = "automatic"; PLAIN = "plain"; INSET = "inset"
    GROUPED = "grouped"; INSET_GROUPED = "insetGrouped"; SIDEBAR = "sidebar"


class FormStyle:
    AUTOMATIC = "automatic"; GROUPED = "grouped"; COLUMNS = "columns"


class GroupBoxStyle:
    AUTOMATIC = "automatic"; PLAIN = "plain"; CARD = "card"


class DisclosureGroupStyle:
    AUTOMATIC = "automatic"; COMPACT = "compact"; CARD = "card"


@dataclass(frozen=True)
class ListRowBackgroundModifier(ViewModifier):
    color: Color
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class ListRowSeparatorModifier(ViewModifier):
    visibility: str
    def __post_init__(self):
        if self.visibility not in {"automatic", "visible", "hidden"}: raise ValueError("invalid row separator visibility")
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class ListRowInsetsModifier(ViewModifier):
    insets: EdgeInsets
    def size_that_fits(self, content, proposal):
        return content.size_that_fits(proposal.deflated_by(self.insets)).expanded_by(self.insets)
    def place(self, content, origin, size):
        content.place(type(origin)(origin.x + self.insets.leading, origin.y + self.insets.top),
                      size.deflated_by(self.insets))


def list_style(view, style): return _style(view, "list_style", style)
def form_style(view, style): return _style(view, "form_style", style)
def group_box_style(view, style): return _style(view, "group_box_style", style)
def disclosure_group_style(view, style): return _style(view, "disclosure_group_style", style)
def section_spacing(view, value): return _style(view, "section_spacing", max(0.0, float(value)))
def header_prominence(view, value):
    if value not in {"standard", "increased"}: raise ValueError("header prominence must be standard or increased")
    return _style(view, "header_prominence", value)
def list_row_background(view, color):
    if not isinstance(color, Color): raise TypeError("list row background expects Color")
    return _apply(view, ListRowBackgroundModifier(color))
def list_row_separator(view, visibility="automatic"): return _apply(view, ListRowSeparatorModifier(visibility))
def list_row_insets(view, insets):
    if not isinstance(insets, EdgeInsets): raise TypeError("list row insets expects EdgeInsets")
    return _apply(view, ListRowInsetsModifier(insets))


from .styles import _VALID
_VALID.update({
    "list_style": {ListStyle.AUTOMATIC, ListStyle.PLAIN, ListStyle.INSET, ListStyle.GROUPED, ListStyle.INSET_GROUPED, ListStyle.SIDEBAR},
    "form_style": {FormStyle.AUTOMATIC, FormStyle.GROUPED, FormStyle.COLUMNS},
    "group_box_style": {GroupBoxStyle.AUTOMATIC, GroupBoxStyle.PLAIN, GroupBoxStyle.CARD},
    "disclosure_group_style": {DisclosureGroupStyle.AUTOMATIC, DisclosureGroupStyle.COMPACT, DisclosureGroupStyle.CARD},
})
