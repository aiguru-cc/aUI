import pytest

from aui import ScrollViewProxy, ScrollViewReader, Size, Text, VStack
from aui.backends.ascii import AsciiBackend
from aui.core.scrolling import IDModifier


def test_scroll_proxy_validates_and_notifies_requests():
    proxy = ScrollViewProxy()
    requests = []
    cancel = proxy.subscribe(lambda view_id, anchor: requests.append((view_id, anchor)))
    proxy.scroll_to("row-20", anchor="center")
    cancel()
    proxy.scroll_to("row-30", anchor="bottom")
    assert requests == [("row-20", "center")]
    assert proxy.last_request == ("row-30", "bottom")
    with pytest.raises(ValueError):
        proxy.scroll_to("x", anchor="leading")


def test_view_id_modifier_is_layout_transparent():
    base = Text("Row")
    identified = base.id("row-1")
    assert isinstance(identified._modifier, IDModifier)
    assert identified.size_that_fits(Size(200, 100)) == base.size_that_fits(Size(200, 100))
    with pytest.raises(TypeError):
        base.id([])


def test_scroll_view_reader_exposes_proxy_and_content():
    captured = []

    def build(proxy):
        captured.append(proxy)
        return VStack([Text("First").id(1), Text("Last").id(2)])

    reader = ScrollViewReader(build)
    assert reader.proxy is captured[0]
    assert len(reader.children()) == 1
    assert "First" in AsciiBackend(width=40, height=5).render(reader)


def test_scroll_view_reader_validates_builder():
    with pytest.raises(TypeError):
        ScrollViewReader(Text("not callable"))
    with pytest.raises(TypeError):
        ScrollViewReader(lambda proxy: "not a view")
