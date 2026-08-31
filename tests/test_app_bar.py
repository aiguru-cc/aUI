import pytest

from aui import AppBar, Button, Size, Text
from aui.backends.ascii import AsciiBackend


def test_app_bar_measurement_and_ascii_fallback():
    bar = AppBar("Workspace", leading=Button("Back", lambda: None),
                 actions=[Button("Save", lambda: None)], center_title=True)
    assert bar.size_that_fits(Size(800, 500)).height == 52
    rendered = AsciiBackend(width=40, height=4).render(bar)
    assert "Workspace" in rendered and "Save" in rendered


def test_app_bar_validates_its_configuration():
    with pytest.raises(TypeError):
        AppBar("Title", leading="menu")
    with pytest.raises(TypeError):
        AppBar("Title", actions=["save"])
    with pytest.raises(ValueError):
        AppBar("Title", height=0)
