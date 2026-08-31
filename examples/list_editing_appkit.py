"""SwiftUI-style List selection, edit mode and row actions on native AppKit."""
from aui import (
    Button, EditMode, HStack, List, ListRowAction, State, Text, VStack, Window,
)
from appkit_support import run_window

selection = State(set())
edit_mode = State(EditMode.ACTIVE)
message = State("Right-click a row for actions")


def note(value):
    message.value = value


list_view = List(
    [
        Text("Design system").id("design").swipe_actions([
            ListRowAction("Pin", lambda: note("Pinned Design system")),
            ListRowAction("Delete", lambda: note("Delete requested"), role="destructive"),
        ]),
        Text("Release checklist").id("release"),
        Text("Archived reference").id("archive").delete_disabled().move_disabled(),
    ],
    selection=selection.binding(),
    edit_mode=edit_mode.binding(),
    on_delete=lambda indices: note(f"Deleted rows {indices}"),
    on_move=lambda indices, destination: note(f"Moved {indices} to {destination}"),
)


def content():
    return VStack([
        Text("Editable List"),
        Text(message.value),
        list_view,
        HStack([
            Button("Delete first", lambda: list_view.delete_rows((0,))),
            Button("Move first down", lambda: list_view.move_rows((0,), 2)),
        ]),
    ], spacing=12)


if __name__ == "__main__":
    run_window("List Editing", content, width=520, height=360)
