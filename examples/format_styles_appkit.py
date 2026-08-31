"""Locale-aware FormatStyle values rendered by Text."""
from datetime import datetime

from aui import (
    ByteCountFormatStyle, DateFormatStyle, ListFormatStyle, NumberFormatStyle,
    Text, VStack, Window,
)
from appkit_support import run_window


def content():
    return VStack([
        Text(1234567.89, format=NumberFormatStyle.number().precision(2)),
        Text(0.732, format=NumberFormatStyle.percent().precision(1)),
        Text(2499.0, format=NumberFormatStyle.currency("EUR")),
        Text(datetime.now(), format=DateFormatStyle("long", "short")),
        Text(["SwiftUI", "Python", "AppKit"], format=ListFormatStyle()),
        Text(48_000_000, format=ByteCountFormatStyle()),
    ]).locale("de-DE")


if __name__ == "__main__":
    run_window("Format Styles", content, width=560, height=360)
