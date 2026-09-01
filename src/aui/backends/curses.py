"""Curses terminal backend for aUI.

Renders the declarative aUI view tree onto an interactive terminal using the
standard-library ``curses`` module. No third-party dependencies and no display
server required — this is the *native* interactive backend for aUI.

Features
--------

* **Full component coverage** — Text / Button / TextField / Toggle / Slider /
  Picker / Stepper / DatePicker / ProgressView / Divider / Image / List /
  Form / NavigationStack / Group.
* **Global scrolling** — when the content is taller than the terminal, the
  whole page scrolls (PageUp / PageDown). The focused element is always kept
  inside the viewport.
* **Keyboard focus navigation** — every interactive component is focusable and
  is visually highlighted when focused (``Tab`` / arrows). ``Enter`` activates.
* **SwiftUI control states** — interactive components render focused and
  disabled states; buttons support semantic destructive/cancel roles, tint,
  buttonStyle and controlSize.
* **Multi-line ``Text``** rendering with word wrap and CJK-aware widths.
* **Accessibility** — ``describe_accessibility()`` exposes the aUI semantic
  tree for terminal screen readers / headless inspection.

Controls
--------

============  =================================================
Key           Action
============  =================================================
``Tab``       next focusable element
``Shift-Tab`` previous focusable element
``↑`` / ``↓`` move focus (same as Tab / Shift-Tab)
``Enter``     activate (button / toggle / tap)
``←`` / ``→`` adjust focused slider / picker / stepper / date
``Backspace`` delete last char of focused text field
typing        edit the focused text field
``PageUp``    scroll up (or scroll the focused list)
``PageDown``  scroll down (or scroll the focused list)
``q`` / ``Q`` quit
============  =================================================
"""
from __future__ import annotations

try:
    import curses
except ImportError:  # Windows CPython without the optional windows-curses wheel
    curses = None  # type: ignore[assignment]
from datetime import datetime, timedelta
from typing import Callable, Dict, List as TList, Optional, Tuple

from ..core.components import (
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
    Group,
    Image,
    Label,
    LabeledContent,
    Link,
    List,
    NavigationStack,
    Picker,
    ProgressView,
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
from ..core.capabilities import Capability
from ..core.accessibility import AccessibilityInfo, describe_accessibility as _describe_accessibility
from ..core.commands import Menu
from ..core.table import Table
from ..core.visual_effects import AngularGradient, EllipticalGradient, Gradient, LinearGradient, OverlayModifier
from ..core.structural import AnyView, EmptyView, ForEach, GroupBox, OutlineGroup, ViewThatFits
from ..core.lazy import LazyHGrid, LazyVGrid
from ..core.scrolling import IDModifier, ScrollViewReader, find_scroll_configuration
from ..core.async_image import AsyncImage
from ..core.focus import FocusedModifier
from ..core.inspector import InspectorView
from ..core.control_group import ControlGroup
from ..core.badges import BadgeModifier
from ..core.keyboard import (
    DefaultFocusModifier, KeyPress, KeyPressResult, KeyboardShortcutModifier,
    OnKeyPressModifier,
)
from ..core.events import (
    OnAppearModifier, OnDisappearModifier, OnSubmitModifier, SubmitLabelModifier,
    run_on_change,
)
from ..core.environment import EnvironmentReader, resolve_environment_tree
from ..core.system_environment import system_environment
from ..core.presentation import collect_presentation_configurations
from ..core.custom_layout import LayoutContainer
from ..core.layout_modifiers import (
    OffsetModifier, PositionModifier, SafeAreaInsetModifier, z_ordered,
)
from ..core.geometry import Color, Point, Size
from ..core.layout import GeometryReader, Grid, GridRow, HStack, NavigationSplitView, Spacer, VStack, ZStack
from ..core.modifiers import TapGestureModifier
from ..core.gestures import (
    DragGestureModifier, GestureHandler, GestureModifier, LongPressGestureModifier,
)
from ..core.view import View, _Frame, _ModifiedContent
from ..core.styles import ButtonStyle, LabelStyle, is_enabled, resolve_style_tree, style_value
from ..core.transitions import KeyframeAnimator, PhaseAnimator
from ..core.animation_modifiers import resolve_transaction_tree
from ..core.canvas import Canvas, TimelineView
from ..core.text import resolve_text_style_tree
from ..core.localization import resolve_semantic_tree
from ..core.preferences import collect_preferences
from ..core.async_actions import cancel_tasks, start_tasks
from ..core.dispatcher import UIDispatcher
from ..core.state import observation_tracking


#: Leaf components that get a recorded frame and (for interactive ones) focus.
_LEAF_TYPES = (
    Text, Button, TextField, SecureField, Toggle, Slider, Picker, Stepper, AsyncImage,
    DatePicker, ProgressView, Divider, Image, ColorPicker, Label, Link,
    Shape, Menu, Table, Gradient,
)

#: Approximate character-cell aspect: an ASCII glyph is ~0.55 * font_size pt.
_GLYPH_RATIO = 0.55


class _Interactive:
    """A focusable / activatable region recorded during layout."""

    __slots__ = ("view", "origin", "size", "kind", "action", "owner_list", "owner_row")

    def __init__(
        self,
        view: View,
        origin: Point,
        size: Size,
        kind: str,
        action: Optional[Callable] = None,
        owner_list: Optional[List] = None,
        owner_row: Optional[int] = None,
    ):
        self.view = view
        self.origin = origin
        self.size = size
        self.kind = kind
        self.action = action
        self.owner_list = owner_list
        self.owner_row = owner_row


class TerminalGrid:
    """A character-cell canvas with cursor-addressable drawing."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._cells: TList[TList[str]] = [[" "] * width for _ in range(height)]

    def put(self, x: int, y: int, text: str) -> None:
        """Write text at (x, y), clipping to the canvas."""
        if not (0 <= y < self.height):
            return
        row = self._cells[y]
        for i, ch in enumerate(text):
            cx = x + i
            if 0 <= cx < self.width:
                row[cx] = ch

    def hline(self, x: int, y: int, length: int, ch: str = "-") -> None:
        self.put(x, y, ch * max(0, length))

    def box(self, x: int, y: int, width: int, height: int) -> None:
        """Draw an ASCII box outline."""
        if width < 2 or height < 2:
            return
        self.put(x, y, "+" + "-" * (width - 2) + "+")
        for yy in range(y + 1, y + height - 1):
            self.put(x, yy, "|")
            self.put(x + width - 1, yy, "|")
        self.put(x, y + height - 1, "+" + "-" * (width - 2) + "+")

    def snapshot(self) -> str:
        return "\n".join("".join(row).rstrip() for row in self._cells)


class CursesBackend:
    """Interactive terminal backend. Use via ``run()`` (blocking main loop)."""

    # The named capability set is intentionally desktop-specific.  Curses has
    # rich terminal interaction, but it must not claim desktop toolbar,
    # native-symbol, file-dialog, or draggable-split semantics merely because
    # it can render a textual approximation of the same view tree.
    CAPABILITIES = frozenset()

    @classmethod
    def supports(cls, capability: str) -> bool:
        return capability in cls.CAPABILITIES

    @classmethod
    def available(cls) -> bool:
        """Return whether the platform exposes a usable curses module.

        Windows obtains curses through the optional ``windows-curses`` wheel;
        macOS/Linux ship it with CPython.  Import is performed at module load,
        so this remains a cheap deterministic capability query.
        """
        return curses is not None

    @classmethod
    def availability_reason(cls) -> str:
        return "available" if cls.available() else "Python curses module is unavailable"

    def __init__(self, view_factory: Callable[[], View]):
        if not self.available():
            raise RuntimeError(
                "CursesBackend requires Python curses; install windows-curses on Windows"
            )
        self._view_factory = view_factory
        self._view: Optional[View] = None
        self._frames: Dict[int, Tuple[Point, Size]] = {}
        self._interactives: TList[_Interactive] = []
        self._lists: TList[List] = []
        self._focus_index = 0
        self._scroll_y = 0.0
        self._did_apply_default_scroll = False
        self._content_height = 0.0
        self._status = ""
        self._stdscr = None
        self._sink = None
        self._viewport_h = 0
        self._color_ok = False
        self._pairs: Dict[Tuple[int, int], int] = {}
        self._scroll_ids: Dict[object, Tuple[Point, Size]] = {}
        self._scroll_cancels: TList[Callable[[], None]] = []
        self._focus_bindings: Dict[int, FocusedModifier] = {}
        self._key_handlers: list[OnKeyPressModifier] = []
        self._keyboard_shortcuts: list[tuple[object, View]] = []
        self._submit_bindings: Dict[int, OnSubmitModifier] = {}
        self._submit_labels: Dict[int, SubmitLabelModifier] = {}
        self._tasks = {}
        self._appeared_keys: set = set()
        self._disappear_actions: Dict[object, Callable[[], None]] = {}
        self._change_values: dict = {}
        self._dispatcher = UIDispatcher()
        self._observation_cancels: list[Callable[[], None]] = []

    # -- Public API ---------------------------------------------------------
    def run(self) -> None:
        """Enter the curses main loop (blocking)."""
        curses.wrapper(self._main)

    def close(self) -> None:
        """Release terminal-owned lifecycle resources exactly once.

        ``curses.wrapper`` restores terminal state, while the backend remains
        responsible for declarative view lifetime: tasks, observations, queued
        UI callbacks and ``onDisappear`` handlers must not outlive the scene.
        """
        cancel_tasks(self._tasks)
        self._tasks.clear()
        for cancel in self._observation_cancels:
            cancel()
        self._observation_cancels = []
        actions, self._disappear_actions = self._disappear_actions, {}
        for action in actions.values():
            action()
        self._dispatcher.close()

    def render_to_string(self, width: int = 80, height: int = 20) -> str:
        """Render the current view to a string without a terminal.

        Useful for testing and headless previews.
        """
        view = self._make_view()
        self._viewport_h = height
        self._layout(view, width, height)
        self._apply_scroll_configuration(view, height)
        grid = TerminalGrid(width, height)
        self._sink = grid
        self._draw(view, grid, Point(0, 0), Size(width, height), scroll_y=self._scroll_y)
        return grid.snapshot()

    def describe_accessibility(self) -> AccessibilityInfo:
        """Return the accessibility tree of the current view."""
        return _describe_accessibility(self._make_view())

    def _make_view(self) -> View:
        for cancel in self._observation_cancels:
            cancel()
        with observation_tracking(self._request_refresh) as cleanups:
            view = self._view_factory()
            collect_presentation_configurations(view)
            resolve_environment_tree(view, system_environment())
            resolve_transaction_tree(view)
            resolve_style_tree(view)
            resolve_text_style_tree(view)
            resolve_semantic_tree(view)
            collect_preferences(view)
            start_tasks(view, self._tasks, self._request_refresh)
        self._observation_cancels = cleanups
        run_on_change(view, self._change_values)
        return view

    def _request_refresh(self) -> None:
        self._dispatcher.schedule_once("refresh", lambda: None)

    # -- Colour setup -------------------------------------------------------
    def _setup_colors(self) -> None:
        if not curses.has_colors():
            self._color_ok = False
            return
        try:
            curses.start_color()
            self._color_ok = True
        except curses.error:
            self._color_ok = False

    def _pair(self, fg: int, bg: int) -> int:
        """Return a curses color-pair id for (fg, bg), caching as needed."""
        if not self._color_ok:
            return 0
        key = (fg, bg)
        pid = self._pairs.get(key)
        if pid is None:
            pid = len(self._pairs) + 1
            try:
                curses.init_pair(pid, fg, bg)
            except curses.error:
                return 0
            self._pairs[key] = pid
        return pid

    # -- Main loop ----------------------------------------------------------
    def _main(self, stdscr) -> None:
        self._dispatcher.adopt_current_thread()
        try:
            curses.curs_set(0)
        except curses.error:
            pass  # Terminal may not support hiding the cursor.
        stdscr.keypad(True)
        self._stdscr = stdscr
        stdscr.timeout(100)
        self._setup_colors()
        try:
            while True:
                self._dispatcher.drain()
                self._render()
                key = stdscr.getch()
                if key == -1:
                    continue
                if key in (ord("q"), ord("Q")):
                    break
                self._handle_key(key)
        finally:
            self.close()

    # -- Layout -------------------------------------------------------------
    def _layout(self, view: View, width: int, height: int) -> None:
        """Lay out the view tree into content coordinates and record frames."""
        resolve_style_tree(view)
        self._frames = {}
        self._scroll_ids = {}
        self._focus_bindings = {}
        self._key_handlers = []
        self._keyboard_shortcuts = []
        self._submit_bindings = {}
        self._submit_labels = {}
        for cancel in self._scroll_cancels:
            cancel()
        self._scroll_cancels = []
        self._interactives = []
        self._lists = []
        self._content_height = 0.0
        self._focus_index = max(0, min(self._focus_index, len(self._interactives) - 1))
        self._walk(view, Point(0, 0), Size(width, max(1.0, float(height))))
        for index, item in enumerate(self._interactives):
            modifier = self._focus_bindings.get(id(item.view))
            if modifier is not None and modifier.is_focused:
                self._focus_index = index
                break

    # -- Character-cell measurement ----------------------------------------
    def _text_proposal_width(self, view: Text, cols: int) -> float:
        size = getattr(view._font, "size", 14.0)
        return max(1.0, float(cols) * _GLYPH_RATIO * size)

    def _char_size(self, view: View, width: float) -> Tuple[int, int]:
        if isinstance(view, EnvironmentReader):
            return self._char_size(view.content, width)
        if isinstance(view, LayoutContainer):
            measured = view.size_that_fits(Size(width, self._viewport_h or 20))
            return (max(1, int(measured.width)), max(1, int(measured.height)))
        if isinstance(view, OutlineGroup):
            return self._char_size(view.content_view(), width)
        if isinstance(view, GeometryReader):
            content = view.resolve(Point(), Size(width, self._viewport_h or 20))
            return self._char_size(content, width)
        if isinstance(view, ScrollViewReader):
            return self._char_size(view.content, width)
        if isinstance(view, (PhaseAnimator, KeyframeAnimator)):
            return self._char_size(view.content, width)
        if isinstance(view, TimelineView):
            return self._char_size(view.content, width)
        if isinstance(view, Canvas):
            return (min(int(width), 20), 1)
        """Return (cols, rows) a view needs given a width in columns."""
        if isinstance(view, Text):
            lines = view._layout_lines(self._text_proposal_width(view, int(width)) + 0.5)
            w = max((self._line_width(line) for line in lines), default=0)
            return (min(int(width), max(1, w)), max(1, len(lines)))
        if isinstance(view, EmptyView):
            return (0, 0)
        if isinstance(view, AnyView):
            return self._char_size(view.content, width)
        if isinstance(view, ViewThatFits):
            return self._char_size(view.selected(Size(width, self._viewport_h or 20)), width)
        if isinstance(view, Button):
            return (max(6, len(view.title) + 4), 1)
        if isinstance(view, Menu):
            selected = view.selected_item.title if view.selected_item else ""
            return (max(10, len(view.title) + len(selected) + 7), 1)
        if isinstance(view, Table):
            return (int(width), max(3, min(len(view.rows) + 2, 12)))
        if isinstance(view, TextEditor):
            lines = (view.text.wrapped_value or view.placeholder).splitlines() or [""]
            return (max(16, min(int(width), 40)), max(3, min(8, len(lines))))
        if isinstance(view, SearchField):
            return (max(12, min(int(width), 28)), 1)
        if isinstance(view, TextField):
            return (max(8, min(int(width), 24)), 1)
        if isinstance(view, SecureField):
            return (max(8, min(int(width), 24)), 1)
        if isinstance(view, Toggle):
            return (max(6, len(view.title) + 5), 1)
        if isinstance(view, Slider):
            return (min(int(width), 24), 1)
        if isinstance(view, Picker):
            return (max(8, len(view.title) + 8), 1)
        if isinstance(view, Stepper):
            return (max(12, len(view.title) + 8), 1)
        if isinstance(view, DatePicker):
            return (max(14, len(view.title) + len(view._current()) + 5), 1)
        if isinstance(view, ColorPicker):
            return (max(14, len(view.title) + 8), 1)
        if isinstance(view, Label):
            return (max(6, len(view.title) + (3 if view.system_name else 0)), 1)
        if isinstance(view, Link):
            return (max(6, len(view.title) + 2), 1)
        if isinstance(view, Shape):
            return (3, 1)
        if isinstance(view, Gradient):
            return (12, 1)
        if isinstance(view, Grid):
            columns, heights = view.metrics(Size(width, float("inf")))
            return (min(int(width), max(1, int(sum(columns)))), max(1, len(heights)))
        if isinstance(view, LazyVGrid):
            widths = view.column_widths(width)
            rows = (len(view.children()) + len(widths) - 1) // max(1, len(widths))
            return (int(width), max(1, rows))
        if isinstance(view, LazyHGrid):
            widths, heights = view.metrics(Size(width, self._viewport_h or float("inf")))
            return (max(1, int(round(sum(widths) + view.column_spacing *
                                     max(0, len(widths) - 1)))),
                    max(1, len(heights)))
        if isinstance(view, GridRow):
            return self._container_char_size(view, int(width))
        if isinstance(view, LabeledContent):
            return self._container_char_size(view, int(width))
        if isinstance(view, ContentUnavailableView):
            return self._container_char_size(view, int(width))
        if isinstance(view, (ForEach, GroupBox)):
            return self._container_char_size(view, int(width))
        if isinstance(view, ProgressView):
            return (min(int(width), 20), 1)
        if isinstance(view, Divider):
            return (int(width), 1)
        if isinstance(view, Image):
            return (5, 1)
        if isinstance(view, AsyncImage):
            return (14, 1)
        if isinstance(view, (VStack, HStack, Form, Group, Section, DisclosureGroup)):
            return self._container_char_size(view, int(width))
        if isinstance(view, NavigationStack):
            inner = self._container_char_size(view.content, int(width))
            header = 1 if view.header_visible else 0
            return (max(len(view.title) + 6 if header else 0, inner[0]), inner[1] + header)
        if isinstance(view, NavigationSplitView):
            sizes = [self._char_size(child, max(1, int(width) // view.column_count))
                     for child in view.children()]
            return (int(width), max((s[1] for s in sizes), default=1))
        if isinstance(view, InspectorView):
            main, panel = view.column_widths(width)
            sizes = [self._char_size(child, max(1, part))
                     for child, part in zip(view.children(), (main, panel)) if part > 0]
            return (int(width), max((item[1] for item in sizes), default=1))
        if isinstance(view, ScrollView):
            return self._container_char_size(view.content, int(width))
        if isinstance(view, TabView):
            active = view.children()
            return self._char_size(active[0], int(width)) if active else (0, 0)
        if isinstance(view, ZStack):
            ws = [self._char_size(c, int(width))[0] for c in view.children()]
            hs = [self._char_size(c, int(width))[1] for c in view.children()]
            return (max(ws, default=0), max(hs, default=1))
        if isinstance(view, Spacer):
            return (0, 0)
        if isinstance(view, List):
            return (int(width), 1)
        return (int(width), 1)

    def _line_width(self, line: str) -> int:
        """Display width of a line in columns (CJK full-width chars = 2)."""
        w = 0
        for ch in line:
            w += 2 if ord(ch) > 0x2E7F else 1
        return max(0, w)

    def _container_char_size(self, view: View, width: int) -> Tuple[int, int]:
        spacing = int(round(getattr(view, "_spacing", 0) or 0))
        total_h = 0
        max_w = 0
        n = 0
        for child in view.children():
            if isinstance(child, Spacer):
                continue
            cw, ch = self._char_size(child, width)
            max_w = max(max_w, cw)
            total_h += ch
            n += 1
        total_h += spacing * max(0, n - 1)
        return (min(width, max(1, max_w)), max(1, total_h))

    # -- Tree walk ----------------------------------------------------------
    def _walk(self, view: View, origin: Point, size: Size) -> None:
        if isinstance(view, EnvironmentReader):
            self._frames[id(view)] = (origin, size)
            self._walk(view.content, origin, size)
            return
        if isinstance(view, LayoutContainer):
            self._frames[id(view)] = (origin, size)
            for placement in view.placements(origin, size):
                self._walk(placement.subview.view, placement.origin, placement.size)
            return
        if isinstance(view, OutlineGroup):
            self._frames[id(view)] = (origin, size)
            self._walk(view.content_view(), origin, size)
            return
        if isinstance(view, GeometryReader):
            self._frames[id(view)] = (origin, size)
            self._walk(view.resolve(origin, size), origin, size)
            return
        if isinstance(view, ScrollViewReader):
            self._frames[id(view)] = (origin, size)
            self._scroll_cancels.append(view.proxy.subscribe(self._scroll_to_id))
            self._walk(view.content, origin, size)
            return
        if isinstance(view, EmptyView):
            self._frames[id(view)] = (origin, Size())
            return
        if isinstance(view, AnyView):
            self._frames[id(view)] = (origin, size)
            self._walk(view.content, origin, size)
            return
        if isinstance(view, ViewThatFits):
            self._frames[id(view)] = (origin, size)
            self._walk(view.selected(size), origin, size)
            return
        if isinstance(view, _ModifiedContent):
            inner = self._unwrap(view.body())
            mod = view._modifier
            if isinstance(mod, FocusedModifier):
                if isinstance(mod, DefaultFocusModifier):
                    mod.activate_if_needed()
                self._focus_bindings[id(inner)] = mod
            if isinstance(mod, OnKeyPressModifier):
                self._key_handlers.append(mod)
            if isinstance(mod, KeyboardShortcutModifier):
                self._keyboard_shortcuts.append((mod.shortcut, inner))
            if isinstance(mod, OnSubmitModifier):
                self._submit_bindings[id(inner)] = mod
            elif isinstance(mod, SubmitLabelModifier):
                self._submit_labels[id(inner)] = mod
            elif isinstance(mod, OnAppearModifier):
                key = self._action_key(mod.action)
                if key not in self._appeared_keys:
                    self._appeared_keys.add(key)
                    mod.action()
            elif isinstance(mod, OnDisappearModifier):
                self._disappear_actions[self._action_key(mod.action)] = mod.action
            if isinstance(mod, (TapGestureModifier, LongPressGestureModifier,
                                DragGestureModifier, GestureModifier)):
                if isinstance(inner, _LEAF_TYPES):
                    cs = self._char_size(inner, size.width)
                    action = getattr(mod, "action", None)
                    if isinstance(mod, GestureModifier) and isinstance(mod.gesture, GestureHandler):
                        action = lambda handler=mod.gesture: handler.emit_ended(Point())
                    self._interactives.append(
                        _Interactive(inner, origin, Size(cs[0], cs[1]), "tap", action)
                    )
            if isinstance(mod, OffsetModifier):
                self._walk(view.body(), Point(origin.x + mod.x, origin.y + mod.y), size)
            elif isinstance(mod, PositionModifier):
                child_size = view.body().size_that_fits(size)
                self._walk(
                    view.body(),
                    Point(origin.x + mod.x - child_size.width / 2,
                          origin.y + mod.y - child_size.height / 2),
                    child_size,
                )
            elif isinstance(mod, SafeAreaInsetModifier):
                inset = mod.insets
                self._walk(
                    view.body(), Point(origin.x + inset.leading, origin.y + inset.top),
                    size.deflated_by(inset),
                )
            else:
                self._walk(view.body(), origin, size)
            if isinstance(mod, IDModifier):
                self._scroll_ids[mod.value] = (origin, size)
            return
        if isinstance(view, _Frame):
            self._walk(view._content, origin, size)
            return
        if isinstance(view, NavigationStack):
            self._frames[id(view)] = (origin, size)
            header = 1 if view.header_visible else 0
            self._walk(
                view.content,
                Point(origin.x, origin.y + header),
                Size(size.width, max(0.0, size.height - header)),
            )
            return
        if isinstance(view, NavigationSplitView):
            self._walk_terminal_split(view, origin, size)
            return
        if isinstance(view, InspectorView):
            self._frames[id(view)] = (origin, size)
            main, panel = view.column_widths(size.width)
            self._walk(view.content, origin, Size(main, size.height))
            panel_x = origin.x if main == 0 else origin.x + main + 1
            self._walk(view.inspector_content, Point(panel_x, origin.y),
                       Size(panel, size.height))
            return
        if isinstance(view, Grid):
            self._walk_terminal_grid(view, origin, size)
            return
        if isinstance(view, LazyVGrid):
            self._walk_terminal_lazy_grid(view, origin, size)
            return
        if isinstance(view, LazyHGrid):
            self._walk_terminal_lazy_hgrid(view, origin, size)
            return
        if isinstance(view, (GridRow, LabeledContent)):
            self._walk_horizontal(view, origin, size,
                                  spacing=int(round(getattr(view, "_spacing", 1))))
            return
        if isinstance(view, (VStack, HStack)):
            self._walk_stack(view, origin, size)
            return
        if isinstance(view, ZStack):
            for child in view.children():
                self._walk(child, origin, size)
            return
        if isinstance(view, Form):
            self._walk_vertical(view, origin, size, spacing=int(round(view._spacing)))
            return
        if isinstance(view, ContentUnavailableView):
            self._walk_vertical(view, origin, size, spacing=1)
            return
        if isinstance(view, (ForEach, GroupBox)):
            self._walk_vertical(view, origin, size,
                                spacing=int(round(getattr(view, "_spacing", 0))))
            return
        if isinstance(view, Group):
            self._walk_vertical(view, origin, size, spacing=0)
            return
        if isinstance(view, Section):
            self._walk_vertical(view, origin, size, spacing=1)
            return
        if isinstance(view, DisclosureGroup):
            self._walk_vertical(view, origin, size, spacing=1)
            return
        if isinstance(view, ScrollView):
            self._walk(view.content, origin, size)
            return
        if isinstance(view, TabView):
            active = view.children()
            if active:
                self._walk(active[0], origin, size)
            return
        if isinstance(view, List):
            self._walk_list(view, origin, size)
            return
        if isinstance(view, Spacer):
            return
        if isinstance(view, _LEAF_TYPES):
            # The caller already measured this leaf with the correct container
            # width (see _char_size). Re-measuring here with ``size.width``
            # could wrap short text (e.g. a List row measured at full width)
            # into multiple lines, so trust the passed-in size.
            self._frames[id(view)] = (origin, Size(size.width, size.height))
            self._record_interactive(view, origin, Size(size.width, size.height))
            self._content_height = max(self._content_height, origin.y + size.height)
            return
        for child in view.children():
            self._walk(child, origin, size)

    def _unwrap(self, view: View) -> View:
        """Strip modifier wrappers to reach the leaf component."""
        while isinstance(view, (_ModifiedContent, _Frame)):
            if isinstance(view, _ModifiedContent):
                view = view.body()
            else:
                view = view._content
        return view

    def _walk_vertical(self, view: View, origin: Point, size: Size, spacing: int) -> None:
        children = view.children()
        sizes: list = []
        flexible = []  # Spacer and List absorb leftover vertical space.
        for i, child in enumerate(children):
            if isinstance(child, (Spacer, List)):
                sizes.append(None)
                flexible.append(i)
            else:
                sizes.append(self._char_size(child, size.width))
        fixed_h = sum(s[1] for s in sizes if s is not None)
        spacing_total = spacing * max(0, len(children) - 1)
        free = max(0.0, size.height - fixed_h - spacing_total)
        flex_h = (free / len(flexible)) if flexible else 0.0
        cursor = origin.y
        for i, child in enumerate(children):
            if sizes[i] is None:
                # Spacer / List: absorb the leftover space (List gets a viewport
                # at least one row tall so it still renders).
                sizes[i] = (int(size.width), max(1, int(flex_h)))
            cw, ch = sizes[i]
            self._walk(child, Point(origin.x, cursor), Size(max(1, cw), max(1, ch)))
            cursor += max(1, ch) + spacing
        self._content_height = max(self._content_height, cursor - origin.y)

    def _walk_stack(self, stack: View, origin: Point, size: Size) -> None:
        if isinstance(stack, VStack):
            self._walk_vertical(stack, origin, size, spacing=int(round(stack._spacing)))
        else:
            self._walk_horizontal(stack, origin, size, spacing=int(round(stack._spacing)))

    def _walk_horizontal(self, stack: View, origin: Point, size: Size, spacing: int) -> None:
        children = stack.children()
        sizes: list = []
        for child in children:
            if isinstance(child, Spacer):
                sizes.append(None)
            else:
                sizes.append(self._char_size(child, size.width))
        spacers = [i for i, s in enumerate(sizes) if s is None]
        fixed_w = sum(s[0] for s in sizes if s is not None)
        spacing_total = spacing * max(0, len(children) - 1)
        free = max(0.0, size.width - fixed_w - spacing_total)
        spacer_w = (free / len(spacers)) if spacers else 0.0
        cursor = origin.x
        for i, child in enumerate(children):
            if sizes[i] is None:
                sizes[i] = (max(0, int(spacer_w)), 1)
            cw, ch = sizes[i]
            self._walk(child, Point(cursor, origin.y), Size(max(1, cw), max(1, ch)))
            cursor += max(1, cw) + spacing

    def _walk_terminal_split(self, view: NavigationSplitView, origin: Point,
                             size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        widths = [int(value) for value in view.column_widths(size.width)]
        cursor = origin.x
        visible_count = 0
        for child, width in zip(view.children(), widths):
            if width <= 0:
                self._frames[id(child)] = (Point(cursor, origin.y), Size(0, size.height))
                continue
            if visible_count:
                cursor += 1
            self._walk(child, Point(cursor, origin.y), Size(width, size.height))
            cursor += width
            visible_count += 1
        self._content_height = max(self._content_height, origin.y + size.height)

    def _walk_terminal_grid(self, view: Grid, origin: Point, size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        rows = list(view.children())
        column_count = max((len(row.children()) for row in rows), default=1)
        cell_width = max(1, int(size.width) // column_count)
        y = origin.y
        for row in rows:
            self._frames[id(row)] = (Point(origin.x, y), Size(size.width, 1))
            for column, child in enumerate(row.children()):
                self._walk(child, Point(origin.x + column * cell_width, y),
                           Size(cell_width, 1))
            y += 1
        self._content_height = max(self._content_height, y)

    def _walk_terminal_lazy_grid(self, view: LazyVGrid, origin: Point,
                                 size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        widths = view.column_widths(size.width)
        count = max(1, len(widths))
        cell_width = max(1, int(size.width) // count)
        children = list(view.children())
        for index, child in enumerate(children):
            self._walk(child,
                       Point(origin.x + (index % count) * cell_width,
                             origin.y + index // count),
                       Size(cell_width, 1))
        rows = (len(children) + count - 1) // count
        self._content_height = max(self._content_height, origin.y + rows)

    def _walk_terminal_lazy_hgrid(self, view: LazyHGrid, origin: Point,
                                  size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        row_count = max(1, len(view.row_heights(size.height)))
        widths, _ = view.metrics(size)
        children = list(view.children())
        x = origin.x
        index = 0
        for width in widths:
            cell_width = max(1, int(round(width)))
            for row in range(row_count):
                if index >= len(children):
                    break
                self._walk(children[index], Point(x, origin.y + row),
                           Size(cell_width, 1))
                index += 1
            x += cell_width + max(0, int(round(view.column_spacing)))
        self._content_height = max(self._content_height,
                                   origin.y + min(row_count, int(size.height)))

    def _walk_list(self, view: List, origin: Point, size: Size) -> None:
        self._lists.append(view)
        self._frames[id(view)] = (origin, size)
        spacing = int(round(view._spacing))
        row_step = max(1, 1 + spacing)
        offset = view.current_offset()
        # The visible window is bounded by the actual viewport, not the layout
        # height (which is 100000 during interactive rendering).
        viewport_h = self._viewport_h if self._viewport_h > 0 else size.height
        count = max(1, int(max(1.0, viewport_h) // row_step) + 1)
        rows = view.rows[offset:offset + count]
        cursor = origin.y
        for row_index, row in enumerate(rows, start=offset):
            cs = self._char_size(row, size.width)
            start = len(self._interactives)
            self._walk(row, Point(origin.x, cursor), Size(cs[0], 1))
            added = self._interactives[start:]
            if not added:
                added = [_Interactive(row, Point(origin.x, cursor),
                                      Size(max(1, size.width), 1), "listrow")]
                self._interactives.extend(added)
            for item in added:
                item.owner_list = view
                item.owner_row = row_index
            cursor += row_step
        self._content_height = max(self._content_height, cursor - origin.y)

    def _record_interactive(self, view: View, origin: Point, size: Size) -> None:
        if not is_enabled(view):
            return
        if isinstance(view, Button):
            self._interactives.append(_Interactive(view, origin, size, "button", view.action))
        elif isinstance(view, Menu):
            self._interactives.append(_Interactive(view, origin, size, "menu"))
        elif isinstance(view, Table):
            self._interactives.append(_Interactive(view, origin, size, "table"))
        elif isinstance(view, TextField):
            self._interactives.append(_Interactive(view, origin, size, "textfield"))
        elif isinstance(view, SecureField):
            self._interactives.append(_Interactive(view, origin, size, "securefield"))
        elif isinstance(view, Toggle):
            self._interactives.append(_Interactive(view, origin, size, "toggle"))
        elif isinstance(view, Slider):
            self._interactives.append(_Interactive(view, origin, size, "slider"))
        elif isinstance(view, Picker):
            self._interactives.append(_Interactive(view, origin, size, "picker"))
        elif isinstance(view, Stepper):
            self._interactives.append(_Interactive(view, origin, size, "stepper"))
        elif isinstance(view, DatePicker):
            self._interactives.append(_Interactive(view, origin, size, "datepicker"))
        elif isinstance(view, ColorPicker):
            self._interactives.append(_Interactive(view, origin, size, "colorpicker"))
        elif isinstance(view, Link):
            self._interactives.append(_Interactive(view, origin, size, "link", view.action))

    # -- Rendering ----------------------------------------------------------
    def _render(self) -> None:
        stdscr = self._stdscr
        h, w = stdscr.getmaxyx()
        viewport_h = max(1, h - 1)  # reserve the status line
        self._viewport_h = viewport_h
        view = self._make_view()
        self._view = view
        self._layout(view, w, 100000)
        self._apply_scroll_configuration(view, viewport_h)

        # Clamp global scroll to the content extent.
        max_scroll = max(0, int(self._content_height) - viewport_h)
        self._scroll_y = max(0, min(self._scroll_y, float(max_scroll)))
        self._ensure_focus_visible(viewport_h)

        stdscr.erase()
        self._sink = stdscr
        self._draw(view, stdscr, Point(0, 0), Size(w, viewport_h), scroll_y=self._scroll_y)
        self._draw_status(stdscr, viewport_h, w)
        stdscr.refresh()

    def _apply_scroll_configuration(self, view: View, viewport_h: int) -> None:
        configuration = find_scroll_configuration(view)
        if configuration is None:
            return
        target = configuration.position.wrapped_value if configuration.position is not None else None
        if target is not None:
            self._viewport_h = viewport_h
            self._scroll_to_id(target, configuration.position_anchor)
            return
        if self._did_apply_default_scroll or configuration.default_anchor == "top":
            return
        maximum = max(0.0, self._content_height - viewport_h)
        self._scroll_y = maximum / 2.0 if configuration.default_anchor == "center" else maximum
        self._did_apply_default_scroll = True

    def _draw_status(self, stdscr, viewport_h: int, width: int) -> None:
        total = int(self._content_height)
        shown = f" h:help"
        scroll = f" scroll {int(self._scroll_y)}/{max(0, total - viewport_h)}"
        status = self._status or f"{shown}{scroll} · q:quit"
        try:
            stdscr.addstr(viewport_h, 0, status[: max(0, width - 1)])
        except curses.error:
            pass

    def _emit(self, x: int, y: int, text: str, pair: int = 0, attr: int = 0) -> None:
        """Write text to the active sink (terminal screen or test grid)."""
        if x < 0 or y < 0:
            return
        if isinstance(self._sink, TerminalGrid):
            self._sink.put(x, y, text)
            return
        try:
            self._sink.addstr(y, x, text, curses.color_pair(pair) | attr)
        except curses.error:
            pass  # Out of bounds: silently clip.

    def _draw(self, view: View, sink, origin: Point, size: Size, scroll_y: float = 0.0) -> None:
        # Keep the active sink in sync with the caller (terminal or grid).
        self._sink = sink
        if isinstance(view, EnvironmentReader):
            self._draw(view.content, sink, origin, size, scroll_y)
            return
        if isinstance(view, OutlineGroup):
            self._draw(view.content_view(), sink, origin, size, scroll_y)
            return
        if isinstance(view, GeometryReader):
            frame = self._frames.get(id(view), (origin, size))
            self._draw(view.resolve(*frame), sink, origin, size, scroll_y)
            return
        if isinstance(view, LayoutContainer):
            for _, child in z_ordered(view.children()):
                self._draw(child, sink, origin, size, scroll_y)
            return
        if isinstance(view, ScrollViewReader):
            self._draw(view.content, sink, origin, size, scroll_y)
            return
        if isinstance(view, EmptyView):
            return
        if isinstance(view, AnyView):
            self._draw(view.content, sink, origin, size, scroll_y)
            return
        if isinstance(view, ViewThatFits):
            frame = self._frames.get(id(view), (origin, size))
            self._draw(view.selected(frame[1]), sink, origin, size, scroll_y)
            return
        if isinstance(view, _ModifiedContent):
            self._draw(view.body(), sink, origin, size, scroll_y)
            if isinstance(view._modifier, OverlayModifier):
                self._draw(view._modifier.overlay, sink, origin, size, scroll_y)
            if isinstance(view._modifier, BadgeModifier):
                frame = self._frames.get(id(view), (origin, size))
                text = f"[{view._modifier.value}]"
                self._emit(int(frame[0].x + max(0, frame[1].width - len(text))),
                           int(frame[0].y - scroll_y), text,
                           self._pair(curses.COLOR_WHITE, curses.COLOR_BLUE), curses.A_BOLD)
            return
        if isinstance(view, _Frame):
            self._draw(view._content, sink, origin, size, scroll_y)
            return

        frame = self._frames.get(id(view))
        if frame is None:
            for child in view.children():
                self._draw(child, sink, origin, size, scroll_y)
            return

        pos, fsize = frame
        x = int(round(pos.x))
        y = int(round(pos.y)) - int(scroll_y)
        fw = int(round(fsize.width))
        fh = int(round(fsize.height))
        if y + fh <= 0 or y >= size.height:
            return  # Fully clipped out of the viewport.

        if isinstance(view, (PhaseAnimator, KeyframeAnimator, TimelineView)):
            self._draw(view.content, sink, origin, size, scroll_y)
            return

        if isinstance(view, NavigationStack):
            self._draw_header(view, x, y, fw, sink)
            for child in view.children():
                self._draw(child, sink, origin, size, scroll_y)
            return
        if isinstance(view, NavigationSplitView):
            widths = []
            children = list(view.children())
            for child in children:
                child_frame = self._frames.get(id(child))
                widths.append(int(child_frame[1].width) if child_frame else 0)
            cursor = x
            for index, child in enumerate(children):
                self._draw(child, sink, origin, size, scroll_y)
                cursor += widths[index]
                if index < len(children) - 1:
                    for yy in range(max(0, y), min(int(size.height), y + max(1, fh))):
                        self._emit(cursor, yy, "│", self._pair(
                            curses.COLOR_WHITE, curses.COLOR_BLACK), curses.A_DIM)
                    cursor += 1
            return
        if isinstance(view, List):
            # Only rows that were laid out (the visible window) have frames.
            for child in view.children():
                if id(child) in self._frames:
                    self._draw(child, sink, origin, size, scroll_y)
            return

        self._draw_leaf(view, x, y, fw, fh, sink)

    def _draw_header(self, view: NavigationStack, x: int, y: int, fw: int, sink) -> None:
        if not view.header_visible:
            return
        title = f"== {view.title} =="
        self._emit(x, y, title[: fw], self._pair(curses.COLOR_WHITE, curses.COLOR_BLUE), curses.A_BOLD)

    # -- Leaf drawing -------------------------------------------------------
    def _draw_leaf(self, view: View, x: int, y: int, fw: int, fh: int, sink) -> None:
        focused = self._is_focused(view)
        if isinstance(view, Text):
            self._draw_text(view, x, y, fw, fh)
            return
        if isinstance(view, Canvas):
            count = len(view.resolve(Size(fw, fh)).commands)
            self._emit(x, y, f"(canvas {count} commands)"[:fw],
                       self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK))
            return
        if isinstance(view, Button):
            self._draw_button(view, x, y, fw, focused)
            return
        if isinstance(view, Menu):
            selected = view.selected_item.title if view.selected_item else ""
            attr = curses.A_REVERSE if focused else (curses.A_DIM if not is_enabled(view) else 0)
            self._emit(x, y, f"[ {view.title} ▾ {selected} ]"[:fw],
                       self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK), attr)
            return
        if isinstance(view, Table):
            self._draw_table(view, x, y, fw, fh, focused)
            return
        if isinstance(view, TextEditor):
            self._draw_texteditor(view, x, y, fw, fh, focused)
            return
        if isinstance(view, SearchField):
            self._draw_searchfield(view, x, y, fw, focused)
            return
        if isinstance(view, TextField):
            self._draw_textfield(view, x, y, fw, focused)
            return
        if isinstance(view, SecureField):
            self._draw_securefield(view, x, y, fw, focused)
            return
        if isinstance(view, Toggle):
            self._draw_toggle(view, x, y, fw, focused)
            return
        if isinstance(view, Slider):
            self._draw_slider(view, x, y, fw, focused)
            return
        if isinstance(view, Picker):
            self._draw_picker(view, x, y, fw, focused)
            return
        if isinstance(view, Stepper):
            self._draw_stepper(view, x, y, fw, focused)
            return
        if isinstance(view, DatePicker):
            self._draw_datepicker(view, x, y, fw, focused)
            return
        if isinstance(view, ColorPicker):
            self._draw_colorpicker(view, x, y, fw, focused)
            return
        if isinstance(view, Label):
            self._draw_label(view, x, y, fw)
            return
        if isinstance(view, Link):
            attr = curses.A_UNDERLINE | (curses.A_REVERSE if focused else 0)
            self._emit(x, y, (view.title + " ↗")[:fw],
                       self._pair(curses.COLOR_BLUE, curses.COLOR_BLACK), attr)
            return
        if isinstance(view, ProgressView):
            self._draw_progress(view, x, y, fw)
            return
        if isinstance(view, Divider):
            self._emit(x, y, "─" * max(0, fw), self._pair(curses.COLOR_BLUE, curses.COLOR_BLACK), curses.A_DIM)
            return
        if isinstance(view, AsyncImage):
            marker = "loading" if view.phase.is_empty else (
                "image" if view.phase.is_success else "image failed"
            )
            self._emit(x, y, f"({marker})"[:fw], self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK))
            return
        if isinstance(view, Image):
            variable = (f" {view.variable_value:.0%}"
                        if view.variable_value is not None else "")
            self._emit(x, y, f"(img {view.resolved_system_name}{variable})"[: fw], self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK))
            return
        if isinstance(view, Shape):
            symbol = "◔" if view.trim_range != (0.0, 1.0) else (
                "◩" if isinstance(view, UnevenRoundedRectangle) else (
                "⬭" if isinstance(view, Ellipse) else (
                "▰" if isinstance(view, Capsule) else (
                "○" if isinstance(view, Circle) else (
                "▢" if isinstance(view, RoundedRectangle) else "□"
            )))))
            self._emit(x, y, symbol, self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK))
            return
        if isinstance(view, Gradient):
            text = "◉ angular" if isinstance(view, AngularGradient) else (
                "⬭ elliptical" if isinstance(view, EllipticalGradient) else (
                "⇢ gradient" if isinstance(view, LinearGradient) else "◎ gradient"))
            self._emit(x, y, text[:fw], self._pair(curses.COLOR_MAGENTA, curses.COLOR_BLACK))
            return

    def _draw_text(self, view: Text, x: int, y: int, fw: int, fh: int) -> None:
        # Add a small tolerance to the proposal so text that exactly fills the
        # row is not split by floating-point rounding in Text._wrap_line.
        lines = view._layout_lines(self._text_proposal_width(view, fw) + 0.5)
        pair, attr = self._text_style(view)
        for i in range(min(max(1, fh), len(lines))):
            self._emit(x, y + i, lines[i][:fw], pair, attr)

    def _text_style(self, view: Text) -> Tuple[int, int]:
        color = getattr(view, "_color", None)
        attr = 0
        pair = self._pair(curses.COLOR_WHITE, curses.COLOR_BLACK)
        if color is not None:
            fg = self._curses_color(color)
            pair = self._pair(fg, curses.COLOR_BLACK)
            if fg in (curses.COLOR_BLACK, curses.COLOR_BLUE, curses.COLOR_MAGENTA):
                attr = curses.A_BOLD
        return pair, attr

    def _curses_color(self, color: Color) -> int:
        """Map an aUI Color to the nearest curses colour constant."""
        r, g, b = color.red, color.green, color.blue
        if r > 0.8 and g > 0.8 and b > 0.8:
            return curses.COLOR_WHITE
        if r < 0.2 and g < 0.2 and b < 0.2:
            return curses.COLOR_BLACK
        if r > 0.8 and g < 0.4 and b < 0.4:
            return curses.COLOR_RED
        if r < 0.4 and g > 0.8 and b < 0.4:
            return curses.COLOR_GREEN
        if r > 0.8 and g > 0.8 and b < 0.4:
            return curses.COLOR_YELLOW
        if r < 0.4 and g < 0.5 and b > 0.8:
            return curses.COLOR_BLUE
        if r > 0.8 and g < 0.5 and b > 0.8:
            return curses.COLOR_MAGENTA
        if r < 0.6 and g > 0.6 and b > 0.6:
            return curses.COLOR_CYAN
        return curses.COLOR_WHITE

    def _draw_button(self, view: Button, x: int, y: int, fw: int, focused: bool) -> None:
        style = style_value(view, "button_style", ButtonStyle.AUTOMATIC)
        label = view.title if style in (ButtonStyle.PLAIN, ButtonStyle.BORDERLESS, ButtonStyle.LINK) else f"[ {view.title} ]"
        if not is_enabled(view):
            fg, bg = curses.COLOR_BLACK, curses.COLOR_WHITE
            attr = curses.A_DIM
        else:
            fg, bg = ((curses.COLOR_WHITE, curses.COLOR_RED)
                      if view.role == "destructive" else
                      ((curses.COLOR_BLACK, curses.COLOR_WHITE)
                       if view.role == "cancel" else
                       (curses.COLOR_WHITE, curses.COLOR_BLUE)))
            attr = curses.A_BOLD
            if focused:
                attr |= curses.A_REVERSE
        pair = self._pair(fg, bg)
        self._emit(x, y, label[:fw], pair, attr)

    def _draw_securefield(self, view: SecureField, x: int, y: int, fw: int, focused: bool) -> None:
        val = view.text.wrapped_value if view.text else ""
        hidden = "*" * len(val or "")
        shown = (hidden if hidden else view.placeholder)[: max(0, fw - 2)]
        if not is_enabled(view):
            attr = curses.A_DIM
        elif focused:
            attr = curses.A_REVERSE
        else:
            attr = 0
        pair = self._pair(curses.COLOR_WHITE, curses.COLOR_BLACK)
        self._emit(x, y, "[" + shown + "]", pair, attr)

    def _draw_colorpicker(self, view: ColorPicker, x: int, y: int, fw: int, focused: bool) -> None:
        col = view.selection.wrapped_value if view.selection else None
        hexs = col.to_tk() if col else "??????"
        shown = f"[ {view.title} {hexs} ]"
        if not is_enabled(view):
            attr = curses.A_DIM
        elif focused:
            attr = curses.A_REVERSE
        else:
            attr = 0
        pair = self._pair(curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        self._emit(x, y, shown[: fw], pair, attr)

    def _draw_label(self, view: Label, x: int, y: int, fw: int) -> None:
        style = style_value(view, "label_style", LabelStyle.AUTOMATIC)
        text = view.system_name if style == LabelStyle.ICON_ONLY else view.title
        if style in (LabelStyle.AUTOMATIC, LabelStyle.TITLE_AND_ICON) and view.system_name:
            text = f"* {text}"
        self._emit(x, y, text[: fw], self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK))

    def _draw_textfield(self, view: TextField, x: int, y: int, fw: int, focused: bool) -> None:
        val = view.text.wrapped_value if view.text else ""
        shown = (val if val else view.placeholder)[: max(0, fw - 2)]
        if not is_enabled(view):
            attr = curses.A_DIM
        elif focused:
            attr = curses.A_REVERSE
        else:
            attr = 0
        pair = self._pair(curses.COLOR_WHITE, curses.COLOR_BLACK)
        self._emit(x, y, "[" + shown + "]", pair, attr)

    def _draw_table(self, view: Table, x: int, y: int, fw: int, fh: int,
                    focused: bool) -> None:
        columns = view.visible_columns
        if not view.displayed_rows:
            self._emit(x, y, view.empty_message[:fw],
                       self._pair(curses.COLOR_WHITE, curses.COLOR_BLACK), curses.A_DIM)
            return
        count = len(columns)
        cell_width = max(4, (fw - max(0, count - 1)) // max(1, count))
        header = "│".join(column.title[:cell_width].ljust(cell_width)
                          for column in columns)
        self._emit(x, y, header[:fw], self._pair(curses.COLOR_WHITE, curses.COLOR_BLACK),
                   curses.A_BOLD)
        if fh > 1:
            self._emit(x, y + 1, "─" * fw,
                       self._pair(curses.COLOR_WHITE, curses.COLOR_BLACK), curses.A_DIM)
        for offset, row in enumerate(view.displayed_rows[: max(0, fh - 2)]):
            text = "│".join(str(column.get_value(row))[:cell_width].ljust(cell_width)
                            for column in columns)
            attr = curses.A_REVERSE if focused and offset == view.cursor_index else 0
            self._emit(x, y + 2 + offset, text[:fw],
                       self._pair(curses.COLOR_WHITE, curses.COLOR_BLACK), attr)

    def _draw_searchfield(self, view: SearchField, x: int, y: int, fw: int,
                          focused: bool) -> None:
        value = view.text.wrapped_value or view.placeholder
        attr = curses.A_REVERSE if focused else (curses.A_DIM if not is_enabled(view) else 0)
        self._emit(x, y, ("[? " + value + "]")[:fw],
                   self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK), attr)

    def _draw_texteditor(self, view: TextEditor, x: int, y: int, fw: int,
                         fh: int, focused: bool) -> None:
        lines = (view.text.wrapped_value or view.placeholder).splitlines() or [""]
        attr = curses.A_REVERSE if focused else (curses.A_DIM if not is_enabled(view) else 0)
        for offset in range(max(1, fh)):
            content = lines[offset] if offset < len(lines) else ""
            self._emit(x, y + offset, ("│ " + content)[:fw],
                       self._pair(curses.COLOR_WHITE, curses.COLOR_BLACK), attr)

    def _draw_toggle(self, view: Toggle, x: int, y: int, fw: int, focused: bool) -> None:
        on = bool(view.is_on and view.is_on.wrapped_value)
        mark = "[x]" if on else "[ ]"
        if not is_enabled(view):
            attr = curses.A_DIM
        elif focused:
            attr = curses.A_REVERSE
        else:
            attr = 0
        pair = self._pair(curses.COLOR_GREEN if on else curses.COLOR_WHITE, curses.COLOR_BLACK)
        self._emit(x, y, f"{mark} {view.title}"[: fw], pair, attr)

    def _draw_slider(self, view: Slider, x: int, y: int, fw: int, focused: bool) -> None:
        lo, hi = view.range
        cur = view.value.wrapped_value if view.value else lo
        span = max(0.0, hi - lo)
        ratio = 0.0 if span == 0 else (cur - lo) / span
        total = max(1, fw - 2)
        posn = int(round(ratio * (total - 1)))
        bar = "-" * posn + "o" + "-" * (total - posn - 1)
        if not is_enabled(view):
            attr = curses.A_DIM
        elif focused:
            attr = curses.A_REVERSE
        else:
            attr = 0
        pair = self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK)
        self._emit(x, y, "[" + bar + "]", pair, attr)

    def _draw_picker(self, view: Picker, x: int, y: int, fw: int, focused: bool) -> None:
        sel = view.selection.wrapped_value if view.selection else None
        shown = f"< {view.title}: {sel} >"
        if not is_enabled(view):
            attr = curses.A_DIM
        elif focused:
            attr = curses.A_REVERSE
        else:
            attr = 0
        pair = self._pair(curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        self._emit(x, y, shown[: fw], pair, attr)

    def _draw_stepper(self, view: Stepper, x: int, y: int, fw: int, focused: bool) -> None:
        val = view.value.wrapped_value if view.value else 0
        shown = f"[- {view.title} {val} +]"
        if not is_enabled(view):
            attr = curses.A_DIM
        elif focused:
            attr = curses.A_REVERSE
        else:
            attr = 0
        pair = self._pair(curses.COLOR_YELLOW, curses.COLOR_BLACK)
        self._emit(x, y, shown[: fw], pair, attr)

    def _draw_datepicker(self, view: DatePicker, x: int, y: int, fw: int, focused: bool) -> None:
        shown = f"[ {view.title} {view._current()} ]"
        if not is_enabled(view):
            attr = curses.A_DIM
        elif focused:
            attr = curses.A_REVERSE
        else:
            attr = 0
        pair = self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK)
        self._emit(x, y, shown[: fw], pair, attr)

    def _draw_progress(self, view: ProgressView, x: int, y: int, fw: int) -> None:
        total = max(1, fw - 2)
        if view.value is None:
            self._emit(x, y, "[" + "?" * total + "]", self._pair(curses.COLOR_CYAN, curses.COLOR_BLACK))
            return
        ratio = max(0.0, min(1.0, float(view.value)))
        filled = int(round(ratio * total))
        bar = "#" * filled + "-" * (total - filled)
        self._emit(x, y, "[" + bar + "]", self._pair(curses.COLOR_GREEN, curses.COLOR_BLACK))

    # -- Focus helpers ------------------------------------------------------
    def _is_focused(self, view: View) -> bool:
        if not (0 <= self._focus_index < len(self._interactives)):
            return False
        return self._interactives[self._focus_index].view is view

    def _current_item(self) -> Optional[_Interactive]:
        if not self._interactives:
            return None
        idx = max(0, min(self._focus_index, len(self._interactives) - 1))
        return self._interactives[idx]

    def _move_focus(self, delta: int) -> None:
        if not self._interactives:
            return
        n = len(self._interactives)
        previous = self._current_item()
        if previous is not None:
            modifier = self._focus_bindings.get(id(previous.view))
            if modifier is not None:
                modifier.deactivate()
        self._focus_index = (self._focus_index + delta) % n
        item = self._interactives[self._focus_index]
        modifier = self._focus_bindings.get(id(item.view))
        if modifier is not None:
            modifier.activate()
        kind = type(item.view).__name__
        self._status = f" focus: {kind} ({item.origin.x}, {item.origin.y}) — Enter 激活 · q 退出"

    def _ensure_focus_visible(self, viewport_h: int) -> None:
        item = self._current_item()
        if item is None:
            return
        top = item.origin.y - self._scroll_y
        bottom = item.origin.y + item.size.height - self._scroll_y
        if top < 0:
            self._scroll_y += top
        elif bottom > viewport_h:
            self._scroll_y += bottom - viewport_h

    # -- Event handling -----------------------------------------------------
    def _handle_key(self, key: int) -> None:
        if self._dispatch_key_press(key):
            return
        if key == ord("\t"):
            self._move_focus(1)
        elif key == curses.KEY_BTAB:
            self._move_focus(-1)
        elif key in (curses.KEY_DOWN, ord("j")):
            self._move_focus(1)
        elif key in (curses.KEY_UP, ord("k")):
            self._move_focus(-1)
        elif key in (curses.KEY_ENTER, 10, 13, ord(" ")):
            self._activate()
        elif key == ord("D"):
            self._delete_list_row()
        elif key == ord("K"):
            self._move_list_row(-1)
        elif key == ord("J"):
            self._move_list_row(1)
        elif key == curses.KEY_LEFT:
            self._adjust(-1)
        elif key == curses.KEY_RIGHT:
            self._adjust(1)
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self._edit_backspace()
        elif key == 27:  # Escape: navigate back when hosted in a NavigationStack.
            self._navigate_back()
        elif key in (curses.KEY_PPAGE, ord("[")):
            self._scroll_page(-1)
        elif key in (curses.KEY_NPAGE, ord("]")):
            self._scroll_page(1)
        elif key in (ord("h"), ord("H")):
            self._status = " Tab/↑↓:焦点 · Enter:激活 · ←→:调整 · 打字:编辑 · PgUp/PgDn:滚动 · q:退出"
        elif 32 <= key < 127:
            self._edit_typed(chr(key))

    def _dispatch_key_press(self, key: int) -> bool:
        names = {27: "escape", curses.KEY_ENTER: "return", 10: "return", 13: "return",
                 curses.KEY_UP: "upArrow", curses.KEY_DOWN: "downArrow",
                 curses.KEY_LEFT: "leftArrow", curses.KEY_RIGHT: "rightArrow"}
        value = names.get(key, chr(key) if 0 <= key < 256 else str(key))
        event = KeyPress(value)
        for modifier in reversed(self._key_handlers):
            if modifier.dispatch(event) is KeyPressResult.HANDLED:
                return True
        for shortcut, view in reversed(self._keyboard_shortcuts):
            expected = {"\r": "return", "\x1b": "escape"}.get(shortcut.key, shortcut.key)
            if not shortcut.modifiers and expected == value:
                action = getattr(view, "action", None)
                if callable(action) and is_enabled(view):
                    action()
                    return True
        return False

    def _scroll_page(self, delta: int) -> None:
        item = self._current_item()
        if item is not None and item.owner_list is not None:
            lst = item.owner_list
            lst.scroll_to(lst.current_offset() + delta * 5)
            self._status = f" list scroll: offset {lst.current_offset()}"
            return
        page = max(3, self._viewport_h // 2)
        self._scroll_y += delta * page
        self._scroll_y = max(0.0, self._scroll_y)
        self._status = f" scroll: {int(self._scroll_y)}"

    def _scroll_to_id(self, view_id, anchor: str = "top") -> None:
        frame = self._scroll_ids.get(view_id)
        if frame is None:
            return
        point, size = frame
        viewport = max(1, self._viewport_h)
        if anchor == "center":
            target = point.y - (viewport - size.height) / 2.0
        elif anchor == "bottom":
            target = point.y - viewport + size.height
        else:
            target = point.y
        self._scroll_y = max(0.0, min(target, max(0.0, self._content_height - viewport)))
        self._status = f" scroll to: {view_id}"

    def _navigate_back(self) -> None:
        if self._view is None:
            return
        stack = self._view.find(lambda item: isinstance(item, NavigationStack))
        if isinstance(stack, NavigationStack) and len(stack.path):
            stack.go_back()
            self._status = " navigation: back"

    def _activate(self) -> None:
        item = self._current_item()
        if item is None:
            return
        view = item.view
        if not is_enabled(view):
            self._status = f" disabled: {getattr(view, 'title', type(view).__name__)}"
            return
        if item.owner_list is not None and item.owner_row is not None:
            item.owner_list.select_row(item.owner_row,
                                       extending=item.owner_list.allows_multiple_selection)
            if item.kind == "listrow":
                self._status = f" list row: {item.owner_row + 1}"
                return
        if item.kind in ("textfield", "securefield"):
            modifier = self._submit_bindings.get(id(view))
            if modifier is not None:
                modifier.action()
                label = self._submit_labels.get(id(view))
                self._status = f" submitted: {label.label if label else 'return'}"
            return
        if item.kind == "tap":
            if item.action is not None:
                item.action()
                self._status = f" tapped: {type(view).__name__}"
            elif isinstance(view, Toggle) and view.is_on is not None:
                view.is_on.wrapped_value = not view.is_on.wrapped_value
                self._status = f" toggled: {view.title}"
        elif item.kind == "button":
            view.action()
            self._status = f" activated: {view.title}"
        elif item.kind == "toggle":
            if view.is_on is not None:
                view.is_on.wrapped_value = not view.is_on.wrapped_value
                self._status = f" toggled: {view.title}"
        elif item.kind == "link":
            if item.action is not None:
                item.action()
                self._status = f" opened: {view.title}"
            else:
                self._status = f" link: {view.url}"
        elif item.kind == "menu":
            view.activate_selected()
            if view.selected_item is not None:
                self._status = f" menu: {view.selected_item.title}"
        elif item.kind == "table":
            view.select_row(view.cursor_index)
            self._status = f" table row: {view.cursor_index + 1}"

    def _delete_list_row(self) -> None:
        item = self._current_item()
        if item is None or item.owner_list is None or item.owner_row is None:
            return
        if not item.owner_list.is_editing:
            self._status = " list editing is inactive"
            return
        removed = item.owner_list.delete_rows((item.owner_row,))
        self._status = " list row deleted" if removed else " row deletion disabled"

    def _move_list_row(self, delta: int) -> None:
        item = self._current_item()
        if item is None or item.owner_list is None or item.owner_row is None:
            return
        if not item.owner_list.is_editing:
            self._status = " list editing is inactive"
            return
        source = item.owner_row
        destination = source + (2 if delta > 0 else -1)
        before = tuple(item.owner_list.rows)
        item.owner_list.move_rows((source,), destination)
        self._status = " list row moved" if tuple(item.owner_list.rows) != before else " row move disabled"

    @staticmethod
    def _action_key(action) -> tuple:
        code = getattr(action, "__code__", None)
        return (
            getattr(action, "__module__", ""),
            getattr(action, "__qualname__", repr(action)),
            getattr(code, "co_firstlineno", None),
        )

    def _adjust(self, delta: int) -> None:
        item = self._current_item()
        if item is None:
            return
        view = item.view
        if item.kind == "slider" and view.value is not None:
            lo, hi = view.range
            step = view.step if view.step and view.step > 0 else (hi - lo) / 20.0
            cur = view.value.wrapped_value
            view.value.wrapped_value = max(lo, min(hi, cur + delta * step))
            self._status = f" slider: {view.value.wrapped_value:.2f}"
        elif item.kind == "picker" and view.selection is not None and view.options:
            opts = view.options
            cur = view.selection.wrapped_value
            idx = opts.index(cur) if cur in opts else 0
            view.selection.wrapped_value = opts[(idx + delta) % len(opts)]
            self._status = f" picker: {view.selection.wrapped_value}"
        elif item.kind == "stepper":
            view.increment() if delta > 0 else view.decrement()
            self._status = f" stepper: {view.value.wrapped_value if view.value else ''}"
        elif item.kind == "datepicker" and view.selection is not None:
            cur = view.selection.wrapped_value
            if isinstance(cur, datetime):
                view.selection.wrapped_value = cur + timedelta(days=delta)
                self._status = f" date: {view._current()}"
        elif item.kind == "colorpicker" and view.selection is not None:
            from ..core.geometry import Color
            base = [Color.red, Color.blue, Color.green, Color.orange, Color.purple, Color.teal]
            cur = view.selection.wrapped_value
            idx = base.index(cur) if cur in base else 0
            view.selection.wrapped_value = base[(idx + delta) % len(base)]
            self._status = f" color: {view.selection.wrapped_value.to_tk()}"
        elif item.kind == "menu":
            view.move_selection(delta)
            if view.selected_item is not None:
                self._status = f" menu: {view.selected_item.title}"
        elif item.kind == "table":
            view.move_selection(delta)
            self._status = f" table row: {view.cursor_index + 1}"

    def _edit_typed(self, ch: str) -> None:
        item = self._current_item()
        if item is None or item.kind not in ("textfield", "securefield"):
            return
        if not getattr(item.view, "enabled", True):
            return
        b = item.view.text
        b.wrapped_value = (b.wrapped_value or "") + ch
        self._status = f" value: {'*' * len(b.wrapped_value) if item.kind == 'securefield' else b.wrapped_value}"

    def _edit_backspace(self) -> None:
        item = self._current_item()
        if item is None or item.kind not in ("textfield", "securefield"):
            return
        if not getattr(item.view, "enabled", True):
            return
        b = item.view.text
        b.wrapped_value = (b.wrapped_value or "")[:-1]
        self._status = f" value: {'*' * len(b.wrapped_value) if item.kind == 'securefield' else b.wrapped_value}"
