"""Structural SwiftUI-style views: ForEach, GroupBox and ViewThatFits."""

from dataclasses import dataclass

from aui import (
    AnyView, EmptyView, ForEach, GroupBox, HStack, Size, Text, ViewThatFits,
    VStack, Window,
)
from aui.backends.appkit import AppKitApplication


@dataclass(frozen=True)
class Feature:
    id: int
    name: str
    detail: str


features = [
    Feature(1, "Declarative", "Views describe state"),
    Feature(2, "Native", "Rendered with AppKit"),
    Feature(3, "Adaptive", "Chooses a fitting layout"),
]


def make_view():
    rows = ForEach(
        features,
        lambda feature: HStack([
            Text(feature.name),
            Text(feature.detail),
        ], spacing=18),
        id="id",
        spacing=10,
    )
    adaptive = ViewThatFits([
        HStack([Text("Wide layout"), Text("All information visible")], spacing=18),
        VStack([Text("Compact layout"), Text("Information stacked")], spacing=6),
    ], axis="horizontal")
    return VStack([
        GroupBox("Features", rows),
        GroupBox("Adaptive content", adaptive),
        AnyView(Text("Type-erased content")),
        EmptyView(),
    ], spacing=20, alignment="leading").padding(length=24)


def main():
    AppKitApplication(
        Window("aUI · Structural Views", make_view, default_size=Size(620, 480))
    ).run()


if __name__ == "__main__":
    main()
