from dataclasses import dataclass

import pytest

from aui import OutlineGroup, Size, State, Text
from aui.backends.ascii import AsciiBackend


@dataclass(frozen=True)
class Node:
    id: str
    name: str
    children: tuple = ()


TREE = (
    Node("projects", "Projects", (
        Node("aui", "aUI", (Node("src", "Sources"), Node("tests", "Tests"))),
    )),
    Node("archive", "Archive"),
)


def make_outline(expanded=None):
    return OutlineGroup(
        TREE,
        children="children",
        content=lambda node: Text(node.name),
        id="id",
        expanded=expanded,
    )


def test_outline_group_starts_collapsed_and_can_expand_recursively():
    outline = make_outline()
    assert [view.content for view in outline.flatten() if isinstance(view, Text)] == [
        "Projects", "Archive"
    ]

    outline.toggle(TREE[0])
    assert "aUI" in [view.content for view in outline.flatten() if isinstance(view, Text)]
    outline.toggle(TREE[0].children[0])
    labels = [view.content for view in outline.flatten() if isinstance(view, Text)]
    assert labels == ["Projects", "aUI", "Sources", "Tests", "Archive"]


def test_outline_group_writes_expansion_binding():
    expanded = State({"projects"})
    outline = make_outline(expanded.binding())

    assert outline.is_expanded(TREE[0])
    outline.toggle(TREE[0])
    assert expanded.value == set()


def test_outline_group_notifies_renderer_for_toggle_and_selection():
    expanded = State(set())
    selected = State(None)
    outline = OutlineGroup(
        TREE, "children", lambda node: Text(node.name), id="id",
        expanded=expanded.binding(), selection=selected.binding(),
    )
    calls = []
    outline._set_interaction_callback(lambda: calls.append("refresh"))

    outline.toggle("projects")
    outline.select("projects")

    assert calls == ["refresh", "refresh"]


def test_outline_group_preserves_content_identity_across_toggle():
    outline = make_outline()
    projects = next(view for view in outline.flatten()
                    if isinstance(view, Text) and view.content == "Projects")
    outline.toggle(TREE[0])
    assert projects is next(view for view in outline.flatten()
                            if isinstance(view, Text) and view.content == "Projects")


def test_outline_group_renders_through_ascii_and_measures():
    outline = make_outline(State({"projects"}).binding())
    rendered = AsciiBackend(width=50, height=8).render(outline)

    assert "Projects" in rendered and "aUI" in rendered and "Archive" in rendered
    assert outline.size_that_fits(Size(400, 500)).height > 0


def test_outline_group_validates_unique_and_hashable_ids():
    duplicate = [Node("same", "One"), Node("same", "Two")]
    with pytest.raises(ValueError, match="unique identities"):
        OutlineGroup(duplicate, "children", lambda node: Text(node.name), id="id")

    with pytest.raises(TypeError, match="hashable"):
        OutlineGroup([{"id": [], "children": []}], "children",
                     lambda node: Text("node"), id="id")


def test_outline_group_builder_must_return_view():
    outline = OutlineGroup(TREE, "children", lambda node: node.name, id="id")
    with pytest.raises(TypeError, match="return a View"):
        outline.children()


def test_outline_default_expansion_depth_and_visible_nodes():
    outline = OutlineGroup(
        TREE, "children", lambda node: Text(node.name), id="id",
        default_expanded_depth=2,
    )
    assert outline.expanded.value == {"projects", "aui"}
    assert [(node.id, depth) for node, depth in outline.visible_nodes] == [
        ("projects", 0), ("aui", 1), ("src", 2), ("tests", 2), ("archive", 0)
    ]
    outline.collapse_all()
    assert outline.expanded.value == set()
    outline.expand_all()
    assert outline.expanded.value == {"projects", "aui"}


def test_outline_single_and_multiple_selection():
    selected = State(None)
    outline = OutlineGroup(
        TREE, "children", lambda node: Text(node.name), id="id",
        selection=selected.binding(),
    )
    outline.select("projects")
    assert selected.value == "projects"
    multiple = State(set())
    outline = OutlineGroup(
        TREE, "children", lambda node: Text(node.name), id="id",
        selection=multiple.binding(),
    )
    outline.select("projects", extending=True)
    outline.select("archive", extending=True)
    assert multiple.value == {"projects", "archive"}
    outline.select("projects", extending=True)
    assert multiple.value == {"archive"}


def test_outline_binding_validation():
    with pytest.raises(TypeError):
        OutlineGroup(TREE, "children", lambda node: Text(node.name), id="id", expanded=set())
    with pytest.raises(TypeError):
        OutlineGroup(TREE, "children", lambda node: Text(node.name), id="id", selection="x")
