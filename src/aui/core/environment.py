"""Scoped environment propagation and deferred environment readers."""
from __future__ import annotations

from typing import Any, Callable

from .geometry import Point, Size
from .state import Environment, EnvironmentObject, EnvironmentValue
from .view import View, ViewModifier, _ModifiedContent, _apply


class EnvironmentModifier(ViewModifier):
    def __init__(self, key: str, value: Any):
        if not key:
            raise ValueError("environment key cannot be empty")
        self.key = key
        self.value = value

    def size_that_fits(self, content: View, proposal: Size) -> Size:
        return content.size_that_fits(proposal)

    def place(self, content: View, origin: Point, size: Size) -> None:
        content.place(origin, size)


class EnvironmentReader(View):
    """Build content lazily from a scoped EnvironmentValue or EnvironmentObject."""

    def __init__(self, request: EnvironmentValue | EnvironmentObject,
                 content: Callable[[Any], View]):
        if not isinstance(request, (EnvironmentValue, EnvironmentObject)):
            raise TypeError("EnvironmentReader requires EnvironmentValue or EnvironmentObject")
        if not callable(content):
            raise TypeError("EnvironmentReader content must be callable")
        self.request = request
        self._builder = content
        self.content = None
        self._children = []

    def resolve(self, environment: Environment) -> View:
        value = self.request.resolve(environment)
        content = self._builder(value)
        if not isinstance(content, View):
            raise TypeError("EnvironmentReader content must return a View")
        self.content = content
        self._children = [content]
        return content

    def size_that_fits(self, proposal: Size) -> Size:
        if self.content is None:
            self.resolve(Environment())
        return self.content.size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        if self.content is None:
            self.resolve(Environment())
        self.content.place(origin, size)

    def children(self):
        return self._children


def environment(view: View, key: str, value: Any) -> View:
    return _apply(view, EnvironmentModifier(key, value))


def environment_object(view: View, value: Any) -> View:
    key = EnvironmentObject(type(value)).key
    return environment(view, key, value)


def resolve_environment_tree(view: View, base: Environment | None = None) -> View:
    """Resolve scoped readers before measurement and native rendering."""
    root = base or Environment()

    def visit(node: View, current: Environment) -> None:
        node._environment = current
        if isinstance(node, _ModifiedContent):
            child_environment = current
            if isinstance(node._modifier, EnvironmentModifier):
                child_environment = current.set(node._modifier.key, node._modifier.value)
                node._environment = child_environment
            visit(node._content, child_environment)
            return
        if isinstance(node, EnvironmentReader):
            visit(node.resolve(current), current)
            return
        for child in node.children():
            visit(child, current)

    visit(view, root)
    return view


__all__ = [
    "EnvironmentModifier", "EnvironmentReader", "environment",
    "environment_object", "resolve_environment_tree",
]
