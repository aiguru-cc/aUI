"""SwiftUI-like searchable containers, suggestions, scopes, and tokens."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Sequence

from .geometry import Point, Size
from .layout import VStack
from .state import Binding
from .view import View


@dataclass(frozen=True)
class SearchToken:
    value: Any
    label: str
    system_name: str = ""


class DismissSearchAction:
    def __init__(self, text: Binding[str], is_presented: Binding[bool] | None = None):
        self.text, self.is_presented = text, is_presented

    def __call__(self) -> None:
        self.text.wrapped_value = ""
        if self.is_presented is not None: self.is_presented.wrapped_value = False


class SearchableView(VStack):
    """A structural searchable wrapper rendered by every backend."""

    PLACEMENTS = {"automatic", "toolbar", "sidebar", "navigationBarDrawer"}

    def __init__(self, content: View, text: Binding[str], prompt: str = "Search",
                 placement: str = "automatic", suggestions=(),
                 scopes: Sequence[Any] = (), scope: Binding | None = None,
                 tokens: Sequence[SearchToken] = (), is_presented: Binding[bool] | None = None,
                 on_submit: Optional[Callable[[str], None]] = None):
        if not isinstance(content, View): raise TypeError("searchable content must be a View")
        if not isinstance(text, Binding): raise TypeError("searchable text must be a Binding")
        if placement not in self.PLACEMENTS: raise ValueError(f"unsupported search placement: {placement!r}")
        if scope is not None and not isinstance(scope, Binding): raise TypeError("search scope must be a Binding")
        if not all(isinstance(token, SearchToken) for token in tokens): raise TypeError("tokens must be SearchToken values")
        self.content, self.text, self.prompt, self.placement = content, text, str(prompt), placement
        self.suggestions_source, self.scopes, self.scope = suggestions, tuple(scopes), scope
        self.tokens, self.is_presented, self.submit_action = tuple(tokens), is_presented, on_submit
        self.dismiss_search = DismissSearchAction(text, is_presented)
        super().__init__(self._make_children(), spacing=6.0, alignment="leading")

    def _suggestion_values(self):
        source = self.suggestions_source
        values = source(self.text.wrapped_value) if callable(source) else source
        return list(values or ())

    @property
    def visible_suggestions(self):
        from .components import Text
        query = self.text.wrapped_value.casefold().strip()
        values = self._suggestion_values()
        if not query: return []
        result = []
        for value in values:
            view = value if isinstance(value, View) else Text(str(value))
            haystack = getattr(view, "content", str(value)).casefold()
            if query in haystack: result.append(view)
        return result

    def _make_children(self):
        from .components import Picker, SearchField, Text
        from .styles import PickerStyle
        from .layout import HStack
        search = SearchField(self.text, self.prompt)
        if self.submit_action is not None:
            search = search.on_submit(lambda: self.submit_action(self.text.wrapped_value))
        header: View = search
        if self.scopes:
            if self.scope is None: raise ValueError("search scopes require a scope Binding")
            scopes = Picker("", selection=self.scope, options=self.scopes).picker_style(
                PickerStyle.SEGMENTED
            )
            header = HStack([search, scopes])
        children = [header]
        if self.tokens:
            children.append(HStack([Text(f"#{token.label}") for token in self.tokens], spacing=4))
        children.extend(self.visible_suggestions)
        children.append(self.content)
        return children

    def refresh(self) -> "SearchableView":
        self._children = self._make_children()
        return self

    def submit(self) -> None:
        if self.submit_action is not None: self.submit_action(self.text.wrapped_value)


def searchable(view: View, text: Binding[str], prompt="Search", placement="automatic",
               suggestions=(), scopes=(), scope=None, tokens=(), is_presented=None,
               on_submit=None) -> SearchableView:
    return SearchableView(view, text, prompt, placement, suggestions, scopes, scope,
                          tokens, is_presented, on_submit)
