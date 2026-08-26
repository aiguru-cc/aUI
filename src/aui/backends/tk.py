"""Tkinter backend for aUI.

Renders the declarative aUI view tree onto native Tk widgets. Tkinter ships
with CPython on macOS/Windows/Linux, so this keeps aUI dependency-free while
still providing a real, interactive GUI backend.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

from ..core.components import (
    Button,
    Divider,
    Form,
    Image,
    List,
    NavigationStack,
    Picker,
    ProgressView,
    Slider,
    Stepper,
    Text,
    TextField,
    Toggle,
)
from ..core.geometry import Color, Font, Point, Size
from ..core.layout import HStack, Spacer, VStack, ZStack
from ..core.view import View, _Frame, _ModifiedContent


class TkBackend:
    """Renders aUI views into a Tk window. Not thread-safe; run on main thread."""

    def __init__(self, root: Optional[tk.Tk] = None):
        self.root = root or tk.Tk()
        self.root.title("aUI")
        self._widgets: Dict[int, tk.Widget] = {}
        self._next_id = 0

    # -- Public API ---------------------------------------------------------
    def render(self, view: View) -> None:
        """(Re)render a view tree into the root window."""
        for widget in self.root.winfo_children():
            widget.destroy()
        self._widgets.clear()
        self._draw(view, self.root, 0, 0)

    def mainloop(self) -> None:
        self.root.mainloop()

    # -- Drawing ------------------------------------------------------------
    def _draw(self, view: View, parent: tk.Widget, x: int, y: int) -> None:
        if isinstance(view, _ModifiedContent):
            self._draw(view.body(), parent, x, y)
            return
        if isinstance(view, _Frame):
            self._draw(view._content, parent, x, y)
            return

        if isinstance(view, VStack):
            self._draw_stack(view, parent, vertical=True)
        elif isinstance(view, HStack):
            self._draw_stack(view, parent, vertical=False)
        elif isinstance(view, ZStack):
            for child in view.children():
                self._draw(child, parent, x, y)
        elif isinstance(view, Text):
            self._make_text(view, parent)
        elif isinstance(view, Button):
            self._make_button(view, parent)
        elif isinstance(view, TextField):
            self._make_textfield(view, parent)
        elif isinstance(view, Toggle):
            self._make_toggle(view, parent)
        elif isinstance(view, Slider):
            self._make_slider(view, parent)
        elif isinstance(view, Picker):
            self._make_picker(view, parent)
        elif isinstance(view, Divider):
            ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=4)
        elif isinstance(view, Image):
            tk.Label(parent, text="\u25a0", fg=view._color.to_tk() if view._color else "gray").pack()
        elif isinstance(view, Stepper):
            self._make_stepper(view, parent)
        elif isinstance(view, ProgressView):
            self._make_progress(view, parent)
        elif isinstance(view, NavigationStack):
            self._make_navigation(view, parent)
        elif isinstance(view, Form):
            frame = ttk.LabelFrame(parent, text="Form")
            frame.pack(fill="both", expand=True, padx=4, pady=4)
            for child in view.children():
                self._draw(child, frame, 0, 0)
        elif isinstance(view, Spacer):
            tk.Frame(parent, height=1).pack(expand=True, fill="both")
        elif isinstance(view, List):
            for row in view.rows:
                self._draw(row, parent, 0, 0)
        else:
            for child in view.children():
                self._draw(child, parent, x, y)

    def _draw_stack(self, stack, parent: tk.Widget, vertical: bool) -> None:
        frame = ttk.Frame(parent)
        frame.pack(
            side="top" if vertical else "left",
            fill="both",
            expand=True,
            padx=4,
            pady=4,
        )
        for child in stack.children():
            if isinstance(child, Spacer):
                tk.Frame(frame, height=1).pack(expand=True, fill="both")
                continue
            self._draw(child, frame, 0, 0)

    # -- Widget factories ---------------------------------------------------
    def _make_text(self, view: Text, parent: tk.Widget) -> None:
        color = view._color.to_tk() if view._color else "black"
        tk.Label(
            parent,
            text=view.content,
            fg=color,
            font=(view._font.family, int(view._font.size)),
        ).pack(anchor="w")

    def _make_button(self, view: Button, parent: tk.Widget) -> None:
        btn = ttk.Button(parent, text=view.title, command=view.action)
        btn.pack(anchor="w", pady=2)

    def _make_textfield(self, view: TextField, parent: tk.Widget) -> None:
        var = tk.StringVar(value=view.text.wrapped_value)
        entry = ttk.Entry(parent, textvariable=var)
        entry.pack(fill="x", pady=2)

        def on_change(*_args):
            view.text.wrapped_value = var.get()

        var.trace_add("write", on_change)

    def _make_toggle(self, view: Toggle, parent: tk.Widget) -> None:
        var = tk.BooleanVar(value=view.is_on.wrapped_value if view.is_on else False)
        cb = ttk.Checkbutton(parent, text=view.title, variable=var)
        cb.pack(anchor="w", pady=2)

        def on_change():
            if view.is_on is not None:
                view.is_on.wrapped_value = var.get()

        cb.config(command=on_change)

    def _make_slider(self, view: Slider, parent: tk.Widget) -> None:
        lo, hi = view.range
        var = tk.DoubleVar(value=view.value.wrapped_value if view.value else lo)
        slider = ttk.Scale(parent, from_=lo, to=hi, variable=var, command=lambda _v: None)
        slider.pack(fill="x", pady=2)

        def on_change(*_args):
            if view.value is not None:
                view.value.wrapped_value = var.get()

        var.trace_add("write", on_change)

    def _make_picker(self, view: Picker, parent: tk.Widget) -> None:
        var = tk.StringVar(value=str(view.selection.wrapped_value) if view.selection else "")
        combo = ttk.Combobox(parent, textvariable=var, values=[str(o) for o in view.options], state="readonly")
        combo.pack(fill="x", pady=2)

        def on_change(event=None):
            if view.selection is not None:
                view.selection.wrapped_value = var.get()

        combo.bind("<<ComboboxSelected>>", on_change)

    def _make_stepper(self, view: Stepper, parent: tk.Widget) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=view.title).pack(side="left")
        ttk.Button(row, text="-", width=2, command=view.decrement).pack(side="right")
        ttk.Button(row, text="+", width=2, command=view.increment).pack(side="right")
        if view.value is not None:
            ttk.Label(row, text=str(view.value.wrapped_value)).pack(side="right", padx=4)

    def _make_progress(self, view: ProgressView, parent: tk.Widget) -> None:
        if view.label:
            ttk.Label(parent, text=view.label).pack(anchor="w")
        if view.value is None:
            pb = ttk.Progressbar(parent, mode="indeterminate")
            pb.pack(fill="x", pady=2)
            pb.start(20)
        else:
            pb = ttk.Progressbar(parent, mode="determinate", maximum=1.0, value=view.value)
            pb.pack(fill="x", pady=2)

    def _make_navigation(self, view: NavigationStack, parent: tk.Widget) -> None:
        header = tk.Label(parent, text=view.title, font=("TkDefaultFont", 14, "bold"))
        header.pack(fill="x", pady=4)
        self._draw(view.content, parent, 0, 0)
