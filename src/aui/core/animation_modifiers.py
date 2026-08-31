"""Transaction and matched-geometry view modifiers."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from typing import Callable

from .animation import Animation, Transaction
from .view import View, ViewModifier, _apply

REDUCE_MOTION_KEY = "accessibilityReduceMotion"


_namespace_ids = count(1)


@dataclass(frozen=True)
class Namespace:
    """Identity scope used to pair matched-geometry views."""

    id: int

    @classmethod
    def create(cls) -> "Namespace":
        return cls(next(_namespace_ids))


@dataclass(frozen=True)
class TransactionModifier(ViewModifier):
    transform: Callable[[Transaction], None]

    def resolve(self, base: Transaction | None = None) -> Transaction:
        source = base or Transaction()
        value = Transaction(source.animation, source.disables_animations, source.is_continuous)
        result = self.transform(value)
        if result is not None:
            if not isinstance(result, Transaction):
                raise TypeError("transaction transform must mutate or return a Transaction")
            value = result
        return value

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


@dataclass(frozen=True)
class MatchedGeometryEffectModifier(ViewModifier):
    matched_id: object
    namespace: Namespace
    properties: str = "frame"
    anchor: str = "center"
    is_source: bool = True

    def __post_init__(self):
        if self.properties not in {"position", "size", "frame"}:
            raise ValueError(f"unsupported matched geometry properties: {self.properties!r}")
        if self.anchor not in {
            "topLeading", "top", "topTrailing", "leading", "center", "trailing",
            "bottomLeading", "bottom", "bottomTrailing",
        }:
            raise ValueError(f"unsupported matched geometry anchor: {self.anchor!r}")

    @property
    def key(self): return (self.namespace.id, self.matched_id)

    @property
    def anchor_fraction(self):
        return {
            "topLeading": (0.0, 0.0), "top": (0.5, 0.0),
            "topTrailing": (1.0, 0.0), "leading": (0.0, 0.5),
            "center": (0.5, 0.5), "trailing": (1.0, 0.5),
            "bottomLeading": (0.0, 1.0), "bottom": (0.5, 1.0),
            "bottomTrailing": (1.0, 1.0),
        }[self.anchor]

    def size_that_fits(self, content, proposal): return content.size_that_fits(proposal)
    def place(self, content, origin, size): content.place(origin, size)


def transaction(view: View, transform: Callable[[Transaction], None]) -> View:
    if not callable(transform):
        raise TypeError("transaction transform must be callable")
    return _apply(view, TransactionModifier(transform))


def matched_geometry_effect(view: View, matched_id, namespace: Namespace, *,
                            properties: str = "frame", anchor: str = "center",
                            is_source: bool = True) -> View:
    if not isinstance(namespace, Namespace):
        raise TypeError("matched_geometry_effect expects a Namespace")
    return _apply(view, MatchedGeometryEffectModifier(
        matched_id, namespace, properties, anchor, is_source
    ))


def accessibility_reduce_motion(view: View, enabled: bool = True) -> View:
    from .environment import environment
    return environment(view, REDUCE_MOTION_KEY, bool(enabled))


def resolve_transaction_tree(root: View, base: Transaction | None = None) -> View:
    """Resolve transaction policy, including the reduce-motion environment."""
    initial = base or Transaction()

    def visit(node: View, current: Transaction) -> None:
        value = Transaction(current.animation, current.disables_animations, current.is_continuous)
        environment = getattr(node, "_environment", None)
        if environment is not None and environment.get(REDUCE_MOTION_KEY, False):
            value.disables_animations = True
            value.animation = None
        if hasattr(node, "_modifier") and isinstance(node._modifier, TransactionModifier):
            value = node._modifier.resolve(value)
            if value.disables_animations:
                value.animation = None
        node._resolved_transaction = value
        for child in node.children():
            visit(child, value)

    visit(root, initial)
    return root


def resolved_animation(view: View, proposed: Animation | None = None) -> Animation | None:
    """Resolve a view's transaction animation against a backend animation scope."""
    transaction = getattr(view, "_resolved_transaction", None)
    if transaction is None:
        return proposed
    if transaction.disables_animations:
        return None
    return transaction.animation if transaction.animation is not None else proposed


def animations_disabled(view: View) -> bool:
    transaction = getattr(view, "_resolved_transaction", None)
    return bool(transaction is not None and transaction.disables_animations)
