"""Tests for the ASCII headless backend."""
from aui.backends.ascii import AsciiBackend
from aui.core.components import Button, Text
from aui.core.layout import VStack


def test_ascii_render_contains_text():
    backend = AsciiBackend(width=40, height=10)
    out = backend.render(Text("hello world"))
    assert "hello world" in out


def test_ascii_render_button():
    backend = AsciiBackend(width=40, height=10)
    out = backend.render(Button("OK", action=lambda: None))
    assert "OK" in out


def test_ascii_render_stack():
    backend = AsciiBackend(width=40, height=10)
    out = backend.render(VStack([Text("top"), Text("bottom")]))
    assert "top" in out
    assert "bottom" in out


def test_ascii_reused_renderer_does_not_keep_previous_frame_glyphs():
    backend = AsciiBackend(width=20, height=3)
    assert "longer value" in backend.render(Text("longer value"))
    later = backend.render(Text("short"))
    assert "short" in later
    assert "longer value" not in later
