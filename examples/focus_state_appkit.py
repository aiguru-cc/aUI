"""Declarative native first-responder management with FocusState."""

from aui import Button, FocusState, HStack, Size, State, Text, TextField, VStack, Window
from aui.backends.appkit import AppKitApplication

name = State("")
email = State("")
focused_field = FocusState("name")


def make_view():
    return VStack([
        Text("FocusState"),
        TextField(name.binding(), "Name").focused(focused_field.binding(), "name"),
        TextField(email.binding(), "Email").focused(focused_field.binding(), "email"),
        HStack([
            Button("Focus name", lambda: focused_field._set("name")),
            Button("Focus email", lambda: focused_field._set("email")),
            Button("Done", lambda: focused_field._set(None)),
        ], spacing=10),
        Text(f"Focused field: {focused_field.wrapped_value or 'none'}"),
    ], spacing=16, alignment="leading").padding(length=24)


def main():
    AppKitApplication(
        Window("aUI · FocusState", make_view, default_size=Size(560, 380))
    ).run()


if __name__ == "__main__":
    main()
