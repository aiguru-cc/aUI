"""Native SwiftUI-style sheet and alert presentation."""

from aui import Button, Size, State, Text, TextEditor, VStack, Window
from aui.backends.appkit import AppKitApplication

show_editor = State(False)
show_delete_alert = State(False)
show_actions = State(False)
show_help = State(False)
notes = State("Edit this text in a native sheet.")


def editor_sheet(dismiss):
    return VStack([
        Text("Editor"),
        TextEditor(notes.binding(), min_height=160),
        Button("Done", dismiss),
    ], spacing=16, alignment="leading").padding(length=24)


def make_view():
    help_button = Button("Help", lambda: show_help._set(True)).popover(
        show_help.binding(),
        lambda dismiss: VStack([
            Text("Popover help"),
            Text("This view is anchored to the Help button."),
            Button("Close", dismiss),
        ], spacing=12).padding(length=18),
        size=Size(320, 190),
        edge="trailing",
    )
    content = VStack([
        Text("Presentation"),
        Button("Open sheet", lambda: show_editor._set(True)),
        Button("Delete…", lambda: show_delete_alert._set(True)),
        Button("More actions…", lambda: show_actions._set(True)),
        help_button,
    ], spacing=16, alignment="leading").padding(length=24)

    return content.sheet(
        show_editor.binding(), editor_sheet, title="Edit notes", size=Size(560, 380)
    ).confirmation_dialog(
        "Choose an action",
        show_actions.binding(),
        buttons=[
            Button("Archive", lambda: print("archived")),
            Button("Delete", lambda: print("deleted"), role="destructive"),
            Button("Cancel", lambda: None, role="cancel"),
        ],
    ).alert(
        "Delete document?",
        show_delete_alert.binding(),
        "This operation cannot be undone.",
        [
            Button("Delete", lambda: print("deleted"), role="destructive"),
            Button("Cancel", lambda: None, role="cancel"),
        ],
    )


def main():
    AppKitApplication(
        Window("aUI · Presentation", make_view, default_size=Size(520, 360))
    ).run()


if __name__ == "__main__":
    main()
