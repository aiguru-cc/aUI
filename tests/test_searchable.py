import pytest

from aui import (
    DismissSearchAction, Picker, PickerStyle, SearchToken,
    State, Text, VStack,
)
from aui.core.styles import resolve_style_tree
from aui.core.components import SearchField
from aui.core.search import SearchableView
from aui.backends.ascii import AsciiBackend


def test_searchable_builds_native_search_field_and_content():
    query = State("")
    content = VStack([Text("Inbox")]).searchable(query.binding(), prompt="Find mail")
    assert isinstance(content, SearchableView)
    assert isinstance(content.find(lambda view: isinstance(view, SearchField)), SearchField)
    assert content.content.find(lambda view: isinstance(view, Text)).content == "Inbox"


def test_suggestions_filter_and_refresh():
    query = State("")
    view = Text("Results").searchable(
        query.binding(), suggestions=["Apple", "Apricot", "Banana"]
    )
    assert view.visible_suggestions == []
    query.wrapped_value = "ap"
    view.refresh()
    assert [item.content for item in view.visible_suggestions] == ["Apple", "Apricot"]
    output = AsciiBackend(40, 8).render(view)
    assert "Apple" in output and "Banana" not in output


def test_dynamic_suggestion_builder_receives_query():
    query = State("py")
    calls = []
    view = Text("Content").searchable(
        query.binding(), suggestions=lambda value: calls.append(value) or [value.upper()]
    )
    assert view.visible_suggestions[0].content == "PY"
    assert calls[-1] == "py"


def test_search_scopes_build_segmented_picker():
    query, scope = State(""), State("All")
    view = Text("Content").searchable(
        query.binding(), scopes=["All", "Unread"], scope=scope.binding()
    )
    resolve_style_tree(view)
    segmented = view.find(
        lambda item: isinstance(item, Picker)
        and getattr(item, "_resolved_style", {}).get("picker_style") == PickerStyle.SEGMENTED
    )
    assert segmented.options == ["All", "Unread"]
    with pytest.raises(ValueError):
        Text("x").searchable(query.binding(), scopes=["A", "B"])


def test_search_tokens_are_rendered():
    query = State("")
    tokens = [SearchToken("swift", "Swift", "swift"), SearchToken("python", "Python")]
    view = Text("Content").searchable(query.binding(), tokens=tokens)
    output = AsciiBackend(40, 6).render(view)
    assert "#Swift" in output and "#Python" in output


def test_submit_and_dismiss_search():
    query, presented = State("hello"), State(True)
    submitted = []
    view = Text("Content").searchable(
        query.binding(), is_presented=presented.binding(), on_submit=submitted.append
    )
    view.submit()
    assert submitted == ["hello"]
    view.dismiss_search()
    assert query.wrapped_value == "" and not presented.wrapped_value


def test_searchable_validation():
    query = State("")
    with pytest.raises(ValueError): Text("x").searchable(query.binding(), placement="window")
    with pytest.raises(TypeError): SearchableView(Text("x"), "query")
    with pytest.raises(TypeError): Text("x").searchable(query.binding(), tokens=["token"])
