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
