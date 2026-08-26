"""Example: gesture system (T20) — tap, long-press and drag in a Tk window.

Run:  python3 examples/gestures_tk.py

Shows the three supported gestures:
  - onTapGesture:        click to increment a counter
  - onLongPressGesture:  hold for 0.6s to toggle a flag
  - onDragGesture:       drag to track the delta

The Tk backend binds native <Button-1> / <B1-Motion> events to the attached
gesture callbacks (see ADR-0007).
"""
import _bootstrap  # noqa: F401
from aui.backends.tk import TkBackend
from aui.core.components import Text
from aui.core.geometry import Color
from aui.core.layout import VStack
from aui.core.modifiers import background, foreground_color, on_tap_gesture, padding
from aui.core.gestures import on_drag_gesture, on_long_press_gesture
from aui.core.state import State


def main():
    taps = State(0)
    held = State(False)
    drag = State((0, 0))

    def make_view():
        return VStack(
            [
                on_tap_gesture(
                    padding(Text(f"Tap me (x{taps.wrapped_value})"), length=10)
                    .background(Color.blue)
                    .foregroundColor(Color.white),
                    lambda: taps._set(taps.wrapped_value + 1),
                ),
                on_long_press_gesture(
                    padding(
                        Text(f"Hold me ({'ON' if held.wrapped_value else 'off'})"),
                        length=10,
                    ).background(Color.green if held.wrapped_value else Color.gray),
                    lambda: held._set(not held.wrapped_value),
                    minimum_duration=0.6,
                ),
                on_drag_gesture(
                    padding(Text(f"Drag me (dx={drag.wrapped_value[0]}, dy={drag.wrapped_value[1]})"), length=10)
                    .background(Color.orange),
                    lambda start, current: drag._set(
                        (int(current.x - start.x), int(current.y - start.y))
                    ),
                ),
            ],
            spacing=12,
        )

    backend = TkBackend()
    backend.render(make_view())

    def on_state_change():
        backend.render(make_view())

    for s in (taps, held, drag):
        s._owner = type("Owner", (), {"_invalidate": on_state_change})()
    backend.mainloop()


if __name__ == "__main__":
    main()
