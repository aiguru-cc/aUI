"""Curses terminal backend for aUI.

Renders the declarative aUI view tree onto an interactive terminal using the
standard-library ``curses`` module. No third-party dependencies and no display
server required.

The backend reuses the pure-Python layout engine (``size_that_fits`` /
``place``) from ``aui.core`` and records the final frame of every component
during layout, then draws them onto a character grid and runs a keyboard event
loop that dispatches to buttons and tap gestures.
"""
from __future__ import annotations

import curses
from typing import Callable, Dict, List as TList, Optional, Tuple

from ..core.components import (
    Button,
    DatePicker,
    Divider,
    Form,
    Image,
    List,
    NavigationStack,
    Picker,
    ProgressView,
    Slider,
    Stepper,
    Text,
    TextField,
    Toggle,
)
from ..core.accessibility import AccessibilityInfo, describe_accessibility as _describe_accessibility
from ..core.geometry import Color, EdgeInsets, Font, Point, Size
from ..core.layout import HStack, Spacer, VStack, ZStack
from ..core.modifiers import TapGestureModifier
from ..core.view import View, _Frame, _ModifiedContent


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

    def __init__(self, view_factory: Callable[[], View]):
        self._view_factory = view_factory
        self._view: Optional[View] = None
        self._frames: Dict[int, Tuple[Point, Size]] = {}
        self._buttons: TList[Tuple[Button, Point, Size]] = []
        self._taps: TList[Tuple[View, Point, Size, Optional[Callable]]] = []
        self._focused: Optional[TextField] = None
        self._focus_index = 0
        self._tap_index = 0
        self._textfields: TList[TextField] = []
        self._lists: TList[List] = []
        self._status = ""

    # -- Public API ---------------------------------------------------------
    def run(self) -> None:
        """Enter the curses main loop (blocking)."""
        curses.wrapper(self._main)

    def render_to_string(self, width: int = 80, height: int = 20) -> str:
        """Render the current view to a string without a terminal.

        Useful for testing and headless previews.
        """
        view = self._view_factory()
        self._layout(view, width, height)
        grid = TerminalGrid(width, height)
        self._draw(view, grid, Point(0, 0), Size(width, height))
        return grid.snapshot()

    def describe_accessibility(self) -> AccessibilityInfo:
        """Return the accessibility tree of the current view.

        Exposes the aUI accessibility tree (roles / labels / hints /
        values) for assistive technology and terminal screen readers.
        """
        return _describe_accessibility(self._view_factory())

    def _main(self, stdscr) -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass  # Terminal may not support hiding the cursor.
        stdscr.keypad(True)
        self._stdscr = stdscr
        while True:
            self._render()
            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                break
            self._handle_key(key)

    # -- Layout -------------------------------------------------------------
    def _layout(self, view: View, width: int, height: int) -> None:
        """Lay out the view tree and record frames for every component."""
        self._frames = {}
        self._buttons = []
        self._taps = []
        self._textfields = []
        self._lists = []
        self._walk(view, Point(0, 0), Size(width, height))

    def _walk(self, view: View, origin: Point, size: Size) -> None:
        # Record the frame of leaf components.
        if isinstance(
            view,
            (Button, TextField, Toggle, Slider, Picker, Divider, Image, Text, Stepper, ProgressView, DatePicker),
        ):
            self._frames[id(view)] = (origin, size)
            if isinstance(view, Button):
                self._buttons.append((view, origin, size))
            elif isinstance(view, TextField):
                self._textfields.append(view)
            elif isinstance(view, Toggle):
                self._taps.append((view, origin, size, None))
            return

        if isinstance(view, _ModifiedContent):
            if isinstance(view._modifier, TapGestureModifier):
                # Record a tappable region for the wrapped content.
                inner = view.body()
                if isinstance(inner, (Button, TextField, Toggle, Slider, Picker,
                                      Divider, Image, Text, Stepper, ProgressView, DatePicker)):
                    self._frames[id(inner)] = (origin, size)
                    self._taps.append((inner, origin, size, view._modifier.action))
            self._walk(view.body(), origin, size)
            return
        if isinstance(view, _Frame):
            self._walk(view._content, origin, size)
            return

        if isinstance(view, NavigationStack):
            # Record a frame so the header can be drawn at the right position.
            self._frames[id(view)] = (origin, size)
            self._walk(view.content, Point(origin.x, origin.y + 1), Size(size.width, max(0.0, size.height - 1)))
            return

        if isinstance(view, VStack):
            self._walk_stack(view, origin, size, vertical=True)
        elif isinstance(view, HStack):
            self._walk_stack(view, origin, size, vertical=False)
        elif isinstance(view, ZStack):
            for child in view.children():
                self._walk(child, origin, size)
        elif isinstance(view, Spacer):
            return
        elif isinstance(view, Form):
            cursor = origin.y
            for child in view.children():
                child_size = Size(size.width, 1.0)
                self._walk(child, Point(origin.x, cursor), child_size)
                cursor += child_size.height + view._spacing
        elif isinstance(view, List):
            self._lists.append(view)
            # Lazy: only lay out the visible viewport (ADR-0008).
            cursor = origin.y
            for row in view.visible_rows(size.height, size.width):
                row_size = Size(size.width, 1.0)
                self._walk(row, Point(origin.x, cursor), row_size)
                cursor += row_size.height + view._spacing
        else:
            for child in view.children():
                self._walk(child, origin, size)

    def _walk_stack(self, stack, origin: Point, size: Size, vertical: bool) -> None:
        children = stack.children()
        if not children:
            return
        # Measure children along the main axis.
        main_attr = "height" if vertical else "width"
        cross_attr = "width" if vertical else "height"
        cross = getattr(size, cross_attr)
        sizes = []
        for child in children:
            if isinstance(child, Spacer):
                sizes.append(Size())
                continue
            if vertical:
                # Vertical stack: child fills container width, single row.
                sizes.append(Size(cross, 1.0))
            else:
                # Horizontal stack: child keeps content width, single row.
                child_size = child.size_that_fits(Size(float("inf"), 1.0))
                sizes.append(Size(child_size.width, 1.0))

        spacers = [i for i, c in enumerate(children) if isinstance(c, Spacer)]
        spacing = stack._spacing * max(0, len(children) - 1)
        fixed = sum(getattr(s, main_attr) for i, s in enumerate(sizes) if i not in spacers)
        free = max(0.0, getattr(size, main_attr) - fixed - spacing)
        spacer_main = free / len(spacers) if spacers else 0.0

        cursor = 0.0
        # For horizontal stacks, if children overflow the container width,
        # scale them down proportionally so nothing is clipped.
        if not vertical:
            total = sum(getattr(s, main_attr) for s in sizes) + spacing
            avail = getattr(size, main_attr)
            if total > avail > 0:
                ratio = avail / total
                sizes = [
                    Size(getattr(s, "width") * ratio, getattr(s, "height")) for s in sizes
                ]
        for i, child in enumerate(children):
            child_size = sizes[i]
            if i in spacers:
                child_size = Size(**{main_attr: spacer_main, cross_attr: cross})
            child_main = getattr(child_size, main_attr)
            child_cross = getattr(child_size, cross_attr)
            # Children fill the container along the cross axis.
            child_cross = cross
            align = {"leading": 0.0, "top": 0.0, "center": 0.5, "trailing": 1.0, "bottom": 1.0}.get(
                stack._alignment, 0.5
            )
            offset = max(0.0, (cross - child_cross) * align)
            if vertical:
                pos = Point(origin.x + offset, origin.y + cursor)
            else:
                pos = Point(origin.x + cursor, origin.y + offset)
            self._walk(child, pos, child_size)
            cursor += child_main + stack._spacing

    # -- Rendering ----------------------------------------------------------
    def _render(self) -> None:
        stdscr = self._stdscr
        h, w = stdscr.getmaxyx()
        view = self._view_factory()
        self._view = view
        self._layout(view, w, h - 1)

        grid = TerminalGrid(w, h - 1)
        self._draw(view, grid, Point(0, 0), Size(w, h - 1))

        for y in range(min(h - 1, len(grid._cells))):
            stdscr.addstr(y, 0, "".join(grid._cells[y][:w]))
        status = self._status or " q: quit"
        try:
            stdscr.addstr(h - 1, 0, status[: w - 1])
        except curses.error:
            pass
        stdscr.refresh()

    def _draw(self, view: View, grid: TerminalGrid, origin: Point, size: Size) -> None:
        if isinstance(view, _ModifiedContent):
            self._draw(view.body(), grid, origin, size)
            return
        if isinstance(view, _Frame):
            self._draw(view._content, grid, origin, size)
            return

        frame = self._frames.get(id(view))
        if frame is None:
            # Container: recurse.
            for child in view.children():
                self._draw(child, grid, origin, size)
            return
        pos, fsize = frame
        x, y = int(round(pos.x)), int(round(pos.y))
        fw, fh = int(round(fsize.width)), int(round(fsize.height))

        if isinstance(view, Text):
            grid.put(x, y, view.content[: max(0, fw)])
        elif isinstance(view, Button):
            label = " " + view.title + " "
            grid.put(x, y, "[" + label[: max(0, fw - 2)] + "]")
        elif isinstance(view, TextField):
            val = view.text.wrapped_value
            shown = (val if val else view.placeholder)[: max(0, fw - 2)]
            grid.put(x, y, "[" + shown + "]")
        elif isinstance(view, Toggle):
            mark = "[x]" if (view.is_on and view.is_on.wrapped_value) else "[ ]"
            grid.put(x, y, mark + " " + view.title)
        elif isinstance(view, Slider):
            lo, hi = view.range
            cur = view.value.wrapped_value if view.value else lo
            span = max(0.0, hi - lo)
            ratio = 0.0 if span == 0 else (cur - lo) / span
            total = max(1, fw - 2)
            posn = int(round(ratio * (total - 1)))
            grid.put(x, y, "[" + "-" * posn + "o" + "-" * (total - posn - 1) + "]")
        elif isinstance(view, Picker):
            grid.put(x, y, "< " + view.title + " >")
        elif isinstance(view, Divider):
            grid.hline(x, y, fw)
        elif isinstance(view, Image):
            grid.put(x, y, "(img)")
        elif isinstance(view, DatePicker):
            label = f"[ {view.title} {view._current()} ]"
            grid.put(x, y, label[: max(0, fw)])
        elif isinstance(view, Stepper):
            label = f"[- {view.title} +]"
            grid.put(x, y, label[: max(0, fw)])
        elif isinstance(view, ProgressView):
            total = max(1, fw - 2)
            if view.value is None:
                grid.put(x, y, "[" + "?" * total + "]")
            else:
                ratio = max(0.0, min(1.0, view.value))
                filled = int(round(ratio * total))
                grid.put(x, y, "[" + "#" * filled + "-" * (total - filled) + "]")
        elif isinstance(view, NavigationStack):
            grid.put(x, y, "== " + view.title + " ==")
            for child in view.children():
                self._draw(child, grid, origin, size)
        elif isinstance(view, Form):
            for child in view.children():
                self._draw(child, grid, origin, size)
        else:
            for child in view.children():
                self._draw(child, grid, origin, size)

    # -- Event handling -----------------------------------------------------
    def _handle_key(self, key: int) -> None:
        if key in (curses.KEY_UP, ord("k")):
            self._move_focus(-1)
        elif key in (curses.KEY_DOWN, ord("j")):
            self._move_focus(1)
        elif key in (curses.KEY_ENTER, 10, 13):
            if self._activate_tap():
                return
            self._activate_focused()
        elif key in (ord("t"), ord("T")):
            self._move_tap(1)
        elif key == ord("\t"):
            self._move_focus(1)
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self._edit_focused(lambda s: s[:-1])
        elif key == curses.KEY_LEFT:
            self._edit_focused(lambda s: s[:-1])
        elif key == curses.KEY_RIGHT:
            pass
        elif key in (curses.KEY_PPAGE, ord("[")):
            self._scroll_list(-1)
        elif key in (curses.KEY_NPAGE, ord("]")):
            self._scroll_list(1)
        elif 32 <= key < 127:
            self._edit_focused(lambda s, k=key: s + chr(k))
        else:
            return

    def _scroll_list(self, delta: int) -> None:
        """Scroll the first (or focused) List by ``delta`` rows."""
        if not self._lists:
            return
        lst = self._lists[0]
        lst.scroll_to(lst.current_offset() + delta)
        self._status = f" list scroll: offset {lst.current_offset()}"

    def _move_focus(self, delta: int) -> None:
        if not self._textfields:
            return
        n = len(self._textfields)
        self._focus_index = (self._focus_index + delta) % n
        self._focused = self._textfields[self._focus_index]
        self._status = f" editing: {self._focused.placeholder or 'field'} (q: quit)"

    def _move_tap(self, delta: int) -> None:
        if not self._taps:
            return
        n = len(self._taps)
        self._tap_index = (self._tap_index + delta) % n
        view, origin, size, action = self._taps[self._tap_index]
        self._status = f" tap: {type(view).__name__} (Enter to activate, q: quit)"

    def _activate_tap(self) -> bool:
        """Activate the currently selected tappable region. Returns True if a
        tap was fired (so the caller can skip other activation logic)."""
        if not self._taps:
            return False
        view, origin, size, action = self._taps[self._tap_index]
        if action is not None:
            action()
            self._status = f" tapped: {type(view).__name__}"
            return True
        # Fall back to the view's own activation (e.g. Toggle flips).
        if isinstance(view, Toggle) and view.is_on is not None:
            view.is_on.wrapped_value = not view.is_on.wrapped_value
            self._status = f" toggled: {view.title}"
            return True
        return False

    def _activate_focused(self) -> None:
        if self._focused is None:
            return
        self._status = f" activated: {self._focused.text.wrapped_value}"

    def _edit_focused(self, fn: Callable[[str], str]) -> None:
        if self._focused is None:
            return
        self._focused.text.wrapped_value = fn(self._focused.text.wrapped_value)
        self._status = f" value: {self._focused.text.wrapped_value}"
