"""Native SF Symbols driven by normalized variable values."""
from aui import HStack, Image, ImageScale, Text, VStack, Window
from appkit_support import run_window


def content():
    values = (0.0, 0.25, 0.5, 0.75, 1.0)
    speakers = [
        Image(system_name="speaker.wave.3", variable_value=value, size=44)
            .image_scale(ImageScale.LARGE)
        for value in values
    ]
    gauges = [
        Image(system_name="chart.bar.fill", variable_value=value, size=44)
        for value in values
    ]
    return VStack([
        Text("Variable SF Symbols"),
        HStack(speakers, spacing=18),
        HStack(gauges, spacing=18),
    ], spacing=22)


if __name__ == "__main__":
    run_window("Variable Symbols", content, width=430, height=250)
