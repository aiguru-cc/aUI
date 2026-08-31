from aui import DisclosureGroup, List, NavigationRail, NavigationRailDestination, TabView, Text, VStack
from aui.core.state_persistence import restore_local_state


def test_local_tab_disclosure_list_and_rail_state_survive_a_matching_rebuild():
    old_tab = TabView([("One", Text("1")), ("Two", Text("2"))]); old_tab.select(1)
    old_disclosure = DisclosureGroup(Text("More"), [Text("Body")]); old_disclosure.toggle()
    old_list = List([Text("A"), Text("B")]); old_list.scroll_to(1)
    old_rail = NavigationRail([NavigationRailDestination("Home"), NavigationRailDestination("Settings")]); old_rail.select(1)
    old = VStack([old_tab, old_disclosure, old_list, old_rail])

    new_tab = TabView([("One", Text("1")), ("Two", Text("2"))])
    new_disclosure = DisclosureGroup(Text("More"), [Text("Body")])
    new_list = List([Text("A"), Text("B")])
    new_rail = NavigationRail([NavigationRailDestination("Home"), NavigationRailDestination("Settings")])
    restore_local_state(old, VStack([new_tab, new_disclosure, new_list, new_rail]))

    assert new_tab._active_index() == 1
    assert not new_disclosure.expanded
    assert new_list.current_offset() == 1
    assert new_rail.active_index == 1


def test_bound_state_remains_authoritative_during_rebuild():
    from aui import State
    selection = State(0)
    old = TabView([("One", Text("1")), ("Two", Text("2"))], selection.binding())
    old.select(1)
    current = TabView([("One", Text("1")), ("Two", Text("2"))], selection.binding())
    restore_local_state(old, current)
    assert current._active_index() == 1


def test_explicit_view_ids_keep_local_state_with_reordered_siblings():
    old_first = DisclosureGroup(Text("First"), [Text("A")]).id("first")
    old_second = DisclosureGroup(Text("Second"), [Text("B")]).id("second")
    old_first._content.toggle()
    old = VStack([old_first, old_second])

    new_second = DisclosureGroup(Text("Second"), [Text("B")]).id("second")
    new_first = DisclosureGroup(Text("First"), [Text("A")]).id("first")
    restore_local_state(old, VStack([new_second, new_first]))
    assert not new_first._content.expanded
    assert new_second._content.expanded


def test_state_restore_does_not_walk_virtualized_list_rows():
    rows = [Text(str(index)) for index in range(100_000)]
    old, current = List(rows), List(rows)
    old.scroll_to(50_000)
    restore_local_state(old, current)
    assert current.current_offset() == 50_000
