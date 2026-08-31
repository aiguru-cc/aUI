"""Advanced SwiftUI-like accessibility metadata and actions."""
from aui import Button, Slider, State, Text, VStack, Window
from appkit_support import run_window


rating = State(3)


def adjust(direction):
    delta = 1 if direction == "increment" else -1
    rating.wrapped_value = max(1, min(5, rating.wrapped_value + delta))


def content():
    return VStack([
        Text("Account overview")
        .accessibility_heading(1)
        .accessibility_identifier("account.heading"),
        Text(f"Rating: {rating.wrapped_value}")
        .accessibility_value(f"{rating.wrapped_value} of 5")
        .accessibility_adjustable_action(adjust)
        .accessibility_custom_content("Maximum", "5", "high"),
        Button("Archive", lambda: None)
        .accessibility_hint("Moves this item to the archive")
        .accessibility_action("Archive", lambda: None)
        .accessibility_input_labels(["Archive", "Store"]),
    ])


if __name__ == "__main__":
    run_window("Advanced Accessibility", content, width=560, height=320)
