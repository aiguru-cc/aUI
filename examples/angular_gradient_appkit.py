"""Native conic/angular gradients for rings and colorful surfaces."""
from aui import AngularGradient, Color, Size, Text, VStack, Window
from appkit_support import run_window


def content():
    spectrum = AngularGradient(
        [Color.red, Color.yellow, Color.green, Color.blue, Color.purple, Color.red],
        center=(0.5, 0.5),
        start_angle=-90,
        end_angle=270,
        size=Size(300, 180),
    ).corner_radius(24)
    return VStack([Text("AngularGradient"), spectrum], spacing=16)


if __name__ == "__main__":
    run_window("Angular Gradient", content, width=420, height=300)
