import pytest

from aui import NavigationRail, NavigationRailDestination, State
from aui.backends.ascii import AsciiBackend


def test_navigation_rail_updates_its_bound_selection():
    selection = State(0)
    rail = NavigationRail([
        NavigationRailDestination("Home", "house"),
        NavigationRailDestination("Settings", "gear", "gearshape.fill"),
    ], selection.binding(), extended=True)
    rail.select(1)
    assert selection.wrapped_value == 1
    assert rail.active_index == 1
    assert "● Settings" in AsciiBackend(width=40, height=4).render(rail)


def test_navigation_rail_validates_destinations_and_indexes():
    with pytest.raises(TypeError):
        NavigationRail([])
    with pytest.raises(ValueError):
        NavigationRailDestination("")
    rail = NavigationRail([NavigationRailDestination("Home")])
    with pytest.raises(IndexError):
        rail.select(1)
