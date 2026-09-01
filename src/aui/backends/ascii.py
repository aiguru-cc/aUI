"""A UI backend that renders aUI views as plain-text ASCII art.

This backend requires no display and no third-party dependencies. It is used
for tests, documentation examples and headless rendering.

It also exposes the aUI accessibility tree via ``describe_accessibility()``
so headless tooling and documentation can inspect the semantic structure.
"""
from __future__ import annotations

from typing import List, Optional

from ..core.accessibility import AccessibilityInfo, describe_accessibility as _describe_accessibility
from ..core.components import (
    AppBar,
    Button,
    Capsule,
    Circle,
    ColorPicker,
    DatePicker,
    DisclosureGroup,
    ContentUnavailableView,
    Divider,
    Ellipse,
    Form,
    Gauge,
    Group,
    Image,
    Label,
    LabeledContent,
    Link,
    List,
    NavigationRail,
    NavigationStack,
    Picker,
    ProgressView,
    Rectangle,
    RoundedRectangle,
    Shape,
    ScrollView,
    SearchField,
    Section,
    SecureField,
    Slider,
    Stepper,
    TabView,
    Text,
    TextEditor,
    TextField,
    Toggle,
    UnevenRoundedRectangle,
)
from ..core.geometry import Point, Size
from ..core.commands import Menu
from ..core.table import Table
from ..core.visual_effects import AngularGradient, EllipticalGradient, Gradient, LinearGradient, OverlayModifier
from ..core.structural import AnyView, EmptyView, ForEach, GroupBox, OutlineGroup, ViewThatFits
from ..core.lazy import LazyHGrid, LazyVGrid
from ..core.scrolling import ScrollViewReader
from ..core.async_image import AsyncImage
from ..core.inspector import InspectorView
from ..core.control_group import ControlGroup
from ..core.badges import BadgeModifier
from ..core.layout import (
    GeometryReader, Grid, GridRow, HStack, NavigationSplitView, ResponsiveItem,
    ResponsiveRow, Spacer, VStack, ZStack,
)
from ..core.view import View, _Frame, _ModifiedContent
from ..core.environment import EnvironmentReader, resolve_environment_tree
from ..core.custom_layout import LayoutContainer
from ..core.layout_modifiers import (
    OffsetModifier, PositionModifier, SafeAreaInsetModifier, z_ordered,
)
from ..core.styles import ButtonStyle, LabelStyle, PickerStyle, ProgressViewStyle, resolve_style_tree, style_value
from ..core.transitions import KeyframeAnimator, PhaseAnimator
from ..core.animation_modifiers import resolve_transaction_tree
from ..core.canvas import Canvas, TimelineView
from ..core.text import resolve_text_style_tree
from ..core.localization import resolve_semantic_tree
from ..core.preferences import collect_preferences
from ..core.presentation import collect_presentation_configurations
from ..core.system_environment import system_environment
from ..core.capabilities import Capability


class AsciiBackend:
    """Renders a view tree to a text canvas."""

    CAPABILITIES = frozenset({Capability.RESPONSIVE_ROW, Capability.NAVIGATION_RAIL, Capability.APP_BAR})

    @classmethod
    def supports(cls, capability: str) -> bool:
        return capability in cls.CAPABILITIES

    @classmethod
    def available(cls) -> bool:
        """ASCII rendering is always available in the standard library."""
        return True

    @classmethod
    def availability_reason(cls) -> str:
        return "available"

    def __init__(self, width: int = 60, height: int = 20):
        self.width = width
        self.height = height
        self._canvas: List[List[str]] = [
            [" "] * width for _ in range(height)
        ]

    # -- Public API ---------------------------------------------------------
    def render(self, view: View) -> str:
        # Rendering is a pure snapshot operation.  Reusing a backend for a
        # shorter subsequent state must never leave glyphs from the prior frame.
        self._canvas = [[" "] * self.width for _ in range(self.height)]
        collect_presentation_configurations(view)
        resolve_environment_tree(view, system_environment())
        resolve_transaction_tree(view)
        resolve_style_tree(view)
        resolve_text_style_tree(view)
        resolve_semantic_tree(view)
        collect_preferences(view)
        size = Size(self.width, self.height)
        self._draw(view, 0, 0, size)
        return self._snapshot()

    def describe_accessibility(self, view: View) -> AccessibilityInfo:
        """Return the accessibility tree for ``view`` (headless inspection)."""
        return _describe_accessibility(view)

    # -- Drawing ------------------------------------------------------------
    def _draw(self, view: View, x: int, y: int, size: Size) -> None:
        if isinstance(view, EnvironmentReader):
            self._draw(view.content, x, y, size)
            return
        if isinstance(view, OutlineGroup):
            self._draw(view.content_view(), x, y, size)
            return
        if isinstance(view, GeometryReader):
            self._draw(view.resolve(Point(float(x), float(y)), size), x, y, size)
            return
        if isinstance(view, ScrollViewReader):
            self._draw(view.content, x, y, size)
            return
        if isinstance(view, (PhaseAnimator, KeyframeAnimator)):
            self._draw(view.content, x, y, size)
            return
        if isinstance(view, TimelineView):
            self._draw(view.content, x, y, size)
            return
        if isinstance(view, EmptyView):
            return
        if isinstance(view, AnyView):
            self._draw(view.content, x, y, size)
            return
        if isinstance(view, ViewThatFits):
            self._draw(view.selected(size), x, y, size)
            return
        if isinstance(view, _ModifiedContent):
            if isinstance(view._modifier, OffsetModifier):
                self._draw(view.body(), int(x + view._modifier.x),
                           int(y + view._modifier.y), size)
            elif isinstance(view._modifier, PositionModifier):
                child_size = view.body().size_that_fits(size)
                self._draw(
                    view.body(), int(x + view._modifier.x - child_size.width / 2),
                    int(y + view._modifier.y - child_size.height / 2), child_size,
                )
            elif isinstance(view._modifier, SafeAreaInsetModifier):
                inset = view._modifier.insets
                self._draw(view.body(), int(x + inset.leading), int(y + inset.top),
                           size.deflated_by(inset))
            else:
                self._draw(view.body(), x, y, size)
            if isinstance(view._modifier, OverlayModifier):
                self._draw(view._modifier.overlay, x, y, size)
            if isinstance(view._modifier, BadgeModifier):
                text = f"[{view._modifier.value}]"
                self._put(x + max(0, int(size.width) - len(text)), y, text)
            return
        if isinstance(view, _Frame):
            self._draw(view._content, x, y, size)
            return

        if isinstance(view, LayoutContainer):
            for placement in view.placements(Point(float(x), float(y)), size):
                self._draw(placement.subview.view, int(placement.origin.x),
                           int(placement.origin.y), placement.size)
        elif isinstance(view, ControlGroup):
            self._put(x, y, "{")
            self._draw_stack(view, x + 1, y, Size(max(0, size.width - 2), size.height), vertical=False)
            self._put(x + max(1, int(size.width) - 1), y, "}")
        elif isinstance(view, VStack):
            self._draw_stack(view, x, y, size, vertical=True)
        elif isinstance(view, HStack):
            self._draw_stack(view, x, y, size, vertical=False)
        elif isinstance(view, Grid):
            rows = list(view.children())
            for row_index, row in enumerate(rows):
                cells = list(row.children())
                cell_width = max(1, int(size.width) // max(1, len(cells)))
                for column, child in enumerate(cells):
                    self._draw(child, x + column * cell_width, y + row_index,
                               Size(cell_width, 1))
        elif isinstance(view, ResponsiveRow):
            for item, point, item_size in view.placements(Point(x, y), size):
                self._draw(item.content, int(point.x), int(point.y), item_size)
        elif isinstance(view, ResponsiveItem):
            self._draw(view.content, x, y, size)
        elif isinstance(view, LazyVGrid):
            widths = view.column_widths(size.width)
            columns = max(1, len(widths))
            cell_width = max(1, int(size.width) // columns)
            for index, child in enumerate(view.children()):
                self._draw(child, x + (index % columns) * cell_width,
                           y + index // columns, Size(cell_width, 1))
        elif isinstance(view, LazyHGrid):
            heights = view.row_heights(size.height)
            row_count = max(1, len(heights))
            widths, _ = view.metrics(size)
            column_width = max(1, int(max(widths, default=1)))
            for index, child in enumerate(view.children()):
                self._draw(child, x + (index // row_count) * column_width,
                           y + index % row_count, Size(column_width, 1))
        elif isinstance(view, GridRow):
            self._draw_stack(view, x, y, size, vertical=False)
        elif isinstance(view, ZStack):
            for _, child in z_ordered(view.children()):
                self._draw(child, x, y, size)
        elif isinstance(view, Text):
            self._put(x, y, view.display_content[: max(0, self.width - x)])
        elif isinstance(view, Canvas):
            self._put(x, y, f"(canvas {len(view.resolve(size).commands)} commands)")
        elif isinstance(view, Button):
            style = style_value(view, "button_style", ButtonStyle.AUTOMATIC)
            if style in (ButtonStyle.PLAIN, ButtonStyle.BORDERLESS, ButtonStyle.LINK):
                self._put(x, y, view.title)
            else:
                self._box(x, y, view.title)
        elif isinstance(view, Menu):
            selected = view.selected_item.title if view.selected_item else ""
            self._put(x, y, f"[ {view.title} ▾ {selected} ]")
        elif isinstance(view, Table):
            columns = view.visible_columns
            if not view.displayed_rows:
                self._put(x, y, view.empty_message)
                return
            widths = [max(6, int(column.resolved_width(100) / 10)) for column in columns]
            header = " | ".join(column.title[:width].ljust(width)
                                for column, width in zip(columns, widths))
            self._put(x, y, header)
            self._put(x, y + 1, "-+-".join("-" * width for width in widths))
            for offset, row in enumerate(view.displayed_rows[: max(0, int(size.height) - 2)]):
                text = " | ".join(str(column.get_value(row))[:width].ljust(width)
                                  for column, width in zip(columns, widths))
                self._put(x, y + 2 + offset, text)
        elif isinstance(view, SearchField):
            self._put(x, y, "[? " + (view.text.wrapped_value or view.placeholder) + "]")
        elif isinstance(view, TextEditor):
            lines = (view.text.wrapped_value or view.placeholder).splitlines() or [""]
            for offset, line in enumerate(lines[: max(1, int(size.height))]):
                self._put(x, y + offset, "| " + line)
        elif isinstance(view, TextField):
            self._put(x, y, "[" + view.placeholder + "]"[: max(0, self.width - x)])
        elif isinstance(view, SecureField):
            self._put(x, y, "[" + "*" * len(view.placeholder) + "]"[: max(0, self.width - x)])
        elif isinstance(view, Toggle):
            title = "" if style_value(view, "labels_hidden", False) else view.title
            self._put(x, y, ("[x] " + title).rstrip())
        elif isinstance(view, Slider):
            self._put(x, y, "-----o-----")
        elif isinstance(view, Picker) and style_value(view, "picker_style") == PickerStyle.SEGMENTED:
            selected = view.selection.wrapped_value if view.selection else None
            text = " ".join(f"[{o}]" if o == selected else str(o) for o in view.options)
            self._put(x, y, text)
        elif isinstance(view, Picker):
            title = "" if style_value(view, "labels_hidden", False) else view.title
            self._put(x, y, ("< " + title + " >").replace("  ", " "))
        elif isinstance(view, Divider):
            self._hline(x, y, min(size.width, self.width - x))
        elif isinstance(view, AsyncImage):
            marker = "loading" if view.phase.is_empty else (
                "image" if view.phase.is_success else "image failed"
            )
            self._put(x, y, f"({marker})")
        elif isinstance(view, Image):
            name = f" {view.resolved_system_name}" if view.system_name else ""
            if view.variable_value is not None:
                name += f" {view.variable_value:.0%}"
            self._put(x, y, f"(img{name})")
        elif isinstance(view, DatePicker):
            self._put(x, y, "[ " + view.title + " " + view._current() + " ]")
        elif isinstance(view, ColorPicker):
            self._put(x, y, "[ " + view.title + " " + (view.selection.wrapped_value.to_tk() if view.selection and view.selection.wrapped_value else "??????") + " ]")
        elif isinstance(view, Stepper):
            self._put(x, y, "[- " + view.title + " +]")
        elif isinstance(view, Gauge):
            self._draw_progress(view, x, y, size)
        elif isinstance(view, ProgressView):
            if style_value(view, "progress_view_style") == ProgressViewStyle.CIRCULAR:
                self._put(x, y, "◌")
            else:
                self._draw_progress(view, x, y, size)
        elif isinstance(view, Label):
            style = style_value(view, "label_style", LabelStyle.AUTOMATIC)
            text = view.system_name if style == LabelStyle.ICON_ONLY else view.title
            if style in (LabelStyle.AUTOMATIC, LabelStyle.TITLE_AND_ICON) and view.system_name:
                text = "* " + text
            self._put(x, y, text)
        elif isinstance(view, Link):
            self._put(x, y, view.title + " ↗")
        elif isinstance(view, Shape):
            symbol = "◔" if view.trim_range != (0.0, 1.0) else (
                "◩" if isinstance(view, UnevenRoundedRectangle) else (
                "⬭" if isinstance(view, Ellipse) else (
                "▰" if isinstance(view, Capsule) else (
                "○" if isinstance(view, Circle) else (
                "▢" if isinstance(view, RoundedRectangle) else "□"
            )))))
            self._put(x, y, symbol)
        elif isinstance(view, Gradient):
            marker = "◉ angular" if isinstance(view, AngularGradient) else (
                "⬭ elliptical" if isinstance(view, EllipticalGradient) else (
                "⇢ gradient" if isinstance(view, LinearGradient) else "◎ gradient"))
            self._put(x, y, marker)
        elif isinstance(view, LabeledContent):
            left, right = view.children()
            self._draw(left, x, y, size)
            right_size = right.size_that_fits(size)
            self._draw(right, max(x, x + int(size.width - right_size.width)), y, size)
        elif isinstance(view, ContentUnavailableView):
            for offset, child in enumerate(view.children()):
                self._draw(child, x, y + offset, size)
        elif isinstance(view, (ForEach, GroupBox)):
            cy = y
            for child in view.children():
                self._draw(child, x, cy, size)
                cy += 1
        elif isinstance(view, NavigationStack):
            offset = 1 if view.header_visible else 0
            if view.header_visible:
                self._put(x, y, "== " + view.title + " ==")
            for child in view.children():
                self._draw(child, x, y + offset, size)
        elif isinstance(view, AppBar):
            self._put(x, y, "==")
            self._draw(view.title, x + 3, y, Size(max(0, size.width - 3), 1))
            for action in view.actions:
                self._draw(action, x, y + 1, size)
        elif isinstance(view, NavigationSplitView):
            widths = [int(value) for value in view.column_widths(size.width)]
            cx = x
            visible = [(child, width) for child, width in zip(view.children(), widths) if width > 0]
            for index, (child, width) in enumerate(visible):
                self._draw(child, cx, y, Size(width, size.height))
                cx += width
                if index < len(visible) - 1:
                    for yy in range(y, min(self.height, y + int(size.height))):
                        self._put(cx, yy, "|")
                    cx += 1
        elif isinstance(view, NavigationRail):
            for index, destination in enumerate(view.destinations):
                marker = "●" if index == view.active_index else "○"
                title = destination.label if view.extended else (destination.system_name or destination.label)
                self._put(x, y + index, f"{marker} {title}"[: max(0, self.width - x)])
        elif isinstance(view, InspectorView):
            main, panel = view.column_widths(size.width)
            if main > 0:
                self._draw(view.content, x, y, Size(main, size.height))
            if panel > 0:
                panel_x = x if main == 0 else x + int(main) + 1
                if main > 0:
                    for yy in range(y, min(self.height, y + int(size.height))):
                        self._put(panel_x - 1, yy, "|")
                self._draw(view.inspector_content, panel_x, y, Size(panel, size.height))
        elif isinstance(view, Form):
            cy = y
            for child in view.children():
                self._draw(child, x, cy, size)
                cy += 1
        elif isinstance(view, Spacer):
            return
        elif isinstance(view, ScrollView):
            self._draw(view.content, x, y, size)
        elif isinstance(view, Section):
            cy = y
            for child in view.children():
                self._draw(child, x, cy, size)
                cy += 1
        elif isinstance(view, DisclosureGroup):
            cy = y
            for child in view.children():
                self._draw(child, x, cy, size)
                cy += 1
        elif isinstance(view, TabView):
            for child in view.children():
                self._draw(child, x, y, size)
                break
        else:
            # Generic container: draw children.
            for child in view.children():
                self._draw(child, x, y, size)

    def _draw_stack(self, stack, x: int, y: int, size: Size, vertical: bool) -> None:
        children = stack.children()
        if not children:
            return
        # Simple fixed distribution for ASCII preview.
        if vertical:
            each = max(1, int(size.height // len(children)))
            cy = y
            for child in children:
                self._draw(child, x, cy, Size(size.width, each))
                cy += each
        else:
            each = max(1, int(size.width // len(children)))
            cx = x
            for child in children:
                self._draw(child, cx, y, Size(each, size.height))
                cx += each

    # -- Primitives ---------------------------------------------------------
    def _put(self, x: int, y: int, text: str) -> None:
        if not (0 <= y < self.height):
            return
        for i, ch in enumerate(text):
            cx = x + i
            if 0 <= cx < self.width:
                self._canvas[y][cx] = ch

    def _hline(self, x: int, y: int, length: float) -> None:
        self._put(x, y, "-" * max(0, int(length)))

    def _box(self, x: int, y: int, label: str) -> None:
        text = " " + label + " "
        self._put(x, y, "[" + text[: max(0, self.width - x - 2)] + "]")

    def _draw_progress(self, view: ProgressView, x: int, y: int, size: Size) -> None:
        total = max(1, int(min(size.width, self.width - x) - 2))
        if view.value is None:
            self._put(x, y, "[" + "?" * total + "]")
            return
        ratio = max(0.0, min(1.0, view.value))
        filled = int(round(ratio * total))
        self._put(x, y, "[" + "#" * filled + "-" * (total - filled) + "]")

    def _snapshot(self) -> str:
        return "\n".join("".join(row).rstrip() for row in self._canvas)
