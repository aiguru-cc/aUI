"""Structural and adaptive views inspired by SwiftUI."""
from __future__ import annotations

import builtins
from typing import Any, Callable, Optional, Sequence

from .geometry import Point, Size
from .state import Binding, State
from .view import View


class EmptyView(View):
    """A view that occupies no space and renders nothing."""

    def __init__(self):
        self._children = []

    def size_that_fits(self, proposal: Size) -> Size:
        return Size()

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self):
        return self._children


class AnyView(View):
    """Type-erased storage for one concrete view."""

    def __init__(self, content: View):
        if not isinstance(content, View):
            raise TypeError("AnyView content must be a View")
        self.content = content
        self._children = [content]

    def size_that_fits(self, proposal: Size) -> Size:
        return self.content.size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        self.content.place(origin, size)

    def children(self):
        return self._children


class ForEach(View):
    """Build views from identified data while preserving identity by key."""

    def __init__(self, data: Sequence[Any], content: Callable[[Any], View],
                 id: Optional[Callable[[Any], Any] | str] = None,
                 spacing: float = 0.0):
        if not callable(content):
            raise TypeError("ForEach content must be callable")
        self.data = list(data)
        self.content = content
        self.id = id
        self._spacing = max(0.0, float(spacing))
        self._cache: dict[Any, View] = {}
        keys = [self.key_for(item, index) for index, item in enumerate(self.data)]
        if len(keys) != len(set(keys)):
            raise ValueError("ForEach data must have unique identities")

    def key_for(self, item: Any, index: int) -> Any:
        if callable(self.id):
            key = self.id(item)
        elif isinstance(self.id, str):
            key = item.get(self.id) if isinstance(item, dict) else getattr(item, self.id)
        elif hasattr(item, "id"):
            key = item.id
        else:
            key = index
        try:
            hash(key)
        except TypeError as exc:
            raise TypeError("ForEach identities must be hashable") from exc
        return key

    def children(self):
        views = self.children_range(0, len(self.data))
        live_keys = {self.key_for(item, index) for index, item in enumerate(self.data)}
        self._cache = {key: view for key, view in self._cache.items() if key in live_keys}
        return views

    def children_range(self, start: int, end: int):
        """Build only a half-open data range while retaining cached identities."""
        lo = max(0, int(start))
        hi = max(lo, min(int(end), len(self.data)))
        views = []
        for index in range(lo, hi):
            item = self.data[index]
            key = self.key_for(item, index)
            if key not in self._cache:
                view = self.content(item)
                if not isinstance(view, View):
                    raise TypeError("ForEach content must return a View")
                self._cache[key] = view
            views.append(self._cache[key])
        return views

    def size_that_fits(self, proposal: Size) -> Size:
        sizes = [child.size_that_fits(Size(proposal.width, float("inf")))
                 for child in self.children()]
        return Size(max((size.width for size in sizes), default=0.0),
                    sum(size.height for size in sizes) +
                    self._spacing * max(0, len(sizes) - 1))

    def place(self, origin: Point, size: Size) -> None:
        y = origin.y
        for child in self.children():
            measured = child.size_that_fits(Size(size.width, float("inf")))
            child.place(Point(origin.x, y), measured)
            y += measured.height + self._spacing


class ViewThatFits(View):
    """Select the first candidate whose measured size fits the proposal."""

    def __init__(self, children: Sequence[View], axis: str = "both"):
        self._children = list(children)
        if not self._children or not all(isinstance(child, View) for child in self._children):
            raise ValueError("ViewThatFits requires at least one View")
        if axis not in ("both", "horizontal", "vertical"):
            raise ValueError("axis must be both, horizontal, or vertical")
        self.axis = axis

    def selected(self, proposal: Size) -> View:
        for child in self._children:
            size = child.size_that_fits(proposal)
            width_ok = self.axis == "vertical" or size.width <= proposal.width
            height_ok = self.axis == "horizontal" or size.height <= proposal.height
            if width_ok and height_ok:
                return child
        return self._children[-1]

    def size_that_fits(self, proposal: Size) -> Size:
        return self.selected(proposal).size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        self.selected(size).place(origin, size)

    def children(self):
        return self._children


class GroupBox(View):
    """A labeled visual group for related content."""

    def __init__(self, label: Any, content: View, spacing: float = 10.0):
        from .components import Text
        self.label = label if isinstance(label, View) else Text(str(label))
        if not isinstance(content, View):
            raise TypeError("GroupBox content must be a View")
        self.content = content
        self._spacing = max(0.0, float(spacing))
        self._children = [self.label, content]

    def size_that_fits(self, proposal: Size) -> Size:
        label_size = self.label.size_that_fits(proposal)
        content_size = self.content.size_that_fits(proposal)
        return Size(max(label_size.width, content_size.width),
                    label_size.height + self._spacing + content_size.height)

    def place(self, origin: Point, size: Size) -> None:
        label_size = self.label.size_that_fits(size)
        self.label.place(origin, label_size)
        self.content.place(Point(origin.x, origin.y + label_size.height + self._spacing),
                           self.content.size_that_fits(size))

    def children(self):
        return self._children


class OutlineGroup(View):
    """Render identified hierarchical data with bindable disclosure state."""

    def __init__(self, data: Sequence[Any], children: Callable[[Any], Sequence[Any]] | str,
                 content: Callable[[Any], View], id: Callable[[Any], Any] | str | None = None,
                 expanded: Optional[Binding[set]] = None, indentation: float = 18.0,
                 spacing: float = 4.0, selection: Optional[Binding] = None,
                 allows_multiple_selection: Optional[bool] = None,
                 default_expanded_depth: int = 0):
        if not callable(content):
            raise TypeError("OutlineGroup content must be callable")
        if not (callable(children) or isinstance(children, str)):
            raise TypeError("OutlineGroup children must be callable or an attribute name")
        self.data = list(data)
        self._children_source = children
        self._content_builder = content
        self.id = id
        self.indentation = max(0.0, float(indentation))
        self._spacing = max(0.0, float(spacing))
        if expanded is not None and not isinstance(expanded, Binding):
            raise TypeError("OutlineGroup expanded must be a Binding")
        if expanded is not None and not isinstance(expanded.wrapped_value, (set, frozenset)):
            raise TypeError("OutlineGroup expanded Binding must contain a set")
        if selection is not None and not isinstance(selection, Binding):
            raise TypeError("OutlineGroup selection must be a Binding")
        self.selection = selection
        selected = selection.wrapped_value if selection is not None else None
        self.allows_multiple_selection = (
            isinstance(selected, (set, frozenset)) if allows_multiple_selection is None
            else bool(allows_multiple_selection)
        )
        self.default_expanded_depth = max(0, int(default_expanded_depth))
        self._content_cache: dict[Any, View] = {}
        self._tree = None
        self._interaction_callback: Optional[Callable[[], None]] = None
        self._validate_identities()
        defaults = self._keys_before_depth(self.default_expanded_depth)
        self._expansion_state = State(defaults) if expanded is None else None
        self.expanded = expanded or self._expansion_state.binding()

    def key_for(self, item: Any) -> Any:
        if callable(self.id):
            key = self.id(item)
        elif isinstance(self.id, str):
            key = item.get(self.id) if isinstance(item, dict) else getattr(item, self.id)
        elif isinstance(item, dict) and "id" in item:
            key = item["id"]
        elif hasattr(item, "id"):
            key = item.id
        else:
            key = builtins.id(item)
        try:
            hash(key)
        except TypeError as exc:
            raise TypeError("OutlineGroup identities must be hashable") from exc
        return key

    def children_for(self, item: Any) -> list[Any]:
        source = self._children_source
        if callable(source):
            value = source(item)
        elif isinstance(item, dict):
            value = item.get(source, ())
        else:
            value = getattr(item, source, ())
        return list(value or ())

    def _validate_identities(self) -> None:
        seen = set()

        def visit(items):
            for item in items:
                key = self.key_for(item)
                if key in seen:
                    raise ValueError("OutlineGroup data must have unique identities")
                seen.add(key)
                visit(self.children_for(item))

        visit(self.data)

    def _keys_before_depth(self, maximum_depth: int) -> set:
        keys = set()
        def visit(items, depth):
            if depth >= maximum_depth: return
            for item in items:
                if self.children_for(item): keys.add(self.key_for(item))
                visit(self.children_for(item), depth + 1)
        visit(self.data, 0)
        return keys

    @property
    def all_items(self) -> list[Any]:
        result = []
        def visit(items):
            for item in items:
                result.append(item); visit(self.children_for(item))
        visit(self.data)
        return result

    def item_for_key(self, key: Any) -> Any:
        return next((item for item in self.all_items if self.key_for(item) == key), None)

    def _coerce_key(self, item_or_key: Any) -> Any:
        try:
            if self.item_for_key(item_or_key) is not None:
                return item_or_key
        except (TypeError, AttributeError):
            pass
        return self.key_for(item_or_key)

    @property
    def visible_nodes(self) -> list[tuple[Any, int]]:
        result = []
        def visit(items, depth):
            for item in items:
                result.append((item, depth))
                if self.key_for(item) in self.expanded.value:
                    visit(self.children_for(item), depth + 1)
        visit(self.data, 0)
        return result

    def is_expanded(self, item_or_key: Any) -> bool:
        key = self._coerce_key(item_or_key)
        return key in self.expanded.value

    def toggle(self, item_or_key: Any) -> None:
        self._toggle_key(self._coerce_key(item_or_key))

    def _toggle_key(self, key: Any) -> None:
        values = set(self.expanded.value)
        values.remove(key) if key in values else values.add(key)
        self.expanded.value = values
        self._tree = None
        self._notify_interaction()

    def expand_all(self) -> None:
        self.expanded.value = {self.key_for(item) for item in self.all_items
                               if self.children_for(item)}
        self._tree = None

    def collapse_all(self) -> None:
        self.expanded.value = set()
        self._tree = None

    def select(self, item_or_key: Any, extending: bool = False) -> None:
        if self.selection is None: return
        key = self._coerce_key(item_or_key)
        if self.allows_multiple_selection:
            values = set(self.selection.wrapped_value or ())
            if extending and key in values: values.remove(key)
            elif extending: values.add(key)
            else: values = {key}
            self.selection.wrapped_value = values
        else:
            self.selection.wrapped_value = key
        self._notify_interaction()

    def _set_interaction_callback(self, callback: Optional[Callable[[], None]]) -> None:
        """Set the renderer-owned invalidation hook for native interactions."""
        self._interaction_callback = callback

    def _notify_interaction(self) -> None:
        if self._interaction_callback is not None:
            self._interaction_callback()

    def _content_for(self, item: Any) -> View:
        key = self.key_for(item)
        if key not in self._content_cache:
            view = self._content_builder(item)
            if not isinstance(view, View):
                raise TypeError("OutlineGroup content must return a View")
            self._content_cache[key] = view
        return self._content_cache[key]

    def _rows(self, items: Sequence[Any], depth: int = 0) -> list[View]:
        from .components import Button
        from .layout import HStack

        rows = []
        for item in items:
            key = self.key_for(item)
            descendants = self.children_for(item)
            is_open = key in self.expanded.value
            prefix = Button("▾" if is_open else "▸",
                            action=lambda value=key: self._toggle_key(value)) if descendants else None
            parts = ([prefix] if prefix is not None else []) + [self._content_for(item)]
            row = HStack(parts, spacing=6.0, alignment="center")
            if depth:
                from .geometry import EdgeInsets
                row = row.padding(edges=EdgeInsets(leading=self.indentation * depth))
            rows.append(row)
            if descendants and is_open:
                rows.extend(self._rows(descendants, depth + 1))
        return rows

    def content_view(self) -> View:
        from .layout import VStack
        if self._tree is None:
            self._tree = VStack(self._rows(self.data), spacing=self._spacing,
                                alignment="leading")
        return self._tree

    def size_that_fits(self, proposal: Size) -> Size:
        return self.content_view().size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        self.content_view().place(origin, size)

    def children(self):
        return [self.content_view()]


__all__ = ["AnyView", "EmptyView", "ForEach", "GroupBox", "OutlineGroup", "ViewThatFits"]
