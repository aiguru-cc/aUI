"""System environment values and actions on the native AppKit backend."""
from aui import (
    Button, ColorScheme, EnvironmentReader, Link, Text, VStack,
    color_scheme, dismiss, scene_phase,
)
from aui.backends.appkit import AppKitBackend
from appkit_support import run_window


def content():
    return EnvironmentReader(scene_phase, lambda phase: EnvironmentReader(
        color_scheme, lambda scheme: EnvironmentReader(
            dismiss,
            lambda close: VStack([
                Text(f"Scene: {phase.value}"),
                Text(f"Color scheme: {scheme.value}"),
                Link("Open Python", "https://python.org"),
                Button("Close window", close),
            ]).padding(length=20),
        ),
    )).preferred_color_scheme(ColorScheme.DARK)


if __name__ == "__main__":
    run_window("System Environment", content)
