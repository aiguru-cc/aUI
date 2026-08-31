import pytest

from aui import Point, ResponsiveBreakpoint, ResponsiveItem, ResponsiveRow, Size, Text
from aui.backends.ascii import AsciiBackend


def test_responsive_item_selects_the_active_breakpoint_span():
    item = ResponsiveItem(Text("Card"), {"xs": 12, "sm": 6, "lg": 3})
    assert item.span(400) == 12
    assert item.span(600) == 6
    assert item.span(1100) == 3


def test_responsive_row_wraps_items_and_preserves_column_geometry():
    row = ResponsiveRow([
        ResponsiveItem(Text("A"), {"xs": 12, "md": 4}),
        ResponsiveItem(Text("B"), {"xs": 12, "md": 4}),
        ResponsiveItem(Text("C"), {"xs": 12, "md": 4}),
    ])
    narrow = row.placements(origin=Point(), size=Size(500, 500))
    wide = row.placements(origin=Point(), size=Size(900, 500))
    assert len({point.y for _, point, _ in narrow}) == 3
    assert len({point.y for _, point, _ in wide}) == 1
    assert sum(item_size.width for _, _, item_size in wide) + row.spacing * 2 == pytest.approx(900)


def test_responsive_row_ascii_fallback_and_validation():
    row = ResponsiveRow([ResponsiveItem(Text("Responsive"), 12)])
    assert "Responsive" in AsciiBackend(width=40, height=4).render(row)
    with pytest.raises(ValueError):
        ResponsiveItem(Text("Bad"), {"phone": 4})
    with pytest.raises(ValueError):
        ResponsiveRow([], columns=0)
    assert ResponsiveBreakpoint.XL == "xl"
