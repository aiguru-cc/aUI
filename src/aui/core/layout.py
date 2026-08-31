"""Layout containers for aUI.

Mirrors SwiftUI's core layout containers: ``VStack``, ``HStack``, ``ZStack``
and ``Spacer``. Layout is computed in pure Python (no GUI needed), so it can be
unit-tested without a display.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence

from .geometry import EdgeInsets, Point, Rect, Size
from .measurement import measure
from .state import Binding
from .view import View


class _Stack(View):
    """Base class for VStack/HStack with flexible spacer handling."""

    axis: str = "vertical"  # "vertical" or "horizontal"

    def __init__(self, children: Sequence[View], spacing: float = 8.0, alignment: str = "center"):
        self._children = list(children)
        self._spacing = spacing
        self._alignment = alignment

    @property
    def _main(self) -> str:
        return "height" if self.axis == "vertical" else "width"

    @property
    def _cross(self) -> str:
        return "width" if self.axis == "vertical" else "height"

    def size_that_fits(self, proposal: Size) -> Size:
        children = list(self.children())
        main = getattr(proposal, self._main)
        cross = getattr(proposal, self._cross)

        # First pass: measure non-spacer children with a proposal that is
        # unlimited along the main axis.
        sizes: List[Size] = []
        has_spacer = False
        for child in children:
            if isinstance(child, Spacer):
                has_spacer = True
                sizes.append(Size())
                continue
            child_proposal = Size(**{self._main: float("inf"), self._cross: cross})
            sizes.append(child.size_that_fits(child_proposal))

        spacers = sum(1 for c in children if isinstance(c, Spacer))
        n_non_spacer = len(children) - spacers
        spacing_total = self._spacing * max(0, len(children) - 1)

        if has_spacer:
            # Spacers absorb all remaining space along the main axis.
            used_main = sum(getattr(s, self._main) for s in sizes) + spacing_total
            main_size = max(main, used_main)
        else:
            main_size = sum(getattr(s, self._main) for s in sizes) + spacing_total

        cross_size = max((getattr(s, self._cross) for s in sizes), default=0.0)
        if not has_spacer:
            cross_size = max(cross_size, cross) if cross != float("inf") else cross_size

        return Size(**{self._main: main_size, self._cross: cross_size})

    def place(self, origin: Point, size: Size) -> None:
        children = list(self.children())
        main = getattr(size, self._main)
        cross = getattr(size, self._cross)

        # Measure children (unlimited main axis).
        sizes: List[Size] = []
        for child in children:
            if isinstance(child, Spacer):
                sizes.append(Size())
                continue
            proposal = Size(**{self._main: float("inf"), self._cross: cross})
            sizes.append(child.size_that_fits(proposal))

        spacers = [i for i, c in enumerate(children) if isinstance(c, Spacer)]
        spacing_total = self._spacing * max(0, len(children) - 1)
        fixed_main = sum(getattr(s, self._main) for i, s in enumerate(sizes) if i not in spacers)
        free_main = max(0.0, main - fixed_main - spacing_total)
        spacer_main = free_main / len(spacers) if spacers else 0.0

        cursor = 0.0
        for i, child in enumerate(children):
            child_size = sizes[i]
            if i in spacers:
                child_size = Size(**{self._main: spacer_main, self._cross: cross})
            child_main = getattr(child_size, self._main)
            child_cross = getattr(child_size, self._cross)
            offset = (cross - child_cross) * self._cross_alignment()
            if self.axis == "vertical":
                pos = Point(origin.x + offset, origin.y + cursor)
            else:
                pos = Point(origin.x + cursor, origin.y + offset)
            child.place(pos, child_size)
            cursor += child_main + self._spacing

    def _cross_alignment(self) -> float:
        return {
            "leading": 0.0, "top": 0.0,
            "center": 0.5,
            "trailing": 1.0, "bottom": 1.0,
        }.get(self._alignment, 0.5)

    def children(self) -> Sequence[View]:
        return self._children


class VStack(_Stack):
    """Arranges children vertically (top to bottom)."""

    axis = "vertical"

    def __init__(self, children: Sequence[View] = (), spacing: float = 8.0, alignment: str = "center"):
        super().__init__(children, spacing, alignment)


class HStack(_Stack):
    """Arranges children horizontally (leading to trailing)."""

    axis = "horizontal"

    def __init__(self, children: Sequence[View] = (), spacing: float = 8.0, alignment: str = "center"):
        super().__init__(children, spacing, alignment)

    def children(self) -> Sequence[View]:
        from .localization import LAYOUT_DIRECTION_KEY
        environment = getattr(self, "_environment", None)
        if environment is not None and environment.get(LAYOUT_DIRECTION_KEY) == "rightToLeft":
            return tuple(reversed(self._children))
        return self._children


class ZStack(View):
    """Overlays children on top of each other (back to front)."""

    def __init__(self, children: Sequence[View] = (), alignment: str = "center"):
        self._children = list(children)
        self._alignment = alignment

    def size_that_fits(self, proposal: Size) -> Size:
        width = 0.0
        height = 0.0
        for child in self._children:
            s = child.size_that_fits(proposal)
            width = max(width, s.width)
            height = max(height, s.height)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        for child in self._children:
            child_size = child.size_that_fits(size)
            from .view import _aligned_offset
            dx, dy = _aligned_offset(size, child_size, self._alignment)
            child.place(Point(origin.x + dx, origin.y + dy), child_size)

    def children(self) -> Sequence[View]:
        return self._children


class Spacer(View):
    """A flexible empty space that expands along the stack's main axis."""

    def __init__(self, min_length: float = 0.0):
        self.min_length = min_length
        self._children = []

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(0.0, 0.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class GeometryProxy:
    """Read-only geometry supplied to a ``GeometryReader`` content builder."""

    def __init__(self, size: Size, origin: Point = Point(),
                 safe_area_insets: EdgeInsets = EdgeInsets()):
        self.size = size
        self.safe_area_insets = safe_area_insets
        self._origin = origin

    def frame(self, coordinate_space: str = "local") -> Rect:
        if coordinate_space == "local":
            return Rect(Point(), self.size)
        if coordinate_space == "global":
            return Rect(self._origin, self.size)
        raise ValueError("coordinate_space must be 'local' or 'global'")


class GeometryReader(View):
    """A greedy container whose builder receives its resolved geometry."""

    def __init__(self, content: Callable[[GeometryProxy], View],
                 safe_area_insets: EdgeInsets = EdgeInsets()):
        if not callable(content):
            raise TypeError("GeometryReader content must be callable")
        self._builder = content
        self._safe_area_insets = safe_area_insets
        self._proxy = GeometryProxy(Size(), safe_area_insets=safe_area_insets)
        self.content = content(self._proxy)
        if not isinstance(self.content, View):
            raise TypeError("GeometryReader content must return a View")
        self._children = [self.content]

    @staticmethod
    def _finite(proposal: Size) -> Size:
        return Size(
            0.0 if proposal.width == float("inf") else proposal.width,
            0.0 if proposal.height == float("inf") else proposal.height,
        )

    def resolve(self, origin: Point, size: Size) -> View:
        proxy = GeometryProxy(size, origin, self._safe_area_insets)
        if (proxy.size, proxy._origin) != (self._proxy.size, self._proxy._origin):
            content = self._builder(proxy)
            if not isinstance(content, View):
                raise TypeError("GeometryReader content must return a View")
            self._proxy = proxy
            self.content = content
            self._children = [content]
        return self.content

    def size_that_fits(self, proposal: Size) -> Size:
        finite = self._finite(proposal)
        child = self.resolve(Point(), finite)
        natural = child.size_that_fits(proposal)
        return Size(
            natural.width if proposal.width == float("inf") else proposal.width,
            natural.height if proposal.height == float("inf") else proposal.height,
        )

    def place(self, origin: Point, size: Size) -> None:
        self.resolve(origin, size).place(origin, size)

    def children(self) -> Sequence[View]:
        return self._children


class ResponsiveBreakpoint:
    """Flet-compatible width breakpoints for :class:`ResponsiveRow`."""

    XS = "xs"
    SM = "sm"
    MD = "md"
    LG = "lg"
    XL = "xl"
    VALUES = (XS, SM, MD, LG, XL)
    MINIMUMS = {XS: 0.0, SM: 576.0, MD: 768.0, LG: 992.0, XL: 1200.0}


class ResponsiveItem(View):
    """A responsive-grid child with a Flet-style ``col`` span definition."""

    def __init__(self, content: View, col: int | dict[str, int] = 12):
        if not isinstance(content, View):
            raise TypeError("ResponsiveItem content must be a View")
        if isinstance(col, int):
            columns = {ResponsiveBreakpoint.XS: col}
        elif isinstance(col, dict):
            columns = dict(col)
        else:
            raise TypeError("ResponsiveItem col must be an int or breakpoint mapping")
        if not columns or any(key not in ResponsiveBreakpoint.VALUES for key in columns):
            raise ValueError("ResponsiveItem uses xs, sm, md, lg, or xl breakpoints")
        if any(not isinstance(value, int) or not 1 <= value <= 12 for value in columns.values()):
            raise ValueError("ResponsiveItem column spans must be integers from 1 through 12")
        self.content = content
        self.columns = columns
        self._children = [content]

    def span(self, available_width: float, column_count: int = 12) -> int:
        active = ResponsiveBreakpoint.XS
        for name in ResponsiveBreakpoint.VALUES:
            if available_width >= ResponsiveBreakpoint.MINIMUMS[name] and name in self.columns:
                active = name
        return min(column_count, self.columns.get(active, self.columns.get(ResponsiveBreakpoint.XS, column_count)))

    def size_that_fits(self, proposal: Size) -> Size:
        return self.content.size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        self.content.place(origin, size)


class ResponsiveRow(View):
    """A 12-column, breakpoint-aware layout inspired by Flet's ResponsiveRow."""

    def __init__(self, items: Sequence[ResponsiveItem | View] = (), *, columns: int = 12,
                 spacing: float = 8.0, run_spacing: Optional[float] = None):
        if not isinstance(columns, int) or columns < 1:
            raise ValueError("ResponsiveRow columns must be a positive integer")
        normalized = [item if isinstance(item, ResponsiveItem) else ResponsiveItem(item)
                      for item in items]
        self.columns = columns
        self.spacing = max(0.0, float(spacing))
        self.run_spacing = self.spacing if run_spacing is None else max(0.0, float(run_spacing))
        self._children = normalized

    def placements(self, origin: Point, size: Size) -> list[tuple[ResponsiveItem, Point, Size]]:
        width = max(1.0, size.width if size.width != float("inf") else 1024.0)
        unit = max(0.0, (width - self.spacing * (self.columns - 1)) / self.columns)
        placed: list[tuple[ResponsiveItem, Point, Size]] = []
        row: list[tuple[ResponsiveItem, int, float]] = []
        occupied, y = 0, origin.y

        def flush() -> None:
            nonlocal row, occupied, y
            if not row:
                return
            row_height = max(height for _, _, height in row)
            x = origin.x
            for item, span, _ in row:
                item_width = unit * span + self.spacing * (span - 1)
                placed.append((item, Point(x, y), Size(item_width, row_height)))
                x += item_width + self.spacing
            y += row_height + self.run_spacing
            row, occupied = [], 0

        for item in self._children:
            span = item.span(width, self.columns)
            if occupied and occupied + span > self.columns:
                flush()
            item_width = unit * span + self.spacing * (span - 1)
            height = item.size_that_fits(Size(item_width, float("inf"))).height
            row.append((item, span, height))
            occupied += span
        flush()
        return placed

    def size_that_fits(self, proposal: Size) -> Size:
        width = proposal.width if proposal.width != float("inf") else 1024.0
        placements = self.placements(Point(), Size(width, proposal.height))
        height = max((point.y + size.height for _, point, size in placements), default=0.0)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        for item, point, item_size in self.placements(origin, size):
            item.place(point, item_size)


class NavigationSplitViewVisibility:
    AUTOMATIC = "automatic"
    ALL = "all"
    DOUBLE_COLUMN = "doubleColumn"
    DETAIL_ONLY = "detailOnly"


class NavigationSplitViewColumn:
    SIDEBAR = "sidebar"
    CONTENT = "content"
    DETAIL = "detail"


class NavigationSplitViewStyle:
    AUTOMATIC = "automatic"
    BALANCED = "balanced"
    PROMINENT_DETAIL = "prominentDetail"


class NavigationSplitView(View):
    """Adaptive two- or three-column navigation layout.

    The sidebar and optional content column use bounded widths while the
    detail column absorbs the remaining space.  This mirrors SwiftUI's
    ``NavigationSplitView`` without tying the layout model to AppKit.
    """

    def __init__(
        self,
        sidebar: View,
        detail: View,
        content: Optional[View] = None,
        sidebar_width: tuple = (180.0, 220.0, 320.0),
        content_width: tuple = (220.0, 280.0, 400.0),
        detail_width: tuple = (280.0, 480.0, float("inf")),
        divider_width: float = 1.0,
        column_visibility: Optional[Binding[str]] = None,
        sidebar_visibility: Optional[Binding[bool]] = None,
        preferred_compact_column: str | Binding[str] = "detail",
        style: str = "automatic",
    ):
        self.sidebar = sidebar
        self.content = content
        self.detail = detail
        self.sidebar_width = self._validated_widths(sidebar_width)
        self.content_width = self._validated_widths(content_width)
        self.detail_width = self._validated_widths(detail_width, allows_infinity=True)
        self.divider_width = max(0.0, float(divider_width))
        if column_visibility is not None and not isinstance(column_visibility, Binding):
            raise TypeError("column_visibility must be a Binding")
        if sidebar_visibility is not None and not isinstance(sidebar_visibility, Binding):
            raise TypeError("sidebar_visibility must be a Binding")
        self.column_visibility = column_visibility
        self.sidebar_visibility = sidebar_visibility
        self.preferred_compact_column = preferred_compact_column
        self.style = self._validated_style(style)
        self._children = [sidebar] + ([content] if content is not None else []) + [detail]

    @staticmethod
    def _validated_widths(value: tuple, allows_infinity: bool = False) -> tuple:
        if len(value) != 3:
            raise ValueError("column widths must be a (minimum, ideal, maximum) tuple")
        lo, ideal, hi = map(float, value)
        if lo <= 0 or not lo <= ideal <= hi:
            raise ValueError("column widths must satisfy 0 < minimum <= ideal <= maximum")
        return lo, ideal, hi

    @staticmethod
    def _validated_style(value: str) -> str:
        if value not in ("automatic", "balanced", "prominentDetail"):
            raise ValueError("split view style must be automatic, balanced, or prominentDetail")
        return value

    @staticmethod
    def _validated_visibility(value: str) -> str:
        if value not in ("automatic", "all", "doubleColumn", "detailOnly"):
            raise ValueError("column visibility must be automatic, all, doubleColumn, or detailOnly")
        return value

    @staticmethod
    def _validated_column(value: str) -> str:
        if value not in ("sidebar", "content", "detail"):
            raise ValueError("split view column must be sidebar, content, or detail")
        return value

    @property
    def visibility(self) -> str:
        value = self.column_visibility.wrapped_value if self.column_visibility is not None else "automatic"
        return self._validated_visibility(value)

    @property
    def is_sidebar_visible(self) -> bool:
        """Whether the leading navigation column is currently presented."""
        return (bool(self.sidebar_visibility.wrapped_value)
                if self.sidebar_visibility is not None else True)

    @property
    def compact_column(self) -> str:
        value = (self.preferred_compact_column.wrapped_value
                 if isinstance(self.preferred_compact_column, Binding)
                 else self.preferred_compact_column)
        value = self._validated_column(value)
        return "detail" if value == "content" and self.content is None else value

    def set_column_visibility(self, value: str) -> None:
        value = self._validated_visibility(value)
        if self.column_visibility is None:
            raise RuntimeError("split view has no column_visibility Binding")
        self.column_visibility.wrapped_value = value

    def navigation_split_view_style(self, style: str) -> "NavigationSplitView":
        self.style = self._validated_style(style)
        return self

    def navigation_split_view_column_width(self, column: str, minimum: float,
                                           ideal: float, maximum: float) -> "NavigationSplitView":
        column = self._validated_column(column)
        widths = self._validated_widths((minimum, ideal, maximum), allows_infinity=column == "detail")
        setattr(self, f"{column}_width", widths)
        return self

    @property
    def column_count(self) -> int:
        return len(self._children)

    def column_widths(self, available_width: float) -> list[float]:
        """Resolve concrete column widths for a finite container width."""
        count = self.column_count
        visibility = self.visibility
        visible = list(range(count))
        detail_index = count - 1
        if visibility == "detailOnly":
            visible = [detail_index]
        elif visibility == "doubleColumn":
            visible = [0, detail_index]
        elif visibility == "automatic" and available_width < (420.0 if count == 2 else 520.0):
            names = ["sidebar"] + (["content"] if self.content is not None else []) + ["detail"]
            visible = [names.index(self.compact_column)]
        elif visibility == "automatic" and self.content is not None and available_width < 760.0:
            visible = [0, detail_index]
        if not self.is_sidebar_visible and len(visible) > 1:
            visible = [index for index in visible if index != 0]
        available = max(0.0, float(available_width) - self.divider_width * max(0, len(visible) - 1))
        result = [0.0] * count
        if len(visible) == 1:
            result[visible[0]] = available
            return result
        side_ideal = self.sidebar_width[0] if self.style == "prominentDetail" else self.sidebar_width[1]
        side = min(self.sidebar_width[2], max(self.sidebar_width[0], side_ideal))
        if self.content is None:
            detail = max(0.0, available - side)
            return [side, detail]
        if visible == [0, detail_index]:
            side = min(side, max(0.0, available - self.detail_width[0]))
            return [side, 0.0, max(0.0, available - side)]
        middle_ideal = self.content_width[0] if self.style == "prominentDetail" else self.content_width[1]
        middle = min(self.content_width[2], max(self.content_width[0], middle_ideal))
        if visible == [1, detail_index]:
            middle = min(middle, max(0.0, available - self.detail_width[0]))
            return [0.0, middle, max(0.0, available - middle)]
        detail = available - side - middle
        if detail < self.detail_width[0]:
            shortage = self.detail_width[0] - detail
            shrink_middle = min(shortage, middle - self.content_width[0])
            middle -= shrink_middle
            shortage -= shrink_middle
            side -= min(shortage, side - self.sidebar_width[0])
            detail = max(0.0, available - side - middle)
        return [side, middle, detail]

    def size_that_fits(self, proposal: Size) -> Size:
        ideal_width = self.sidebar_width[1] + self.divider_width
        if self.content is not None:
            ideal_width += self.content_width[1] + self.divider_width
        ideal_width += 480.0
        width = ideal_width if proposal.width == float("inf") else proposal.width
        heights = [child.size_that_fits(Size(width, proposal.height)).height
                   for child in self._children]
        height = max(heights, default=0.0)
        if proposal.height != float("inf"):
            height = max(height, proposal.height)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        x = origin.x
        for child, width in zip(self._children, self.column_widths(size.width)):
            child.place(Point(x, origin.y), Size(width, size.height))
            x += width + self.divider_width

    def children(self) -> Sequence[View]:
        return self._children


class GridRow(View):
    """A horizontal row inside a :class:`Grid`."""

    def __init__(self, children: Sequence[View] = (), spacing: float = 8.0):
        self._children = list(children)
        self._spacing = max(0.0, float(spacing))

    def size_that_fits(self, proposal: Size) -> Size:
        sizes = [child.size_that_fits(proposal) for child in self._children]
        return Size(
            sum(s.width for s in sizes) + self._spacing * max(0, len(sizes) - 1),
            max((s.height for s in sizes), default=0.0),
        )

    def place(self, origin: Point, size: Size) -> None:
        cursor = origin.x
        for child in self._children:
            child_size = child.size_that_fits(size)
            child.place(Point(cursor, origin.y), child_size)
            cursor += child_size.width + self._spacing

    def children(self) -> Sequence[View]:
        return self._children


class Grid(View):
    """A two-dimensional layout with aligned columns across all rows."""

    def __init__(self, rows: Sequence[GridRow] = (), horizontal_spacing: float = 12.0,
                 vertical_spacing: float = 8.0, alignment: str = "leading"):
        self._rows = list(rows)
        if not all(isinstance(row, GridRow) for row in self._rows):
            raise TypeError("Grid children must be GridRow instances")
        self.horizontal_spacing = max(0.0, float(horizontal_spacing))
        self.vertical_spacing = max(0.0, float(vertical_spacing))
        self.alignment = alignment
        self._children = self._rows

    def metrics(self, proposal: Size) -> tuple[list[float], list[float]]:
        column_count = max((len(row.children()) for row in self._rows), default=0)
        columns = [0.0] * column_count
        heights: list[float] = []
        for row in self._rows:
            row_height = 0.0
            for index, child in enumerate(row.children()):
                measured = measure(child, proposal)
                columns[index] = max(columns[index], measured.width)
                row_height = max(row_height, measured.height)
            heights.append(row_height)
        return columns, heights

    def size_that_fits(self, proposal: Size) -> Size:
        columns, heights = self.metrics(proposal)
        return Size(
            sum(columns) + self.horizontal_spacing * max(0, len(columns) - 1),
            sum(heights) + self.vertical_spacing * max(0, len(heights) - 1),
        )

    def place(self, origin: Point, size: Size) -> None:
        columns, heights = self.metrics(size)
        y = origin.y
        for row, row_height in zip(self._rows, heights):
            x = origin.x
            for index, child in enumerate(row.children()):
                measured = measure(child, Size(columns[index], row_height))
                child.place(Point(x, y), measured)
                x += columns[index] + self.horizontal_spacing
            y += row_height + self.vertical_spacing

    def children(self) -> Sequence[View]:
        return self._children
