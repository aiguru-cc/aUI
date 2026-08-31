import pytest

from aui import EdgeInsets, GeometryProxy, GeometryReader, Point, Rect, Size, Text
from aui.backends.ascii import AsciiBackend


def test_rect_exposes_swiftui_style_edges_and_centers():
    rect = Rect(Point(10, 20), Size(80, 40))

    assert (rect.min_x, rect.min_y) == (10, 20)
    assert (rect.max_x, rect.max_y) == (90, 60)
    assert (rect.mid_x, rect.mid_y) == (50, 40)


def test_geometry_proxy_local_global_and_safe_area():
    insets = EdgeInsets(top=12, leading=4, bottom=8, trailing=4)
    proxy = GeometryProxy(Size(300, 180), Point(20, 30), insets)

    assert proxy.frame("local") == Rect(Point(), Size(300, 180))
    assert proxy.frame("global") == Rect(Point(20, 30), Size(300, 180))
    assert proxy.safe_area_insets == insets
    with pytest.raises(ValueError, match="local.*global"):
        proxy.frame("named")


def test_geometry_reader_takes_finite_proposed_size():
    seen = []
    reader = GeometryReader(lambda proxy: seen.append(proxy.size) or Text("content"))

    assert reader.size_that_fits(Size(320, 200)) == Size(320, 200)
    assert seen[-1] == Size(320, 200)


def test_geometry_reader_uses_child_natural_size_for_unbounded_axes():
    reader = GeometryReader(lambda proxy: Text("hello"))
    size = reader.size_that_fits(Size(float("inf"), float("inf")))

    assert size.width == pytest.approx(5 * 14 * 0.55)
    assert size.height == pytest.approx(19.6)


def test_geometry_reader_updates_global_frame_when_placed():
    frames = []
    reader = GeometryReader(
        lambda proxy: frames.append(proxy.frame("global")) or Text("frame")
    )

    reader.place(Point(12, 34), Size(200, 90))
    assert frames[-1] == Rect(Point(12, 34), Size(200, 90))


def test_geometry_reader_is_transparent_to_ascii_backend():
    view = GeometryReader(lambda proxy: Text(f"width={int(proxy.size.width)}"))

    output = AsciiBackend(width=24, height=3).render(view)
    assert "width=24" in output


def test_geometry_reader_requires_view_content():
    with pytest.raises(TypeError, match="return a View"):
        GeometryReader(lambda proxy: "not a view")
