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
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Dict, Generic, List, Optional, Set, TypeVar

T = TypeVar("T")

_CURRENT_OBSERVER: ContextVar[Optional[Callable[[], None]]] = ContextVar(
    "aui_current_observer", default=None
)
_CURRENT_CLEANUPS: ContextVar[Optional[list[Callable[[], None]]]] = ContextVar(
    "aui_current_cleanups", default=None
)


def _track_object(value: Any) -> None:
    observer = _CURRENT_OBSERVER.get()
    cleanups = _CURRENT_CLEANUPS.get()
    if observer is None or cleanups is None or not hasattr(value, "add_listener"):
        return
    value.add_listener(observer)
    cleanup = lambda: value.remove_listener(observer)
    if cleanup not in cleanups:
        cleanups.append(cleanup)


@contextmanager
def observation_tracking(observer: Callable[[], None]):
    """Track observable values read while building a declarative view tree."""
    cleanups: list[Callable[[], None]] = []
    observer_token = _CURRENT_OBSERVER.set(observer)
    cleanup_token = _CURRENT_CLEANUPS.set(cleanups)
    try:
        yield cleanups
    finally:
        _CURRENT_CLEANUPS.reset(cleanup_token)
        _CURRENT_OBSERVER.reset(observer_token)


class ObservableObject:
    """Base class for shared observable state (mirrors ObservableObject)."""

    def __init__(self) -> None:
        self._listeners: Set[Callable[[], None]] = set()
        self._listener_lock = threading.RLock()

    def _notify(self) -> None:
        with self._listener_lock:
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener()

    def object_will_change(self) -> None:
        self._notify()

    def add_listener(self, listener: Callable[[], None]) -> None:
        with self._listener_lock:
            self._listeners.add(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        with self._listener_lock:
            self._listeners.discard(listener)


def observable(cls: type) -> type:
    """Class decorator: make attribute writes notify observers.

    Usage::

        @observable
        class Counter:
            count = 0
    """
    original_init = cls.__init__
    original_getattribute = cls.__getattribute__
    original_setattr = cls.__setattr__

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        self._listeners: Set[Callable[[], None]] = set()
        self._listener_lock = threading.RLock()

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
                _track_object(inst)
                return inst.__dict__.get(attr, default)

            def setter(inst: Any, val: Any) -> None:
                if inst.__dict__.get(attr) != val:
                    inst.__dict__[attr] = val
                    lock = getattr(inst, "_listener_lock", None)
                    if lock is None:
                        listeners = tuple(getattr(inst, "_listeners", ()))
                    else:
                        with lock:
                            listeners = tuple(getattr(inst, "_listeners", ()))
                    for listener in listeners:
                        listener()

            return property(getter, setter)

        setattr(cls, name, make_prop(name, value))

    def add_listener(self, listener: Callable[[], None]) -> None:
        if not callable(listener):
            raise TypeError("observable listener must be callable")
        with self._listener_lock:
            self._listeners.add(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        with self._listener_lock:
            self._listeners.discard(listener)

    def __getattribute__(self, name: str):
        value = original_getattribute(self, name)
        if not name.startswith("_") and not callable(value):
            _track_object(self)
        return value

    def __setattr__(self, name: str, value: Any) -> None:
        descriptor = vars(cls).get(name)
        if name.startswith("_") or isinstance(descriptor, property):
            original_setattr(self, name, value)
            return
        missing = object()
        previous = self.__dict__.get(name, missing)
        original_setattr(self, name, value)
        if ((previous is not missing and previous == value)
                or "_listeners" not in self.__dict__):
            return
        with self._listener_lock:
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener()

    cls.add_listener = add_listener
    cls.remove_listener = remove_listener
    cls.__getattribute__ = __getattribute__
    cls.__setattr__ = __setattr__
    return cls


class State(Generic[T]):
    """View-local mutable state that invalidates its owner on change.

    ``State`` must be created inside a ``View`` subclass attribute or via
    ``State.initial`` so the view can register itself as an observer.
    """

    def __init__(self, initial: T, owner: Optional[Any] = None):
        self._value = initial
        self._owner = owner
        self._listeners: Set[Callable[[], None]] = set()
        self._lock = threading.RLock()

    @classmethod
    def initial(cls, value: T) -> "State[T]":
        return cls(value)

    @property
    def wrapped_value(self) -> T:
        _track_object(self)
        with self._lock:
            return self._value

    @wrapped_value.setter
    def wrapped_value(self, value: T) -> None:
        with self._lock:
            if self._value == value:
                return
            self._value = value
            listeners = tuple(self._listeners)
        if self._owner is not None:
            self._owner._invalidate()
        for listener in listeners:
            listener()

    def add_listener(self, listener: Callable[[], None]) -> None:
        if not callable(listener):
            raise TypeError("State listener must be callable")
        with self._lock:
            self._listeners.add(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        with self._lock:
            self._listeners.discard(listener)

    # SwiftUI-style accessors
    @property
    def value(self) -> T:
        return self.wrapped_value

    @value.setter
    def value(self, value: T) -> None:
        self.wrapped_value = value

    def binding(self) -> "Binding[T]":
        return Binding(getter=lambda: self.wrapped_value, setter=self._set)

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


class ObservedObject(Generic[T]):
    """A non-owning observable model reference tracked during view construction."""

    def __init__(self, value: T):
        if not hasattr(value, "add_listener") or not hasattr(value, "remove_listener"):
            raise TypeError("ObservedObject value must support add_listener/remove_listener")
        self._value = value

    @property
    def wrapped_value(self) -> T:
        _track_object(self._value)
        return self._value

    @property
    def value(self) -> T:
        return self.wrapped_value

    def binding(self, attribute: str) -> Binding:
        if not attribute:
            raise ValueError("ObservedObject binding attribute cannot be empty")
        return Binding(
            getter=lambda: getattr(self.wrapped_value, attribute),
            setter=lambda value: setattr(self.wrapped_value, attribute, value),
        )


class StateObject(ObservedObject[T]):
    """An owning, lazily created observable model reference."""

    def __init__(self, factory: Callable[[], T] | T):
        if callable(factory):
            self._factory = factory
            self._value = None
        else:
            self._factory = None
            self._value = factory
            self._validate(factory)

    @staticmethod
    def _validate(value: Any) -> None:
        if not hasattr(value, "add_listener") or not hasattr(value, "remove_listener"):
            raise TypeError("StateObject value must support add_listener/remove_listener")

    @property
    def wrapped_value(self) -> T:
        if self._value is None:
            value = self._factory()
            self._validate(value)
            self._value = value
        _track_object(self._value)
        return self._value

    @property
    def value(self) -> T:
        return self.wrapped_value


class EnvironmentValue(Generic[T]):
    """A typed lookup request consumed by ``EnvironmentReader``."""

    def __init__(self, key: str, default: Optional[T] = None):
        if not key:
            raise ValueError("EnvironmentValue key cannot be empty")
        self.key = key
        self.default = default

    def resolve(self, environment: "Environment") -> T:
        return environment.get(self.key, self.default)


class EnvironmentObject(Generic[T]):
    """A typed observable-model lookup consumed by ``EnvironmentReader``."""

    def __init__(self, object_type: type[T]):
        if not isinstance(object_type, type):
            raise TypeError("EnvironmentObject requires a type")
        self.object_type = object_type

    @property
    def key(self) -> str:
        return f"object:{self.object_type.__module__}.{self.object_type.__qualname__}"

    def resolve(self, environment: "Environment") -> T:
        value = environment.get(self.key)
        if value is None:
            raise LookupError(f"no environment object for {self.object_type.__name__}")
        if not isinstance(value, self.object_type):
            raise TypeError(f"environment object is not {self.object_type.__name__}")
        _track_object(value)
        return value


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

    def object(self, value: Any) -> "Environment":
        key = f"object:{type(value).__module__}.{type(value).__qualname__}"
        return self.set(key, value)


__all__ = [
    "Binding", "Environment", "EnvironmentObject", "EnvironmentValue",
    "ObservableObject", "ObservedObject", "State", "StateObject", "observable",
    "observation_tracking",
]
