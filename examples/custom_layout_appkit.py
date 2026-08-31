"""Custom FlowLayout, AnyLayout switching and layout priorities."""

from aui import (
    AnyLayout, HStackLayout, Layout, LayoutPlacement, Picker, PickerStyle, Point,
    Size, State, Text, VStack, Window,
)
from aui.backends.appkit import AppKitApplication


class FlowLayout(Layout):
    def __init__(self, spacing=10):
        self.spacing = spacing

    def _flow(self, width, subviews, origin=Point()):
        placements = []
        x = origin.x
        y = origin.y
        row_height = 0.0
        for subview in subviews:
            size = subview.size_that_fits(Size(float("inf"), float("inf")))
            if x > origin.x and x + size.width > origin.x + width:
                x = origin.x
                y += row_height + self.spacing
                row_height = 0.0
            placements.append(LayoutPlacement(subview, Point(x, y), size))
            x += size.width + self.spacing
            row_height = max(row_height, size.height)
        return placements, y - origin.y + row_height

    def size_that_fits(self, proposal, subviews):
        width = 520 if proposal.width == float("inf") else proposal.width
        _, height = self._flow(width, subviews)
        return Size(width, height)

    def place_subviews(self, bounds, proposal, subviews):
        return self._flow(bounds.size.width, subviews, bounds.origin)[0]


mode = State("Flow")
tags = ["SwiftUI", "Native AppKit", "Python", "AnyLayout", "Priority", "Adaptive"]


def make_view():
    children = [
        Text(tag).padding(length=8).layout_priority(10 if tag == "Native AppKit" else 0)
        for tag in tags
    ]
    layout = AnyLayout(FlowLayout() if mode.value == "Flow" else HStackLayout(spacing=10))
    return VStack([
        Text("Custom Layout"),
        Picker("", selection=mode.binding(), options=["Flow", "Row"]).picker_style(PickerStyle.SEGMENTED),
        layout(children).frame(width=520, height=150, alignment="topLeading"),
        Text("Offset label").offset(x=18).safe_area_inset("top", 8),
    ], spacing=18, alignment="leading").padding(length=24)


def main():
    AppKitApplication(
        Window("aUI · Layout Protocol", make_view, default_size=Size(620, 440))
    ).run()


if __name__ == "__main__":
    main()
