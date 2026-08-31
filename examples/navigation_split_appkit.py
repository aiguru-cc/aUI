"""Native three-column aUI application with two declarative windows."""

from aui import (
    Button, Color, Form, Gauge, Link, NavigationSplitView,
    NavigationSplitViewColumn, NavigationSplitViewStyle,
    NavigationSplitViewVisibility, Picker, PickerStyle, Size, State, TextField,
    Text, TextEditor, VStack, Window, WindowGroup,
)
from aui.backends.appkit import AppKitApplication, AppKitTheme

query = State("")
selection = State("Inbox")
note = State("Select an item to edit its details.")
visibility = State(NavigationSplitViewVisibility.ALL)


def make_split_view():
    sidebar = VStack([
        Text("Workspace"),
        TextField(query.binding(), "Filter"),
        Picker("", selection=selection.binding(), options=["Inbox", "Today"]).picker_style(PickerStyle.SEGMENTED),
        Button("New item", action=lambda: None),
    ], spacing=14, alignment="leading").padding(length=18)

    content = Form([
        Text("Items"),
        Text("Design review"),
        Text("Release checklist"),
        Text("Customer feedback"),
    ], spacing=14).padding(length=18)

    detail = VStack([
        Text("Design review"),
        TextEditor(note.binding(), min_height=180),
        Gauge(0.68, label="Progress"),
        Link("Project documentation", "https://docs.python.org/3/"),
    ], spacing=18, alignment="leading").padding(length=24)

    return NavigationSplitView(
        sidebar, content=content, detail=detail,
        column_visibility=visibility.binding(),
        preferred_compact_column=NavigationSplitViewColumn.DETAIL,
    ).navigation_split_view_style(
        NavigationSplitViewStyle.PROMINENT_DETAIL
    ).navigation_split_view_column_width(
        NavigationSplitViewColumn.SIDEBAR, 180, 220, 300
    )


def make_inspector():
    return Form([Text("Inspector"), Text("No selection")], spacing=12).padding(length=20)


def main():
    scenes = WindowGroup([
        Window("aUI · Three-column workspace", make_split_view,
               default_size=Size(1080, 700)),
        Window("Inspector", make_inspector, id="inspector",
               default_size=Size(360, 420)),
    ])
    AppKitApplication(scenes, AppKitTheme().with_accent(Color.indigo)).run()


if __name__ == "__main__":
    main()
