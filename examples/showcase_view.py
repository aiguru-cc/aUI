"""Shared showcase view tree for aUI — used by every backend.

The single ``make_view()`` factory builds the *same* declarative aUI view
tree for all backends (curses terminal, ASCII headless, AppKit native window),
so each backend demonstrates exactly the same component surface. It exercises:

  * Components        Text, Button, TextField, SecureField, Toggle, Slider,
                      Picker, ColorPicker, DatePicker, Stepper, ProgressView,
                      Divider, Image, Label, List, Form, NavigationStack,
                      Group, Section, DisclosureGroup, ScrollView, TabView
  * Layout            VStack / HStack / ZStack / Spacer + frame()
  * Modifiers         padding, background, foregroundColor, font, border,
                      cornerRadius, opacity, hidden, onTapGesture
  * Gestures          onTapGesture / onLongPressGesture / onDragGesture
  * Animation         Animation + with_animation + .animation() modifier
  * State             State / Binding / ObservableObject / @observable /
                      Environment
  * Accessibility     accessibilityLabel/Hint/Value/Hidden/Element +
                      describe_accessibility() tree
  * SwiftUI styles    buttonStyle, controlSize, tint, disabled and badge

  * Custom component  a subclass of View
"""
from datetime import datetime

from aui import (
    CHILDREN_COMBINE,
    Animation,
    Button,
    Color,
    ColorPicker,
    Circle,
    ContentUnavailableView,
    DatePicker,
    DisclosureGroup,
    Divider,
    Environment,
    Font,
    Form,
    Gauge,
    Group,
    Grid,
    GridRow,
    HStack,
    Image,
    Label,
    LabeledContent,
    Link,
    List,
    NavigationStack,
    ObservableObject,
    Picker,
    PickerStyle,
    ProgressView,
    RoundedRectangle,
    ScrollView,
    Section,
    SecureField,
    Slider,
    Spacer,
    State,
    Stepper,
    TabView,
    Text,
    TextEditor,
    TextField,
    Toggle,
    VStack,
    View,
    ZStack,
    observable,
    with_animation,
)
from aui.core.geometry import Point, Size

# ---------------------------------------------------------------------------
# State — one of each flavour so the state-management API is exercised.
# ---------------------------------------------------------------------------
name = State("aUI")
password = State("secret")
enabled = State(True)
volume = State(0.4)
qty = State(3.0)
color_choice = State("blue")
color_value = State(Color.teal)
deadline = State(datetime(2026, 8, 26))
progress = State(0.65)
animated_index = State(0)
taps = State(0)
held = State(False)
drag = State((0, 0))
disabled_flag = State(False)
expanded = State(True)
tab_index = State(0)
search_query = State("")
notes = State("Native multi-line editor\nwith two-way binding.")
segment = State("Overview")


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
class UserCard(View):
    """A custom card that composes built-in views via the chainable API."""

    def __init__(self, title: str, subtitle: str, accent: Color = Color.blue):
        self._title = title
        self._subtitle = subtitle
        self._accent = accent
        self._children = [
            HStack(
                [
                    VStack(
                        [
                            Text(title).font(Font.headline()).foreground_color(Color.white),
                            Text(subtitle).font(Font.caption()).foreground_color(Color.white),
                        ],
                        alignment="leading",
                        spacing=2,
                    ),
                    Spacer(),
                    Text("Profile").badge("VIP"),
                ],
                spacing=6,
            )
            .padding(length=10)
            .background(self._accent)
            .corner_radius(6),
        ]

    def size_that_fits(self, proposal: Size) -> Size:
        return self._children[0].size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        self._children[0].place(origin, size)

    def children(self):
        return self._children


palette = [Color.red, Color.blue, Color.green, Color.orange, Color.purple]


def next_color() -> None:
    """Change the animated color inside a ``with_animation`` scope."""
    with with_animation(Animation.ease_in_out(0.4)):
        animated_index._set((animated_index.wrapped_value + 1) % len(palette))


def showcase_section(children) -> View:
    """A comfortably spaced grouped card on AppKit, plain layout elsewhere."""
    return Form(children, spacing=10).padding(length=14)


# ---------------------------------------------------------------------------
# View factory — recreated on every state change and re-rendered with diffing.
# ---------------------------------------------------------------------------
def make_view() -> View:
    animated_color = palette[animated_index.wrapped_value % len(palette)]
    show_disabled = disabled_flag.wrapped_value

    # -- 1. Text & Button (SwiftUI-style chainable API) ---------------------
    text_section = showcase_section(
        [
            Text("1 · Text & Button (chainable)").font(Font.headline()),
            Text(
                "Multi-line text: 第一行\n第二行 and long lines wrap automatically.",
                line_limit=3,
                line_spacing=2,
            ).font(Font.body()),
            Text("Styled title").font(Font.title()).foreground_color(Color.red),
            Text("Framed")
            .frame(width=120, height=36, alignment="center")
            .corner_radius(6)
            .border(Color.blue, 2),
            HStack(
                [
                    Text("Faded").opacity(0.4),
                    Text("Bold").font(Font.system(size=16, weight="bold")),
                    Text("Hidden?").hidden(),
                    Text("Teal").foreground_color(Color.teal),
                ],
                spacing=8,
            ),
            Text("SwiftUI button roles and styles").font(Font.headline()),
            HStack(
                [
                    Button("Primary", action=lambda: taps._set(taps.wrapped_value + 1)),
                    Button("Secondary", action=lambda: taps._set(taps.wrapped_value + 1)),
                    Button("Success", action=lambda: taps._set(taps.wrapped_value + 1)),
                    Button("Danger", action=lambda: taps._set(taps.wrapped_value + 1)),
                ],
                spacing=2,
            ),
            HStack(
                [
                    Button("Warning", action=lambda: taps._set(taps.wrapped_value + 1)),
                    Button("Info", action=lambda: taps._set(taps.wrapped_value + 1)),
                    Button("Dark", action=lambda: taps._set(taps.wrapped_value + 1)),
                    Button("Link", action=lambda: taps._set(taps.wrapped_value + 1)),
                ],
                spacing=2,
            ),
            HStack(
                [
                    Button("Outline", action=lambda: taps._set(taps.wrapped_value + 1)),
                    Button("Pill", action=lambda: taps._set(taps.wrapped_value + 1)),
                    Button("LG", action=lambda: taps._set(taps.wrapped_value + 1)),
                    Button("SM", action=lambda: taps._set(taps.wrapped_value + 1)),
                ],
                spacing=2,
            ),
            Button(
                "Block + shadow",
                action=lambda: taps._set(taps.wrapped_value + 1),
            ),
            Button(
                "Disabled button (greyed)",
                action=lambda: None,
            ).disabled() if show_disabled else Button(
                "Enabled button",
                action=lambda: taps._set(taps.wrapped_value + 1),
            ),
        ]
    )

    # -- 2. Input controls ---------------------------------------------------
    inputs = showcase_section(
        [
            Text("2 · Input controls").font(Font.headline()),
            TextField(name.binding(), placeholder="TextField (bound to name)"),
            SecureField(password.binding(), placeholder="SecureField (password)"),
            Text("Toggle").font(Font.subheadline()),
            Toggle("Toggle (primary)", is_on=enabled.binding()),
            Toggle("Toggle (success, lg)", is_on=enabled.binding()),
            Text(f"Slider: {volume.wrapped_value:.0%}"),
            Slider(value=volume.binding(), in_range=(0.0, 1.0), step=0.05)
            ,
            Stepper("Stepper", value=qty.binding(), in_range=(0.0, 10.0), step=1.0),
            Text(f"Picker: {color_choice.wrapped_value}"),
            Picker("Color", selection=color_choice.binding(), options=["red", "green", "blue", "teal"]),
            Text(f"ColorPicker: {color_value.wrapped_value.to_tk()}"),
            ColorPicker("Pick a color", selection=color_value.binding()),
            DatePicker(
                "Deadline",
                selection=deadline.binding(),
                displayed_components="date hourAndMinute",
            ),
            Text(f"Progress: {progress.wrapped_value:.0%}"),
            ProgressView(value=progress.wrapped_value, label="ProgressView"),
            Text("Disabled variants").font(Font.headline()),
            TextField(name.binding(), placeholder="disabled field").disabled(),
            Toggle("disabled toggle", is_on=enabled.binding()).disabled(),
            Slider(value=volume.binding(), in_range=(0.0, 1.0)).disabled(),
            Picker("Color", selection=color_choice.binding(), options=["red", "green"]).disabled(),
            Stepper("Qty", value=qty.binding(), in_range=(0.0, 10.0)).disabled(),
        ]
    )

    # -- 3. Gestures ---------------------------------------------------------
    gestures = showcase_section(
        [
            Text("3 · Gestures (chainable)").font(Font.headline()),
            Text(f"Tap me  (x{taps.wrapped_value})")
            .padding(length=10)
            .background(Color.blue)
            .foreground_color(Color.white)
            .on_tap_gesture(lambda: taps._set(taps.wrapped_value + 1)),
            Text(f"Hold me  ({'ON' if held.wrapped_value else 'off'})")
            .padding(length=10)
            .background(Color.green if held.wrapped_value else Color.gray)
            .on_long_press_gesture(
                lambda: held._set(not held.wrapped_value),
                minimum_duration=0.6,
            ),
            Text(f"Drag me  (dx={drag.wrapped_value[0]}, dy={drag.wrapped_value[1]})")
            .padding(length=10)
            .background(Color.orange)
            .on_drag_gesture(
                lambda start, current: drag._set(
                    (int(current.x - start.x), int(current.y - start.y))
                ),
            ),
        ]
    )

    # -- 4. Animation --------------------------------------------------------
    animation_section = showcase_section(
        [
            Text("4 · Animation (chainable)").font(Font.headline()),
            Text("Animated color")
            .font(Font.headline())
            .foreground_color(animated_color)
            .padding(length=4)
            .animation(Animation.ease_in_out(0.4)),
            Button("Next color", action=next_color),
        ]
    )

    # -- 5. State & environment ----------------------------------------------
    state_section = showcase_section(
        [
            Text("5 · State management").font(Font.headline()),
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
    layout_section = showcase_section(
        [
            Text("6 · Layout (chainable)").font(Font.headline()),
            HStack([Text("H"), Text("S"), Text("T"), Text("A"), Text("C"), Text("K")], spacing=6),
            HStack([Text("Left"), Spacer(), Text("Right")], spacing=4),
            ZStack(
                [
                    Text("ZStack bottom").padding(length=8).background(Color.yellow),
                    Text("top").padding(length=8).background(Color.green),
                ],
                alignment="topTrailing",
            ),
        ]
    )

    # -- 7. New SwiftUI-style components -------------------------------------
    modern_section = showcase_section(
        [
            Text("7 · Modern components").font(Font.headline()),
            TextField(search_query.binding(), placeholder="Search components"),
            TextEditor(notes.binding(), placeholder="Write notes…", min_height=72),
            Picker("", selection=segment.binding(),
                options=["Overview", "Details", "History"]
            ).picker_style(PickerStyle.SEGMENTED),
            Gauge(0.72, label="Capacity"),
            Link("Open Python documentation", "https://docs.python.org/3/"),
            Grid(
                [
                    GridRow([Text("Platform"), Text("macOS")]),
                    GridRow([Text("Renderer"), Text("AppKit")]),
                    GridRow([Text("Language"), Text("Python")]),
                ],
                horizontal_spacing=20,
                vertical_spacing=10,
            ),
            LabeledContent("Version", "0.1.0"),
            HStack([
                Circle(size=Size(28, 28)).fill(Color.indigo),
                RoundedRectangle(corner_radius=8, size=Size(64, 28)).fill(Color.teal),
            ], spacing=10),
            ContentUnavailableView(
                "No recent documents", "doc", "Open a document to see it here."
            ),
            HStack(
                [
                    Label("Home", system_name="house"),
                    Label("Mail", system_name="envelope"),
                    Label("Settings", system_name="gear"),
                ],
                spacing=10,
            ),
            HStack(
                [
                    Text("Inbox").badge("New"),
                    Text("Alerts").badge("Hot"),
                    Text("Details").badge("Info"),
                    Text("Tasks").badge("Done"),
                ],
                spacing=4,
            ),
            Section(
                Text("Section header").font(Font.headline()),
                children=[Text("Section child 1"), Text("Section child 2")],
                footer=Text("Section footer"),
            ),
            DisclosureGroup(
                Text(f"DisclosureGroup ({'open' if expanded.wrapped_value else 'closed'})"),
                children=[Text("Disclosure child")],
                is_expanded=expanded.binding(),
            ),
            ScrollView(
                VStack([Text(f"Scroll row {i}") for i in range(12)], spacing=1),
                axis="vertical",
            ),
            TabView(
                [
                    ("Tab A", Text("Tab A content").padding(length=6).background(Color.blue).foreground_color(Color.white)),
                    ("Tab B", Text("Tab B content").padding(length=6).background(Color.green).foreground_color(Color.black)),
                    ("Tab C", Text("Tab C content").padding(length=6).background(Color.orange).foreground_color(Color.black)),
                ],
                selection=tab_index.binding(),
            ),
        ]
    )

    # -- 8. Decorative + custom + list --------------------------------------
    misc_section = showcase_section(
        [
            Text("8 · Divider / Image / Group / Custom / List").font(Font.headline()),
            Divider(),
            HStack([Image(system_name="star", color=Color.yellow, size=20), Text("Image")], spacing=6),
            Group([Text("Group child 1"), Text("Group child 2")]),
            UserCard("Ada Lovelace", "Analytical engine · 1815", Color.indigo),
            UserCard("Grace Hopper", "Compiler · 1906", Color.teal),
            Text("9 · List (lazy, scrollable)").font(Font.headline()),
        ]
    )

    list_rows = [Text(f"Row {i:02d} — clickable").on_tap_gesture(lambda i=i: taps._set(i)) for i in range(60)]

    # -- Accessibility: chainable metadata ----------------------------------
    accessible_button = (
        Button("Accessible button", action=lambda: taps._set(taps.wrapped_value + 1))
        
        .accessibility_label("Increment the tap counter")
        .accessibility_hint("Adds one to the counter shown above")
    )
    accessible_combined = HStack(
        [Text("Name:"), Text(name.wrapped_value)]
    ).accessibility_element(CHILDREN_COMBINE)
    accessible_hidden_deco = Text("Decorative").accessibility_hidden()

    body = VStack(
        [
            text_section,
            inputs,
            gestures,
            animation_section,
            state_section,
            layout_section,
            modern_section,
            accessible_button,
            accessible_combined,
            accessible_hidden_deco,
            misc_section,
            List(list_rows, row_height=1),
        ],
        spacing=6,
    )

    return NavigationStack(body.navigation_title(env.get("app_name")))
