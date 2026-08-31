"""Type-safe, locale-aware TextField parsing and native styles."""
from aui import (
    NumberFormatStyle, State, Text, TextField, TextFieldStyle, VStack, Window,
)
from appkit_support import run_window


amount = State(1234.5)
percent = State(0.25)
plain = State("Plain text")


def content():
    return VStack([
        Text(f"Model amount: {amount.wrapped_value}"),
        TextField(
            placeholder="Amount", value=amount.binding(),
            format=NumberFormatStyle.currency("EUR"),
        ).text_field_style(TextFieldStyle.ROUNDED_BORDER),
        TextField(
            placeholder="Percent", value=percent.binding(),
            format=NumberFormatStyle.percent().precision(1),
        ).text_field_style(TextFieldStyle.SQUARE_BORDER),
        TextField(plain.binding())
        .text_field_style(TextFieldStyle.PLAIN),
    ]).locale("de-DE")


if __name__ == "__main__":
    run_window("Formatted TextField", content, width=560, height=340)
