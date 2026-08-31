import pytest

from aui import IconButton, Size


def test_icon_button_has_a_symbol_accessibility_label_and_compact_size():
    button = IconButton("trash", lambda: None, label="Delete")
    assert button.system_name == "trash"
    assert button.title == "Delete"
    assert button.size_that_fits(Size(400, 400)) == Size(34, 32)


def test_icon_button_requires_a_system_name():
    with pytest.raises(ValueError):
        IconButton("", lambda: None)
