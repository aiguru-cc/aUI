"""Adaptive identity-preserving LazyVGrid example."""

from dataclasses import dataclass

from aui import (
    Color, GridItem, GroupBox, LazyHStack, LazyVGrid, Size, Text, VStack, Window,
)
from aui.backends.appkit import AppKitApplication


@dataclass(frozen=True)
class Project:
    id: int
    title: str
    status: str


projects = [Project(i, f"Project {i + 1}", "Active" if i % 2 == 0 else "Draft")
            for i in range(18)]


def project_card(project):
    return GroupBox(
        project.title,
        VStack([
            Text(project.status),
            Text(f"Stable identity: {project.id}"),
        ], spacing=6, alignment="leading"),
    ).padding(length=12).material_background("regular").shadow(radius=5, y=2)


def make_view():
    filters = LazyHStack(
        ["All", "Active", "Draft"], lambda value: Text(value).padding(length=8),
        id=lambda value: value, spacing=10,
    )
    grid = LazyVGrid(
        projects,
        [GridItem.adaptive(minimum=150, maximum=220)],
        project_card,
        id="id",
        spacing=14,
        row_spacing=14,
    )
    return VStack([
        Text("Projects"),
        filters,
        grid,
    ], spacing=18, alignment="leading").padding(length=24)


def main():
    AppKitApplication(
        Window("aUI · Lazy Grid", make_view, default_size=Size(760, 640))
    ).run()


if __name__ == "__main__":
    main()
