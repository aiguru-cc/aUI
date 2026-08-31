"""GeometryReader adaptive layout and coordinate-space example."""

from aui import GeometryReader, HStack, Size, Text, VStack, Window
from aui.backends.appkit import AppKitApplication


def adaptive_content(proxy):
    summary = Text(
        f"{int(proxy.size.width)} × {int(proxy.size.height)} pt · "
        f"global x={int(proxy.frame('global').min_x)}"
    )
    cards = [Text("Sidebar"), Text("Content"), Text("Inspector")]
    layout = HStack(cards, spacing=16) if proxy.size.width >= 700 else VStack(cards, spacing=12)
    return VStack([
        Text("GeometryReader"),
        summary,
        layout,
    ], spacing=18, alignment="leading").padding(length=24)


def main():
    AppKitApplication(
        Window(
            "aUI · Adaptive Geometry",
            lambda: GeometryReader(adaptive_content),
            default_size=Size(820, 480),
        )
    ).run()


if __name__ == "__main__":
    main()
