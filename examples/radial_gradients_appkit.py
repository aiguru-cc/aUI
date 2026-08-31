"""Native radial and elliptical gradients with inner/outer radii."""
from aui import Color, EllipticalGradient, HStack, RadialGradient, Size, Text, VStack, Window
from appkit_support import run_window


def content():
    radial = RadialGradient(
        [Color.white, Color.blue, Color.indigo],
        start_radius=18,
        end_radius=110,
        size=Size(190, 150),
    ).corner_radius(20)
    elliptical = EllipticalGradient(
        [Color.yellow, Color.orange, Color.red],
        start_radius_fraction=0.12,
        end_radius_fraction=0.65,
        size=Size(190, 150),
    ).corner_radius(20)
    return VStack([
        Text("Radial Gradient Family"),
        HStack([radial, elliptical], spacing=20),
    ], spacing=16)


if __name__ == "__main__":
    run_window("Radial Gradients", content, width=470, height=270)
