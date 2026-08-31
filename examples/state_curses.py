"""Example: state management with ObservableObject and @observable.

Demonstrates two ways to share mutable state across views, and how aUI
re-renders when state changes.

Run:  python3 examples/state_curses.py

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
from aui.core.state import Binding, ObservableObject, State, observable


# 1) Manual ObservableObject: call object_will_change() after mutations.
class Counter(ObservableObject):
    def __init__(self):
        super().__init__()
        self.count = 0

    def increment(self):
        self.count += 1
        self.object_will_change()

    def reset(self):
        self.count = 0
        self.object_will_change()


# 2) @observable decorator: attribute writes notify automatically.
@observable
class Profile:
    name = ""


def main():
    counter = Counter()
    profile = Profile()

    def make_view():
        return VStack(
            [
                Text("State management (q: quit)"),
                Text(f"Counter (ObservableObject): {counter.count}"),
                HStack(
                    [
                        Button("+1", action=counter.increment),
                        Button("Reset", action=counter.reset),
                    ],
                    spacing=1,
                ),
                Text(f"Profile (@observable): {profile.name or '(empty)'}"),
                TextField(
                    Binding(getter=lambda: profile.name, setter=lambda v: setattr(profile, "name", v)),
                    placeholder="type your name",
                ),
            ],
            spacing=1,
        )

    CursesBackend(make_view).run()


if __name__ == "__main__":
    main()
