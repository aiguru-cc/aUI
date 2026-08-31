"""Immediate-mode Canvas drawing and deterministic TimelineView."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from .geometry import Color, Point, Rect, Size
from .view import View


@dataclass(frozen=True)
class FillStyle:
    """Shape fill rule and edge-antialiasing preference."""

    eo_fill: bool = False
    antialiased: bool = True


@dataclass(frozen=True)
class StrokeStyle:
    line_width: float = 1.0
    line_cap: str = "butt"
    line_join: str = "miter"
    miter_limit: float = 10.0
    dash: tuple[float, ...] = ()
    dash_phase: float = 0.0

    def __post_init__(self):
        if self.line_width < 0:
            raise ValueError("line width cannot be negative")
        if self.line_cap not in {"butt", "round", "square"}:
            raise ValueError(f"unsupported line cap: {self.line_cap!r}")
        if self.line_join not in {"miter", "round", "bevel"}:
            raise ValueError(f"unsupported line join: {self.line_join!r}")
        if self.miter_limit < 0:
            raise ValueError("miter limit cannot be negative")
        if any(value < 0 for value in self.dash):
            raise ValueError("dash lengths cannot be negative")


class Path:
    """Backend-neutral vector path."""

    def __init__(self):
        self.commands: list[tuple] = []

    def move(self, point: Point) -> "Path":
        self.commands.append(("move", point)); return self

    def line(self, point: Point) -> "Path":
        self.commands.append(("line", point)); return self

    def quad_curve(self, point: Point, control: Point) -> "Path":
        self.commands.append(("quad", point, control)); return self

    def curve(self, point: Point, control1: Point, control2: Point) -> "Path":
        self.commands.append(("curve", point, control1, control2)); return self

    def close(self) -> "Path":
        self.commands.append(("close",)); return self

    def add_rect(self, rect: Rect) -> "Path":
        self.commands.append(("rect", rect)); return self

    def add_ellipse(self, rect: Rect) -> "Path":
        self.commands.append(("ellipse", rect)); return self

    @classmethod
    def rectangle(cls, rect: Rect) -> "Path": return cls().add_rect(rect)
    @classmethod
    def ellipse(cls, rect: Rect) -> "Path": return cls().add_ellipse(rect)


@dataclass(frozen=True)
class DrawCommand:
    operation: str
    path: Path
    color: Color
    style: Optional[StrokeStyle] = None


class GraphicsContext:
    """Records drawing commands for a backend to execute."""

    def __init__(self):
        self.commands: list[DrawCommand] = []
        self.opacity = 1.0

    def fill(self, path: Path, color: Color) -> None:
        self._validate(path, color)
        effective = Color(color.red, color.green, color.blue, color.alpha * self.opacity)
        self.commands.append(DrawCommand("fill", path, effective))

    def stroke(self, path: Path, color: Color, style: StrokeStyle | None = None) -> None:
        self._validate(path, color)
        effective = Color(color.red, color.green, color.blue, color.alpha * self.opacity)
        self.commands.append(DrawCommand("stroke", path, effective, style or StrokeStyle()))

    @staticmethod
    def _validate(path, color):
        if not isinstance(path, Path): raise TypeError("drawing expects a Path")
        if not isinstance(color, Color): raise TypeError("drawing expects a Color")


class Canvas(View):
    """Immediate-mode vector drawing surface."""

    def __init__(self, renderer: Callable[[GraphicsContext, Size], None],
                 width: float = 240.0, height: float = 160.0,
                 opaque: bool = False, renders_asynchronously: bool = False):
        if not callable(renderer): raise TypeError("Canvas renderer must be callable")
        self.renderer = renderer
        self.ideal_size = Size(max(0.0, width), max(0.0, height))
        self.opaque = bool(opaque)
        self.renders_asynchronously = bool(renders_asynchronously)
        self._children = []

    def resolve(self, size: Size) -> GraphicsContext:
        context = GraphicsContext()
        self.renderer(context, size)
        return context

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(min(self.ideal_size.width, proposal.width),
                    min(self.ideal_size.height, proposal.height))

    def place(self, origin: Point, size: Size) -> None: pass


@dataclass(frozen=True)
class TimelineContext:
    date: datetime
    cadence: str


class TimelineView(View):
    """A time-dependent view with an explicitly advanceable clock."""

    CADENCES = {"live", "seconds", "minutes"}

    def __init__(self, content: Callable[[TimelineContext], View], cadence: str = "seconds",
                 date: Optional[datetime] = None):
        if cadence not in self.CADENCES: raise ValueError(f"unsupported cadence: {cadence!r}")
        self.builder = content
        self.cadence = cadence
        self.date = date or datetime.now(timezone.utc)
        self._content = self._build()
        self._children = [self._content]

    @property
    def content(self): return self._content

    def _build(self):
        value = self.builder(TimelineContext(self.date, self.cadence))
        if not isinstance(value, View): raise TypeError("TimelineView content must return a View")
        return value

    def tick(self, date: Optional[datetime] = None) -> View:
        self.date = date or datetime.now(timezone.utc)
        self._content = self._build()
        self._children = [self._content]
        return self._content

    def size_that_fits(self, proposal): return self._content.size_that_fits(proposal)
    def place(self, origin, size): self._content.place(origin, size)
