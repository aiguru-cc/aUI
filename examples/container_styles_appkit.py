"""SwiftUI-like list, form, group box and row styles."""
from aui import (
    Color, EdgeInsets, Form, FormStyle, GroupBox, GroupBoxStyle, List,
    ListStyle, Section, Text, TextField, State, VStack, Window,
)
from appkit_support import run_window


name = State("Ada")


def content():
    rows = [
        Text(f"Recent item {index}")
        .list_row_insets(EdgeInsets.symmetric(horizontal=14, vertical=7))
        .list_row_background(Color.rgb(242, 246, 255))
        for index in range(1, 4)
    ]
    return VStack([
        List(rows).list_style(ListStyle.INSET_GROUPED),
        Form([
            Section(Text("PROFILE"), [TextField(name.binding(), "Name")])
            .header_prominence("increased").section_spacing(8),
        ]).form_style(FormStyle.GROUPED),
        GroupBox("Summary", Text("Container styles inherit through their subtrees"))
        .group_box_style(GroupBoxStyle.CARD),
    ])


if __name__ == "__main__":
    run_window("Container Styles", content, width=620, height=480)
