"""Native AppKit example for SwiftUI-style LazyHGrid."""
from aui import GridItem, LazyHGrid, ScrollView, Text, VStack, Window
from appkit_support import run_window


def tile(index):
    return VStack([Text(f"Card {index}"), Text("Native Python")], spacing=4).frame(
        width=120, height=72
    )


def content():
    grid = LazyHGrid(
        range(12),
        [GridItem.fixed(72, spacing=16, alignment="top"),
         GridItem.flexible(64, 96, alignment="bottom")],
        tile,
        spacing=12,
        column_spacing=16,
    )
    return VStack([
        Text("LazyHGrid"),
        ScrollView(grid, axis="horizontal"),
    ], spacing=12)


if __name__ == "__main__":
    run_window("Horizontal Grid", content, width=720, height=300)
