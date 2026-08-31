import pytest

from aui import Text, VStack
from aui.core.reconciliation import ChangeKind, reconcile, snapshot


def test_explicit_ids_survive_sibling_reordering_as_moves():
    old = VStack([Text("A").id("a"), Text("B").id("b")])
    new = VStack([Text("B").id("b"), Text("A").id("a")])
    changes = reconcile(old, new)
    kinds = [change.kind for change in changes]
    assert kinds.count(ChangeKind.MOVE) == 2
    assert ChangeKind.INSERT not in kinds
    assert ChangeKind.REMOVE not in kinds


def test_unidentified_children_use_structural_type_and_position():
    tree = VStack([Text("A"), Text("B")])
    paths = list(snapshot(tree))
    assert len(paths) == 3
    assert paths[1][-1][1] == 0
    assert paths[2][-1][1] == 1


def test_insertions_are_parent_first_and_removals_child_first():
    empty = VStack([])
    nested = VStack([VStack([Text("child")]).id("group")])
    inserts = reconcile(empty, nested)
    inserted_paths = [change.path for change in inserts if change.kind == ChangeKind.INSERT]
    assert inserted_paths == sorted(inserted_paths, key=lambda path: (len(path), repr(path)))
    removals = reconcile(nested, empty)
    removed_paths = [change.path for change in removals if change.kind == ChangeKind.REMOVE]
    assert removed_paths == sorted(removed_paths, key=lambda path: (-len(path), repr(path)))


def test_duplicate_explicit_sibling_ids_are_rejected():
    tree = VStack([Text("A").id("same"), Text("B").id("same")])
    with pytest.raises(ValueError, match="duplicate sibling view id"):
        snapshot(tree)
