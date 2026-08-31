"""Expandable hierarchical sidebar data with OutlineGroup."""

from dataclasses import dataclass

from aui import OutlineGroup, Size, State, Text, VStack, Window
from aui.backends.appkit import AppKitApplication


@dataclass(frozen=True)
class Node:
    id: str
    title: str
    children: tuple = ()


library = (
    Node("favorites", "Favorites", (
        Node("recents", "Recents"),
        Node("downloads", "Downloads"),
    )),
    Node("projects", "Projects", (
        Node("aui", "aUI", (
            Node("sources", "Sources"),
            Node("tests", "Tests"),
        )),
    )),
)
expanded = State({"favorites", "projects", "aui"})
selection = State({"recents"})


def make_view():
    outline = OutlineGroup(
        library,
        children="children",
        content=lambda node: Text(node.title),
        id="id",
        expanded=expanded.binding(),
        selection=selection.binding(),
        allows_multiple_selection=True,
        spacing=6,
    )
    return VStack([Text("Project Navigator"), outline], spacing=16,
                  alignment="leading").padding(length=24)


def main():
    AppKitApplication(
        Window("aUI · OutlineGroup", make_view, default_size=Size(440, 520))
    ).run()


if __name__ == "__main__":
    main()
