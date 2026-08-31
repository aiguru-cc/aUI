"""Remote image loading phases, cache and native NSImage rendering."""

from aui import AsyncImage, Size, Text, VStack, Window
from aui.backends.appkit import AppKitApplication


def make_view():
    return VStack([
        Text("AsyncImage"),
        AsyncImage("https://picsum.photos/480/260", size=Size(480, 260)),
        Text("The event loop remains responsive while the image loads."),
    ], spacing=16, alignment="leading").padding(length=24)


def main():
    AppKitApplication(
        Window("aUI · AsyncImage", make_view, default_size=Size(560, 420))
    ).run()


if __name__ == "__main__":
    main()
