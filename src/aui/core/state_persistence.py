"""Restore local control state when a declarative view factory rebuilds."""
from __future__ import annotations

from .components import DisclosureGroup, List, NavigationRail, TabView
from .reconciliation import explicit_view_id
from .view import View


def restore_local_state(previous: View | None, current: View) -> None:
    """Carry unbound interaction state across structurally compatible rebuilds.

    Bound state remains the application's source of truth.  This only mirrors
    SwiftUI's identity behaviour for controls that deliberately use their
    internal selection/expansion/scroll state.
    """
    if previous is None:
        return
    before, after = _state_nodes(previous), _state_nodes(current)
    for path in before.keys() & after.keys():
        old, new = before[path], after[path]
        if type(old) is not type(new):
            continue
        if isinstance(new, TabView) and new.selection is None:
            new._internal = old._active_index()
        elif isinstance(new, DisclosureGroup) and new.is_expanded is None:
            new._internal_expanded = old.expanded
        elif isinstance(new, List) and new._scroll_offset is None:
            new._internal_offset = old.current_offset()
        elif isinstance(new, NavigationRail) and new.selected_index is None:
            new._internal_index = old.active_index


def _state_nodes(root: View) -> dict[tuple, View]:
    """Collect stateful nodes without descending through virtualized List rows."""
    result = {}

    def visit(view: View, path: tuple) -> None:
        result[path] = view
        if isinstance(view, List):
            return
        seen_ids = set()
        for index, child in enumerate(view.children()):
            identity = explicit_view_id(child)
            if identity is not None:
                if identity in seen_ids:
                    raise ValueError(f"duplicate sibling view id: {identity!r}")
                seen_ids.add(identity)
                segment = ("id", identity)
            else:
                segment = (f"{type(child).__module__}.{type(child).__qualname__}", index)
            visit(child, path + (segment,))

    identity = explicit_view_id(root)
    segment = ("id", identity) if identity is not None else (
        f"{type(root).__module__}.{type(root).__qualname__}", 0)
    visit(root, (segment,))
    return result
