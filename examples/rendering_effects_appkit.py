"""Native Core Animation/Core Image visual effects showcase."""
from aui import (
    BlendMode, Color, HStack, RoundedRectangle, Text, VStack, Window,
)
from appkit_support import run_window


def content():
    card = (VStack([
        Text("Native rendering").rotation_effect(-2),
        Text("Core Animation + Core Image").saturation(1.4),
    ])
    .padding(length=18)
    .background(Color.rgb(225, 235, 255))
    .clip_shape(RoundedRectangle(18))
    .scale_effect(1.04)
    .drawing_group())

    return VStack([
        card,
        HStack([
            Text("Blur").blur(1.2),
            Text("Gray").grayscale(),
            Text("Contrast").contrast(1.5),
        ]).compositing_group(),
        Text("Overlay blend").blend_mode(BlendMode.OVERLAY),
    ])


if __name__ == "__main__":
    run_window("Rendering Effects", content, width=560, height=320)
