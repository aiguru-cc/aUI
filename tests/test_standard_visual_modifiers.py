"""Portable rendering contracts for StandardBackend visual containment."""
from __future__ import annotations

from aui import Color, LabeledContent, Text
from aui.backends import standard
from aui.backends.standard import StandardBackend
from aui.backends.standard_theme import StandardTheme
from aui.core.structural import GroupBox


class _Frame:
    def __init__(self, parent, **options):
        self.parent = parent
        self.options = options
        self.pack_options = None

    def pack(self, **options):
        self.pack_options = options

    def configure(self, **options):
        self.options.update(options)


class _Tk:
    Frame = _Frame


class _Ttk:
    Frame = _Frame
    LabelFrame = _Frame


def _build_modifier(view):
    backend = type("Backend", (), {})()
    backend.theme = StandardTheme()
    captured = []
    backend._build = lambda content, parent: captured.append((content, parent))
    StandardBackend._build(backend, view, object())
    assert len(captured) == 1
    return captured[0][1]


def test_standard_background_modifier_uses_a_portable_tk_surface(monkeypatch):
    monkeypatch.setattr(standard, "tk", _Tk)
    frame = _build_modifier(Text("Status").background(Color.indigo))

    assert frame.options == {"background": "#5856d6"}
    assert frame.pack_options == {"fill": "x"}


def test_standard_border_modifier_keeps_color_and_width(monkeypatch):
    monkeypatch.setattr(standard, "tk", _Tk)
    frame = _build_modifier(Text("Status").border(Color.red, width=2))

    assert frame.options["highlightbackground"] == "#ff0000"
    assert frame.options["highlightthickness"] == 2


def test_standard_group_box_and_labeled_content_keep_their_structure(monkeypatch):
    monkeypatch.setattr(standard, "ttk", _Ttk)
    backend = type("Backend", (), {})()
    backend.theme = StandardTheme()
    built = []
    backend._build = lambda content, parent: built.append((content, parent))

    StandardBackend._build(backend, GroupBox("Details", Text("Value")), object())
    group = built[-1][1]
    assert group.options["text"] == "Details"
    assert isinstance(group, _Frame)

    built.clear()
    StandardBackend._build(backend, LabeledContent("Status", "Ready"), object())
    assert [item.display_content for item, _ in built] == ["Status", "Ready"]
    assert built[0][1].pack_options["side"] == "left"
    assert built[1][1].pack_options["side"] == "right"
