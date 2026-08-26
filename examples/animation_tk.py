"""Example: animated color transitions with aUI (T19, ADR-0006).

Run:  python3 examples/animation_tk.py

Demonstrates SwiftUI-style animation:
  - ``Animation`` value type (easeInOut / linear / spring)
  - ``with_animation`` context manager wrapping a state change
  - ``.animation()`` modifier marking which view should animate

The Tk backend interpolates the foreground color over the animation duration
(frame-driven via ``after``), instead of snapping to the new value.
"""
import _bootstrap  # noqa: F401
from aui import Animation, Button, Text, VStack, with_animation, animation
from aui.core.geometry import Color, Font
from aui.core.modifiers import padding
from aui.core.state import State
from aui.backends.tk import TkBackend


def _next_color():
    with with_animation(Animation.ease_in_out(0.4)):
        color_index._set((color_index.wrapped_value + 1) % len(palette))


color_index = State(0)
palette = [Color.red, Color.blue, Color.green, Color.orange, Color.purple]


def main():

    def make_view():
        color = palette[color_index.wrapped_value % len(palette)]
        return VStack(
            [
                padding(Text("Animated Color", font=Font.title())),
                animation(
                    padding(Text("Hello, aUI!", color=color, font=Font.headline())),
                    Animation.ease_in_out(0.4),
                ),
                Button(
                    "Next Color",
                    action=lambda: _next_color(),
                ),
            ],
            spacing=8,
        )

    backend = TkBackend()
    backend.render(make_view())

    def on_state_change():
        backend.render(make_view())

    color_index._owner = type("Owner", (), {"_invalidate": on_state_change})()
    backend.mainloop()


if __name__ == "__main__":
    main()
