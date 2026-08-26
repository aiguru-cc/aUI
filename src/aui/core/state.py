"""Declarative state management for aUI.

Mirrors SwiftUI's ``@State`` / ``@Binding`` / ``ObservableObject`` model:

* ``State``  — view-local mutable state that triggers re-render on change.
* ``Binding`` — a two-way reference to a piece of state.
* ``ObservableObject`` + ``@observable`` — shared observable state.
* ``Environment`` — a lightweight dependency-injection container.
"""
from __future__ import annotations

import inspect
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Set, TypeVar

T = TypeVar("T")


class ObservableObject:
    """Base class for shared observable state (mirrors ObservableObject)."""

    def __init__(self) -> None:
        self._listeners: Set[Callable[[], None]] = set()

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def object_will_change(self) -> None:
        self._notify()

    def add_listener(self, listener: Callable[[], None]) -> None:
        self._listeners.add(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        self._listeners.discard(listener)


def observable(cls: type) -> type:
    """Class decorator: make attribute writes notify observers.

    Usage::

        @observable
        class Counter:
            count = 0
    """
    original_init = cls.__init__

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        self._listeners: Set[Callable[[], None]] = set()

    cls.__init__ = __init__

    for name, value in list(vars(cls).items()):
        if name.startswith("__"):
            continue
        if isinstance(value, (classmethod, staticmethod, property)):
            continue
        if callable(value):
            continue

        def make_prop(attr: str, default: Any):
            def getter(inst: Any) -> Any:
                return inst.__dict__.get(attr, default)

            def setter(inst: Any, val: Any) -> None:
                if inst.__dict__.get(attr) != val:
                    inst.__dict__[attr] = val
                    for listener in list(getattr(inst, "_listeners", ())):
                        listener()

            return property(getter, setter)

        setattr(cls, name, make_prop(name, value))

    def add_listener(self, listener: Callable[[], None]) -> None:
        self._listeners.add(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        self._listeners.discard(listener)

    cls.add_listener = add_listener
    cls.remove_listener = remove_listener
    return cls


class State(Generic[T]):
    """View-local mutable state that invalidates its owner on change.

    ``State`` must be created inside a ``View`` subclass attribute or via
    ``State.initial`` so the view can register itself as an observer.
    """

    def __init__(self, initial: T, owner: Optional[Any] = None):
        self._value = initial
        self._owner = owner

    @classmethod
    def initial(cls, value: T) -> "State[T]":
        return cls(value)

    @property
    def wrapped_value(self) -> T:
        return self._value

    @wrapped_value.setter
    def wrapped_value(self, value: T) -> None:
        if self._value != value:
            self._value = value
            if self._owner is not None:
                self._owner._invalidate()

    # SwiftUI-style accessors
    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, value: T) -> None:
        self.wrapped_value = value

    def binding(self) -> "Binding[T]":
        return Binding(getter=lambda: self._value, setter=self._set)

    def _set(self, value: T) -> None:
        self.wrapped_value = value

    def __repr__(self) -> str:  # pragma: no cover
        return f"State({self._value!r})"


class Binding(Generic[T]):
    """A two-way reference to some state (mirrors SwiftUI's Binding)."""

    def __init__(self, getter: Callable[[], T], setter: Callable[[T], None]):
        self._getter = getter
        self._setter = setter

    @property
    def wrapped_value(self) -> T:
        return self._getter()

    @wrapped_value.setter
    def wrapped_value(self, value: T) -> None:
        self._setter(value)

    @property
    def value(self) -> T:
        return self._getter()

    @value.setter
    def value(self, value: T) -> None:
        self._setter(value)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Binding({self._getter()!r})"


class Environment:
    """A read-only environment passed down the view tree (mirrors @Environment)."""

    def __init__(self, values: Optional[Dict[str, Any]] = None):
        self._values: Dict[str, Any] = dict(values or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> "Environment":
        merged = dict(self._values)
        merged[key] = value
        return Environment(merged)

    def __contains__(self, key: str) -> bool:
        return key in self._values
