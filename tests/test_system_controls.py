import pytest

from aui import PasteButton, ShareLink, State, describe_accessibility
from aui.backends.ascii import AsciiBackend


def test_share_link_normalizes_items_and_calls_injected_handler():
    shared = []
    link = ShareLink(
        ["https://example.com", "Notes"],
        subject="Project",
        message="Take a look",
        share_handler=lambda items: shared.append(items),
    )

    link.action()
    assert shared == [("https://example.com", "Notes")]
    assert link.subject == "Project"
    assert describe_accessibility(link).role == "button"
    assert "Share" in AsciiBackend().render(link)


def test_share_link_requires_content_and_can_replace_handler():
    with pytest.raises(ValueError, match="at least one item"):
        ShareLink([])

    shared = []
    link = ShareLink("first", share_handler=lambda items: shared.append("old"))
    link.connect(lambda items: shared.append(items[0]))
    link.action()
    assert shared == ["first"]


def test_paste_button_writes_binding_and_callback():
    text = State("")
    received = []
    button = PasteButton(
        text=text.binding(),
        on_paste=received.append,
        provider=lambda: "pasted text",
    )

    button.action()
    assert text.value == "pasted text"
    assert received == ["pasted text"]
    assert describe_accessibility(button).label == "Paste"


def test_paste_button_ignores_empty_pasteboard_and_validates_sink():
    text = State("original")
    PasteButton(text=text.binding(), provider=lambda: None).action()
    assert text.value == "original"

    with pytest.raises(ValueError, match="binding or on_paste"):
        PasteButton()
    with pytest.raises(TypeError, match="must be callable"):
        PasteButton(on_paste="invalid")
