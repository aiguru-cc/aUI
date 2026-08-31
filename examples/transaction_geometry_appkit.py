"""Transactions, matched geometry identity, and reduce-motion policy."""
from aui import (
    Animation, Button, ButtonStyle, Namespace, State, Text, Transaction,
    VStack, Window, with_transaction,
)
from appkit_support import run_window


expanded = State(False)
hero = Namespace.create()


def toggle():
    with with_transaction(Transaction(Animation.spring(0.45))):
        expanded.wrapped_value = not expanded.wrapped_value


def content():
    title = (Text("Matched card — expanded" if expanded.wrapped_value else "Matched card")
             .matched_geometry_effect("hero", hero, is_source=not expanded.wrapped_value))
    return VStack([
        title,
        Text("Transactions carry animation policy with state mutations."),
        Button("Toggle", toggle).button_style(ButtonStyle.BORDERED_PROMINENT),
    ]).transaction(lambda tx: setattr(tx, "is_continuous", True))


if __name__ == "__main__":
    run_window("Animation Transactions", content, width=520, height=280)
