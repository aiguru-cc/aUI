"""Native gradients, materials, overlays, shadows and vector shapes."""

from aui import (
    Capsule, Circle, Color, Ellipse, HStack, LinearGradient, Material,
    RadialGradient, RoundedRectangle, Size, Text, VStack, Window, ZStack,
)
from aui.backends.appkit import AppKitApplication


def make_view():
    hero = ZStack([
        LinearGradient(
            [Color.indigo, Color.purple, Color.pink],
            start_point=(0, 0), end_point=(1, 1), size=Size(440, 150),
        ),
        VStack([
            Text("Native visual effects").foreground_color(Color.white),
            Text("Core Animation · AppKit material").foreground_color(Color.white),
        ], spacing=8),
    ]).shadow(radius=14, y=6).overlay(
        Capsule(size=Size(54, 22)).fill(Color.orange), alignment="topTrailing"
    )

    shapes = HStack([
        Circle(size=Size(54, 54)).fill(Color.indigo),
        Ellipse(size=Size(86, 54)).fill(Color.teal),
        RoundedRectangle(corner_radius=12, size=Size(86, 54)).fill(Color.orange),
        RadialGradient([Color.white, Color.blue], size=Size(64, 54)),
    ], spacing=14)

    card = VStack([
        Text("Material card"),
        Text("Automatically follows the active macOS appearance."),
    ], spacing=8, alignment="leading").padding(length=20).material_background(
        Material.REGULAR
    ).shadow(radius=10, y=4)

    return VStack([hero, shapes, card], spacing=24, alignment="leading").padding(length=28)


def main():
    AppKitApplication(
        Window("aUI · Visual Effects", make_view, default_size=Size(560, 520))
    ).run()


if __name__ == "__main__":
    main()
