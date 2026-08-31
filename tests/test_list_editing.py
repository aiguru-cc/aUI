import pytest

from aui import EditMode, List, ListRowAction, State, Text
from aui.backends.curses import CursesBackend
from aui.core.list_editing import list_row_editing


def rows():
    return [Text("Alpha").id("a"), Text("Beta").id("b"), Text("Gamma").id("c")]


def test_list_single_and_multiple_selection_use_stable_row_ids():
    single = State(None)
    view = List(rows(), selection=single.binding())
    view.select_row(1)
    assert single.value == "b"

    multiple = State(set())
    view = List(rows(), selection=multiple.binding())
    view.select_row(0, extending=True)
    view.select_row(2, extending=True)
    view.select_row(0, extending=True)
    assert multiple.value == {"c"}


def test_delete_respects_row_restriction_and_cleans_selection():
    selected = State({"a", "b", "c"})
    events = []
    view = List(
        [rows()[0], rows()[1].delete_disabled(), rows()[2]],
        selection=selected.binding(), on_delete=events.append,
    )
    removed = view.delete_rows((0, 1, 2))
    assert len(removed) == 2
    assert [view.row_id(row, index) for index, row in enumerate(view.rows)] == ["b"]
    assert selected.value == {"b"}
    assert events == [(0, 2)]


def test_move_rows_and_move_disabled():
    events = []
    view = List(rows(), on_move=lambda indices, destination: events.append((indices, destination)))
    view.move_rows((0,), 3)
    assert [view.row_id(row, index) for index, row in enumerate(view.rows)] == ["b", "c", "a"]
    assert events == [((0,), 3)]

    locked = List([Text("A").move_disabled(), Text("B")])
    locked.move_rows((0,), 2)
    assert [row.body().content for row in locked.rows] == ["A", "B"]


def test_row_actions_and_edit_mode_validate():
    called = []
    row = Text("Row").swipe_actions([
        ListRowAction("Archive", lambda: called.append("archive")),
        ListRowAction("Delete", lambda: called.append("delete"), role="destructive"),
    ])
    actions, edge, full_swipe = list_row_editing(row)["swipe_actions"]
    actions[1].action()
    assert called == ["delete"]
    assert edge == "trailing" and full_swipe is True

    with pytest.raises(ValueError, match="edit mode"):
        List([], edit_mode=State("unknown").binding())
    with pytest.raises(ValueError, match="title"):
        ListRowAction("", lambda: None)


def test_curses_exposes_plain_rows_for_selection_delete_and_move():
    selected = State(None)
    mode = State(EditMode.ACTIVE)
    view = List(rows(), selection=selected.binding(), edit_mode=mode.binding())
    backend = CursesBackend(lambda: view)
    backend.render_to_string(width=30, height=8)

    backend._activate()
    assert selected.value == "a"
    backend._handle_key(ord("J"))
    assert [view.row_id(row, index) for index, row in enumerate(view.rows)] == ["b", "a", "c"]
    backend._handle_key(ord("D"))
    assert len(view.rows) == 2


def test_curses_edit_commands_require_active_edit_mode():
    mode = State(EditMode.INACTIVE)
    view = List(rows(), edit_mode=mode.binding())
    backend = CursesBackend(lambda: view)
    backend.render_to_string(width=30, height=8)
    backend._handle_key(ord("D"))
    assert len(view.rows) == 3
