"""Gesture composition, transient GestureState, magnification and rotation."""
from aui import (
    GestureState, MagnifyGesture, RotateGesture, TapGesture, Text, VStack, Window,
)
from appkit_support import run_window


scale = GestureState(1.0)
angle = GestureState(0.0)


magnify = (MagnifyGesture()
           .updating(scale, lambda value, state: value.magnification))
rotate = (RotateGesture()
          .updating(angle, lambda value, state: value.rotation))
double_tap = TapGesture(2).on_ended(lambda value: (scale.reset(), angle.reset()))


def content():
    return VStack([
        Text("Gesture card")
        .scale_effect(scale.value)
        .rotation_effect(angle.value)
        .gesture(magnify.simultaneously(rotate))
        .high_priority_gesture(double_tap),
        Text("Pinch + rotate; double-tap resets"),
    ])


if __name__ == "__main__":
    run_window("Advanced Gestures", content, width=520, height=320)
