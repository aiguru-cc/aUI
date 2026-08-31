import pytest

from aui import (
    NavigationLink, NavigationPath, NavigationStack, Size, Text,
    describe_accessibility,
)
from aui.backends.ascii import AsciiBackend


def test_navigation_path_push_pop_and_notifications():
    path = NavigationPath()
    lengths = []
    cancel = path.subscribe(lambda value: lengths.append(len(value)))
    path.append("detail")
    path.append(2)
    path.remove_last()
    path.clear()
    cancel()
    assert lengths == [1, 2, 1, 0]
    assert len(path) == 0


def test_navigation_path_rejects_invalid_operations():
    path = NavigationPath(["root"])
    with pytest.raises(TypeError):
        path.append([])
    with pytest.raises(IndexError):
        path.remove_last(2)
    with pytest.raises(ValueError):
        path.remove_last(-1)


def test_navigation_stack_resolves_typed_destination():
    path = NavigationPath()
    stack = NavigationStack(Text("Root").navigation_title("Library"), path=path)
    stack.navigation_destination(str, lambda value: Text(f"Article: {value}"))
    link = NavigationLink("Open", "SwiftUI", path)
    link.activate()
    assert stack.content.content == "Article: SwiftUI"
    assert stack.children()[0] is stack.content
    stack.go_back()
    assert stack.content._content.content == "Root"


def test_navigation_link_accessibility_and_ascii():
    link = NavigationLink("Details", 42, NavigationPath())
    assert describe_accessibility(link).role == "link"
    assert "Details" in AsciiBackend().render(link)


def test_navigation_stack_uses_content_first_constructor():
    stack = NavigationStack(Text("Content").navigation_title("Title"))
    assert stack.size_that_fits(Size(300, 200)).height > 24
    with pytest.raises(TypeError):
        NavigationStack("Title", Text("Content"))
