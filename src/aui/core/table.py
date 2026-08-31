"""Declarative tabular data views."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

from .geometry import Point, Size
from .state import Binding
from .view import View


@dataclass(frozen=True)
class SortOrder:
    key: str
    ascending: bool = True


@dataclass(frozen=True)
class TableColumn:
    title: str
    key: str
    width: Optional[float] = None
    value: Optional[Callable[[Any], Any]] = None
    minimum_width: float = 40.0
    maximum_width: float = float("inf")
    visible: bool | Binding[bool] = True

    def __post_init__(self):
        if self.minimum_width <= 0 or self.minimum_width > self.maximum_width:
            raise ValueError("table column widths must satisfy 0 < minimum <= maximum")

    @property
    def is_visible(self) -> bool:
        return bool(self.visible.wrapped_value if isinstance(self.visible, Binding) else self.visible)

    def resolved_width(self, fallback: float = 140.0) -> float:
        value = self.width if self.width is not None else fallback
        return min(float(self.maximum_width), max(float(self.minimum_width), float(value)))

    def get_value(self, row: Any) -> Any:
        if self.value is not None:
            return self.value(row)
        if isinstance(row, dict):
            return row.get(self.key, "")
        return getattr(row, self.key, "")


class Table(View):
    """A selectable, sortable collection of rows and typed columns."""

    def __init__(self, rows: Sequence[Any], columns: Sequence[TableColumn],
                 selection: Optional[Binding] = None, id_key: str = "id",
                 sort_order: Optional[Binding[SortOrder]] = None,
                 row_height: float = 28.0, min_height: float = 160.0,
                 allows_multiple_selection: Optional[bool] = None,
                 alternating_rows: bool = True, empty_message: str = "No Rows"):
        self.rows = list(rows)
        self.columns = list(columns)
        if not self.columns or not all(isinstance(column, TableColumn) for column in self.columns):
            raise ValueError("Table requires at least one TableColumn")
        keys = [column.key for column in self.columns]
        if len(keys) != len(set(keys)):
            raise ValueError("Table column keys must be unique")
        self.selection = selection
        self.id_key = id_key
        self.sort_order = sort_order
        if selection is not None and not isinstance(selection, Binding):
            raise TypeError("Table selection must be a Binding")
        if sort_order is not None and not isinstance(sort_order, Binding):
            raise TypeError("Table sort_order must be a Binding")
        current_selection = selection.wrapped_value if selection is not None else None
        self.allows_multiple_selection = (
            isinstance(current_selection, (set, frozenset))
            if allows_multiple_selection is None else bool(allows_multiple_selection)
        )
        self.alternating_rows = bool(alternating_rows)
        self.empty_message = str(empty_message)
        self.row_height = max(18.0, float(row_height))
        self.min_height = max(self.row_height * 2, float(min_height))
        self._cursor_index = 0
        self._children = []

    def row_id(self, row: Any) -> Any:
        if isinstance(row, dict):
            return row.get(self.id_key)
        return getattr(row, self.id_key, None)

    @property
    def displayed_rows(self) -> list[Any]:
        rows = list(self.rows)
        orders = self.sort_orders
        for order in reversed(orders):
            column = next((item for item in self.columns if item.key == order.key), None)
            if column is not None:
                rows.sort(key=lambda row: (column.get_value(row) is None,
                                           column.get_value(row)),
                          reverse=not order.ascending)
        return rows

    @property
    def sort_orders(self) -> tuple[SortOrder, ...]:
        value = self.sort_order.wrapped_value if self.sort_order is not None else None
        if value is None: return ()
        if isinstance(value, SortOrder): return (value,)
        values = tuple(value)
        if not all(isinstance(item, SortOrder) for item in values):
            raise TypeError("Table sort order must contain SortOrder values")
        return values

    @property
    def visible_columns(self) -> list[TableColumn]:
        return [column for column in self.columns if column.is_visible]

    def select_row(self, index: int, extending: bool = False) -> None:
        rows = self.displayed_rows
        if self.selection is not None and 0 <= index < len(rows):
            row_id = self.row_id(rows[index])
            if self.allows_multiple_selection:
                current = set(self.selection.wrapped_value or ())
                if extending and row_id in current:
                    current.remove(row_id)
                elif extending:
                    current.add(row_id)
                else:
                    current = {row_id}
                self.selection.wrapped_value = current
            else:
                self.selection.wrapped_value = row_id

    def set_sort(self, key: str, ascending: Optional[bool] = None,
                 additive: bool = False) -> None:
        if key not in {column.key for column in self.columns}:
            raise KeyError(key)
        if self.sort_order is None:
            return
        current = list(self.sort_orders)
        existing = next((item for item in current if item.key == key), None)
        value = SortOrder(key, not existing.ascending if ascending is None and existing
                          else True if ascending is None else bool(ascending))
        values = ([item for item in current if item.key != key] + [value]
                  if additive else [value])
        original = self.sort_order.wrapped_value
        self.sort_order.wrapped_value = values[0] if isinstance(original, SortOrder) else values

    @property
    def cursor_index(self) -> int:
        return self._cursor_index

    def move_selection(self, delta: int) -> None:
        if self.displayed_rows:
            self._cursor_index = max(
                0, min(len(self.displayed_rows) - 1, self._cursor_index + int(delta))
            )
            self.select_row(self._cursor_index)

    def size_that_fits(self, proposal: Size) -> Size:
        natural_width = sum(column.resolved_width() for column in self.visible_columns)
        width = min(natural_width, proposal.width) if proposal.width != float("inf") else natural_width
        natural_height = 28.0 + self.row_height * len(self.rows)
        height = max(self.min_height, natural_height)
        if proposal.height != float("inf"):
            height = min(height, proposal.height)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self):
        return self._children


__all__ = ["SortOrder", "Table", "TableColumn"]
