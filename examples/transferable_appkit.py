"""Transferable model values and SwiftUI-style drag/drop destinations."""
import json
from dataclasses import dataclass

from aui import (
    DataRepresentation, State, Text, Transferable, UTType, VStack, Window,
)
from appkit_support import run_window


@dataclass
class Card(Transferable):
    title: str


Card.transfer_representations = (
    DataRepresentation(
        UTType.JSON,
        lambda card: json.dumps({"title": card.title}).encode(),
        lambda data: Card(json.loads(data)["title"]),
    ),
)


dropped = State("Nothing dropped")
targeted = State(False)


def accept(cards, location):
    dropped.wrapped_value = ", ".join(card.title for card in cards)
    return True


def content():
    return VStack([
        Text("Drag this card").draggable(Card("SwiftUI-style data")),
        Text("Drop destination" if not targeted.wrapped_value else "Release here")
        .drop_destination(Card, accept, targeted.binding()),
        Text(dropped.wrapped_value),
    ])


if __name__ == "__main__":
    run_window("Transferable", content, width=520, height=300)
