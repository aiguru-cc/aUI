"""SF Symbol variants, palette rendering, and image interpolation."""
from aui import Color, HStack, Image, ImageInterpolation, ImageScale, SymbolRenderingMode, Text, VStack, Window
from appkit_support import run_window


def content():
    symbols = [
        Image(system_name="star", size=64).symbol_variant("circle", "fill")
            .image_scale(ImageScale.LARGE).symbol_weight("bold"),
        Image(system_name="cloud.sun", size=64).symbol_rendering_mode(
            SymbolRenderingMode.PALETTE, [Color.blue, Color.yellow]
        ),
        Image(system_name="person.3", size=64).symbol_rendering_mode(
            SymbolRenderingMode.HIERARCHICAL
        ).interpolation(ImageInterpolation.HIGH),
    ]
    return VStack([Text("SF Symbol Rendering"), HStack(symbols, spacing=28)], spacing=20)


if __name__ == "__main__":
    run_window("Symbol Rendering", content, width=420, height=220)
