"""SF Symbols and in-memory images with SwiftUI-style scaling modes."""

import base64

from aui import Color, HStack, Image, Size, Text, VStack, Window
from aui.backends.appkit import AppKitApplication


tiny_png = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF"
    "gAIXVclZrgAAAABJRU5ErkJggg=="
)


def make_view():
    symbols = HStack([
        Image(system_name="star.fill", color=Color.yellow, size=40, label="Favorite"),
        Image(system_name="heart.fill", color=Color.red, size=40, label="Liked"),
        Image(system_name="sparkles", color=Color.purple, size=40, decorative=True),
    ], spacing=20)
    memory_image = Image.from_data(
        tiny_png, size=Size(180, 100), label="Embedded PNG"
    ).scaled_to_fill()
    return VStack([
        Text("Image Sources"),
        symbols,
        memory_image,
        Text("Images can also load directly from pathlib.Path."),
    ], spacing=18, alignment="leading").padding(length=24)


def main():
    AppKitApplication(
        Window("aUI · Images", make_view, default_size=Size(520, 380))
    ).run()


if __name__ == "__main__":
    main()
