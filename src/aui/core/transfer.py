"""SwiftUI-inspired Transferable values and drag/drop destinations."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Type

from .geometry import Point
from .state import Binding
from .view import View, ViewModifier, _ModifiedContent, _apply


@dataclass(frozen=True)
class UTType:
    identifier: str

    def conforms_to(self, other: "UTType") -> bool:
        parents = {
            "public.plain-text": {"public.text", "public.data"},
            "public.text": {"public.data"}, "public.json": {"public.text", "public.data"},
            "public.url": {"public.data"}, "public.file-url": {"public.url", "public.data"},
            "public.image": {"public.data"},
            "public.png": {"public.image", "public.data"},
            "public.jpeg": {"public.image", "public.data"},
        }
        return self == other or other.identifier in parents.get(self.identifier, set())


UTType.DATA = UTType("public.data")
UTType.TEXT = UTType("public.text")
UTType.PLAIN_TEXT = UTType("public.plain-text")
UTType.JSON = UTType("public.json")
UTType.URL = UTType("public.url")
UTType.FILE_URL = UTType("public.file-url")
UTType.IMAGE = UTType("public.image")
UTType.PNG = UTType("public.png")
UTType.JPEG = UTType("public.jpeg")


@dataclass(frozen=True)
class TransferPayload:
    content_type: UTType
    data: bytes
    suggested_name: str = ""


@dataclass(frozen=True)
class DataRepresentation:
    content_type: UTType
    export: Callable[[Any], bytes]
    import_: Callable[[bytes], Any]


@dataclass(frozen=True)
class FileRepresentation:
    content_type: UTType
    export: Callable[[Any], Path]
    import_: Callable[[Path], Any]


class Transferable:
    """Protocol-style base class for transferable application models."""

    transfer_representations: tuple[DataRepresentation | FileRepresentation, ...] = ()

    def transfer_payload(self, content_type: UTType | None = None) -> TransferPayload:
        for representation in self.transfer_representations:
            if content_type is not None and representation.content_type != content_type:
                continue
            if isinstance(representation, DataRepresentation):
                data = representation.export(self)
                if not isinstance(data, bytes): raise TypeError("data representation export must return bytes")
                return TransferPayload(representation.content_type, data)
            path = Path(representation.export(self))
            return TransferPayload(representation.content_type, str(path).encode(), path.name)
        raise LookupError("no matching transfer representation")

    @classmethod
    def from_payload(cls, payload: TransferPayload):
        for representation in cls.transfer_representations:
            if not payload.content_type.conforms_to(representation.content_type):
                continue
            if isinstance(representation, DataRepresentation):
                return representation.import_(payload.data)
            return representation.import_(Path(payload.data.decode()))
        raise ValueError(f"{cls.__name__} cannot import {payload.content_type.identifier}")


def payload_for(value: Any) -> TransferPayload:
    if isinstance(value, TransferPayload): return value
    if isinstance(value, Transferable): return value.transfer_payload()
    if isinstance(value, str): return TransferPayload(UTType.PLAIN_TEXT, value.encode("utf-8"))
    if isinstance(value, bytes): return TransferPayload(UTType.DATA, value)
    if isinstance(value, Path): return TransferPayload(UTType.FILE_URL, str(value).encode(), value.name)
    try:
        return TransferPayload(UTType.JSON, json.dumps(value).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise TypeError(f"value is not transferable: {type(value).__name__}") from exc


@dataclass(frozen=True)
class DropInfo:
    location: Point
    payloads: tuple[TransferPayload, ...]

    def has_items_conforming_to(self, content_types: Iterable[UTType]) -> bool:
        return any(payload.content_type.conforms_to(kind)
                   for payload in self.payloads for kind in content_types)


@dataclass(frozen=True)
class DraggableModifier(ViewModifier):
    item: Any
    preview: Optional[Callable[[], View]] = None

    def payload(self): return payload_for(self.item() if callable(self.item) else self.item)
    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


class DropDestinationModifier(ViewModifier):
    def __init__(self, item_type: Type, action: Callable[[list, Point], bool],
                 is_targeted: Binding | None = None):
        if not isinstance(item_type, type): raise TypeError("drop item_type must be a type")
        if not callable(action): raise TypeError("drop action must be callable")
        self.item_type, self.action, self.is_targeted = item_type, action, is_targeted

    def decode(self, payloads):
        values = []
        for payload in payloads:
            if issubclass(self.item_type, Transferable):
                values.append(self.item_type.from_payload(payload))
            elif self.item_type is str and payload.content_type in {UTType.TEXT, UTType.PLAIN_TEXT}:
                values.append(payload.data.decode("utf-8"))
            elif self.item_type is bytes:
                values.append(payload.data)
        return values

    def perform(self, payloads, location=Point()) -> bool:
        if self.is_targeted is not None: self.is_targeted.wrapped_value = True
        try:
            values = self.decode(tuple(payloads))
            return bool(values) and bool(self.action(values, location))
        finally:
            if self.is_targeted is not None: self.is_targeted.wrapped_value = False

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def draggable(view: View, item: Any, preview=None) -> View:
    return _apply(view, DraggableModifier(item, preview))


def drop_destination(view: View, item_type: Type, action, is_targeted=None) -> View:
    return _apply(view, DropDestinationModifier(item_type, action, is_targeted))


def simulate_drop(view: View, payloads, location=Point()) -> bool:
    node = view
    while isinstance(node, _ModifiedContent):
        if isinstance(node._modifier, DropDestinationModifier):
            return node._modifier.perform(tuple(payload_for(item) for item in payloads), location)
        node = node._content
    return False
