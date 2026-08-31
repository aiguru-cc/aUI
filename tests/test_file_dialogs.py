from pathlib import Path

import pytest

from aui import Button, FileDialogResult, Size, State
from aui.core.file_dialogs import FileExporterModifier, FileImporterModifier


def test_file_importer_is_layout_transparent_and_normalizes_extensions():
    presented = State(True)
    results = []
    base = Button("Import", lambda: None)
    view = base.file_importer(
        presented.binding(), [".JSON", "txt"], results.append, allows_multiple=True
    )

    assert isinstance(view._modifier, FileImporterModifier)
    assert view._modifier.allowed_extensions == ("json", "txt")
    assert view._modifier.allows_multiple
    assert view.size_that_fits(Size(200, 100)) == base.size_that_fits(Size(200, 100))


def test_file_dialog_completion_resets_presentation_binding(tmp_path):
    presented = State(True)
    results = []
    view = Button("Import", lambda: None).file_importer(
        presented.binding(), ["txt"], results.append
    )
    result = FileDialogResult((tmp_path / "notes.txt",))

    view._modifier.complete(result)
    assert presented.value is False
    assert results == [result]
    assert result.is_success
    assert not FileDialogResult(cancelled=True).is_success


def test_file_exporter_writes_text_and_bytes_atomically(tmp_path):
    results = []
    view = Button("Export", lambda: None).file_exporter(
        State(True).binding(), lambda: "你好", "report.txt", results.append
    )
    modifier = view._modifier
    assert isinstance(modifier, FileExporterModifier)
    path = modifier.write_to(tmp_path / "folder" / "report.txt")

    assert path.read_text(encoding="utf-8") == "你好"
    bytes_view = Button("Export", lambda: None).file_exporter(
        State(True).binding(), b"binary", "data.bin", results.append
    )
    assert bytes_view._modifier.write_to(tmp_path / "data.bin").read_bytes() == b"binary"


def test_failed_export_keeps_existing_destination(tmp_path):
    destination = tmp_path / "report.txt"
    destination.write_text("old", encoding="utf-8")
    modifier = Button("Export", lambda: None).file_exporter(
        State(True).binding(), object(), "report.txt", lambda result: None
    )._modifier

    with pytest.raises(TypeError, match="str or bytes"):
        modifier.write_to(destination)
    assert destination.read_text(encoding="utf-8") == "old"


def test_file_dialog_validation():
    binding = State(False).binding()
    callback = lambda result: None
    with pytest.raises(TypeError, match="Binding"):
        Button("x", lambda: None).file_importer(True, ["txt"], callback)
    with pytest.raises(ValueError, match="simple file extensions"):
        Button("x", lambda: None).file_importer(binding, ["bad/path"], callback)
    with pytest.raises(ValueError, match="without directories"):
        Button("x", lambda: None).file_exporter(
            binding, "data", "folder/report.txt", callback
        )
