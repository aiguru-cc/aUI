"""Native ShareLink and PasteButton system integrations."""

from pathlib import Path

from aui import PasteButton, ShareLink, Size, State, Text, TextField, VStack, Window
from aui.backends.appkit import AppKitApplication


notes = State("")


def make_view():
    return VStack([
        Text("System Services"),
        TextField(notes.binding(), placeholder="Paste some text"),
        PasteButton("Paste from Clipboard", text=notes.binding()),
        ShareLink(
            ["https://github.com", Path(__file__)],
            title="Share Link and Example…",
            subject="aUI system controls",
            message="Shared from a native Python AppKit application.",
        ),
        Text(f"Current text: {notes.value or '(empty)'}"),
    ], spacing=16, alignment="leading").padding(length=24)


def main():
    AppKitApplication(
        Window("aUI · System Services", make_view, default_size=Size(620, 420))
    ).run()


if __name__ == "__main__":
    main()
