"""Native searchable content with suggestions, scopes and tokens."""
from aui import (
    List, SearchToken, State, Text, VStack, Window,
)
from appkit_support import run_window


query = State("")
scope = State("All")
submitted = State("")
items = ["SwiftUI", "AppKit", "Python", "Declarative UI", "Accessibility"]


def suggestions(value):
    return [item for item in items if value.casefold() in item.casefold()]


def content():
    rows = [Text(item) for item in items if query.wrapped_value.casefold() in item.casefold()]
    return VStack([
        Text(f"Submitted: {submitted.wrapped_value or '—'}"),
        List(rows),
    ]).searchable(
        query.binding(), prompt="Search topics", placement="toolbar",
        suggestions=suggestions, scopes=["All", "Favorites"], scope=scope.binding(),
        tokens=[SearchToken("docs", "Docs", "doc.text")],
        on_submit=submitted._set,
    )


if __name__ == "__main__":
    run_window("Searchable", content, width=620, height=440)
