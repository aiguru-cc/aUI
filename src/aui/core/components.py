"""UI components for aUI.

Mirrors SwiftUI's core controls: ``Text``, ``Button``, ``TextField``,
``Toggle``, ``Slider``, ``Picker``, ``Image``, ``Divider`` and ``List``.
Components are declarative descriptions; the render backend turns them into
native widgets.
"""
from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence

from .geometry import Color, EdgeInsets, Font, Point, Size
from .state import Binding
from .view import View


class Text(View):
    """Static or dynamic text with multi-line layout (mirrors SwiftUI Text).

    Supports explicit line breaks (``\\n``), word-wrapping to a proposal width,
    ``line_limit`` truncation and ``line_spacing``. Text measurement accounts
    for CJK full-width characters (double width) vs. ASCII (single width).
    """

    def __init__(
        self,
        content: Any = "",
        font: Optional[Font] = None,
        color: Optional[Color] = None,
        line_limit: Optional[int] = None,
        line_spacing: float = 0.0,
    ):
        self._content = str(content)
        self._font = font or Font.body()
        self._color = color
        self._line_limit = line_limit
        self._line_spacing = line_spacing
        self._children = []

    @property
    def content(self) -> str:
        return self._content

    @property
    def line_limit(self) -> Optional[int]:
        return self._line_limit

    @property
    def line_spacing(self) -> float:
        return self._line_spacing

    # -- Text measurement ---------------------------------------------------
    @staticmethod
    def _char_width(ch: str, font_size: float) -> float:
        """Approximate glyph width: CJK full-width chars are double width."""
        if ord(ch) > 0x2E7F:  # CJK / full-width ranges
            return font_size
        return font_size * 0.55

    def _measure_line(self, line: str) -> float:
        return sum(self._char_width(ch, self._font.size) for ch in line)

    def _wrap_line(self, line: str, max_width: float) -> list:
        """Greedy word wrap of a single logical line into visual lines."""
        if max_width == float("inf") or max_width <= 0:
            return [line] if line else [""]
        words = line.split(" ")
        if not words:
            return [""]
        lines: list = []
        current = ""
        current_w = 0.0
        for word in words:
            word_w = self._measure_line(word)
            sep_w = self._char_width(" ", self._font.size)
            if current and current_w + sep_w + word_w > max_width:
                lines.append(current)
                current = word
                current_w = word_w
            else:
                if current:
                    current += " "
                    current_w += sep_w
                current += word
                current_w += word_w
        if current:
            lines.append(current)
        return lines or [""]

    def _layout_lines(self, proposal_width: float) -> list:
        """Return the visual lines (wrapped, truncated) for this text."""
        if not self._content:
            return []
        lines: list = []
        for logical in self._content.split("\n"):
            lines.extend(self._wrap_line(logical, proposal_width))
        if self._line_limit is not None and len(lines) > self._line_limit:
            lines = lines[: self._line_limit]
        return lines

    def size_that_fits(self, proposal: Size) -> Size:
        lines = self._layout_lines(proposal.width)
        if not lines:
            return Size(0.0, 0.0)
        width = max(self._measure_line(line) for line in lines)
        line_height = self._font.size * 1.4
        height = line_height * len(lines) + self._line_spacing * max(0, len(lines) - 1)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Button(View):
    """A clickable button (mirrors SwiftUI Button)."""

    def __init__(self, title: str, action: Callable[[], None], role: str = "normal"):
        self._title = title
        self._action = action
        self._role = role
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def action(self) -> Callable[[], None]:
        return self._action

    def size_that_fits(self, proposal: Size) -> Size:
        width = max(64.0, len(self._title) * 8.0 + 24.0)
        return Size(width, 32.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class TextField(View):
    """A single-line text input (mirrors SwiftUI TextField)."""

    def __init__(self, text: Binding[str], placeholder: str = ""):
        self._text = text
        self._placeholder = placeholder
        self._children = []

    @property
    def text(self) -> Binding[str]:
        return self._text

    @property
    def placeholder(self) -> str:
        return self._placeholder

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(160.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Toggle(View):
    """An on/off switch (mirrors SwiftUI Toggle)."""

    def __init__(self, title: str = "", is_on: Optional[Binding[bool]] = None):
        self._title = title
        self._is_on = is_on
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def is_on(self) -> Optional[Binding[bool]]:
        return self._is_on

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(90.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Slider(View):
    """A horizontal value slider (mirrors SwiftUI Slider)."""

    def __init__(
        self,
        value: Optional[Binding[float]] = None,
        in_range: tuple = (0.0, 1.0),
        step: Optional[float] = None,
    ):
        self._value = value
        self._range = in_range
        self._step = step
        self._children = []

    @property
    def value(self) -> Optional[Binding[float]]:
        return self._value

    @property
    def range(self) -> tuple:
        return self._range

    @property
    def step(self) -> Optional[float]:
        return self._step

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(160.0, 24.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Picker(View):
    """A dropdown selector (mirrors SwiftUI Picker)."""

    def __init__(self, title: str, selection: Optional[Binding] = None, options: Sequence[Any] = ()):
        self._title = title
        self._selection = selection
        self._options = list(options)
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def selection(self) -> Optional[Binding]:
        return self._selection

    @property
    def options(self) -> List[Any]:
        return self._options

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(140.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Image(View):
    """A placeholder image view (mirrors SwiftUI Image)."""

    def __init__(self, system_name: str = "", color: Optional[Color] = None, size: float = 24.0):
        self._system_name = system_name
        self._color = color
        self._size = size
        self._children = []

    @property
    def system_name(self) -> str:
        return self._system_name

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(self._size, self._size)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Divider(View):
    """A thin horizontal separator line (mirrors SwiftUI Divider)."""

    def __init__(self, color: Optional[Color] = None):
        self._color = color
        self._children = []

    @property
    def color(self) -> Optional[Color]:
        return self._color

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(proposal.width if proposal.width != float("inf") else 200.0, 1.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class List(View):
    """A vertical list of rows (mirrors SwiftUI List)."""

    def __init__(self, rows: Sequence[View] = (), spacing: float = 2.0):
        self._rows = list(rows)
        self._spacing = spacing
        self._children = list(rows)

    @property
    def rows(self) -> List[View]:
        return self._rows

    def size_that_fits(self, proposal: Size) -> Size:
        height = 0.0
        width = 0.0
        for row in self._rows:
            s = row.size_that_fits(Size(proposal.width, float("inf")))
            height += s.height
            width = max(width, s.width)
        height += self._spacing * max(0, len(self._rows) - 1)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        cursor = origin.y
        for row in self._rows:
            row_size = row.size_that_fits(Size(size.width, float("inf")))
            row.place(Point(origin.x, cursor), row_size)
            cursor += row_size.height + self._spacing

    def children(self) -> Sequence[View]:
        return self._children


class Group(View):
    """A container that groups children without adding layout (mirrors Group)."""

    def __init__(self, children: Sequence[View] = ()):
        self._children = list(children)

    def size_that_fits(self, proposal: Size) -> Size:
        width = 0.0
        height = 0.0
        for child in self._children:
            s = child.size_that_fits(proposal)
            width = max(width, s.width)
            height += s.height
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        cursor = origin.y
        for child in self._children:
            child_size = child.size_that_fits(Size(size.width, float("inf")))
            child.place(Point(origin.x, cursor), child_size)
            cursor += child_size.height

    def children(self) -> Sequence[View]:
        return self._children


class Stepper(View):
    """A value stepper with +/- buttons (mirrors SwiftUI Stepper).

    ``value`` is an optional two-way binding; when absent the ``on_increment`` /
    ``on_decrement`` callbacks are used.
    """

    def __init__(
        self,
        title: str = "",
        value: Optional[Binding[float]] = None,
        in_range: tuple = (0.0, 100.0),
        step: float = 1.0,
        on_increment: Optional[Callable[[], None]] = None,
        on_decrement: Optional[Callable[[], None]] = None,
    ):
        self._title = title
        self._value = value
        self._range = in_range
        self._step = step
        self._on_increment = on_increment
        self._on_decrement = on_decrement
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def value(self) -> Optional[Binding[float]]:
        return self._value

    @property
    def range(self) -> tuple:
        return self._range

    @property
    def step(self) -> float:
        return self._step

    def increment(self) -> None:
        if self._on_increment is not None:
            self._on_increment()
        elif self._value is not None:
            lo, hi = self._range
            self._value.wrapped_value = min(hi, self._value.wrapped_value + self._step)

    def decrement(self) -> None:
        if self._on_decrement is not None:
            self._on_decrement()
        elif self._value is not None:
            lo, hi = self._range
            self._value.wrapped_value = max(lo, self._value.wrapped_value - self._step)

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(120.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class ProgressView(View):
    """A determinate progress bar (mirrors SwiftUI ProgressView).

    ``value`` is a float in ``[0, 1]`` (or a Binding); when None the view is
    indeterminate (animated spinner in some backends).
    """

    def __init__(self, value: Optional[float] = None, label: str = ""):
        self._value = value
        self._label = label
        self._children = []

    @property
    def value(self) -> Optional[float]:
        return self._value

    @property
    def label(self) -> str:
        return self._label

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(160.0, 20.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Form(View):
    """A grouped vertical container for settings-style forms (mirrors Form).

    Renders children stacked vertically with a subtle section feel.
    """

    def __init__(self, children: Sequence[View] = (), spacing: float = 4.0):
        self._children = list(children)
        self._spacing = spacing

    def size_that_fits(self, proposal: Size) -> Size:
        width = 0.0
        height = 0.0
        for child in self._children:
            s = child.size_that_fits(Size(proposal.width, float("inf")))
            width = max(width, s.width)
            height += s.height
        height += self._spacing * max(0, len(self._children) - 1)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        cursor = origin.y
        for child in self._children:
            child_size = child.size_that_fits(Size(size.width, float("inf")))
            child.place(Point(origin.x, cursor), child_size)
            cursor += child_size.height + self._spacing

    def children(self) -> Sequence[View]:
        return self._children


class NavigationStack(View):
    """A navigation container with a title bar (mirrors NavigationStack).

    ``title`` is shown in a header bar; ``content`` is the main body.
    """

    def __init__(self, title: str, content: View):
        self._title = title
        self._content = content
        self._children = [content]

    @property
    def title(self) -> str:
        return self._title

    @property
    def content(self) -> View:
        return self._content

    def size_that_fits(self, proposal: Size) -> Size:
        inner = self._content.size_that_fits(proposal)
        header = 24.0
        return Size(inner.width, inner.height + header)

    def place(self, origin: Point, size: Size) -> None:
        inner_size = self._content.size_that_fits(size)
        self._content.place(Point(origin.x, origin.y + 24.0), inner_size)

    def children(self) -> Sequence[View]:
        return self._children
