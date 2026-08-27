"""Example: the aUI showcase — every component and feature in one window.

Run:  python3 examples/showcase_tk.py

This single Tk window demonstrates the whole aUI API surface at once:

  * Components        Text, Button, TextField, Toggle, Slider, Picker,
                      DatePicker, Stepper, ProgressView, Divider, Image,
                      List, Form, NavigationStack, Group
  * Layout            VStack / HStack / ZStack / Spacer + frame()
  * Modifiers         padding, background, foregroundColor, font, border,
                      cornerRadius, opacity, hidden, onTapGesture
  * Gestures          onTapGesture / onLongPressGesture / onDragGesture
  * Animation         Animation + with_animation + .animation() modifier
  * State             State / Binding / ObservableObject / @observable /
                      Environment
  * Accessibility     accessibilityLabel/Hint/Value/Hidden/Element +
                      describe_accessibility() tree
  * Custom component  a subclass of View

The accessibility tree of the current view is printed to the console on every
render, so you can see how the declarative metadata maps to semantics.
"""
import _bootstrap  # noqa: F401
from datetime import datetime

# Everything below comes from the public API (`from aui import *`).
from aui import (
    # accessibility
    CHILDREN_COMBINE,
    accessibility_element,
    accessibility_hidden,
    accessibility_hint,
    accessibility_label,
    accessibility_value,
    # animation
    Animation,
    with_animation,
    # components
    Button,
    DatePicker,
    Divider,
    Form,
    Group,
    Image,
    List,
    NavigationStack,
    Picker,
    ProgressView,
    Slider,
    Stepper,
    Text,
    TextField,
    Toggle,
    # geometry
    Color,
    Font,
    # gestures
    on_drag_gesture,
    on_long_press_gesture,
    on_tap_gesture,
    # layout
    HStack,
    Spacer,
    VStack,
    ZStack,
    # modifiers
    animation,
    background,
    border,
    corner_radius,
    font,
    foreground_color,
    frame,
    hidden,
    opacity,
    padding,
    # state
    Environment,
    ObservableObject,
    State,
    observable,
    # view
    View,
)
from aui.backends.tk import TkBackend
from aui.core.geometry import Size, Point


# ---------------------------------------------------------------------------
# State — one of each flavour so the state-management API is exercised.
# ---------------------------------------------------------------------------
name = State("aUI")
enabled = State(True)
volume = State(0.4)
qty = State(3.0)
color_choice = State("blue")
deadline = State(datetime(2026, 8, 26))
progress = State(0.65)
animated_index = State(0)
taps = State(0)
held = State(False)
drag = State((0, 0))


@observable
class Settings:
    """Shared observable state (@observable class decorator)."""

    notifications = True
    theme = "light"


settings = Settings()


class AppModel(ObservableObject):
    """Shared observable state (ObservableObject base class)."""

    def __init__(self):
        super().__init__()
        self._count = 0

    @property
    def count(self) -> int:
        return self._count

    def bump(self) -> None:
        self._count += 1
        self.object_will_change()


model = AppModel()


#: A read-only dependency-injection container (mirrors @Environment).
env = Environment({"app_name": "aUI Showcase", "locale": "zh-CN"})


# ---------------------------------------------------------------------------
# Custom component — subclass View and implement the layout contract.
# ---------------------------------------------------------------------------
class Badge(View):
    """A small colored badge that composes built-in views (SwiftUI-style)."""

    def __init__(self, title: str, color: Color = Color.blue):
        self._title = title
        self._color = color
        self._children = [
            corner_radius(
                background(padding(Text(title, color=Color.white, font=Font.caption()), length=4), color),
                4,
            )
        ]

    def size_that_fits(self, proposal: Size) -> Size:
        return self._children[0].size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        self._children[0].place(origin, size)

    def children(self):
        return self._children


# ---------------------------------------------------------------------------
# Palette used by the animation section.
# ---------------------------------------------------------------------------
palette = [Color.red, Color.blue, Color.green, Color.orange, Color.purple]


def next_color() -> None:
    """Change the animated color inside a ``with_animation`` scope."""
    with with_animation(Animation.ease_in_out(0.4)):
        animated_index._set((animated_index.wrapped_value + 1) % len(palette))


# ---------------------------------------------------------------------------
# View factory — recreated on every state change and re-rendered with diffing.
# ---------------------------------------------------------------------------
def make_view() -> View:
    animated_color = palette[animated_index.wrapped_value % len(palette)]

    # -- 1. Text & Button with every modifier --------------------------------
    text_section = Form(
        [
            padding(Text("1 · Text & Button", font=Font.headline()), length=4),
            Text(
                "Multi-line text: 第一行\n第二行 and long lines wrap automatically.",
                line_limit=3,
                line_spacing=2,
                font=Font.body(),
            ),
            foreground_color(Text("Styled", font=Font.title()), Color.red),
            border(corner_radius(frame(Text("Framed"), width=120, height=36, alignment="center"), 6), Color.blue, 2),
            HStack(
                [
                    opacity(Text("Faded"), 0.4),
                    font(Text("Bold"), Font.system(size=16, weight="bold")),
                    hidden(Text("Hidden?")),
                    foreground_color(Text("Custom color"), Color.teal),
                ],
                spacing=8,
            ),
            Button(
                "Button (normal)",
                action=lambda: taps._set(taps.wrapped_value + 1),
            ),
            Button(
                "Button (destructive)",
                action=lambda: taps._set(taps.wrapped_value + 1),
                role="destructive",
            ),
        ]
    )

    # -- 2. Input controls ---------------------------------------------------
    inputs = Form(
        [
            padding(Text("2 · Input controls", font=Font.headline()), length=4),
            TextField(name.binding(), placeholder="TextField (bound to name)"),
            Toggle("Toggle", is_on=enabled.binding()),
            accessibility_value(
                Text(f"Slider: {volume.wrapped_value:.0%}"),
                f"{volume.wrapped_value:.0%}",
            ),
            Slider(value=volume.binding(), in_range=(0.0, 1.0), step=0.05),
            Stepper("Stepper", value=qty.binding(), in_range=(0.0, 10.0), step=1.0),
            Text(f"Picker: {color_choice.wrapped_value}"),
            Picker("Color", selection=color_choice.binding(), options=["red", "green", "blue", "teal"]),
            DatePicker(
                "Deadline",
                selection=deadline.binding(),
                displayed_components="date hourAndMinute",
            ),
            Text(f"Progress: {progress.wrapped_value:.0%}"),
            ProgressView(value=progress.wrapped_value, label="ProgressView"),
        ]
    )

    # -- 3. Gestures ---------------------------------------------------------
    gestures = Form(
        [
            padding(Text("3 · Gestures", font=Font.headline()), length=4),
            on_tap_gesture(
                foreground_color(background(padding(Text(f"Tap me  (x{taps.wrapped_value})"), length=10), Color.blue), Color.white),
                lambda: taps._set(taps.wrapped_value + 1),
            ),
            on_long_press_gesture(
                background(
                    padding(Text(f"Hold me  ({'ON' if held.wrapped_value else 'off'})"), length=10),
                    Color.green if held.wrapped_value else Color.gray,
                ),
                lambda: held._set(not held.wrapped_value),
                minimum_duration=0.6,
            ),
            on_drag_gesture(
                background(
                    padding(Text(f"Drag me  (dx={drag.wrapped_value[0]}, dy={drag.wrapped_value[1]})"), length=10),
                    Color.orange,
                ),
                lambda start, current: drag._set(
                    (int(current.x - start.x), int(current.y - start.y))
                ),
            ),
        ]
    )

    # -- 4. Animation --------------------------------------------------------
    animation_section = Form(
        [
            padding(Text("4 · Animation", font=Font.headline()), length=4),
            animation(
                padding(foreground_color(Text("Animated color", font=Font.headline()), animated_color), length=4),
                Animation.ease_in_out(0.4),
            ),
            Button("Next color", action=next_color),
        ]
    )

    # -- 5. State & environment ----------------------------------------------
    state_section = Form(
        [
            padding(Text("5 · State management", font=Font.headline()), length=4),
            Text(f"State: {name.wrapped_value} | Binding: {color_choice.wrapped_value}"),
            Text(f"ObservableObject count: {model.count}"),
            Button("Bump ObservableObject", action=model.bump),
            Text(f"@observable notifications: {settings.notifications}"),
            Button(
                "Toggle @observable",
                action=lambda: setattr(
                    settings, "notifications", not settings.notifications
                ),
            ),
            Text(f"Environment: {env.get('app_name')} / {env.get('locale')}"),
        ]
    )

    # -- 6. Layout primitives ------------------------------------------------
    layout_section = Form(
        [
            padding(Text("6 · Layout", font=Font.headline()), length=4),
            HStack([Text("H"), Text("S"), Text("T"), Text("A"), Text("C"), Text("K")], spacing=6),
            HStack([Text("Left"), Spacer(), Text("Right")], spacing=4),
            ZStack(
                [
                    padding(background(Text("ZStack bottom"), Color.yellow), length=8),
                    padding(background(Text("top"), Color.green), length=8),
                ],
                alignment="topTrailing",
            ),
        ]
    )

    # -- 7. Decorative + custom + list --------------------------------------
    misc_section = Form(
        [
            padding(Text("7 · Divider / Image / Group / Custom / List", font=Font.headline()), length=4),
            Divider(),
            HStack([Image(system_name="star", color=Color.yellow, size=20), Text("Image")], spacing=6),
            Group([Text("Group child 1"), Text("Group child 2")]),
            Badge("Custom", Color.indigo),
            padding(Text("8 · List (lazy, scrollable)", font=Font.headline()), length=4),
        ]
    )

    list_rows = [Text(f"Row {i}") for i in range(60)]

    # -- Accessibility: wrap a couple of views with metadata ----------------
    accessible_button = accessibility_hint(
        accessibility_label(
            Button("Accessible button", action=lambda: taps._set(taps.wrapped_value + 1)),
            "Increment the tap counter",
        ),
        "Adds one to the counter shown above",
    )
    accessible_combined = accessibility_element(
        HStack([Text("Name:"), Text(name.wrapped_value)]),
        CHILDREN_COMBINE,
    )
    accessible_hidden_deco = accessibility_hidden(Text("Decorative"), True)

    body = VStack(
        [
            text_section,
            inputs,
            gestures,
            animation_section,
            state_section,
            layout_section,
            accessible_button,
            accessible_combined,
            accessible_hidden_deco,
            misc_section,
            List(list_rows, row_height=24),
        ],
        spacing=6,
    )

    return NavigationStack(
        env.get("app_name"),
        body,
    )


def main() -> None:
    backend = TkBackend()
    backend.root.geometry("560x760")
    backend.render(make_view())

    def on_state_change() -> None:
        backend.render(make_view())
        # Print the accessibility tree on every change so you can inspect how
        # the declarative metadata maps to semantics (ADR-0010).
        print(backend.describe_accessibility().summary())

    # Connect every State / observable to the re-render hook.
    # ``staticmethod`` is required so the fake owner passes the hook no
    # arguments (otherwise ``_invalidate`` would receive the owner as ``self``).
    owner_type = type("Owner", (), {"_invalidate": staticmethod(on_state_change)})
    for s in (
        name, enabled, volume, qty, color_choice, deadline, progress,
        animated_index, taps, held, drag,
    ):
        s._owner = owner_type()
    model.add_listener(on_state_change)
    settings.add_listener(on_state_change)

    # Show the initial accessibility tree too.
    print(backend.describe_accessibility().summary())

    backend.mainloop()


if __name__ == "__main__":
    main()
