from dataclasses import dataclass

import pytest

from aui import SortOrder, State, Table, TableColumn, describe_accessibility
from aui.backends.ascii import AsciiBackend
from aui.core.geometry import Size


@dataclass
class Person:
    id: int
    name: str
    age: int


ROWS = [Person(1, "Ada", 36), Person(2, "Grace", 85), Person(3, "Alan", 41)]
COLUMNS = [TableColumn("Name", "name"), TableColumn("Age", "age", width=80)]


def test_table_sorts_and_selects_object_rows():
    selected = State(None)
    order = State(SortOrder("age", ascending=False))
    table = Table(ROWS, COLUMNS, selection=selected.binding(), sort_order=order.binding())
    assert [row.name for row in table.displayed_rows] == ["Grace", "Alan", "Ada"]
    table.select_row(1)
    assert selected.wrapped_value == 3
    table.move_selection(1)
    assert selected.wrapped_value == 3


def test_table_supports_dicts_and_value_closures():
    rows = [{"key": "a", "first": "Ada", "last": "Lovelace"}]
    table = Table(rows, [
        TableColumn("Name", "name", value=lambda row: f"{row['first']} {row['last']}")
    ], id_key="key")
    assert table.columns[0].get_value(rows[0]) == "Ada Lovelace"
    assert table.size_that_fits(Size(500, 400)).height >= 160


def test_table_validates_columns_and_renders_headless():
    with pytest.raises(ValueError):
        Table([], [])
    with pytest.raises(ValueError):
        Table([], [TableColumn("A", "x"), TableColumn("B", "x")])
    table = Table(ROWS, COLUMNS)
    rendered = AsciiBackend(width=60, height=8).render(table)
    assert "Name" in rendered and "Grace" in rendered
    assert describe_accessibility(table).role == "table"


def test_table_multiple_selection_binding():
    selected = State({1, 3})
    table = Table(ROWS, COLUMNS, selection=selected.binding())
    assert table.allows_multiple_selection is True
    table.select_row(1, extending=True)
    assert selected.value == {1, 2, 3}
    table.select_row(0, extending=True)
    assert selected.value == {2, 3}
    table.select_row(1)
    assert selected.value == {2}


def test_table_multi_column_sort_chain_and_updates():
    rows = [
        {"id": 1, "team": "B", "score": 2},
        {"id": 2, "team": "A", "score": 1},
        {"id": 3, "team": "A", "score": 3},
    ]
    order = State([SortOrder("team"), SortOrder("score", ascending=False)])
    table = Table(rows, [TableColumn("Team", "team"), TableColumn("Score", "score")],
                  sort_order=order.binding())
    assert [row["id"] for row in table.displayed_rows] == [3, 2, 1]
    table.set_sort("score", ascending=True, additive=True)
    assert order.value[-1] == SortOrder("score", True)
    with pytest.raises(KeyError): table.set_sort("missing")


def test_table_column_visibility_width_constraints_and_empty_state():
    show_age = State(False)
    columns = [
        TableColumn("Name", "name", width=500, minimum_width=100, maximum_width=220),
        TableColumn("Age", "age", visible=show_age.binding()),
    ]
    table = Table(ROWS, columns)
    assert [column.key for column in table.visible_columns] == ["name"]
    assert columns[0].resolved_width() == 220
    show_age.value = True
    assert len(table.visible_columns) == 2
    empty = Table([], columns, empty_message="Nothing Here")
    assert "Nothing Here" in AsciiBackend(width=40, height=4).render(empty)
    with pytest.raises(ValueError):
        TableColumn("Bad", "bad", minimum_width=200, maximum_width=100)


def test_table_binding_validation():
    with pytest.raises(TypeError): Table(ROWS, COLUMNS, selection=1)
    with pytest.raises(TypeError): Table(ROWS, COLUMNS, sort_order=SortOrder("age"))
