"""Consistent standard-library desktop backend for macOS, Linux and Windows."""
from __future__ import annotations

import sys
import inspect
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

try:
    import tkinter as tk
    from tkinter import ttk
    _TK_AVAILABLE = True
    _TK_IMPORT_ERROR = ""
except ImportError as exc:  # pragma: no cover - depends on Python distribution
    tk = ttk = None
    _TK_AVAILABLE = False
    _TK_IMPORT_ERROR = str(exc)

from ..core.components import (
    AppBar, Button, ColorPicker, DatePicker, DisclosureGroup, Divider, Form, Gauge,
    Group, IconButton, Image, Label, LabeledContent, List, NavigationRail, NavigationStack, Picker, ProgressView, ScrollView,
    Section, SecureField, Slider, Stepper, TabView, Text, TextEditor, TextField,
    Toggle,
)
from ..core.capabilities import Capability
from ..core.dispatcher import UIDispatcher
from ..core.animation import Animation, current_animation, interpolate
from ..core.animation_runtime import AnimationDriver, sample_symbol_effect
from ..core.async_actions import cancel_tasks, start_tasks
from ..core.animation_modifiers import (
    MatchedGeometryEffectModifier, TransactionModifier, animations_disabled,
    resolve_transaction_tree, resolved_animation,
)
from ..core.commands import (
    CommandMenu, Commands, KeyboardShortcut, Menu, MenuDivider, ToolbarModifier,
)
from ..core.environment import EnvironmentModifier, EnvironmentReader, resolve_environment_tree
from ..core.events import (
    OnAppearModifier, OnDisappearModifier, OnSubmitModifier,
    SubmitLabelModifier, run_on_change,
)
from ..core.file_dialogs import FileDialogResult, FileExporterModifier, FileImporterModifier
from ..core.focus import FocusedModifier
from ..core.geometry import Color, Point, Size
from ..core.layout import HStack, NavigationSplitView, ResponsiveItem, ResponsiveRow, Spacer, VStack, ZStack
from ..core.keyboard import DefaultFocusModifier, KeyboardShortcutModifier, OnKeyPressModifier
from ..core.lazy import LazyHGrid, LazyHStack, LazyVGrid, LazyVStack
from ..core.async_image import AsyncImage, AsyncImagePhase
from ..core.canvas import Canvas, TimelineView
from ..core.inspector import InspectorView
from ..core.table import Table
from ..core.state import observation_tracking
from ..core.presentation import (
    AlertModifier, ConfirmationDialogModifier, FullScreenCoverModifier,
    PopoverModifier, SheetModifier, SnackBarModifier, collect_presentation_configurations,
)
from ..core.reconciliation import snapshot
from ..core.state_persistence import restore_local_state
from ..core.scrolling import IDModifier
from ..core.scenes import (
    DismissWindowAction, DismissWindowLink, MenuBarExtra, Settings, SettingsLink,
    Window, WindowGroup, WindowLevel, WindowLink, WindowResizability, WindowStyle,
)
from ..core.structural import AnyView, EmptyView, GroupBox, OutlineGroup, ViewThatFits
from ..core.transitions import (
    ContentTransition, ContentTransitionModifier, SymbolEffectModifier,
)
from ..core.modifiers import BackgroundModifier, BorderModifier, resolve_visual_style_tree
from ..core.preferences import collect_preferences
from ..core.localization import resolve_semantic_tree
from ..core.styles import is_enabled, resolve_style_tree
from ..core.system_environment import ScenePhase, system_environment
from ..core.text import resolve_text_style_tree
from ..core.view import View, _Frame, _ModifiedContent
from ..core.visual_effects import Gradient
from .standard_theme import DEFAULT_STANDARD_THEME, StandardTheme, color_hex


def platform_family(value: Optional[str] = None) -> str:
    platform = value or sys.platform
    if platform == "darwin":
        return "macos"
    if platform.startswith("win"):
        return "windows"
    return "linux"


class StandardBackend:
    """A ttk desktop renderer with one API and metric set on all platforms."""

    CAPABILITIES = frozenset({
        Capability.TOOLBAR, Capability.SNACK_BAR, Capability.SNACK_BAR_ACTION,
        Capability.WINDOW_EVENTS, Capability.RESPONSIVE_ROW, Capability.NAVIGATION_RAIL,
        Capability.APP_BAR, Capability.FILE_DIALOGS, Capability.SPLIT_DIVIDER_DRAG,
    })

    @classmethod
    def supports(cls, capability: str) -> bool:
        return capability in cls.CAPABILITIES

    def __init__(self, view_factory: Callable[[], View],
                 theme: Optional[StandardTheme] = None,
                 on_resize: Optional[Callable[[Size], None]] = None,
                 on_focus_changed: Optional[Callable[[bool], None]] = None,
                 on_close: Optional[Callable[[], None]] = None):
        if not callable(view_factory):
            raise TypeError("view_factory must be callable")
        self._view_factory = view_factory
        self.theme = theme or DEFAULT_STANDARD_THEME
        self._on_resize = on_resize
        self._on_focus_changed = on_focus_changed
        self._on_close = on_close
        self._root = None
        self._host = None
        self._view: Optional[View] = None
        self._observation_cancels: list[Callable[[], None]] = []
        self._tasks = {}
        self._dispatcher = UIDispatcher()
        self._window_width = 720
        self._window_height = 520
        self._images: list[object] = []
        self._async_image_cancels: list[Callable[[], None]] = []
        self._outline_interaction_cancels: list[Callable[[], None]] = []
        self._pending_presentations: list[object] = []
        self._active_presentations: set[tuple[type, int]] = set()
        self._scene_phase = ScenePhase.ACTIVE
        self._pending_toolbar: Optional[ToolbarModifier] = None
        self._focus_modifier: Optional[FocusedModifier] = None
        self._bound_sequences: set[str] = set()
        self._widgets: dict[int, tuple[object, object]] = {}
        self._lazy_offsets: dict[tuple[type, int], float] = {}
        self._lazy_index = 0
        self._pending_animation = None
        self._animation_driver: Optional[AnimationDriver] = None
        self._animation_handles: dict[int, object] = {}
        self._split_width_overrides: dict[int, dict[int, float]] = {}
        self._split_build_index = 0
        self._timeline_timer = None
        self._appear_actions: list[Callable[[], None]] = []
        self._disappear_actions: list[Callable[[], None]] = []
        self._change_values: dict = {}
        self._submit_modifier: Optional[OnSubmitModifier] = None
        # Renderer-local context used to give NavigationSplitView sidebars
        # list-row styling without changing ordinary Button semantics.
        self._split_column_context: Optional[int] = None

    @staticmethod
    def available() -> bool:
        return _TK_AVAILABLE

    @staticmethod
    def availability_reason() -> str:
        """Explain why the standard desktop renderer cannot start, if any."""
        if _TK_AVAILABLE:
            return ""
        detail = f" ({_TK_IMPORT_ERROR})" if _TK_IMPORT_ERROR else ""
        return "Python was built without tkinter/_tkinter" + detail

    @property
    def platform(self) -> str:
        return platform_family()

    def run(self, width: int = 720, height: int = 520, title: str = "aUI") -> None:
        if not _TK_AVAILABLE:
            raise RuntimeError(
                "Standard backend requires Python's tkinter module: "
                + self.availability_reason()
            )
        try:
            root = tk.Tk()
        except Exception as exc:
            raise RuntimeError("Standard backend could not connect to a desktop display") from exc
        self._start_window(root, width, height, title)
        root.mainloop()

    def _start_window(self, root, width: int, height: int, title: str) -> None:
        self._root = root
        self._dispatcher.adopt_current_thread()
        self._animation_driver = AnimationDriver(
            lambda delay, callback: root.after(max(0, round(delay * 1000)), callback)
        )
        self._window_width, self._window_height = int(width), int(height)
        root.title(title)
        root.geometry(f"{int(width)}x{int(height)}")
        root.minsize(320, 240)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.configure(background=color_hex(self.theme.background))
        self._configure_styles()
        self._host = ttk.Frame(root, style="AUI.Surface.TFrame", padding=self.theme.content_padding)
        self._host.pack(fill="both", expand=True)
        root.bind("<Configure>", self._window_resized, add=True)
        root.bind("<FocusIn>", lambda _event: self._set_scene_phase(ScenePhase.ACTIVE), add=True)
        root.bind("<FocusOut>", lambda _event: self._set_scene_phase(ScenePhase.INACTIVE), add=True)
        root.bind("<Unmap>", lambda _event: self._set_scene_phase(ScenePhase.BACKGROUND), add=True)
        root.bind("<Map>", lambda _event: self._set_scene_phase(ScenePhase.ACTIVE), add=True)
        self._refresh()
        root.after(16, self._poll_dispatcher)

    def close(self) -> None:
        self._scene_phase = ScenePhase.BACKGROUND
        for handle in self._animation_handles.values():
            handle.cancel()
        self._animation_handles.clear()
        if self._timeline_timer is not None and self._root is not None:
            try:
                self._root.after_cancel(self._timeline_timer)
            except Exception:
                pass
            self._timeline_timer = None
        self._dispatcher.close()
        cancel_tasks(self._tasks)
        self._tasks.clear()
        for cancel in self._async_image_cancels:
            cancel()
        self._async_image_cancels = []
        for cancel in self._outline_interaction_cancels:
            cancel()
        self._outline_interaction_cancels = []
        for cancel in self._observation_cancels:
            cancel()
        self._observation_cancels = []
        self._run_disappear_actions()
        if self._on_close is not None:
            callback, self._on_close = self._on_close, None
            callback()
        # PhotoImage owns a Tcl-side object.  Drop Python references while
        # its originating Tk interpreter is still alive; otherwise a later
        # destructor (possibly after another window starts) can attempt Tcl
        # cleanup from the wrong thread.
        self._images = []
        if self._root is not None:
            self._root.destroy()
            self._root = None

    def _configure_styles(self) -> None:
        style = ttk.Style(self._root)
        theme = self.theme
        # The host's default ttk theme varies substantially across macOS,
        # Linux and Windows.  Clam gives us a stable baseline before applying
        # the semantic SwiftUI-like colours below.
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except Exception:
            pass
        background, surface = color_hex(theme.background), color_hex(theme.surface)
        primary, accent = color_hex(theme.primary), color_hex(theme.accent)
        style.configure("AUI.Surface.TFrame", background=surface)
        style.configure("AUI.Selected.TFrame", background=accent)
        style.configure("AUI.TFrame", background=background)
        style.configure("AUI.TLabel", background=surface, foreground=primary,
                        font=(theme.font_family, theme.scaled_font_size()))
        style.configure("AUI.TButton", padding=(12, 6), font=(theme.font_family, theme.scaled_font_size()),
                        background=surface, foreground=primary, borderwidth=1,
                        relief="solid", focusthickness=1, focuscolor=accent)
        style.map("AUI.TButton", background=[("pressed", accent), ("active", "#eef5ff"), ("disabled", background)],
                  foreground=[("pressed", "white"), ("disabled", color_hex(theme.secondary))])
        style.configure("AUI.TCheckbutton", background=surface, foreground=primary,
                        font=(theme.font_family, theme.scaled_font_size()))
        style.configure("AUI.Horizontal.TProgressbar", background=accent, troughcolor=background)
        style.configure("AUI.Section.TLabelframe", background=surface, foreground=primary)
        style.configure("AUI.Section.TLabelframe.Label", background=surface, foreground=primary,
                        font=(theme.font_family, theme.scaled_font_size(), "bold"))
        style.configure("AUI.TNotebook", background=background, borderwidth=0,
                        tabmargins=(0, 0, 0, 0))
        style.configure("AUI.TNotebook.Tab", padding=(14, 7),
                        font=(theme.font_family, theme.scaled_font_size()))
        style.configure("AUI.Sidebar.TButton", padding=(10, 7),
                        font=(theme.font_family, theme.scaled_font_size()),
                        background=surface, foreground=primary, borderwidth=0,
                        relief="flat", anchor="w", focusthickness=1, focuscolor=accent)
        style.map("AUI.Sidebar.TButton",
                  background=[("active", "#e8f1ff"), ("pressed", "#dbeaff"),
                              ("disabled", background)],
                  foreground=[("disabled", color_hex(theme.secondary))])

    def _make_view(self) -> View:
        for cancel in self._observation_cancels:
            cancel()
        with observation_tracking(self._request_refresh) as cleanups:
            view = self._view_factory()
            if not isinstance(view, View):
                raise TypeError("view_factory must return a View")
            resolve_environment_tree(view, system_environment(phase=self._scene_phase))
            resolve_transaction_tree(view)
            resolve_style_tree(view)
            resolve_visual_style_tree(view)
            resolve_text_style_tree(view)
            resolve_semantic_tree(view)
            collect_presentation_configurations(view)
            collect_preferences(view)
            start_tasks(view, self._tasks, self._request_refresh)
        self._observation_cancels = cleanups
        return view

    def _request_refresh(self) -> None:
        animation = current_animation()
        if animation is not None:
            self._pending_animation = animation
        self._dispatcher.schedule_once("refresh", self._refresh)

    def _window_resized(self, event) -> None:
        if event.widget is not self._root:
            return
        # Tk emits transient Configure notifications (commonly 1×1 and
        # 200×200) while a new root is being mapped.  They are not usable
        # layout sizes and would make SwiftUI-style geometry/state callbacks
        # observe a fake initial viewport.
        if event.width < 320 or event.height < 240:
            return
        size = (int(event.width), int(event.height))
        if size != (self._window_width, self._window_height):
            self._window_width, self._window_height = size
            if self._on_resize is not None:
                self._on_resize(Size(float(event.width), float(event.height)))
            self._request_refresh()

    def _set_scene_phase(self, phase: str) -> None:
        if phase != self._scene_phase:
            self._scene_phase = phase
            if self._on_focus_changed is not None:
                self._on_focus_changed(phase == ScenePhase.ACTIVE)
            self._request_refresh()

    def _poll_dispatcher(self) -> None:
        """Drain worker invalidations only from Tk's owning UI thread."""
        if self._root is None:
            return
        self._dispatcher.drain()
        if self._root is not None:
            self._root.after(16, self._poll_dispatcher)

    def _refresh(self) -> None:
        if self._host is None:
            return
        for cancel in self._async_image_cancels:
            cancel()
        self._async_image_cancels = []
        for cancel in self._outline_interaction_cancels:
            cancel()
        self._outline_interaction_cancels = []
        old_view, old_widgets = self._view, dict(self._widgets)
        new_view = self._make_view()
        restore_local_state(old_view, new_view)
        animation, self._pending_animation = self._pending_animation, None
        if old_view is not None and self._update_widget_tree(
                old_view, new_view, old_widgets, animation=animation):
            self._view = new_view
            self._install_timeline_timer()
            run_on_change(self._view, self._change_values)
            self._present_pending()
            return
        self._view = new_view
        self._run_disappear_actions()
        for handle in self._animation_handles.values():
            handle.cancel()
        self._animation_handles.clear()
        if self._root is not None:
            for sequence in self._bound_sequences:
                self._root.unbind(sequence)
        self._bound_sequences.clear()
        self._images = []
        self._pending_presentations = []
        self._pending_toolbar = None
        self._appear_actions = []
        self._disappear_actions = []
        self._widgets = {}
        self._lazy_index = 0
        self._split_build_index = 0
        for child in self._host.winfo_children():
            child.destroy()
        self._build(self._view, self._host)
        self._install_toolbar()
        self._install_timeline_timer()
        self._run_appear_actions()
        run_on_change(self._view, self._change_values)
        self._present_pending()

    def _install_timeline_timer(self) -> None:
        """Advance TimelineView at its declared cadence on the Tk UI thread."""
        if self._root is None or self._view is None:
            return
        if self._timeline_timer is not None:
            try:
                self._root.after_cancel(self._timeline_timer)
            except Exception:
                pass
            self._timeline_timer = None
        timelines = [node for node in self._view.flatten() if isinstance(node, TimelineView)]
        if not timelines:
            return
        delays = {"live": 1000 // 30, "seconds": 1000, "minutes": 60_000}
        delay = min(delays[node.cadence] for node in timelines)

        def tick(nodes=timelines):
            self._timeline_timer = None
            if self._root is None:
                return
            for node in nodes:
                node.tick()
            self._request_refresh()

        self._timeline_timer = self._root.after(delay, tick)

    def _run_appear_actions(self) -> None:
        actions, self._appear_actions = self._appear_actions, []
        for action in actions:
            action()

    def _run_disappear_actions(self) -> None:
        actions, self._disappear_actions = self._disappear_actions, []
        for action in actions:
            action()

    def _build(self, view: View, parent) -> None:
        if isinstance(view, EmptyView):
            return
        if isinstance(view, EnvironmentReader):
            self._build(view.content, parent)
            return
        if isinstance(view, AnyView):
            self._build(view.content, parent)
            return
        if isinstance(view, _ModifiedContent):
            modifier = view._modifier
            if isinstance(modifier, (AlertModifier, SheetModifier, PopoverModifier, SnackBarModifier,
                                     FileImporterModifier, FileExporterModifier)):
                self._queue_presentation(modifier)
            if isinstance(modifier, ToolbarModifier):
                self._pending_toolbar = modifier
            if isinstance(modifier, KeyboardShortcutModifier):
                action = self._button_action(view._content)
                if action is not None:
                    self._bind_shortcut(modifier.shortcut, action)
            if isinstance(modifier, OnKeyPressModifier):
                self._bind_key_handler(modifier)
            if isinstance(modifier, OnAppearModifier):
                self._appear_actions.append(modifier.action)
            elif isinstance(modifier, OnDisappearModifier):
                self._disappear_actions.append(modifier.action)
            # ttk styles cannot be created safely for every arbitrary Color.
            # A plain Tk frame gives background and border modifiers the same
            # containment semantics on macOS, Linux and Windows without
            # mutating shared global ttk styles.
            if isinstance(modifier, (BackgroundModifier, BorderModifier)):
                options = {}
                if isinstance(modifier, BackgroundModifier):
                    options["background"] = color_hex(modifier.color)
                else:
                    options.update(
                        background=color_hex(self.theme.surface),
                        highlightbackground=color_hex(modifier.color),
                        highlightthickness=max(1, int(round(modifier.width))),
                    )
                frame = tk.Frame(parent, **options)
                frame.pack(fill="x")
                self._build(view.body(), frame)
                return
            previous_focus = self._focus_modifier
            previous_submit = self._submit_modifier
            if isinstance(modifier, FocusedModifier):
                self._focus_modifier = modifier
            if isinstance(modifier, OnSubmitModifier):
                self._submit_modifier = modifier
            self._build(view.body(), parent)
            self._focus_modifier = previous_focus
            self._submit_modifier = previous_submit
            return
        if isinstance(view, _Frame):
            self._build(view._content, parent)
            return
        if isinstance(view, ViewThatFits):
            self._build(view.selected(Size(float(self._window_width),
                                           float(self._window_height))), parent)
            return
        if isinstance(view, InspectorView):
            self._build_inspector(view, parent)
            return
        if isinstance(view, OutlineGroup):
            # OutlineGroup already exposes a lazily cached, interactive row
            # tree; rendering that tree keeps selection and disclosure state
            # identical to the AppKit fallback implementation.
            view._set_interaction_callback(self._request_refresh)
            self._outline_interaction_cancels.append(
                lambda model=view: model._set_interaction_callback(None)
            )
            self._build(view.content_view(), parent)
            return
        if isinstance(view, TimelineView):
            self._build(view.content, parent)
            return
        if isinstance(view, AsyncImage):
            self._build_async_image(view, parent)
            return
        if isinstance(view, Canvas):
            self._build_canvas(view, parent)
            return
        if isinstance(view, Gradient):
            self._build_gradient(view, parent)
            return
        if isinstance(view, Table):
            self._build_table(view, parent)
            return
        if isinstance(view, NavigationSplitView):
            self._build_split_view(view, parent)
            return
        if isinstance(view, NavigationRail):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame", width=184 if view.extended else 72)
            frame.pack(side="left", fill="y")
            for index, destination in enumerate(view.destinations):
                active = index == view.active_index
                icon = destination.selected_system_name if active and destination.selected_system_name else destination.system_name
                title = self._symbol_text(icon) if icon else ""
                if view.extended or not title:
                    title = f"{title}  {destination.label}".strip()
                ttk.Button(
                    frame, text=title, style="AUI.TButton",
                    command=lambda value=index, model=view: (model.select(value), self._request_refresh()),
                ).pack(fill="x", padx=4, pady=2)
            return
        if isinstance(view, AppBar):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="x")
            if view.leading is not None:
                holder = ttk.Frame(frame, style="AUI.Surface.TFrame")
                holder.pack(side="left", padx=(4, 8))
                self._build(view.leading, holder)
            title = ttk.Frame(frame, style="AUI.Surface.TFrame")
            title.pack(side="left", fill="x", expand=True)
            self._build(view.title, title)
            for action in view.actions:
                holder = ttk.Frame(frame, style="AUI.Surface.TFrame")
                holder.pack(side="right", padx=3)
                self._build(action, holder)
            return
        if isinstance(view, NavigationStack):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="both", expand=True)
            if view.header_visible:
                header = ttk.Frame(frame, style="AUI.Surface.TFrame")
                header.pack(fill="x", pady=(0, self.theme.spacing))
                if len(view.path):
                    ttk.Button(header, text="‹", command=lambda model=view: (
                        model.go_back(), self._request_refresh()),
                               style="AUI.TButton").pack(side="left")
                ttk.Label(header, text=view.title, style="AUI.TLabel",
                          font=(self.theme.font_family, self.theme.font_size + 4, "bold")).pack(
                              side="left", padx=(6, 0))
            self._build(view.content, frame)
            return
        if isinstance(view, TabView):
            notebook = ttk.Notebook(parent)
            notebook.pack(fill="both", expand=True)
            for title, content in view.tabs:
                page = ttk.Frame(notebook, style="AUI.Surface.TFrame", padding=self.theme.spacing)
                notebook.add(page, text=title)
                self._build(content, page)
            if view.tabs:
                notebook.select(view._active_index())
                notebook.bind("<<NotebookTabChanged>>",
                              lambda _event, source=notebook, model=view:
                              (model.select(source.index("current")),
                               self._request_refresh()))
            return
        if isinstance(view, ScrollView):
            content = self._scroll_host(parent, horizontal=view.axis == "horizontal")
            self._build(view.content, content)
            return
        if isinstance(view, List):
            viewport = max(1, self._window_height - 2 * self.theme.content_padding)
            row_height = view.effective_row_height(max(1, self._window_width))
            step = row_height + view._spacing
            content, canvas = self._scroll_host(
                parent, return_canvas=True,
                on_scroll=lambda fraction, model=view: self._list_scrolled(model, fraction),
            )
            selected = view.selection.wrapped_value if view.selection else None
            offset = view.current_offset()
            visible = view.visible_rows(viewport, max(1, self._window_width))
            if offset:
                spacer = ttk.Frame(content, style="AUI.Surface.TFrame",
                                   height=max(1, int(offset * step)))
                spacer.pack(fill="x")
                spacer.pack_propagate(False)
            for relative_index, row in enumerate(visible):
                index = offset + relative_index
                holder = ttk.Frame(content, style="AUI.Surface.TFrame", padding=(8, 6))
                holder.pack(fill="x", pady=1)
                holder.configure(height=max(1, int(row_height)))
                if view.selection is not None:
                    row_id = view.row_id(row, index)
                    chosen = row_id in selected if view.allows_multiple_selection else row_id == selected
                    holder.configure(style="AUI.Selected.TFrame" if chosen else "AUI.Surface.TFrame")
                    holder.bind("<Button-1>", lambda event, model=view, value=index:
                                (model.select_row(value, extending=bool(event.state & 0x0001)),
                                 self._request_refresh()))
                self._build(row, holder)
            remaining = max(0, len(view.rows) - offset - len(visible))
            if remaining:
                spacer = ttk.Frame(content, style="AUI.Surface.TFrame",
                                   height=max(1, int(remaining * step)))
                spacer.pack(fill="x")
                spacer.pack_propagate(False)
            if view.rows:
                canvas.after_idle(lambda source=canvas, model=view:
                                  source.yview_moveto(model.current_offset() / len(model.rows)))
            return
        if isinstance(view, Section):
            group = ttk.LabelFrame(parent, style="AUI.Section.TLabelframe",
                                   padding=self.theme.spacing)
            group.pack(fill="x", pady=self.theme.spacing // 2)
            if isinstance(view.header, Text):
                group.configure(text=view.header.display_content)
            else:
                self._build(view.header, group)
            for child in view._children:
                self._build(child, group)
            if view.footer is not None:
                self._build(view.footer, group)
            return
        if isinstance(view, GroupBox):
            group = ttk.LabelFrame(parent, style="AUI.Section.TLabelframe",
                                   padding=self.theme.spacing)
            group.pack(fill="x", pady=self.theme.spacing // 2)
            if isinstance(view.label, Text):
                group.configure(text=view.label.display_content)
            else:
                self._build(view.label, group)
            self._build(view.content, group)
            return
        if isinstance(view, (Form, Group)):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="x")
            for child in view.children():
                holder = ttk.Frame(frame, style="AUI.Surface.TFrame")
                holder.pack(fill="x", pady=self.theme.spacing // 2)
                self._build(child, holder)
            return
        if isinstance(view, LabeledContent):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="x")
            label_host = ttk.Frame(frame, style="AUI.Surface.TFrame")
            label_host.pack(side="left", fill="x", expand=True)
            value_host = ttk.Frame(frame, style="AUI.Surface.TFrame")
            value_host.pack(side="right", anchor="e")
            self._build(view.label, label_host)
            self._build(view.content, value_host)
            return
        if isinstance(view, DisclosureGroup):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="x")
            header = ttk.Button(frame, text="▾" if view.expanded else "▸",
                                command=lambda model=view: (model.toggle(), self._request_refresh()),
                                style="AUI.TButton", width=3)
            header.pack(side="left", anchor="n")
            body = ttk.Frame(frame, style="AUI.Surface.TFrame")
            body.pack(side="left", fill="x", expand=True)
            self._build(view.label, body)
            if view.expanded:
                children = ttk.Frame(body, style="AUI.Surface.TFrame",
                                     padding=(self.theme.content_padding, 4, 0, 0))
                children.pack(fill="x")
                for child in view._children:
                    self._build(child, children)
            return
        if isinstance(view, (LazyVStack, LazyHStack, LazyVGrid, LazyHGrid)):
            self._build_lazy(view, parent)
            return
        if isinstance(view, ResponsiveItem):
            self._build(view.content, parent)
            return
        if isinstance(view, ResponsiveRow):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="x", expand=True)
            for column in range(view.columns):
                frame.columnconfigure(column, weight=1, uniform="aui-responsive")
            row, occupied = 0, 0
            for item in view.children():
                span = item.span(float(self._window_width), view.columns)
                if occupied and occupied + span > view.columns:
                    row, occupied = row + 1, 0
                holder = ttk.Frame(frame, style="AUI.Surface.TFrame")
                holder.grid(row=row, column=occupied, columnspan=span, sticky="nsew",
                            padx=view.spacing / 2, pady=view.run_spacing / 2)
                self._build(item.content, holder)
                occupied += span
            return
        if isinstance(view, (VStack, HStack, ZStack)):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="both" if isinstance(view, ZStack) else "x", expand=isinstance(view, ZStack))
            side = "left" if isinstance(view, HStack) else "top"
            for child in view.children():
                holder = ttk.Frame(frame, style="AUI.Surface.TFrame")
                holder.pack(side=side, fill="both" if isinstance(view, ZStack) else "x",
                            expand=isinstance(view, ZStack), padx=2, pady=self.theme.spacing // 2)
                self._build(child, holder)
            return
        if isinstance(view, Text):
            widget = ttk.Label(parent, text=view.display_content, style="AUI.TLabel",
                               wraplength=640)
            self._configure_text_widget(widget, view)
            widget.pack(anchor="w", fill="x")
            self._register_widget(view, widget)
            return
        if isinstance(view, Button):
            if isinstance(view, SettingsLink):
                view.connect(getattr(self, "_settings_opener", None))
            elif isinstance(view, WindowLink):
                view.connect(getattr(self, "_window_opener", None))
            elif isinstance(view, DismissWindowLink):
                view.connect(getattr(self, "_dismiss_window_action", None))
            title = self._symbol_text(view.system_name) or view.title if isinstance(view, IconButton) else view.title
            button_style = ("AUI.Sidebar.TButton" if self._split_column_context == 0
                            else "AUI.TButton")
            widget = ttk.Button(parent, text=title, command=view.action, style=button_style,
                                state="normal" if is_enabled(view) else "disabled")
            widget.pack(anchor="w")
            self._register_widget(view, widget)
            return
        if isinstance(view, Menu):
            button = ttk.Menubutton(parent, text=view.title, style="AUI.TButton")
            menu = tk.Menu(button, tearoff=False)
            self._populate_menu(menu, view.items)
            button.configure(menu=menu)
            button.pack(anchor="w")
            return
        if isinstance(view, Label):
            symbol = self._symbol_text(view.system_name)
            value = f"{symbol}  {view.title}" if symbol else view.title
            ttk.Label(parent, text=value, style="AUI.TLabel").pack(anchor="w", fill="x")
            return
        if isinstance(view, Image):
            self._build_image(view, parent)
            return
        if isinstance(view, (TextField, SecureField, TextEditor)):
            value = tk.StringVar(value=str(view.text.wrapped_value))
            widget_class = tk.Text if isinstance(view, TextEditor) else ttk.Entry
            if widget_class is tk.Text:
                widget = tk.Text(parent, height=max(3, int(view.min_height / 22)), wrap="word")
                widget.insert("1.0", value.get())
                widget.bind("<KeyRelease>", lambda _event, source=widget, binding=view.text:
                            setattr(binding, "wrapped_value", source.get("1.0", "end-1c")))
            else:
                widget = ttk.Entry(parent, textvariable=value,
                                   show="•" if isinstance(view, SecureField) else "")
                trace_id = value.trace_add("write", lambda *_args, variable=value, binding=view.text:
                                           setattr(binding, "wrapped_value", variable.get()))
                if self._submit_modifier is not None:
                    submit = self._submit_modifier.action
                    widget.bind("<Return>", lambda _event, action=submit:
                                (action(), "break")[1])
            if not is_enabled(view):
                widget.configure(state="disabled")
            widget.pack(fill="x")
            self._register_widget(view, widget, {"variable": value,
                                                  "trace": trace_id if widget_class is not tk.Text else None})
            self._apply_focus(widget)
            return
        if isinstance(view, Toggle):
            value = tk.BooleanVar(value=bool(view.is_on.wrapped_value) if view.is_on else False)
            command = (lambda variable=value, binding=view.is_on:
                       setattr(binding, "wrapped_value", bool(variable.get()))) if view.is_on else None
            widget = ttk.Checkbutton(parent, text=view.title, variable=value, command=command,
                                     style="AUI.TCheckbutton",
                                     state="normal" if is_enabled(view) else "disabled")
            widget.pack(anchor="w")
            self._register_widget(view, widget, {"variable": value})
            return
        if isinstance(view, Slider):
            lo, hi = view.range
            value = float(view.value.wrapped_value) if view.value else lo
            widget = ttk.Scale(parent, from_=lo, to=hi, value=value,
                               command=(lambda raw, binding=view.value:
                                        setattr(binding, "wrapped_value", float(raw))) if view.value else None)
            widget.pack(fill="x")
            self._register_widget(view, widget)
            return
        if isinstance(view, Stepper):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="x")
            title_label = ttk.Label(frame, text=view.title, style="AUI.TLabel")
            title_label.pack(side="left", expand=True, anchor="w")
            state = "normal" if is_enabled(view) else "disabled"
            decrement = ttk.Button(frame, text="−", width=3, command=view.decrement,
                                   state=state, style="AUI.TButton")
            decrement.pack(side="left")
            increment = ttk.Button(frame, text="+", width=3, command=view.increment,
                                   state=state, style="AUI.TButton")
            increment.pack(side="left", padx=(4, 0))
            value_label = None
            if view.value is not None:
                value_label = ttk.Label(frame, text=str(view.value.wrapped_value),
                                        style="AUI.TLabel")
                value_label.pack(side="left", padx=6)
            self._register_widget(view, frame, {
                "decrement": decrement, "increment": increment,
                "value_label": value_label, "title_label": title_label,
            })
            return
        if isinstance(view, Picker):
            variable = tk.StringVar(value=str(view.selection.wrapped_value) if view.selection else "")
            combo = ttk.Combobox(parent, values=tuple(map(str, view.options)), textvariable=variable,
                                 state="readonly" if is_enabled(view) else "disabled")
            if view.selection is not None:
                combo.bind("<<ComboboxSelected>>", lambda _event, source=combo, model=view:
                           self._picker_selected(model, source.current()))
            combo.pack(fill="x")
            self._register_widget(view, combo, {"variable": variable})
            return
        if isinstance(view, DatePicker):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="x")
            title_label = None
            if view.title:
                title_label = ttk.Label(frame, text=view.title, style="AUI.TLabel")
                title_label.pack(side="left", padx=(0, 8))
            value = tk.StringVar(value=view._current())
            entry = ttk.Entry(frame, textvariable=value,
                              state="normal" if is_enabled(view) else "disabled")
            entry.pack(side="left", fill="x", expand=True)
            entry.bind("<Return>", lambda _event, model=view, variable=value:
                       self._date_changed(model, variable.get()))
            entry.bind("<FocusOut>", lambda _event, model=view, variable=value:
                       self._date_changed(model, variable.get()))
            self._register_widget(view, entry, {"variable": value, "title_label": title_label})
            return
        if isinstance(view, ColorPicker):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="x")
            title_label = None
            if view.title:
                title_label = ttk.Label(frame, text=view.title, style="AUI.TLabel")
                title_label.pack(side="left", expand=True, anchor="w")
            color = view.selection.wrapped_value if view.selection else self.theme.accent
            button = ttk.Button(frame, text="●", width=3, style="AUI.TButton",
                                command=lambda model=view: self._choose_color(model),
                                state="normal" if is_enabled(view) else "disabled")
            button.pack(side="right")
            value_label = ttk.Label(frame, text=color_hex(color), style="AUI.TLabel")
            value_label.pack(side="right", padx=6)
            self._register_widget(view, button, {
                "value_label": value_label, "title_label": title_label,
            })
            return
        if isinstance(view, Gauge):
            frame = ttk.Frame(parent, style="AUI.Surface.TFrame")
            frame.pack(fill="x")
            label = None
            if view.label:
                label = ttk.Label(frame, text=view.label, style="AUI.TLabel")
                label.pack(anchor="w")
            lo, hi = view.range
            widget = ttk.Progressbar(frame, maximum=hi - lo,
                                     value=max(lo, min(hi, view.raw_value)) - lo,
                                     style="AUI.Horizontal.TProgressbar")
            widget.pack(fill="x")
            self._register_widget(view, widget, {"label": label})
            return
        if isinstance(view, ProgressView):
            widget = ttk.Progressbar(parent, maximum=100.0,
                                     style="AUI.Horizontal.TProgressbar")
            if view.value is None:
                widget.configure(mode="indeterminate")
                widget.start(12)
            else:
                widget.configure(value=max(0.0, min(1.0, view.value)) * 100.0)
            widget.pack(fill="x")
            self._register_widget(view, widget)
            return
        if isinstance(view, Divider):
            ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=self.theme.spacing)
            return
        children = list(view.children())
        if children:
            for child in children:
                self._build(child, parent)
        else:
            ttk.Label(parent, text=type(view).__name__, style="AUI.TLabel").pack(anchor="w")

    @staticmethod
    def _picker_selected(view: Picker, index: int) -> None:
        if view.selection is not None and 0 <= index < len(view.options):
            view.selection.wrapped_value = view.options[index]

    def _register_widget(self, view: View, widget, auxiliary=None) -> None:
        self._widgets[id(view)] = (widget, auxiliary)

    @staticmethod
    def _configure_text_widget(widget, view: Text) -> None:
        font = view.effective_font
        weight = "bold" if font.weight in {"medium", "semibold", "bold"} else "normal"
        options = {
            "font": (font.family, round(view.effective_font_size), weight),
        }
        if view.effective_color is not None:
            options["foreground"] = color_hex(view.effective_color)
        widget.configure(**options)

    def _update_widget_tree(self, old_view: View, new_view: View,
                            old_widgets: dict[int, tuple[object, object]], animation=None) -> bool:
        if self._contains_virtual_container(old_view) or self._contains_virtual_container(new_view):
            return False
        old_nodes, new_nodes = snapshot(old_view), snapshot(new_view)
        if old_nodes.keys() != new_nodes.keys():
            return False
        if any(type(old_nodes[path].view) is not type(new_nodes[path].view)
               for path in old_nodes):
            return False
        if any(isinstance(node.view, _ModifiedContent)
               and not isinstance(node.view._modifier,
                                  (IDModifier, ContentTransitionModifier,
                                   SymbolEffectModifier, TransactionModifier,
                                   EnvironmentModifier, MatchedGeometryEffectModifier))
               for node in tuple(old_nodes.values()) + tuple(new_nodes.values())):
            return False
        supported = (Text, Button, TextField, SecureField, TextEditor, Toggle,
                     Slider, Stepper, Picker, DatePicker, ColorPicker, Gauge, ProgressView)
        for node in tuple(old_nodes.values()) + tuple(new_nodes.values()):
            if not node.view.children() and not isinstance(node.view, supported + (EmptyView, Spacer)):
                return False
            if isinstance(node.view, Button) and type(node.view) is not Button:
                return False
            if isinstance(node.view, ProgressView) and type(node.view) is not ProgressView:
                return False
        old_paths = {id(node.view): path for path, node in old_nodes.items()}
        updates = []
        for old_id, (widget, auxiliary) in old_widgets.items():
            path = old_paths.get(old_id)
            if path is None or path not in new_nodes:
                return False
            view = new_nodes[path].view
            if not isinstance(view, supported):
                return False
            updates.append((path, old_nodes[path].view, view, widget, auxiliary))
        if sum(isinstance(node.view, supported) for node in new_nodes.values()) != len(updates):
            return False
        remapped = {}
        for path, before, view, widget, auxiliary in updates:
            leaf_animation = resolved_animation(view, animation)
            self._update_widget(view, widget, auxiliary, leaf_animation)
            if (leaf_animation is not None and isinstance(before, Text)
                    and isinstance(view, Text)
                    and before.display_content != view.display_content):
                content_transition = self._content_transition_for_path(new_nodes, path)
                if content_transition not in (None, ContentTransition.IDENTITY):
                    self._animate_text_content(
                        widget, before.display_content, view.display_content,
                        content_transition, leaf_animation)
            old_symbol = self._symbol_effect_for_path(old_nodes, path)
            new_symbol = self._symbol_effect_for_path(new_nodes, path)
            motion_disabled = animations_disabled(view)
            if motion_disabled or (old_symbol is not None and new_symbol is None):
                active = self._animation_handles.pop(id(widget), None)
                if active is not None:
                    active.cancel()
                try:
                    widget.configure(padding=(0, 0, 0, 0))
                except Exception:
                    pass
            symbol_changed = (new_symbol is not None and (
                old_symbol is None or old_symbol.effect != new_symbol.effect
                or old_symbol.value != new_symbol.value
                or old_symbol.repeating != new_symbol.repeating))
            if symbol_changed and not motion_disabled:
                symbol_animation = leaf_animation or Animation.ease_in_out(0.35)
                if new_symbol.repeating:
                    symbol_animation = symbol_animation.repeat_forever(False)
                self._animate_widget_symbol(
                    widget, new_symbol.effect, symbol_animation)
            remapped[id(view)] = (widget, auxiliary)
        self._widgets = remapped
        return True

    @staticmethod
    def _content_transition_for_path(nodes, path):
        for length in range(len(path), 0, -1):
            node = nodes.get(path[:length])
            if (node is not None and isinstance(node.view, _ModifiedContent)
                    and isinstance(node.view._modifier, ContentTransitionModifier)):
                return node.view._modifier.transition
        return None

    @staticmethod
    def _symbol_effect_for_path(nodes, path):
        for length in range(len(path), 0, -1):
            node = nodes.get(path[:length])
            if (node is not None and isinstance(node.view, _ModifiedContent)
                    and isinstance(node.view._modifier, SymbolEffectModifier)):
                return node.view._modifier
        return None

    def _animate_text_content(self, widget, start: str, end: str,
                              transition: str, animation) -> None:
        key = id(widget)
        handle = self._animation_handles.pop(key, None)
        if handle is not None:
            handle.cancel()
        numeric = transition in (ContentTransition.NUMERIC_TEXT,
                                 ContentTransition.INTERPOLATE)
        try:
            start_number, end_number = float(start), float(end)
        except (TypeError, ValueError):
            numeric = False
        integer_result = numeric and start_number.is_integer() and end_number.is_integer()

        def update(progress: float) -> None:
            if numeric:
                value = interpolate(start_number, end_number, progress)
                widget.configure(text=str(round(value)) if integer_result else f"{value:g}")
            else:
                widget.configure(text=start if progress < 0.5 else end)

        update(0.0)
        holder = {}
        def complete() -> None:
            widget.configure(text=end)
            current = holder.get("handle")
            if self._animation_handles.get(key) is current:
                self._animation_handles.pop(key, None)
        holder["handle"] = self._animation_driver.animate(
            animation, 0.0, 1.0, update, complete)
        self._animation_handles[key] = holder["handle"]

    def _animate_widget_symbol(self, widget, effect: str, animation) -> None:
        key = id(widget)
        handle = self._animation_handles.pop(key, None)
        if handle is not None:
            handle.cancel()
        try:
            size = Size(float(widget.winfo_width()), float(widget.winfo_height()))
        except (AttributeError, TypeError, ValueError):
            size = Size(24, 24)

        def update(progress: float) -> None:
            sample = sample_symbol_effect(effect, progress, size)
            x, y = round(sample.offset.x), round(sample.offset.y)
            # ttk has no portable opacity or transforms. Padding preserves the
            # timing and directional motion semantics on all three platforms.
            widget.configure(padding=(max(0, x), max(0, y),
                                      max(0, -x), max(0, -y)))

        holder = {}
        def complete() -> None:
            widget.configure(padding=(0, 0, 0, 0))
            current = holder.get("handle")
            if self._animation_handles.get(key) is current:
                self._animation_handles.pop(key, None)
        holder["handle"] = self._animation_driver.animate(
            animation, 0.0, 1.0, update, complete)
        self._animation_handles[key] = holder["handle"]

    @classmethod
    def _contains_virtual_container(cls, view: View) -> bool:
        if isinstance(view, (List, LazyVStack, LazyHStack, LazyVGrid, LazyHGrid)):
            return True
        return any(cls._contains_virtual_container(child) for child in view.children())

    def _update_widget(self, view: View, widget, auxiliary=None, animation=None) -> None:
        state = "normal" if is_enabled(view) else "disabled"
        if isinstance(view, Text):
            widget.configure(text=view.display_content)
            self._configure_text_widget(widget, view)
        elif isinstance(view, Button):
            widget.configure(text=view.title, command=view.action, state=state)
        elif isinstance(view, TextEditor):
            current = widget.get("1.0", "end-1c")
            value = str(view.text.wrapped_value)
            if current != value:
                widget.delete("1.0", "end")
                widget.insert("1.0", value)
            widget.configure(state=state)
            widget.bind("<KeyRelease>", lambda _event, source=widget, binding=view.text:
                        setattr(binding, "wrapped_value", source.get("1.0", "end-1c")))
        elif isinstance(view, (TextField, SecureField)):
            variable = auxiliary["variable"]
            if auxiliary.get("trace") is not None:
                variable.trace_remove("write", auxiliary["trace"])
            variable.set(str(view.text.wrapped_value))
            auxiliary["trace"] = variable.trace_add(
                "write", lambda *_args, source=variable, binding=view.text:
                setattr(binding, "wrapped_value", source.get()))
            widget.configure(state=state)
        elif isinstance(view, Toggle):
            variable = auxiliary["variable"]
            variable.set(bool(view.is_on.wrapped_value) if view.is_on else False)
            command = (lambda source=variable, binding=view.is_on:
                       setattr(binding, "wrapped_value", bool(source.get()))) if view.is_on else None
            widget.configure(text=view.title, state=state, command=command)
        elif isinstance(view, Slider):
            lo, hi = view.range
            command = (lambda raw, binding=view.value:
                       setattr(binding, "wrapped_value", float(raw))) if view.value else None
            widget.configure(from_=lo, to=hi, state=state)
            if view.value is not None:
                target = float(view.value.wrapped_value)
                if animation is not None and self._animation_driver is not None:
                    handle = self._animation_handles.pop(id(widget), None)
                    if handle is not None:
                        handle.cancel()
                    try:
                        start = float(widget.get())
                    except Exception:
                        start = target
                    widget.configure(command=None)
                    key = id(widget)
                    holder = {}
                    def complete_slider(source=widget, callback=command) -> None:
                        source.configure(command=callback)
                        current = holder.get("handle")
                        if self._animation_handles.get(key) is current:
                            self._animation_handles.pop(key, None)
                    holder["handle"] = self._animation_driver.animate(
                        animation, start, target, widget.set,
                        complete_slider,
                    )
                    self._animation_handles[key] = holder["handle"]
                else:
                    widget.configure(command=command)
                    widget.set(target)
            else:
                widget.configure(command=None)
        elif isinstance(view, Stepper):
            state = "normal" if is_enabled(view) else "disabled"
            auxiliary["decrement"].configure(command=view.decrement, state=state)
            auxiliary["increment"].configure(command=view.increment, state=state)
            label = auxiliary.get("value_label")
            if label is not None and view.value is not None:
                label.configure(text=str(view.value.wrapped_value))
            title_label = auxiliary.get("title_label")
            if title_label is not None:
                title_label.configure(text=view.title)
        elif isinstance(view, Picker):
            widget.configure(values=tuple(map(str, view.options)),
                             state="readonly" if is_enabled(view) else "disabled")
            selected = view.selection.wrapped_value if view.selection else None
            index = next((index for index, option in enumerate(view.options)
                          if option == selected), -1)
            widget.current(index)
            widget.bind("<<ComboboxSelected>>", lambda _event, source=widget, model=view:
                        self._picker_selected(model, source.current()))
        elif isinstance(view, DatePicker):
            variable = auxiliary["variable"]
            variable.set(view._current())
            widget.configure(state=state)
            widget.bind("<Return>", lambda _event, model=view, source=variable:
                        self._date_changed(model, source.get()))
            widget.bind("<FocusOut>", lambda _event, model=view, source=variable:
                        self._date_changed(model, source.get()))
            title_label = auxiliary.get("title_label")
            if title_label is not None:
                title_label.configure(text=view.title)
        elif isinstance(view, ColorPicker):
            widget.configure(command=lambda model=view: self._choose_color(model), state=state)
            color = view.selection.wrapped_value if view.selection else self.theme.accent
            auxiliary["value_label"].configure(text=color_hex(color))
            title_label = auxiliary.get("title_label")
            if title_label is not None:
                title_label.configure(text=view.title)
        elif isinstance(view, Gauge):
            lo, hi = view.range
            widget.configure(maximum=hi - lo,
                             value=max(lo, min(hi, view.raw_value)) - lo)
            label = auxiliary.get("label")
            if label is not None:
                label.configure(text=view.label)
        elif isinstance(view, ProgressView):
            if view.value is None:
                widget.configure(mode="indeterminate")
                widget.start(12)
            else:
                widget.stop()
                target = max(0.0, min(1.0, view.value)) * 100.0
                widget.configure(mode="determinate")
                if animation is not None and self._animation_driver is not None:
                    handle = self._animation_handles.pop(id(widget), None)
                    if handle is not None:
                        handle.cancel()
                    try:
                        start = float(widget.cget("value"))
                    except Exception:
                        start = target
                    key = id(widget)
                    holder = {}
                    def complete_progress() -> None:
                        current = holder.get("handle")
                        if self._animation_handles.get(key) is current:
                            self._animation_handles.pop(key, None)
                    holder["handle"] = self._animation_driver.animate(
                        animation, start, target,
                        lambda value, source=widget: source.configure(value=value),
                        complete_progress,
                    )
                    self._animation_handles[key] = holder["handle"]
                else:
                    widget.configure(value=target)

    @staticmethod
    def _date_changed(view: DatePicker, value: str) -> bool:
        if view.selection is None:
            return False
        formats = {"date": "%Y-%m-%d", "hourAndMinute": "%H:%M"}
        date_format = formats.get(view.displayed_components, "%Y-%m-%d %H:%M")
        try:
            parsed = datetime.strptime(value.strip(), date_format)
        except ValueError:
            return False
        if view.in_range is not None:
            parsed = max(view.in_range[0], min(view.in_range[1], parsed))
        view.selection.wrapped_value = parsed
        return True

    def _choose_color(self, view: ColorPicker) -> None:
        if view.selection is None:
            return
        from tkinter import colorchooser
        _, value = colorchooser.askcolor(color=color_hex(view.selection.wrapped_value),
                                         parent=self._root)
        if value:
            view.selection.wrapped_value = self._color_from_hex(value)

    @staticmethod
    def _color_from_hex(value: str) -> Color:
        text = value.lstrip("#")
        if len(text) != 6:
            raise ValueError("color must use #RRGGBB format")
        try:
            channels = tuple(int(text[index:index + 2], 16) / 255.0
                             for index in (0, 2, 4))
        except ValueError as exc:
            raise ValueError("color must use #RRGGBB format") from exc
        return Color(*channels)

    def _build_inspector(self, view: InspectorView, parent) -> None:
        """Render the inspector beside content, or below it in compact space."""
        available = float(self._window_width)
        main_width, inspector_width = view.column_widths(available)
        if not view.presented:
            self._build(view.content, parent)
            return
        if main_width <= 0.0:  # SwiftUI's compact inspector presentation.
            self._build(view.inspector_content, parent)
            return
        split = ttk.Panedwindow(parent, orient="horizontal")
        split.pack(fill="both", expand=True)
        content = ttk.Frame(split, style="AUI.Surface.TFrame")
        panel = ttk.Frame(split, style="AUI.Surface.TFrame")
        split.add(content, weight=1)
        split.add(panel, weight=0)
        self._build(view.content, content)
        self._build(view.inspector_content, panel)
        # Tk applies sash placement only after a widget has been mapped.
        split.after_idle(lambda source=split, width=main_width: source.sashpos(0, int(width)))

    def _build_async_image(self, view: AsyncImage, parent) -> None:
        if view.phase.is_success and view.phase.data:
            image = None
            try:
                import base64
                image = tk.PhotoImage(data=base64.b64encode(view.phase.data).decode("ascii"))
            except Exception:
                image = None
            if image is not None:
                self._images.append(image)
                ttk.Label(parent, image=image, style="AUI.TLabel").pack(anchor="w")
                return
            text = "Image loaded"
        elif view.phase.is_failure:
            text = "Image unavailable"
        else:
            text = "Loading image…"
            self._async_image_cancels.append(
                view.subscribe(lambda _phase: self._dispatcher.dispatch(self._request_refresh))
            )
            view.start()
        ttk.Label(parent, text=text, style="AUI.TLabel").pack(anchor="w")

    def _build_gradient(self, view: Gradient, parent) -> None:
        width = max(1, int(view.size_that_fits(Size(float(self._window_width),
                                                     float(self._window_height))).width))
        height = max(1, int(view.size_that_fits(Size(float(self._window_width),
                                                      float(self._window_height))).height))
        canvas = tk.Canvas(parent, width=width, height=height, highlightthickness=0,
                           background=color_hex(self.theme.surface))
        canvas.pack(anchor="w")
        # A dense strip approximation is deterministic across Tk platforms.
        for x in range(width):
            color = view.color_at(x / max(1, width - 1))
            canvas.create_line(x, 0, x, height, fill=color_hex(color))

    def _build_canvas(self, view: Canvas, parent) -> None:
        size = view.size_that_fits(Size(float(self._window_width), float(self._window_height)))
        width, height = max(1, int(size.width)), max(1, int(size.height))
        canvas = tk.Canvas(parent, width=width, height=height, highlightthickness=0,
                           background=color_hex(self.theme.surface))
        canvas.pack(anchor="w")
        for draw in view.resolve(Size(float(width), float(height))).commands:
            points, start = [], None
            for command in draw.path.commands:
                kind = command[0]
                if kind == "rect":
                    rect = command[1]
                    method = canvas.create_rectangle
                    options = {"outline": color_hex(draw.color)} if draw.operation == "stroke" else {"fill": color_hex(draw.color), "outline": ""}
                    method(rect.origin.x, rect.origin.y, rect.origin.x + rect.size.width,
                           rect.origin.y + rect.size.height, **options)
                elif kind == "ellipse":
                    rect = command[1]
                    options = {"outline": color_hex(draw.color)} if draw.operation == "stroke" else {"fill": color_hex(draw.color), "outline": ""}
                    canvas.create_oval(rect.origin.x, rect.origin.y, rect.origin.x + rect.size.width,
                                       rect.origin.y + rect.size.height, **options)
                elif kind == "move":
                    start = command[1]; points = [start.x, start.y]
                elif kind in {"line", "quad", "curve"}:
                    point = command[1]; points.extend((point.x, point.y))
                elif kind == "close" and start is not None:
                    points.extend((start.x, start.y))
            if len(points) >= 4:
                options = {"fill": color_hex(draw.color), "width": draw.style.line_width if draw.style else 1}
                canvas.create_line(*points, **options)

    def _build_table(self, view: Table, parent) -> None:
        columns = view.visible_columns
        tree = ttk.Treeview(parent, columns=[column.key for column in columns], show="headings",
                            selectmode="extended" if view.allows_multiple_selection else "browse",
                            height=max(2, int(view.min_height / view.row_height)))
        for column in columns:
            tree.heading(column.key, text=column.title,
                         command=lambda key=column.key, model=view: (model.set_sort(key), self._request_refresh()))
            tree.column(column.key, width=int(column.resolved_width()), stretch=True)
        rows = view.displayed_rows
        for index, row in enumerate(rows):
            tree.insert("", "end", iid=str(index), values=[str(column.get_value(row)) for column in columns])
        if not rows:
            tree.insert("", "end", iid="empty", values=[view.empty_message] + [""] * max(0, len(columns) - 1))
        def select(_event, model=view, source=tree):
            indices = [int(value) for value in source.selection() if value != "empty"]
            if indices:
                if model.allows_multiple_selection and model.selection is not None:
                    model.selection.wrapped_value = {
                        model.row_id(rows[index]) for index in indices
                    }
                else:
                    model.select_row(indices[-1])
                self._request_refresh()
        tree.bind("<<TreeviewSelect>>", select)
        tree.pack(fill="both", expand=True)

    def _build_image(self, view: Image, parent) -> None:
        image = None
        try:
            if view.path is not None:
                image = tk.PhotoImage(file=str(Path(view.path).expanduser()))
            elif view.data is not None:
                import base64
                image = tk.PhotoImage(data=base64.b64encode(view.data).decode("ascii"))
        except Exception:
            image = None
        if image is not None:
            self._images.append(image)
            ttk.Label(parent, image=image, style="AUI.TLabel").pack(anchor="w")
        else:
            symbol = self._symbol_text(view.resolved_system_name) or "◇"
            ttk.Label(parent, text=symbol, style="AUI.TLabel",
                      font=(self.theme.font_family, max(12, int(view.effective_size.height)))).pack(
                          anchor="w")

    @staticmethod
    def _symbol_text(name: str) -> str:
        base = name.split(".")[0] if name else ""
        return {"gear": "⚙", "star": "★", "heart": "♥", "person": "●",
                "folder": "▰", "doc": "▤", "magnifyingglass": "⌕",
                "plus": "+", "minus": "−", "checkmark": "✓",
                "sidebar": "☰", "arrow": "↺", "questionmark": "?",
                "play": "▶"}.get(base, "")

    @staticmethod
    def _button_action(view: View):
        node = view
        while isinstance(node, _ModifiedContent):
            node = node._content
        return node.action if isinstance(node, Button) else None

    def _bind_shortcut(self, shortcut: KeyboardShortcut, action: Callable[[], None]) -> None:
        if self._root is not None:
            sequence = self._shortcut_sequence(shortcut)
            self._root.bind(sequence, lambda _event: (action(), "break")[1], add=True)
            self._bound_sequences.add(sequence)

    def _bind_key_handler(self, modifier: OnKeyPressModifier) -> None:
        if self._root is None:
            return
        def dispatch(event):
            from ..core.keyboard import KeyPress
            key = event.keysym.lower() if event.keysym else event.char
            if modifier.keys is None or key in modifier.keys:
                return "break" if modifier.dispatch(KeyPress(key)).value == "handled" else None
            return None
        self._root.bind("<KeyPress>", dispatch, add=True)
        self._bound_sequences.add("<KeyPress>")

    def _apply_focus(self, widget) -> None:
        modifier = self._focus_modifier
        if modifier is None:
            return
        widget.bind("<FocusIn>", lambda _event, value=modifier: value.activate(), add=True)
        widget.bind("<FocusOut>", lambda _event, value=modifier: value.deactivate(), add=True)
        if modifier.is_focused or isinstance(modifier, DefaultFocusModifier):
            if isinstance(modifier, DefaultFocusModifier):
                modifier.activate_if_needed()
            widget.after_idle(widget.focus_set)

    def _install_toolbar(self) -> None:
        if self._pending_toolbar is None or self._host is None:
            return
        toolbar = ttk.Frame(self._host, style="AUI.Surface.TFrame", padding=(0, 0, 0, 8))
        children = self._host.winfo_children()
        options = {"fill": "x"}
        if children:
            options["before"] = children[0]
        toolbar.pack(**options)
        for item in self._pending_toolbar.items:
            side = "left" if item.placement in ("navigation", "cancellationAction") else "right"
            title = self._symbol_text(item.system_name) if item.system_name else item.label
            ttk.Button(toolbar, text=title or item.label, command=item.action, style="AUI.TButton",
                       state="normal" if item.is_enabled else "disabled").pack(side=side, padx=3)
            if item.shortcut is not None:
                self._bind_shortcut(item.shortcut, item.action)

    def _populate_menu(self, native, items) -> None:
        for item in items:
            if isinstance(item, MenuDivider):
                native.add_separator()
                continue
            native.add_command(label=item.title, command=item.action,
                               state="normal" if item.is_enabled else "disabled",
                               accelerator=self._shortcut_label(item.shortcut))
            if item.shortcut is not None:
                self._bind_shortcut(item.shortcut, item.action)

    @staticmethod
    def _shortcut_sequence(shortcut: KeyboardShortcut, family: Optional[str] = None) -> str:
        names = []
        platform = family or platform_family()
        mapping = {"command": "Command" if platform == "macos" else "Control",
                   "option": "Option" if platform == "macos" else "Alt",
                   "control": "Control", "shift": "Shift"}
        names.extend(mapping[value] for value in shortcut.modifiers)
        key = "Return" if shortcut.key == "\r" else (
            "Escape" if shortcut.key == "\x1b" else shortcut.key.lower())
        return "<" + "-".join((*names, key)) + ">"

    @staticmethod
    def _shortcut_label(shortcut: Optional[KeyboardShortcut]) -> str:
        if shortcut is None:
            return ""
        symbols = {"command": "⌘", "option": "⌥", "control": "⌃", "shift": "⇧"}
        return "".join(symbols[value] for value in shortcut.modifiers) + shortcut.key.upper()

    def _queue_presentation(self, modifier) -> None:
        key = (type(modifier), id(modifier.is_presented))
        if modifier.is_presented.wrapped_value and key not in self._active_presentations:
            self._active_presentations.add(key)
            self._pending_presentations.append((key, modifier))
        elif not modifier.is_presented.wrapped_value:
            self._active_presentations.discard(key)

    def _present_pending(self) -> None:
        pending, self._pending_presentations = self._pending_presentations, []
        for key, modifier in pending:
            if isinstance(modifier, AlertModifier):
                self._present_alert(key, modifier)
            elif isinstance(modifier, SheetModifier):
                self._present_sheet(key, modifier)
            elif isinstance(modifier, PopoverModifier):
                self._present_popover(key, modifier)
            elif isinstance(modifier, SnackBarModifier):
                self._present_snack_bar(key, modifier)
            elif isinstance(modifier, FileImporterModifier):
                self._present_file_importer(key, modifier)
            elif isinstance(modifier, FileExporterModifier):
                self._present_file_exporter(key, modifier)

    def _dismiss_presentation(self, key, modifier, window=None) -> None:
        modifier.is_presented.wrapped_value = False
        self._active_presentations.discard(key)
        if window is not None and window.winfo_exists():
            window.destroy()

    def _present_alert(self, key, modifier: AlertModifier) -> None:
        window = self._modal_window(modifier.title, 420, 180)
        ttk.Label(window, text=modifier.title, style="AUI.TLabel",
                  font=(self.theme.font_family, self.theme.font_size + 2, "bold")).pack(
                      anchor="w", padx=20, pady=(20, 6))
        if modifier.message:
            ttk.Label(window, text=modifier.message, style="AUI.TLabel", wraplength=380).pack(
                anchor="w", padx=20, pady=(0, 16))
        actions = ttk.Frame(window, style="AUI.Surface.TFrame")
        actions.pack(side="bottom", fill="x", padx=16, pady=16)
        for button in modifier.buttons:
            ttk.Button(actions, text=button.title, style="AUI.TButton",
                       command=lambda item=button: self._run_alert_button(
                           key, modifier, window, item)).pack(side="right", padx=4)
        window.protocol("WM_DELETE_WINDOW", lambda: self._dismiss_presentation(key, modifier, window))

    def _run_alert_button(self, key, modifier, window, button: Button) -> None:
        self._dismiss_presentation(key, modifier, window)
        button.action()

    def _present_sheet(self, key, modifier: SheetModifier) -> None:
        if isinstance(modifier, FullScreenCoverModifier):
            width, height = self._window_width, self._window_height
        else:
            width, height = int(modifier.size.width), int(modifier.size.height)
            if modifier.configuration.detents:
                height = int(max(item.resolve(self._window_height)
                                 for item in modifier.configuration.detents))
        window = self._modal_window(modifier.title or "", width, height)
        host = ttk.Frame(window, style="AUI.Surface.TFrame", padding=self.theme.content_padding)
        host.pack(fill="both", expand=True)
        dismiss = lambda: self._dismiss_presentation(key, modifier, window)
        content = modifier.content(dismiss) if len(inspect.signature(modifier.content).parameters) else modifier.content()
        self._build(content, host)
        if not modifier.configuration.interactive_dismiss_disabled:
            window.protocol("WM_DELETE_WINDOW", dismiss)

    def _present_popover(self, key, modifier: PopoverModifier) -> None:
        window = self._modal_window("", int(modifier.size.width), int(modifier.size.height))
        window.transient(self._root)
        host = ttk.Frame(window, style="AUI.Surface.TFrame", padding=self.theme.content_padding)
        host.pack(fill="both", expand=True)
        dismiss = lambda: self._dismiss_presentation(key, modifier, window)
        content = modifier.content(dismiss) if len(inspect.signature(modifier.content).parameters) else modifier.content()
        self._build(content, host)

    def _present_snack_bar(self, key, modifier: SnackBarModifier) -> None:
        window = tk.Toplevel(self._root)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.configure(background=color_hex(self.theme.surface))
        frame = ttk.Frame(window, style="AUI.Surface.TFrame", padding=(14, 9))
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=modifier.message, style="AUI.TLabel").pack(side="left")
        if modifier.action is not None:
            ttk.Button(frame, text=modifier.action.title, command=lambda: (
                modifier.action.action(), self._dismiss_presentation(key, modifier, window)
            ), style="AUI.TButton").pack(side="right", padx=(12, 0))
        window.update_idletasks()
        x = self._root.winfo_rootx() + max(12, (self._root.winfo_width() - window.winfo_width()) // 2)
        y = self._root.winfo_rooty() + max(12, self._root.winfo_height() - window.winfo_height() - 28)
        window.geometry(f"+{x}+{y}")
        window.after(round(modifier.duration * 1000), lambda: self._dismiss_presentation(key, modifier, window))
        window.protocol("WM_DELETE_WINDOW", dismiss)

    def _modal_window(self, title: str, width: int, height: int):
        window = tk.Toplevel(self._root)
        window.title(title)
        window.geometry(f"{max(240, width)}x{max(120, height)}")
        window.configure(background=color_hex(self.theme.surface))
        window.transient(self._root)
        return window

    def _present_file_importer(self, key, modifier: FileImporterModifier) -> None:
        from tkinter import filedialog
        types = [(f"*.{extension}", f"*.{extension}")
                 for extension in modifier.allowed_extensions]
        try:
            if modifier.allows_multiple:
                values = filedialog.askopenfilenames(parent=self._root, filetypes=types)
            else:
                value = filedialog.askopenfilename(parent=self._root, filetypes=types)
                values = (value,) if value else ()
            result = FileDialogResult(tuple(Path(value) for value in values),
                                      cancelled=not bool(values))
        except Exception as exc:
            result = FileDialogResult(error=exc)
        self._active_presentations.discard(key)
        modifier.complete(result)

    def _present_file_exporter(self, key, modifier: FileExporterModifier) -> None:
        from tkinter import filedialog
        try:
            value = filedialog.asksaveasfilename(parent=self._root,
                                                 initialfile=modifier.default_filename)
            if value:
                path = modifier.write_to(value)
                result = FileDialogResult((path,))
            else:
                result = FileDialogResult(cancelled=True)
        except Exception as exc:
            result = FileDialogResult(error=exc)
        self._active_presentations.discard(key)
        modifier.complete(result)

    def _scroll_host(self, parent, horizontal: bool = False, on_scroll=None,
                     return_canvas: bool = False):
        outer = ttk.Frame(parent, style="AUI.Surface.TFrame")
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0,
                           background=color_hex(self.theme.surface))
        def scroll(*args):
            canvas.yview(*args)
            if on_scroll is not None:
                on_scroll(canvas.yview()[0])
        vertical = ttk.Scrollbar(outer, orient="vertical", command=scroll)
        canvas.configure(yscrollcommand=vertical.set)
        if horizontal:
            horizontal_bar = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
            canvas.configure(xscrollcommand=horizontal_bar.set)
            horizontal_bar.pack(side="bottom", fill="x")
        vertical.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        content = ttk.Frame(canvas, style="AUI.Surface.TFrame")
        window = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _event:
                     canvas.configure(scrollregion=canvas.bbox("all")))
        if not horizontal:
            canvas.bind("<Configure>", lambda event:
                        canvas.itemconfigure(window, width=event.width))
        canvas.bind("<MouseWheel>", lambda event:
                    scroll("scroll", -1 if event.delta > 0 else 1, "units"))
        canvas.bind("<Button-4>", lambda _event: scroll("scroll", -1, "units"))
        canvas.bind("<Button-5>", lambda _event: scroll("scroll", 1, "units"))
        return (content, canvas) if return_canvas else content

    def _list_scrolled(self, view: List, fraction: float) -> None:
        if not view.rows:
            return
        target = min(len(view.rows) - 1, max(0, int(float(fraction) * len(view.rows))))
        if target != view.current_offset():
            view.scroll_to(target)
            self._request_refresh()

    def _build_split_view(self, view: NavigationSplitView, parent) -> None:
        split_key = self._split_build_index
        self._split_build_index += 1
        self._apply_split_width_overrides(view, split_key)
        paned = ttk.Panedwindow(parent, orient="horizontal")
        paned.pack(fill="both", expand=True)
        available = max(1, self._window_width - 2 * self.theme.content_padding)
        children = list(view.children())
        for index, (content, width) in enumerate(zip(children, view.column_widths(available))):
            if width <= 0:
                continue
            pane = ttk.Frame(paned, style="AUI.Surface.TFrame", width=int(width),
                             padding=self.theme.spacing)
            paned.add(pane, weight=1 if index == len(children) - 1 else 0)
            previous_column = self._split_column_context
            self._split_column_context = index
            try:
                self._build(content, pane)
            finally:
                self._split_column_context = previous_column
        paned.bind("<ButtonRelease-1>", lambda _event, source=paned, key=split_key,
                   model=view: self._remember_split_sashes(source, model, key), add=True)

    def _apply_split_width_overrides(self, view: NavigationSplitView, split_key: int) -> None:
        for column, ideal in self._split_width_overrides.get(split_key, {}).items():
            name = ("sidebar", "content", "detail")[column]
            minimum, _, maximum = getattr(view, f"{name}_width")
            setattr(view, f"{name}_width", (minimum, min(maximum, max(minimum, ideal)), maximum))

    def _remember_split_sashes(self, paned, view: NavigationSplitView, split_key: int) -> None:
        try:
            visible = [index for index, width in enumerate(view.column_widths(self._window_width)) if width > 0]
            if len(visible) < 2:
                return
            values = self._split_width_overrides.setdefault(split_key, {})
            first = float(paned.sashpos(0))
            if visible[0] in (0, 1):
                values[visible[0]] = first
            if len(visible) > 2 and visible[1] in (0, 1):
                values[visible[1]] = max(1.0, float(paned.sashpos(1)) - first)
            self._request_refresh()
        except Exception:
            return

    def _build_lazy(self, view, parent) -> None:
        key = (type(view), self._lazy_index)
        self._lazy_index += 1
        horizontal = isinstance(view, (LazyHStack, LazyHGrid))
        viewport = self._window_width if horizontal else self._window_height
        offset = self._lazy_offsets.get(key, 0.0)
        content, canvas = self._scroll_host(
            parent, horizontal=horizontal, return_canvas=True,
            on_scroll=lambda fraction, model=view, identity=key:
            self._lazy_scrolled(model, identity, fraction),
        )
        if isinstance(view, (LazyVStack, LazyHStack)):
            estimate = 80.0 if horizontal else 28.0
            start, visible = view.visible_children(offset, viewport, estimate)
            tracks = len(view._foreach.data)
            first_track, last_track = start, start + len(visible)
            groups = [[child] for child in visible]
            extent = estimate + view._spacing
        elif isinstance(view, LazyVGrid):
            count = max(1, len(view.resolved_columns(max(1, self._window_width))))
            start, visible = view.visible_children(offset, viewport, self._window_width)
            tracks = (len(view._foreach.data) + count - 1) // count
            first_track = start // count
            last_track = (start + len(visible) + count - 1) // count
            groups = [visible[index:index + count] for index in range(0, len(visible), count)]
            extent = 40.0 + view.row_spacing
        else:
            count = max(1, len(view.resolved_rows(max(1, self._window_height))))
            start, visible = view.visible_children(offset, viewport, self._window_height)
            tracks = (len(view._foreach.data) + count - 1) // count
            first_track = start // count
            last_track = (start + len(visible) + count - 1) // count
            groups = [visible[index:index + count] for index in range(0, len(visible), count)]
            extent = 120.0 + view.column_spacing
        self._lazy_spacer(content, horizontal, first_track * extent)
        for group in groups:
            track = ttk.Frame(content, style="AUI.Surface.TFrame")
            track.pack(side="left" if horizontal else "top",
                       fill="both" if horizontal else "x")
            for child in group:
                cell = ttk.Frame(track, style="AUI.Surface.TFrame", padding=2)
                cell.pack(side="top" if horizontal else "left", fill="both", expand=True)
                self._build(child, cell)
        self._lazy_spacer(content, horizontal, max(0, tracks - last_track) * extent)
        total_extent = max(1.0, tracks * extent)
        fraction = min(1.0, offset / total_extent)
        canvas.after_idle(lambda source=canvas, value=fraction:
                          source.xview_moveto(value) if horizontal else source.yview_moveto(value))

    @staticmethod
    def _lazy_spacer(parent, horizontal: bool, extent: float) -> None:
        if extent <= 0:
            return
        options = {"width": max(1, int(extent))} if horizontal else {
            "height": max(1, int(extent))}
        spacer = ttk.Frame(parent, **options)
        spacer.pack(side="left" if horizontal else "top")
        spacer.pack_propagate(False)

    def _lazy_scrolled(self, view, key, fraction: float) -> None:
        count = len(view._foreach.data)
        estimate = 80.0 if isinstance(view, LazyHStack) else 28.0
        if isinstance(view, LazyVGrid):
            columns = max(1, len(view.resolved_columns(max(1, self._window_width))))
            count = (count + columns - 1) // columns
            estimate = 40.0
        elif isinstance(view, LazyHGrid):
            rows = max(1, len(view.resolved_rows(max(1, self._window_height))))
            count = (count + rows - 1) // rows
            estimate = 120.0
        value = max(0.0, float(fraction) * count * estimate)
        if abs(value - self._lazy_offsets.get(key, 0.0)) >= 1.0:
            self._lazy_offsets[key] = value
            self._request_refresh()


def available() -> bool:
    return StandardBackend.available()


class StandardApplication:
    """Run declarative Window and Settings scenes on all desktop platforms."""

    def __init__(self, scene: Window | Settings | WindowGroup,
                 theme: Optional[StandardTheme] = None,
                 commands: Commands | tuple[CommandMenu, ...] | list[CommandMenu] = ()):
        self.scene = scene
        self.theme = theme or DEFAULT_STANDARD_THEME
        self.commands = commands if isinstance(commands, Commands) else Commands(commands)
        scenes = list(scene) if isinstance(scene, WindowGroup) else [scene]
        if any(isinstance(item, MenuBarExtra) for item in scenes):
            raise ValueError("MenuBarExtra is only available in the AppKit application backend")
        settings = [item for item in scenes if isinstance(item, Settings)]
        if len(settings) > 1:
            raise ValueError("StandardApplication supports one Settings scene")
        self._scenes = scenes
        self._settings_scene = settings[0] if settings else None
        self._windows = {item.id: item for item in scenes if isinstance(item, Window)}
        self._window_backends: dict[str, StandardBackend] = {}
        self._settings_backend: Optional[StandardBackend] = None
        self.backends: list[StandardBackend] = []
        self._app_root = None

    def run(self) -> None:
        if not _TK_AVAILABLE:
            raise RuntimeError(
                "Standard application requires Python's tkinter module: "
                + StandardBackend.availability_reason()
            )
        try:
            self._app_root = tk.Tk()
        except Exception as exc:
            raise RuntimeError("Standard application could not connect to a desktop display") from exc
        self._app_root.withdraw()
        for window in self._windows.values():
            if window.initially_presented:
                self.open_window(window.id)
        if not self._window_backends and self._settings_scene is not None:
            self.open_settings()
        self._app_root.mainloop()

    def _launch(self, scene: Window | Settings) -> StandardBackend:
        if self._app_root is None:
            raise RuntimeError("StandardApplication must be running before opening windows")
        native = tk.Toplevel(self._app_root)
        backend = StandardBackend(
            scene.make_view, self.theme,
            on_resize=scene.on_resize,
            on_focus_changed=scene.on_focus_changed,
            on_close=scene.on_close,
        )
        backend._settings_opener = self.open_settings
        backend._window_opener = self.open_window
        backend._dismiss_window_action = DismissWindowAction(self.dismiss_window, scene.id)
        backend._start_window(native, int(scene.default_size.width),
                              int(scene.default_size.height), scene.title)
        self._install_commands(native)
        self._apply_scene_configuration(scene, native)
        native.protocol("WM_DELETE_WINDOW", lambda target=scene.id: self.dismiss_window(target))
        return backend

    def _install_commands(self, native) -> None:
        menu_bar = tk.Menu(native)
        if self._settings_scene is not None:
            app_menu = tk.Menu(menu_bar, tearoff=False)
            app_menu.add_command(label=self._settings_scene.title + "…", command=self.open_settings,
                                 accelerator="⌘," if platform_family() == "macos" else "Ctrl+,")
            menu_bar.add_cascade(label="Application", menu=app_menu)
            native.bind(StandardBackend._shortcut_sequence(
                KeyboardShortcut(","), platform_family()), lambda _event: self.open_settings(), add=True)
        for command_menu in self.commands:
            submenu = tk.Menu(menu_bar, tearoff=False)
            for item in command_menu.items:
                if isinstance(item, MenuDivider):
                    submenu.add_separator()
                else:
                    submenu.add_command(label=item.title, command=lambda action=item.action:
                                        self._run_command(action),
                                        state="normal" if item.is_enabled else "disabled",
                                        accelerator=StandardBackend._shortcut_label(item.shortcut))
                    if item.shortcut is not None:
                        native.bind(StandardBackend._shortcut_sequence(item.shortcut),
                                    lambda _event, action=item.action:
                                    (self._run_command(action), "break")[1], add=True)
            menu_bar.add_cascade(label=command_menu.title, menu=submenu)
        native.configure(menu=menu_bar)

    def _run_command(self, action: Callable[[], None]) -> None:
        action()
        for backend in self.backends:
            backend._request_refresh()

    @staticmethod
    def _apply_scene_configuration(scene: Window | Settings, native) -> None:
        native.resizable(scene.effective_resizable, scene.effective_resizable)
        native.minsize(int(scene.min_size.width), int(scene.min_size.height))
        max_width = native.winfo_screenwidth() if scene.max_size.width == float("inf") else int(scene.max_size.width)
        max_height = native.winfo_screenheight() if scene.max_size.height == float("inf") else int(scene.max_size.height)
        native.maxsize(max_width, max_height)
        if scene.style == WindowStyle.HIDDEN_TITLE_BAR:
            native.overrideredirect(True)
        if scene.level == WindowLevel.FLOATING:
            native.attributes("-topmost", True)
        StandardApplication._position_window(scene, native)

    @staticmethod
    def _position_window(scene: Window | Settings, native) -> None:
        position = scene.default_position
        if isinstance(position, Point):
            native.geometry(f"+{int(position.x)}+{int(position.y)}")
            return
        native.update_idletasks()
        width, height = native.winfo_width(), native.winfo_height()
        screen_w, screen_h = native.winfo_screenwidth(), native.winfo_screenheight()
        horizontal = 0 if position.endswith("Leading") else (
            screen_w - width if position.endswith("Trailing") else (screen_w - width) // 2)
        vertical = 0 if position.startswith("top") else (
            screen_h - height if position.startswith("bottom") else (screen_h - height) // 2)
        native.geometry(f"+{horizontal}+{vertical}")

    def open_window(self, window_id: str) -> bool:
        scene = self._windows.get(window_id)
        if scene is None:
            return False
        backend = self._window_backends.get(window_id)
        if backend is None or backend._root is None:
            backend = self._launch(scene)
            self._window_backends[window_id] = backend
            if backend not in self.backends:
                self.backends.append(backend)
        else:
            backend._root.deiconify()
            backend._root.lift()
            backend._root.focus_force()
        return True

    def dismiss_window(self, window_id: str) -> bool:
        backend = (self._settings_backend if self._settings_scene is not None
                   and window_id == self._settings_scene.id
                   else self._window_backends.get(window_id))
        if backend is None or backend._root is None:
            return False
        backend.close()
        return True

    def open_settings(self) -> bool:
        if self._settings_scene is None:
            return False
        if self._settings_backend is None or self._settings_backend._root is None:
            self._settings_backend = self._launch(self._settings_scene)
            if self._settings_backend not in self.backends:
                self.backends.append(self._settings_backend)
        else:
            self._settings_backend._root.deiconify()
            self._settings_backend._root.lift()
            self._settings_backend._root.focus_force()
        return True


__all__ = [
    "StandardApplication", "StandardBackend", "StandardTheme", "available",
    "platform_family",
]
