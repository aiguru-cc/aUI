"""Tkinter backend for aUI with incremental (diff) rendering.

Renders the declarative aUI view tree onto native Tk widgets. Tkinter ships
with CPython on macOS/Windows/Linux, so this keeps aUI dependency-free while
still providing a real, interactive GUI backend.

Rendering strategy (see ADR-0004): each view-tree node gets a structural
identity (a path like ``root/0/1``). On re-render, widgets whose path already
exists and whose *view type* is compatible are **reused** and only their
properties are updated; incompatible or removed paths are rebuilt/destroyed.
This avoids flicker and keeps focus/scroll position across state changes.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional, Set, Tuple, Type

from ..core.animation import Animation, current_animation
from ..core.components import (
    Button,
    DatePicker,
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
from ..core.modifiers import AnimationModifier
from ..core.view import View, _Frame, _ModifiedContent


def _parse_tk_color(value: str):
    """Parse a '#rrggbb' (or named) Tk color into an (r, g, b) tuple in [0,1]."""
    if not value:
        return None
    value = value.strip()
    if value.startswith("#") and len(value) == 7:
        try:
            return (
                int(value[1:3], 16) / 255.0,
                int(value[3:5], 16) / 255.0,
                int(value[5:7], 16) / 255.0,
            )
        except ValueError:
            return None
    # Named colors: fall back to a small mapping, else None.
    named = {
        "black": (0.0, 0.0, 0.0),
        "white": (1.0, 1.0, 1.0),
        "red": (1.0, 0.0, 0.0),
        "green": (0.0, 1.0, 0.0),
        "blue": (0.0, 0.0, 1.0),
        "gray": (0.5, 0.5, 0.5),
        "grey": (0.5, 0.5, 0.5),
    }
    return named.get(value.lower())


def _rgb_to_tk(r: float, g: float, b: float) -> str:
    """Convert (r, g, b) in [0,1] to a '#rrggbb' string."""
    def channel(v: float) -> int:
        return max(0, min(255, int(round(v * 255))))
    return "#%02x%02x%02x" % (channel(r), channel(g), channel(b))


class TkBackend:
    """Renders aUI views into a Tk window with incremental updates.

    Not thread-safe; run on main thread. ``render`` may be called repeatedly
    (e.g. from a state-change callback) and will diff against the previous tree.
    """

    def __init__(self, root: Optional[tk.Tk] = None):
        self.root = root or tk.Tk()
        self.root.title("aUI")
        #: path -> (view type, widget) for the current rendered tree
        self._widgets: Dict[str, Tuple[type, object]] = {}
        self._paths: Set[str] = set()
        #: path -> Animation, set while drawing when a view carries .animation()
        self._animations: Dict[str, Animation] = {}
        #: path -> active frame animation job (after id), for cancellation
        self._animation_jobs: Dict[str, str] = {}

    # -- Public API ---------------------------------------------------------
    def render(self, view: View) -> None:
        """(Re)render a view tree into the root window, diffing against the
        previously rendered tree (see ADR-0004)."""
        new_paths: Set[str] = set()
        self._animations = {}
        self._draw(view, self.root, "root", new_paths)

        # Destroy widgets whose path disappeared from the new tree.
        for path in list(self._paths - new_paths):
            entry = self._widgets.pop(path, None)
            if entry is not None:
                entry[1].destroy()
        self._paths = new_paths

    def mainloop(self) -> None:
        self.root.mainloop()

    # -- Drawing ------------------------------------------------------------
    def _draw(
        self,
        view: View,
        parent: tk.Widget,
        path: str,
        new_paths: Set[str],
    ) -> None:
        if isinstance(view, _ModifiedContent):
            if isinstance(view._modifier, AnimationModifier):
                self._animations[path] = view._modifier.animation
            self._draw(view.body(), parent, path, new_paths)
            return
        if isinstance(view, _Frame):
            self._draw(view._content, parent, path, new_paths)
            return

        new_paths.add(path)

        if isinstance(view, VStack):
            self._draw_stack(view, parent, path, new_paths, vertical=True)
        elif isinstance(view, HStack):
            self._draw_stack(view, parent, path, new_paths, vertical=False)
        elif isinstance(view, ZStack):
            for i, child in enumerate(view.children()):
                self._draw(child, parent, f"{path}/{i}", new_paths)
        elif isinstance(view, Text):
            self._make_text(view, parent, path)
        elif isinstance(view, Button):
            self._make_button(view, parent, path)
        elif isinstance(view, TextField):
            self._make_textfield(view, parent, path)
        elif isinstance(view, Toggle):
            self._make_toggle(view, parent, path)
        elif isinstance(view, Slider):
            self._make_slider(view, parent, path)
        elif isinstance(view, Picker):
            self._make_picker(view, parent, path)
        elif isinstance(view, Divider):
            self._make_divider(view, parent, path)
        elif isinstance(view, Image):
            self._make_image(view, parent, path)
        elif isinstance(view, DatePicker):
            self._make_datepicker(view, parent, path)
        elif isinstance(view, Stepper):
            self._make_stepper(view, parent, path)
        elif isinstance(view, ProgressView):
            self._make_progress(view, parent, path)
        elif isinstance(view, NavigationStack):
            self._make_navigation(view, parent, path, new_paths)
        elif isinstance(view, Form):
            self._make_form(view, parent, path, new_paths)
        elif isinstance(view, Spacer):
            self._make_spacer(view, parent, path)
        elif isinstance(view, List):
            self._make_list(view, parent, path, new_paths)
        else:
            for i, child in enumerate(view.children()):
                self._draw(child, parent, f"{path}/{i}", new_paths)

    def _draw_stack(
        self,
        stack,
        parent: tk.Widget,
        path: str,
        new_paths: Set[str],
        vertical: bool,
    ) -> None:
        frame = self._reuse_or_create(path, ttk.Frame, lambda: ttk.Frame(parent))
        frame.pack(
            side="top" if vertical else "left",
            fill="both",
            expand=True,
            padx=4,
            pady=4,
        )
        for i, child in enumerate(stack.children()):
            if isinstance(child, Spacer):
                self._make_spacer(child, frame, f"{path}/{i}")
                continue
            self._draw(child, frame, f"{path}/{i}", new_paths)

    # -- Widget factories (with diff reuse) ---------------------------------
    def _reuse_or_create(self, path: str, widget_type: type, factory: Callable[[], object]) -> object:
        """Return a widget for ``path``, reusing it if the type is compatible.

        If an existing widget has an incompatible type, destroy it and create a
        fresh one (the subtree changed shape).
        """
        entry = self._widgets.get(path)
        if entry is not None:
            existing_type, existing = entry
            if existing_type is widget_type:
                return existing
            existing.destroy()
        widget = factory()
        self._widgets[path] = (widget_type, widget)
        return widget

    def _make_text(self, view: Text, parent: tk.Widget, path: str) -> None:
        color = view._color.to_tk() if view._color else "black"
        font = (view._font.family, int(view._font.size))
        label = self._reuse_or_create(path, tk.Label, lambda: tk.Label(parent))
        label.pack(anchor="w")

        anim = self._animations.get(path)
        entry = self._widgets.get(path)
        was_new = entry is None or entry[1] is not label
        if not was_new and anim is not None and current_animation() is not None:
            # Animate color transition if the color changed.
            old_color = label.cget("fg")
            if old_color != color and view._color is not None:
                start = _parse_tk_color(old_color) or (0.0, 0.0, 0.0)
                end = (view._color.red, view._color.green, view._color.blue)
                self._animate_color(label, start, end, anim)
        else:
            label.config(fg=color)
        label.config(text=view.content, font=font)

    # -- Animation frame drivers (ADR-0006) --------------------------------
    def _animate_color(self, widget, start, end, anim: Animation) -> None:
        """Interpolate a widget's foreground color over the animation duration."""
        self._cancel_animation(id(widget))
        steps = max(2, int(anim.duration * 60))
        start_t = self.root.tk.call("after", "info")  # monotonic-ish tick
        # Use a simple elapsed-time frame loop.
        import time as _time

        begin = _time.monotonic()

        def frame():
            elapsed = _time.monotonic() - begin
            t = min(1.0, elapsed / anim.duration) if anim.duration > 0 else 1.0
            eased = anim.ease(t)
            r = start[0] + (end[0] - start[0]) * eased
            g = start[1] + (end[1] - start[1]) * eased
            b = start[2] + (end[2] - start[2]) * eased
            try:
                widget.config(fg=_rgb_to_tk(r, g, b))
            except Exception:
                return
            if t < 1.0:
                self._animation_jobs[id(widget)] = self.root.after(16, frame)
            else:
                self._animation_jobs.pop(id(widget), None)

        self._animation_jobs[id(widget)] = self.root.after(0, frame)

    def _cancel_animation(self, key) -> None:
        job = self._animation_jobs.pop(key, None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass

    def _make_button(self, view: Button, parent: tk.Widget, path: str) -> None:
        btn = self._reuse_or_create(path, ttk.Button, lambda: ttk.Button(parent))
        btn.config(text=view.title, command=view.action)
        btn.pack(anchor="w", pady=2)

    def _make_textfield(self, view: TextField, parent: tk.Widget, path: str) -> None:
        entry = self._reuse_or_create(path, ttk.Entry, lambda: ttk.Entry(parent))
        entry.pack(fill="x", pady=2)
        current = entry.get()
        new_value = view.text.wrapped_value
        if current != new_value:
            entry.delete(0, "end")
            entry.insert(0, new_value)

        def on_change(*_args):
            view.text.wrapped_value = entry.get()

        entry._aui_trace = getattr(entry, "_aui_trace", None)
        if entry._aui_trace is not None:
            try:
                entry.trace_remove("write", entry._aui_trace)
            except Exception:
                pass
        entry._aui_trace = entry.trace_add("write", on_change)

    def _make_toggle(self, view: Toggle, parent: tk.Widget, path: str) -> None:
        cb = self._reuse_or_create(path, ttk.Checkbutton, lambda: ttk.Checkbutton(parent))
        cb.config(text=view.title)
        cb.pack(anchor="w", pady=2)
        new_val = bool(view.is_on.wrapped_value) if view.is_on else False
        if cb.instate(["selected"]) != new_val:
            if new_val:
                cb.state(["selected"])
            else:
                cb.state(["!selected"])

        def on_change():
            if view.is_on is not None:
                view.is_on.wrapped_value = bool(cb.instate(["selected"]))

        cb.configure(command=on_change)

    def _make_slider(self, view: Slider, parent: tk.Widget, path: str) -> None:
        lo, hi = view.range
        slider = self._reuse_or_create(path, ttk.Scale, lambda: ttk.Scale(parent))
        slider.configure(from_=lo, to=hi)
        slider.pack(fill="x", pady=2)
        if view.value is not None:
            current = slider.get()
            new_val = view.value.wrapped_value
            if abs(current - new_val) > 1e-9:
                slider.set(new_val)

        def on_change(*_args):
            if view.value is not None:
                view.value.wrapped_value = slider.get()

        slider.configure(command=on_change)

    def _make_picker(self, view: Picker, parent: tk.Widget, path: str) -> None:
        combo = self._reuse_or_create(path, ttk.Combobox, lambda: ttk.Combobox(parent))
        combo.configure(values=[str(o) for o in view.options])
        combo.pack(fill="x", pady=2)
        if view.selection is not None:
            new_val = str(view.selection.wrapped_value)
            if combo.get() != new_val:
                combo.set(new_val)

        def on_change(event=None):
            if view.selection is not None:
                view.selection.wrapped_value = combo.get()

        combo.bind("<<ComboboxSelected>>", on_change)

    def _make_divider(self, view: Divider, parent: tk.Widget, path: str) -> None:
        sep = self._reuse_or_create(path, ttk.Separator, lambda: ttk.Separator(parent))
        sep.pack(fill="x", pady=4)

    def _make_image(self, view: Image, parent: tk.Widget, path: str) -> None:
        color = view._color.to_tk() if view._color else "gray"
        label = self._reuse_or_create(path, tk.Label, lambda: tk.Label(parent))
        label.config(text="\u25a0", fg=color)
        label.pack()

    def _make_datepicker(self, view: DatePicker, parent: tk.Widget, path: str) -> None:
        row = self._reuse_or_create(path, ttk.Frame, lambda: ttk.Frame(parent))
        row.pack(fill="x", pady=2)
        # Rebuild the fixed set of children for the date row.
        for w in row.winfo_children():
            w.destroy()
        if view.title:
            ttk.Label(row, text=view.title).pack(side="left", padx=(0, 4))
        current = view._current()
        ttk.Label(row, text=current or "(select date)").pack(side="left", padx=4)
        if view.selection is not None:
            ttk.Button(
                row,
                text="...",
                width=3,
                command=lambda v=view: self._pick_date(v),
            ).pack(side="right")

    def _pick_date(self, view: DatePicker) -> None:
        """Open a native Tk calendar dialog and write the choice to the binding."""
        import tkinter as tk
        from tkinter import simpledialog

        if view.selection is None:
            return
        current = view.selection.wrapped_value
        if current is None:
            current = datetime.now()
        if view.displayed_components == "hourAndMinute":
            text = simpledialog.askstring(
                "aUI DatePicker",
                "Enter time (HH:MM):",
                initialvalue=current.strftime("%H:%M"),
                parent=self.root,
            )
            if text:
                try:
                    hh, mm = text.split(":")
                    view.selection.wrapped_value = current.replace(
                        hour=int(hh), minute=int(mm)
                    )
                except (ValueError, TypeError):
                    pass
            return
        text = simpledialog.askstring(
            "aUI DatePicker",
            "Enter date (YYYY-MM-DD):",
            initialvalue=current.strftime("%Y-%m-%d"),
            parent=self.root,
        )
        if text:
            try:
                from datetime import datetime as _dt

                view.selection.wrapped_value = _dt.strptime(text, "%Y-%m-%d")
            except ValueError:
                pass

    def _make_stepper(self, view: Stepper, parent: tk.Widget, path: str) -> None:
        row = self._reuse_or_create(path, ttk.Frame, lambda: ttk.Frame(parent))
        row.pack(fill="x", pady=2)
        # Rebuild children of the stepper row (small fixed set).
        for w in row.winfo_children():
            w.destroy()
        ttk.Label(row, text=view.title).pack(side="left")
        ttk.Button(row, text="-", width=2, command=view.decrement).pack(side="right")
        ttk.Button(row, text="+", width=2, command=view.increment).pack(side="right")
        if view.value is not None:
            ttk.Label(row, text=str(view.value.wrapped_value)).pack(side="right", padx=4)

    def _make_progress(self, view: ProgressView, parent: tk.Widget, path: str) -> None:
        if view.label:
            lbl = self._reuse_or_create(
                f"{path}/label",
                ttk.Label,
                lambda: ttk.Label(parent),
            )
            lbl.config(text=view.label)
            lbl.pack(anchor="w")
        if view.value is None:
            pb = self._reuse_or_create(
                path,
                ttk.Progressbar,
                lambda: ttk.Progressbar(parent, mode="indeterminate"),
            )
            pb.pack(fill="x", pady=2)
            pb.start(20)
        else:
            pb = self._reuse_or_create(
                path,
                ttk.Progressbar,
                lambda: ttk.Progressbar(parent, mode="determinate", maximum=1.0),
            )
            pb.configure(value=view.value)
            pb.pack(fill="x", pady=2)

    def _make_navigation(self, view: NavigationStack, parent: tk.Widget, path: str, new_paths: Set[str]) -> None:
        header = self._reuse_or_create(
            f"{path}/header",
            tk.Label,
            lambda: tk.Label(parent),
        )
        header.config(text=view.title, font=("TkDefaultFont", 14, "bold"))
        header.pack(fill="x", pady=4)
        self._draw(view.content, parent, f"{path}/content", new_paths)

    def _make_form(self, view: Form, parent: tk.Widget, path: str, new_paths: Set[str]) -> None:
        frame = self._reuse_or_create(path, ttk.LabelFrame, lambda: ttk.LabelFrame(parent))
        frame.config(text="Form")
        frame.pack(fill="both", expand=True, padx=4, pady=4)
        for i, child in enumerate(view.children()):
            self._draw(child, frame, f"{path}/{i}", new_paths)

    def _make_spacer(self, view: Spacer, parent: tk.Widget, path: str) -> None:
        frame = self._reuse_or_create(path, tk.Frame, lambda: tk.Frame(parent))
        frame.pack(expand=True, fill="both")

    def _make_list(self, view: List, parent: tk.Widget, path: str, new_paths: Set[str]) -> None:
        for i, row in enumerate(view.rows):
            self._draw(row, parent, f"{path}/{i}", new_paths)
