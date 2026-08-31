"""Native sortable and selectable NSTableView example."""

from dataclasses import dataclass

from aui import (
    Button, LabeledContent, Size, SortOrder, State, Table, TableColumn, Text,
    ToolbarItem, VStack, Window,
)
from aui.backends.appkit import AppKitApplication


@dataclass(frozen=True)
class Person:
    id: int
    name: str
    role: str
    score: int


people = [
    Person(1, "Ada Lovelace", "Mathematician", 98),
    Person(2, "Grace Hopper", "Computer scientist", 96),
    Person(3, "Alan Turing", "Cryptanalyst", 99),
    Person(4, "Margaret Hamilton", "Software engineer", 97),
]
selection = State({1})
sort_order = State([SortOrder("name"), SortOrder("score", ascending=False)])
show_role = State(True)


def toggle_sort():
    current = sort_order.wrapped_value[0]
    sort_order._set([SortOrder(current.key, not current.ascending), *sort_order.value[1:]])


def make_view():
    table = Table(
        people,
        [
            TableColumn("Name", "name", width=180),
            TableColumn("Role", "role", width=180, visible=show_role.binding()),
            TableColumn("Score", "score", width=80, minimum_width=60, maximum_width=120),
        ],
        selection=selection.binding(),
        sort_order=sort_order.binding(),
        min_height=260,
        allows_multiple_selection=True,
        empty_message="No People",
    )
    content = VStack([
        Text("People"),
        table,
        LabeledContent("Selected IDs", str(sorted(selection.wrapped_value))),
    ], spacing=16, alignment="leading").padding(length=24)
    return content.toolbar([
        ToolbarItem("sort", Button("Reverse sort", toggle_sort))
    ])


def main():
    AppKitApplication(
        Window("aUI · Table", make_view, default_size=Size(720, 520))
    ).run()


if __name__ == "__main__":
    main()
