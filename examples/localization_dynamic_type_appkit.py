"""Localization, RTL direction, Dynamic Type and redaction showcase."""
from aui import (
    DynamicTypeSize, LocalizedStringKey, Text, VStack, Window,
)
from appkit_support import run_window


welcome = LocalizedStringKey(
    "welcome", "Welcome, {name}",
    {"zh": "欢迎，{name}", "ja": "ようこそ、{name}"}, name="Ada",
)


def content():
    return VStack([
        Text(welcome),
        Text("Dynamic Type accessibility size")
        .dynamic_type_size(DynamicTypeSize.ACCESSIBILITY1),
        Text("Selectable localized content").text_selection(),
        Text("Private account number").redacted("privacy"),
        Text("Hover for help").help("Native AppKit tooltip"),
    ]).locale("zh-CN")


if __name__ == "__main__":
    run_window("Localization & Dynamic Type", content, width=620, height=380)
