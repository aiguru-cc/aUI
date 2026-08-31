"""Backend-neutral view identity and incremental tree reconciliation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Hashable, Optional

from .scrolling import IDModifier
from .view import View, _ModifiedContent


NodePath = tuple[tuple[str, Hashable], ...]


class ChangeKind(str, Enum):
    INSERT = "insert"
    REMOVE = "remove"
    UPDATE = "update"
    MOVE = "move"


@dataclass(frozen=True)
class ViewNode:
    path: NodePath
    parent: Optional[NodePath]
    index: int
    view: View
    explicit_id: Optional[Hashable]


@dataclass(frozen=True)
class TreeChange:
    kind: ChangeKind
    path: NodePath
    old: Optional[ViewNode] = None
    new: Optional[ViewNode] = None


def explicit_view_id(view: View) -> Optional[Hashable]:
    """Return the outermost explicit ``.id`` attached to a view."""
    node = view
    while isinstance(node, _ModifiedContent):
        if isinstance(node._modifier, IDModifier):
            return node._modifier.value
        node = node._content
    return None


def snapshot(root: View) -> dict[NodePath, ViewNode]:
    """Capture stable structural paths for a declarative view tree."""
    result: dict[NodePath, ViewNode] = {}

    def visit(view: View, path: NodePath, parent: Optional[NodePath], index: int) -> None:
        identity = explicit_view_id(view)
        result[path] = ViewNode(path, parent, index, view, identity)
        seen_ids: set[Hashable] = set()
        for child_index, child in enumerate(view.children()):
            child_id = explicit_view_id(child)
            if child_id is not None:
                if child_id in seen_ids:
                    raise ValueError(f"duplicate sibling view id: {child_id!r}")
                seen_ids.add(child_id)
                segment = ("id", child_id)
            else:
                segment = (f"{type(child).__module__}.{type(child).__qualname__}", child_index)
            visit(child, path + (segment,), path, child_index)

    root_segment = ("id", explicit_view_id(root)) if explicit_view_id(root) is not None else (
        f"{type(root).__module__}.{type(root).__qualname__}", 0
    )
    visit(root, (root_segment,), None, 0)
    return result


def reconcile(old_root: View, new_root: View) -> list[TreeChange]:
    """Return deterministic structural changes from ``old_root`` to ``new_root``."""
    old = snapshot(old_root)
    new = snapshot(new_root)
    old_paths, new_paths = set(old), set(new)
    changes: list[TreeChange] = []

    for path in sorted(old_paths - new_paths, key=lambda value: (-len(value), repr(value))):
        changes.append(TreeChange(ChangeKind.REMOVE, path, old=old[path]))
    for path in sorted(new_paths - old_paths, key=lambda value: (len(value), repr(value))):
        changes.append(TreeChange(ChangeKind.INSERT, path, new=new[path]))
    for path in sorted(old_paths & new_paths, key=repr):
        before, after = old[path], new[path]
        if before.index != after.index:
            changes.append(TreeChange(ChangeKind.MOVE, path, before, after))
        if type(before.view) is not type(after.view) or before.view is not after.view:
            changes.append(TreeChange(ChangeKind.UPDATE, path, before, after))
    return changes


__all__ = [
    "ChangeKind", "NodePath", "TreeChange", "ViewNode", "explicit_view_id",
    "reconcile", "snapshot",
]
