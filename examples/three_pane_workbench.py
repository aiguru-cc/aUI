"""A persistent three-pane aUI workbench.

Run one of the following from an editable aUI checkout::

    python examples/three_pane_workbench.py
    python examples/three_pane_workbench.py --standard

The default is the native AppKit window on macOS when PyObjC is installed.
``--standard`` uses the tkinter/ttk StandardBackend and therefore also runs on
Linux and Windows. Every interaction updates the same session model, the
activity stream and the inspector; no control is a one-shot demonstration.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

from aui import (
    Animation, AppBar, Button, Color, ColorPicker, ContentTransition, ControlGroup,
    DatePicker, DisclosureGroup, Divider, Font, Form, Gauge, Grid, GridRow,
    Group, HStack, IconButton, Image, KeyboardShortcut, Label, LabeledContent, Link, List,
    NavigationSplitView, NavigationSplitViewVisibility,
    Picker, PickerStyle, ProgressView, RoundedRectangle, ScrollView, Section,
    ResponsiveItem, ResponsiveRow, SecureField, Size, Slider, Spacer, State, Stepper, TabView, Text, TextEditor,
    TextField, Toggle, ToolbarItem, VStack, Window, ZStack, with_animation,
)
from aui.backends.standard import StandardBackend


# One long-lived state model. The view factory is rebuilt after every mutation,
# while the states below remain alive for the entire application session.
workspace = State("Release cockpit")
query = State("")
selected_area = State("Overview")
selected_project = State("Aurora")
selected_tab = State(0)
notes = State("Keep release scope small, verify keyboard flows, then ship.")
secret = State("token-2026")
notifications = State(True)
focus_mode = State(False)
quality = State(0.72)
capacity = State(6.0)
accent = State(Color.indigo)
deadline = State(datetime.now().replace(second=0, microsecond=0) + timedelta(days=7))
is_advanced_open = State(True)
is_busy = State(False)
column_visibility = State(NavigationSplitViewVisibility.ALL)
sidebar_visible = State(True)
show_help = State(False)
show_snackbar = State(False)
activity = State([
    "Workspace opened",
    "Aurora selected",
    "Ready for a persistent interaction session",
])

PROJECTS = ("Aurora", "Beacon", "Cascade", "Delta")
AREAS = ("Overview", "Components", "Automation", "History")


def record(message: str) -> None:
    """Append a durable in-session event used by the inspector and history."""
    activity._set((activity.wrapped_value + [message])[-12:])


def choose_project(name: str) -> None:
    selected_project._set(name)
    notes._set(f"{name}: review the live control surface and capture follow-up work.")
    record(f"Selected project: {name}")


def create_project() -> None:
    name = f"Draft {len(activity.wrapped_value) + 1}"
    workspace._set(name)
    selected_project._set("Aurora")
    record(f"Created workspace: {name}")


def run_automation() -> None:
    with with_animation(Animation.ease_in_out(0.35)):
        is_busy._set(True)
        quality._set(min(1.0, quality.wrapped_value + 0.08))
        capacity._set(min(10.0, capacity.wrapped_value + 1.0))
    record("Automation completed: quality and capacity recalculated")
    is_busy._set(False)
    show_snackbar._set(True)


def reset_session() -> None:
    workspace._set("Release cockpit")
    query._set("")
    selected_area._set("Overview")
    selected_project._set("Aurora")
    selected_tab._set(0)
    notes._set("Keep release scope small, verify keyboard flows, then ship.")
    quality._set(0.72)
    capacity._set(6.0)
    show_snackbar._set(False)
    record("Reset the visible session controls")


def toggle_sidebar() -> None:
    sidebar_visible._set(not sidebar_visible.wrapped_value)
    record("Sidebar shown" if sidebar_visible.wrapped_value else "Sidebar collapsed")


def open_help() -> None:
    show_help._set(True)
    record("Opened workbench help")


def sidebar() -> VStack:
    project_buttons = [
        Button(name, lambda name=name: choose_project(name))
        .badge("Active" if name == selected_project.wrapped_value else "")
        for name in PROJECTS
    ]
    return VStack([
        Label("aUI Workbench", system_name="rectangle.3.group"),
        Text("Persistent session · all changes stay visible")
        .font(Font.caption()).foreground_color(Color.gray),
        TextField(query.binding(), placeholder="Filter projects or activity"),
        Picker("Area", selection=selected_area.binding(), options=AREAS)
        .picker_style(PickerStyle.SEGMENTED),
        Divider(),
        Text("Projects").font(Font.headline()),
        *project_buttons,
        Spacer(),
        Button("New workspace", create_project),
        Button("Reset session", reset_session).button_style("bordered"),
        Text(f"Events retained: {len(activity.wrapped_value)}")
        .font(Font.caption()),
    ], spacing=12, alignment="leading").padding(length=18)


def live_controls() -> Form:
    return Form([
        Section(Text("Persistent inputs").font(Font.headline()), children=[
            TextField(workspace.binding(), placeholder="Workspace title"),
            SecureField(secret.binding(), placeholder="API token"),
            Toggle("Release notifications", is_on=notifications.binding()),
            Toggle("Focus mode", is_on=focus_mode.binding()),
            LabeledContent("Quality", f"{quality.wrapped_value:.0%}"),
            Slider(quality.binding(), in_range=(0.0, 1.0), step=0.01),
            Stepper("Capacity", capacity.binding(), in_range=(0.0, 10.0), step=1.0),
            ColorPicker("Accent", accent.binding()),
            DatePicker("Target date", deadline.binding(), displayed_components="date hourAndMinute"),
        ]),
        Section(Text("Indicators").font(Font.headline()), children=[
            ProgressView(quality.wrapped_value, label="Release confidence"),
            Gauge(capacity.wrapped_value, in_range=(0.0, 10.0), label="Team capacity"),
            Text(f"{quality.wrapped_value:.0%}")
            .font(Font.title())
            .foreground_color(accent.wrapped_value)
            .content_transition(ContentTransition.NUMERIC_TEXT),
        ]),
    ], spacing=12)


def visual_gallery() -> VStack:
    return VStack([
        Text("Layouts, drawing primitives and stateful presentation").font(Font.headline()),
        Grid([
            GridRow([Text("Project"), Text(selected_project.wrapped_value)]),
            GridRow([Text("Area"), Text(selected_area.wrapped_value)]),
            GridRow([Text("Deadline"), Text(deadline.wrapped_value.strftime("%Y-%m-%d %H:%M"))]),
        ], horizontal_spacing=24, vertical_spacing=8),
        Text("Responsive workspace metrics").font(Font.subheadline()),
        ResponsiveRow([
            ResponsiveItem(
                Section(Text("Confidence").font(Font.caption()), children=[
                    Text(f"{quality.wrapped_value:.0%}").font(Font.title()),
                ]),
                {"xs": 12, "sm": 6, "lg": 4},
            ),
            ResponsiveItem(
                Section(Text("Capacity").font(Font.caption()), children=[
                    Text(f"{capacity.wrapped_value:.0f} / 10").font(Font.title()),
                ]),
                {"xs": 12, "sm": 6, "lg": 4},
            ),
            ResponsiveItem(
                Section(Text("Activity").font(Font.caption()), children=[
                    Text(str(len(activity.wrapped_value))).font(Font.title()),
                ]),
                {"xs": 12, "sm": 12, "lg": 4},
            ),
        ], spacing=10),
        HStack([
            Image(system_name="sparkles", color=accent.wrapped_value, size=22),
            Label("Live accent preview", system_name="paintpalette"),
            Spacer(),
            Text("Running" if is_busy.wrapped_value else "Ready")
            .badge("Live"),
        ], spacing=10),
        ZStack([
            RoundedRectangle(corner_radius=12, size=Size(280, 74)).fill(accent.wrapped_value),
            Text(selected_project.wrapped_value)
            .font(Font.headline()).foreground_color(Color.white),
        ]),
        ControlGroup([
            Button("Run automation", run_automation),
            Button("Record checkpoint", lambda: record("Manual checkpoint recorded")),
        ]),
        Link("Open Python documentation", "https://docs.python.org/3/"),
    ], spacing=14, alignment="leading")


def central_content() -> ScrollView:
    rows = [
        Text(f"{index + 1:02d} · {entry}")
        .on_tap_gesture(lambda entry=entry: record(f"Reviewed activity: {entry}"))
        for index, entry in enumerate(reversed(activity.wrapped_value))
    ]
    tabs = TabView([
        ("Controls", live_controls()),
        ("Visual", visual_gallery()),
        ("Activity", List(rows, row_height=28)),
    ], selection=selected_tab.binding())
    return ScrollView(VStack([
        AppBar(
            VStack([
                Text(workspace.wrapped_value).font(Font.title()),
                Text(f"{selected_project.wrapped_value} · {selected_area.wrapped_value}")
                .foreground_color(Color.gray),
            ], spacing=3, alignment="leading"),
            leading=IconButton("sidebar.leading", toggle_sidebar, label="Toggle sidebar"),
            actions=[IconButton("play.fill", run_automation, label="Run automation")],
        ),
        tabs,
        DisclosureGroup(
            Text("Advanced, persistent controls"),
            children=[
                TextEditor(notes.binding(), placeholder="Write operational notes…", min_height=120),
                Group([
                    Text("Notes remain in the inspector and survive every refresh."),
                    Text("Use the controls above repeatedly; activity never disappears."),
                ]),
            ],
            is_expanded=is_advanced_open.binding(),
        ),
    ], spacing=18, alignment="leading").padding(length=22), axis="vertical")


def inspector() -> VStack:
    event_rows = [Text(f"• {entry}").font(Font.caption()) for entry in activity.wrapped_value[-6:]]
    return VStack([
        Text("Inspector").font(Font.headline()),
        LabeledContent("Workspace", workspace.wrapped_value),
        LabeledContent("Project", selected_project.wrapped_value),
        LabeledContent("Quality", f"{quality.wrapped_value:.0%}"),
        LabeledContent("Focus", "On" if focus_mode.wrapped_value else "Off"),
        LabeledContent("Navigation", "Expanded" if sidebar_visible.wrapped_value else "Collapsed"),
        Divider(),
        Text("Live notes").font(Font.subheadline()),
        Text(notes.wrapped_value, line_limit=6).foreground_color(Color.gray),
        Divider(),
        Text("Recent activity").font(Font.subheadline()),
        *event_rows,
        Spacer(),
        Button("Add inspector note", lambda: record("Inspector note added")),
    ], spacing=10, alignment="leading").padding(length=18)


def make_view():
    split = NavigationSplitView(
        sidebar(), content=central_content(), detail=inspector(),
        column_visibility=column_visibility.binding(),
        sidebar_visibility=sidebar_visible.binding(),
        preferred_compact_column="detail",
    ).navigation_title("aUI · Three-pane Workbench")
    navigation_label = "Hide sidebar" if sidebar_visible.wrapped_value else "Show sidebar"
    return split.alert(
        "Three-pane Workbench Help",
        show_help.binding(),
        message=(
            "Use the toolbar to collapse the sidebar, reset the session, or run automation. "
            "Every change remains visible in the inspector and activity history."
        ),
        buttons=(Button("Got it", lambda: show_help._set(False)),),
    ).snack_bar(
        "Automation completed; release indicators were updated.",
        show_snackbar.binding(),
        action=Button("Dismiss", lambda: show_snackbar._set(False)),
    ).toolbar([
        ToolbarItem(
            "toggle-sidebar",
            Button(navigation_label, toggle_sidebar).keyboard_shortcut(KeyboardShortcut("s")),
            placement="navigation",
            system_name="sidebar.leading",
        ),
        ToolbarItem(
            "reset-session",
            Button("Reset", reset_session).keyboard_shortcut(KeyboardShortcut("r")),
            placement="cancellationAction",
            system_name="arrow.counterclockwise",
        ),
        ToolbarItem(
            "help",
            Button("Help", open_help).keyboard_shortcut(
                KeyboardShortcut("?", ("command", "shift"))),
            system_name="questionmark.circle",
        ),
        ToolbarItem(
            "run-automation",
            Button("Run automation", run_automation).keyboard_shortcut(
                KeyboardShortcut("r", ("command", "shift"))),
            placement="primaryAction",
            system_name="play.fill",
        ),
    ])


def main(argv: list[str] | None = None) -> int:
    arguments = set(argv if argv is not None else sys.argv[1:])
    if "--standard" in arguments:
        if not StandardBackend.available():
            raise RuntimeError("StandardBackend requires Python's tkinter module")
        StandardBackend(make_view).run(width=1280, height=820, title="aUI · Three-pane Workbench")
        return 0
    from aui.backends.appkit import AppKitApplication, available
    if available():
        AppKitApplication(Window(
            "aUI · Three-pane Workbench", make_view, default_size=Size(1280, 820),
        )).run()
        return 0
    if not StandardBackend.available():
        raise RuntimeError(
            "No graphical backend is available: install PyObjC on macOS or use a Python "
            "distribution that includes tkinter for StandardBackend."
        )
    print("[three_pane_workbench] AppKit unavailable; using StandardBackend.")
    StandardBackend(make_view).run(width=1280, height=820, title="aUI · Three-pane Workbench")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
