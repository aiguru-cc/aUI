"""Example: custom components built by composing existing views.

Shows how to create reusable custom views by composing aUI's built-in
components, and use them inside a parent view.

Run:  python3 examples/custom_curses.py

Controls:
    Tab / Up / Down : move focus between text fields
    Type            : edit the focused text field
    Backspace       : delete last char
    Enter           : confirm current text field
    q / Q           : quit
"""

from aui.backends.curses import CursesBackend
from aui.core.components import Button, Text, TextField
from aui.core.layout import HStack, VStack
from aui.core.state import State


class LabeledField:
    """A custom component: a label above a text field."""

    def __init__(self, label, state, placeholder=""):
        self.label = label
        self.state = state
        self.placeholder = placeholder

    def build(self):
        return VStack(
            [
                Text(self.label),
                TextField(self.state.binding(), placeholder=self.placeholder),
            ],
            spacing=0,
        )


class CounterRow:
    """A custom component: a label with +/- stepper buttons."""

    def __init__(self, label, state, lo=0.0, hi=10.0, step=1.0):
        self.label = label
        self.state = state
        self.lo = lo
        self.hi = hi
        self.step = step

    def build(self):
        return HStack(
            [
                Text(self.label),
                Text(str(self.state.wrapped_value)),
                Button("-", action=lambda: self._bump(-self.step)),
                Button("+", action=lambda: self._bump(self.step)),
            ],
            spacing=1,
        )
    def _bump(self, delta):
        new = min(self.hi, max(self.lo, self.state.wrapped_value + delta))
        self.state.wrapped_value = new


def main():
    name = State("")
    qty = State(2.0)

    def make_view():
        return VStack(
            [
                Text("Custom components (q: quit)"),
                LabeledField("Name", name, placeholder="your name").build(),
                CounterRow("Quantity", qty, lo=0.0, hi=10.0, step=1.0).build(),
            ],
            spacing=1,
        )

    CursesBackend(make_view).run()


if __name__ == "__main__":
    main()
