"""Programmatic native scrolling with stable view ids."""

from aui import (
    Button, EdgeInsets, HStack, ScrollIndicatorVisibility, ScrollTargetBehavior,
    ScrollViewReader, Size, State, Text, VStack, Window,
)
from aui.backends.appkit import AppKitApplication


position = State(None)


def reader_content(proxy):
    controls = HStack([
        Button("Top", lambda: proxy.scroll_to(0)),
        Button("Center row 25", lambda: proxy.scroll_to(25, anchor="center")),
        Button("Bottom", lambda: proxy.scroll_to(49, anchor="bottom")),
        Button("Bind row 40", lambda: setattr(position, "value", 40)),
    ], spacing=10)
    rows = [
        Text(f"Row {index:02d} · stable id={index}").padding(length=10).id(index)
        for index in range(50)
    ]
    return VStack([controls, *rows], spacing=4, alignment="leading").padding(length=20)


def make_view():
    return (
        ScrollViewReader(reader_content)
        .scroll_indicators(ScrollIndicatorVisibility.VISIBLE)
        .scroll_target_behavior(ScrollTargetBehavior.VIEW_ALIGNED)
        .content_margins(EdgeInsets.symmetric(horizontal=8, vertical=6))
        .scroll_position(position.binding(), anchor="center")
    )


def main():
    AppKitApplication(
        Window("aUI · ScrollViewReader", make_view, default_size=Size(560, 520))
    ).run()


if __name__ == "__main__":
    main()
