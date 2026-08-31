from dataclasses import dataclass
from pathlib import Path

import pytest

from aui import (
    DataRepresentation, DropInfo, FileRepresentation, Point, State, Text,
    TransferPayload, Transferable, UTType,
)
from aui.core.transfer import (
    DraggableModifier, DropDestinationModifier, payload_for, simulate_drop,
)


@dataclass
class Note(Transferable):
    title: str


Note.transfer_representations = (
    DataRepresentation(
        UTType.JSON,
        lambda note: ('{"title":"' + note.title + '"}').encode(),
        lambda data: Note(__import__("json").loads(data)["title"]),
    ),
)


def test_uttype_conformance_hierarchy():
    assert UTType.PNG.conforms_to(UTType.IMAGE)
    assert UTType.PLAIN_TEXT.conforms_to(UTType.TEXT)
    assert UTType.JSON.conforms_to(UTType.DATA)
    assert not UTType.TEXT.conforms_to(UTType.IMAGE)


def test_builtin_payload_conversion():
    assert payload_for("hello") == TransferPayload(UTType.PLAIN_TEXT, b"hello")
    assert payload_for(b"raw").content_type == UTType.DATA
    assert payload_for(Path("/tmp/file.txt")).suggested_name == "file.txt"
    assert payload_for({"count": 2}).content_type == UTType.JSON


def test_transferable_roundtrip():
    payload = Note("Ideas").transfer_payload()
    assert payload.content_type == UTType.JSON
    assert Note.from_payload(payload) == Note("Ideas")


def test_draggable_modifier_resolves_lazy_item():
    view = Text("Drag").draggable(lambda: Note("Lazy"))
    modifier = view.modifiers[-1]
    assert isinstance(modifier, DraggableModifier)
    assert Note.from_payload(modifier.payload()).title == "Lazy"


def test_drop_destination_decodes_and_reports_target_state():
    targeted = State(False)
    calls = []
    view = Text("Drop here").drop_destination(
        Note, lambda items, location: calls.append((items, location)) or True,
        targeted.binding(),
    )
    assert simulate_drop(view, [Note("One"), Note("Two")], Point(4, 8))
    assert [note.title for note in calls[0][0]] == ["One", "Two"]
    assert calls[0][1] == Point(4, 8)
    assert targeted.wrapped_value is False


def test_plain_text_drop_and_rejection():
    received = []
    view = Text("Drop").drop_destination(str, lambda items, point: received.extend(items) or True)
    assert simulate_drop(view, ["hello"])
    assert received == ["hello"]
    assert not simulate_drop(Text("No destination"), ["hello"])


def test_drop_info_content_type_query():
    info = DropInfo(Point(), (payload_for("hello"), payload_for(b"data")))
    assert info.has_items_conforming_to([UTType.TEXT])
    assert not info.has_items_conforming_to([UTType.IMAGE])


def test_transfer_validation_errors():
    with pytest.raises(TypeError): Text("x").drop_destination("Note", lambda a, b: True)
    with pytest.raises(TypeError): Text("x").drop_destination(Note, None)

    class Empty(Transferable): pass
    with pytest.raises(LookupError): Empty().transfer_payload()
