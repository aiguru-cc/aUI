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
    """A single line of static or dynamic text (mirrors SwiftUI Text)."""

    def __init__(self, content: Any = "", font: Optional[Font] = None, color: Optional[Color] = None):
        self._content = str(content)
        self._font = font or Font.body()
        self._color = color
        self._children = []

    @property
    def content(self) -> str:
        return self._content

    def size_that_fits(self, proposal: Size) -> Size:
        # Approximate text measurement: 0.55 * font size per character.
        width = len(self._content) * self._font.size * 0.55
        return Size(width, self._font.size * 1.4)

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
