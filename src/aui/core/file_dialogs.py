"""SwiftUI-style file importer and exporter presentation modifiers."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from .geometry import Size
from .state import Binding
from .view import View, ViewModifier, _apply


@dataclass(frozen=True)
class FileDialogResult:
    urls: tuple[Path, ...] = ()
    error: Optional[Exception] = None
    cancelled: bool = False

    @property
    def is_success(self) -> bool:
        return self.error is None and not self.cancelled


class _FileDialogModifier(ViewModifier):
    def __init__(self, is_presented: Binding[bool], on_completion: Callable[[FileDialogResult], None]):
        if not isinstance(is_presented, Binding):
            raise TypeError("file dialog is_presented must be a Binding[bool]")
        if not callable(on_completion):
            raise TypeError("file dialog on_completion must be callable")
        self.is_presented = is_presented
        self.on_completion = on_completion

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin, size) -> None:
        content.place(origin, size)

    def complete(self, result: FileDialogResult) -> None:
        self.is_presented.value = False
        self.on_completion(result)


class FileImporterModifier(_FileDialogModifier):
    def __init__(self, is_presented: Binding[bool], allowed_extensions: Sequence[str],
                 on_completion: Callable[[FileDialogResult], None], allows_multiple: bool = False):
        super().__init__(is_presented, on_completion)
        self.allowed_extensions = tuple(self._extension(value) for value in allowed_extensions)
        self.allows_multiple = bool(allows_multiple)

    @staticmethod
    def _extension(value: str) -> str:
        extension = str(value).strip().lower().lstrip(".")
        if not extension or "/" in extension or "\\" in extension:
            raise ValueError("allowed extensions must be simple file extensions")
        return extension


class FileExporterModifier(_FileDialogModifier):
    def __init__(self, is_presented: Binding[bool], document: Any, default_filename: str,
                 on_completion: Callable[[FileDialogResult], None]):
        super().__init__(is_presented, on_completion)
        if not default_filename or Path(default_filename).name != default_filename:
            raise ValueError("default_filename must be a file name without directories")
        self.document = document
        self.default_filename = default_filename

    def data(self) -> bytes:
        value = self.document() if callable(self.document) else self.document
        if isinstance(value, str):
            return value.encode("utf-8")
        if isinstance(value, (bytes, bytearray, memoryview)):
            return bytes(value)
        raise TypeError("export document must produce str or bytes")

    def write_to(self, destination: Path | str) -> Path:
        path = Path(destination).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(self.data())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return path


def file_importer(view: View, is_presented: Binding[bool], allowed_extensions: Sequence[str],
                  on_completion: Callable[[FileDialogResult], None],
                  allows_multiple: bool = False) -> View:
    return _apply(view, FileImporterModifier(
        is_presented, allowed_extensions, on_completion, allows_multiple
    ))


def file_exporter(view: View, is_presented: Binding[bool], document: Any,
                  default_filename: str, on_completion: Callable[[FileDialogResult], None]) -> View:
    return _apply(view, FileExporterModifier(
        is_presented, document, default_filename, on_completion
    ))


__all__ = [
    "FileDialogResult", "FileExporterModifier", "FileImporterModifier",
    "file_exporter", "file_importer",
]
