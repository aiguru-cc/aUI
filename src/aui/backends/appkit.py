"""Native macOS window backend for aUI (AppKit / Cocoa via PyObjC).

Renders the declarative aUI view tree onto **native** Cocoa controls
(``NSButton``, ``NSTextField``, ``NSSlider``, ``NSPopUpButton``, ``NSStepper``,
``NSProgressIndicator``, ``NSSwitch`` …) hosted in an ``NSWindow``. This is the
real GUI backend for macOS: it calls AppKit directly through PyObjC — the
official Apple bridge shipped with the system Python toolchain — so there is
**no Tkinter and no third-party GUI toolkit**.

Why AppKit? SwiftUI is a Swift-only wrapper over AppKit on macOS; going through
PyObjC lets Python drive the exact same native framework. The aUI view tree
stays 100% declarative — the backend maps each component to a native control
and binds two-way via ``Binding``/``State``.

Prerequisite
------------
The ``pyobjc-framework-Cocoa`` package must be importable. On macOS this is
one command::

    python3 -m pip install pyobjc-framework-Cocoa

If PyObjC is missing the module imports fine (``import appkit``) but
``AppKitBackend.available()`` returns ``False`` and ``run()`` raises a clear
error, so CLI runners can degrade to the curses backend gracefully.

Rendering strategy
------------------
1. The aUI layout engine (``size_that_fits`` / ``place``) computes each
   component's frame — the *same* geometry the curses backend uses, expressed
   in logical points instead of character cells.
2. The tree is laid out at its **natural height** (which may be much taller
   than the window — the showcase is ~4000pt in a 480pt window) and hosted in
   an ``NSScrollView`` whose ``documentView`` is **Flipped** (top-left origin,
   y grows down), so aUI coordinates map 1:1 and overflow scrolls natively
   instead of spilling outside the window.
3. ``_build`` walks the view tree and creates the matching native control for
   every component, using the layout frames for position/size. Controls keep
   their natural sizes (text uses its measured line height, buttons their
   title width) — nothing is stretched to fill a row.
4. Native control actions (``@_IBAction``) write straight back into the
   aUI ``Binding``/``State``, and the ``NSApp`` event loop keeps it live.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, Optional, Tuple

from ..core.components import (
    AppBar,
    Button,
    Capsule,
    Circle,
    ColorPicker,
    DatePicker,
    DisclosureGroup,
    ContentUnavailableView,
    Divider,
    Ellipse,
    Form,
    Gauge,
    Group,
    Image,
    IconButton,
    Label,
    LabeledContent,
    Link,
    List,
    NavigationRail,
    NavigationStack,
    NavigationLink,
    Picker,
    PasteButton,
    ProgressView,
    Rectangle,
    RoundedRectangle,
    Shape,
    ScrollView,
    SearchField,
    ShareLink,
    Section,
    SecureField,
    Slider,
    Stepper,
    TabView,
    Text,
    TextEditor,
    TextField,
    Toggle,
    UnevenRoundedRectangle,
)
from ..core.capabilities import Capability
from ..core.geometry import Color, Font, Point, Size
from ..core.layout import (
    GeometryReader, Grid, GridRow, HStack, NavigationSplitView, ResponsiveItem, ResponsiveRow,
    Spacer, VStack, ZStack,
)
from ..core.scenes import (
    DismissWindowAction, DismissWindowLink, MenuBarExtra, Settings, SettingsLink,
    Window, WindowGroup, WindowLevel, WindowLink, WindowRestorationBehavior,
    WindowStyle,
)
from ..core.modifiers import (
    BackgroundModifier,
    BorderModifier,
    CornerRadiusModifier,
    HiddenModifier,
    OpacityModifier,
    PaddingModifier,
    resolve_visual_style_tree,
)
from ..core.accessibility import (
    AccessibilityModifier, HeadingModifier, HiddenModifier as AccessibilityHiddenModifier,
    HintModifier as AccessibilityHintModifier, IdentifierModifier,
    InputLabelsModifier, LabelModifier as AccessibilityLabelModifier,
    SortPriorityModifier, ValueModifier as AccessibilityValueModifier,
)
from ..core.gestures import GestureHandler, GestureModifier, SpatialTapGesture, TapGesture
from ..core.interaction import (
    ContextMenuModifier, HitTestingModifier, HoverEffectModifier, OnHoverModifier,
    SensoryFeedbackModifier,
)
from ..core.container_styles import (
    FormStyle, GroupBoxStyle, ListRowBackgroundModifier,
    ListRowSeparatorModifier, ListStyle,
)
from ..core.list_editing import ListRowEditingModifier
from ..core.presentation import (
    AlertModifier, PopoverModifier, SheetModifier, SnackBarModifier, collect_presentation_configurations,
)
from ..core.commands import (
    CommandMenu, Commands, Menu, MenuDivider, MenuItem, ToolbarItem, ToolbarModifier,
)
from ..core.table import Table
from ..core.visual_effects import (
    AngularGradient, EllipticalGradient, Gradient, LinearGradient, Material, MaterialBackgroundModifier,
    OverlayModifier, RadialGradient, ShadowModifier,
)
from ..core.structural import AnyView, EmptyView, ForEach, GroupBox, OutlineGroup, ViewThatFits
from ..core.lazy import LazyHGrid, LazyVGrid
from ..core.scrolling import (
    IDModifier, ScrollIndicatorVisibility, ScrollViewReader,
    find_scroll_configuration,
)
from ..core.focus import FocusedModifier
from ..core.inspector import InspectorView
from ..core.control_group import ControlGroup
from ..core.badges import BadgeModifier
from ..core.keyboard import DefaultFocusModifier, KeyboardShortcutModifier
from ..core.events import (
    OnAppearModifier, OnDisappearModifier, OnSubmitModifier, SubmitLabelModifier,
    run_on_change,
)
from ..core.state import observation_tracking
from ..core.dispatcher import UIDispatcher
from ..core.reconciliation import snapshot
from ..core.state_persistence import restore_local_state
from ..core.measurement import MeasurementCache, measurement_context
from ..core.animation import Animation, current_animation, interpolate
from ..core.animation_runtime import AnimationDriver, sample_symbol_effect, sample_transition
from ..core.environment import EnvironmentReader, resolve_environment_tree
from ..core.system_environment import (
    COLOR_SCHEME_KEY, OPEN_URL_ACTION_KEY, ColorScheme, ControlActiveState,
    DismissAction, OpenURLAction, ScenePhase, system_environment,
)
from ..core.custom_layout import LayoutContainer
from ..core.layout_modifiers import (
    OffsetModifier, PositionModifier, SafeAreaInsetModifier, z_ordered,
)
from ..core.file_dialogs import (
    FileDialogResult, FileExporterModifier, FileImporterModifier,
)
from ..core.async_image import AsyncImage, AsyncImagePhase
from ..core.view import View, _Frame, _ModifiedContent
from ..core.styles import (
    ButtonStyle, ControlGroupStyle, ControlSize, LabelStyle, PickerStyle, ProgressViewStyle,
    TextFieldStyle, is_enabled, resolve_style_tree, style_value,
)
from ..core.transitions import (
    ContentTransition, ContentTransitionModifier, KeyframeAnimator, PhaseAnimator,
    SymbolEffectModifier, TransitionModifier,
)
from ..core.animation_modifiers import (
    MatchedGeometryEffectModifier, animations_disabled, resolve_transaction_tree,
    resolved_animation,
)
from ..core.canvas import Canvas, TimelineView
from ..core.text import resolve_text_style_tree, text_style_value
from ..core.localization import SemanticModifier, resolve_semantic_tree
from ..core.preferences import collect_preferences
from ..core.async_actions import cancel_tasks, start_tasks
from ..core.rendering import (
    BlendModeModifier, ClipModifier, CompositingModifier, FilterModifier,
    MaskModifier, Rotation3DEffectModifier, RotationEffectModifier,
    ScaleEffectModifier,
)
from .appkit_theme import AppKitTheme, DEFAULT_APPKIT_THEME

# ---------------------------------------------------------------------------
# PyObjC availability
# ---------------------------------------------------------------------------
try:  # pragma: no cover - depends on the machine
    import objc
    from Foundation import NSMakeRect, NSObject

    def _IBAction(method):
        """Objective-C action decoration (available)."""
        return objc.IBAction(method)
    from AppKit import (
        NSApplication,
        NSBackingStoreBuffered,
        NSBezelStyleRounded,
        NSBox,
        NSBoxCustom,
        NSButton,
        NSButtonTypeMomentaryPushIn,
        NSColor,
        NSControl,
        NSFont,
        NSImageView,
        NSLineBreakByWordWrapping,
        NSMenu,
        NSMenuItem,
        NSNoTitle,
        NSProgressIndicator,
        NSProgressIndicatorBarStyle,
        NSPopUpButton,
        NSScrollView,
        NSStatusBar,
        NSSlider,
        NSSliderTypeLinear,
        NSStepper,
        NSSwitch,
        NSTextField,
        NSTextFieldSquareBezel,
        NSView,
        NSViewWidthSizable,
        NSViewHeightSizable,
        NSWindow,
        NSWindowStyleMaskResizable,
        NSWindowStyleMaskTitled,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable,
        NSVariableStatusItemLength,
    )

    _PYOBJC = True
except Exception:  # pragma: no cover - depends on the machine
    _PYOBJC = False

    # Keep geometry helpers patchable on non-macOS backends.  The reconciliation
    # tests replace this symbol with a tuple-producing stub; defining it here
    # also gives portable callers a deterministic value without importing
    # Foundation or attempting to initialise AppKit.
    def NSMakeRect(x, y, width, height):
        return (x, y, width, height)

    def _IBAction(method):
        """No-op decorator so the module imports cleanly without PyObjC.

        Action callbacks only ever fire through the native event loop, which
        itself requires PyObjC, so an identity decorator is safe when PyObjC
        is missing.
        """
        return method


def _pyobjc_ok() -> bool:
    return _PYOBJC


if _PYOBJC:  # pragma: no cover - requires a macOS Python with PyObjC
    class _SplitDividerView(NSView):
        """Native hit target that commits a split-column resize on mouse-up."""

        def initWithBackend_splitKey_leftColumn_(self, backend, split_key, left_column):
            self = objc.super(_SplitDividerView, self).init()
            if self is not None:
                self._backend = backend
                self._split_key = int(split_key)
                self._left_column = int(left_column)
                self._start_x = 0.0
            return self

        def mouseDown_(self, event):
            self._start_x = float(event.locationInWindow().x)

        def mouseUp_(self, event):
            delta = float(event.locationInWindow().x) - self._start_x
            if abs(delta) >= 1.0:
                self._backend.resizeSplitDivider_(self._split_key, self._left_column, delta)


    class _BackendBridge(NSObject):
        """Objective-C facade forwarding AppKit delegates and actions to Python."""

        def initWithBackend_(self, backend):
            self = objc.super(_BackendBridge, self).init()
            if self is not None:
                self._backend = backend
            return self

        def windowWillClose_(self, notification):
            self._backend.windowWillClose_(notification)

        def windowShouldClose_(self, sender):
            return self._backend.windowShouldClose_(sender)

        def windowDidBecomeKey_(self, notification):
            self._backend.windowDidBecomeKey_(notification)

        def windowDidResignKey_(self, notification):
            self._backend.windowDidResignKey_(notification)

        def windowDidMiniaturize_(self, notification):
            self._backend.windowDidMiniaturize_(notification)

        def windowDidDeminiaturize_(self, notification):
            self._backend.windowDidDeminiaturize_(notification)

        def windowDidResize_(self, notification):
            self._backend.windowDidResize_(notification)

        def controlTextDidBeginEditing_(self, notification): self._backend.controlTextDidBeginEditing_(notification)
        def controlTextDidEndEditing_(self, notification): self._backend.controlTextDidEndEditing_(notification)
        def popoverDidClose_(self, notification): self._backend.popoverDidClose_(notification)
        def toolbarItemPressed_(self, sender): self._backend.toolbarItemPressed_(sender)
        def menuItemSelected_(self, sender): self._backend.menuItemSelected_(sender)
        def gestureRecognized_(self, sender): self._backend.gestureRecognized_(sender)
        def mouseEntered_(self, event): self._backend.mouseEntered_(event)
        def mouseExited_(self, event): self._backend.mouseExited_(event)
        def buttonPressed_(self, sender): self._backend.buttonPressed_(sender)
        def fieldChanged_(self, sender): self._backend.fieldChanged_(sender)
        def switchChanged_(self, sender): self._backend.switchChanged_(sender)
        def sliderChanged_(self, sender): self._backend.sliderChanged_(sender)
        def segmentChanged_(self, sender): self._backend.segmentChanged_(sender)
        def pickerChanged_(self, sender): self._backend.pickerChanged_(sender)
        def stepperChanged_(self, sender): self._backend.stepperChanged_(sender)
        def dateChanged_(self, sender): self._backend.dateChanged_(sender)
        def colorChanged_(self, sender): self._backend.colorChanged_(sender)
        def navigationBack_(self, sender): self._backend.navigationBack_(sender)
        def navigationRailSelected_(self, sender): self._backend.navigationRailSelected_(sender)
        def snackBarAction_(self, sender): self._backend.snackBarAction_(sender)
        def linkPressed_(self, sender): self._backend.linkPressed_(sender)

        def outlineView_numberOfChildrenOfItem_(self, outline, item):
            return self._backend.outlineView_numberOfChildrenOfItem_(outline, item)
        def outlineView_child_ofItem_(self, outline, index, item):
            return self._backend.outlineView_child_ofItem_(outline, index, item)
        def outlineView_isItemExpandable_(self, outline, item):
            return self._backend.outlineView_isItemExpandable_(outline, item)
        def outlineView_objectValueForTableColumn_byItem_(self, outline, column, item):
            return self._backend.outlineView_objectValueForTableColumn_byItem_(outline, column, item)
        def outlineViewSelectionDidChange_(self, notification): self._backend.outlineViewSelectionDidChange_(notification)
        def outlineViewItemDidExpand_(self, notification): self._backend.outlineViewItemDidExpand_(notification)
        def outlineViewItemDidCollapse_(self, notification): self._backend.outlineViewItemDidCollapse_(notification)
        def numberOfRowsInTableView_(self, table): return self._backend.numberOfRowsInTableView_(table)
        def tableView_objectValueForTableColumn_row_(self, table, column, row):
            return self._backend.tableView_objectValueForTableColumn_row_(table, column, row)
        def tableViewSelectionDidChange_(self, notification): self._backend.tableViewSelectionDidChange_(notification)
        def tableView_didClickTableColumn_(self, table, column):
            self._backend.tableView_didClickTableColumn_(table, column)


    class _ApplicationBridge(NSObject):
        """Objective-C action target for application-level menus.

        ``NSMenuItem`` retains and messages its target through the Objective-C
        runtime.  A plain :class:`AppKitApplication` is a Python object, so it
        cannot safely be installed as that target (and Cocoa asks it for
        Objective-C methods such as ``className``).  Keep the scene coordinator
        in Python and expose only the selectors AppKit needs here.
        """

        def initWithApplication_(self, application):
            self = objc.super(_ApplicationBridge, self).init()
            if self is not None:
                self._application = application
            return self

        def openSettings_(self, sender):
            self._application.openSettings_(sender)

        def appCommandPressed_(self, sender):
            self._application.appCommandPressed_(sender)

        def menuBarItemPressed_(self, sender):
            self._application.menuBarItemPressed_(sender)
else:
    _BackendBridge = None
    _SplitDividerView = None
    _ApplicationBridge = None


class AppKitBackend:
    """Native Cocoa window backend (macOS only). Use ``run()`` to show a window.

    ``view_factory`` is a zero-argument callable returning the root aUI view.
    The backend re-reads it on each render so state changes rebuild the tree.
    """

    @staticmethod
    def available() -> bool:
        """True when PyObjC is importable (native window support ready)."""
        return _PYOBJC

    @staticmethod
    def availability_reason() -> str:
        """Explain why the native AppKit renderer cannot start, if any."""
        if _PYOBJC:
            return "available"
        detail = f" ({_PYOBJC_IMPORT_ERROR})" if _PYOBJC_IMPORT_ERROR else ""
        return "PyObjC/AppKit bridge is unavailable" + detail

    # Keep this list explicit.  A capability is a public behavioural contract,
    # not a statement that the native toolkit could theoretically implement
    # it.  In particular, receiving drag-and-drop payloads has no AppKit
    # renderer path yet and must remain discoverably unavailable.
    CAPABILITIES = frozenset({
        Capability.NATIVE_SYMBOLS,
        Capability.TOOLBAR,
        Capability.SPLIT_DIVIDER_DRAG,
        Capability.SNACK_BAR,
        Capability.SNACK_BAR_ACTION,
        Capability.WINDOW_EVENTS,
        Capability.RESPONSIVE_ROW,
        Capability.NAVIGATION_RAIL,
        Capability.APP_BAR,
        Capability.FILE_DIALOGS,
    })

    @classmethod
    def supports(cls, capability: str) -> bool:
        return capability in cls.CAPABILITIES

    def __init__(self, view_factory: Callable[[], View], theme: Optional[AppKitTheme] = None,
                 resizable: bool = True,
                 settings_opener: Optional[Callable[[], None]] = None,
                 window_opener: Optional[Callable[[str], bool]] = None,
                 window_closer: Optional[Callable[[str], bool]] = None,
                 scene_id: Optional[str] = None,
                 on_resize: Optional[Callable[[Size], None]] = None,
                 on_focus_changed: Optional[Callable[[bool], None]] = None,
                 on_close: Optional[Callable[[], None]] = None):
        self._view_factory = view_factory
        self.theme = theme or DEFAULT_APPKIT_THEME
        self._resizable = bool(resizable)
        self._on_resize = on_resize
        self._on_focus_changed = on_focus_changed
        self._on_close = on_close
        self._settings_opener = settings_opener
        self._window_opener = window_opener
        self._dismiss_window_action = (
            DismissWindowAction(window_closer, current_id=scene_id)
            if window_closer is not None else None
        )
        self._view: Optional[View] = None
        self._frames: Dict[int, Tuple[Point, Size]] = {}
        self._split_width_overrides: Dict[int, Dict[int, float]] = {}
        self._split_layout_index = 0
        self._window: Optional["NSWindow"] = None
        self._bridge = None
        self._content = None
        self._controls: Dict[int, "NSControl"] = {}
        self._gesture_handlers: Dict[int, GestureHandler] = {}
        self._hover_handlers: Dict[int, Callable[[bool], None]] = {}
        self._sensory_values: Dict[str, object] = {}
        self._tasks = {}
        self._pending_presentations: list = []
        self._pending_file_dialogs: list = []
        self._presented_backends: list["AppKitBackend"] = []
        self._pending_toolbar: Optional[ToolbarModifier] = None
        self._toolbar_items: list[tuple[object, ToolbarItem]] = []
        self._navigation_rail_buttons: list[tuple[object, NavigationRail, int]] = []
        self._snack_bar_actions: list[tuple[object, SnackBarModifier]] = []
        self._presented_snack_bars: dict[int, object] = {}
        self._menu_items: list[tuple[object, MenuItem]] = []
        self._toolbar_accessories: list = []
        self._tables: list[tuple[object, Table]] = []
        self._outlines: list[tuple[object, OutlineGroup]] = []
        self._popovers: list[tuple[object, PopoverModifier, AppKitBackend]] = []
        self._scroll_view = None
        self._scroll_ids: dict[object, tuple[Point, Size]] = {}
        self._scroll_cancels: list[Callable[[], None]] = []
        self._focus_controls: list[tuple[object, FocusedModifier]] = []
        self._submit_controls: list[tuple[object, object]] = []
        self._appear_actions: list[Callable[[], None]] = []
        self._disappear_actions: list[Callable[[], None]] = []
        self._sharing_pickers: list = []
        self._async_image_cancels: list[Callable[[], None]] = []
        self._observation_cancels: list[Callable[[], None]] = []
        self._change_values: dict = {}
        self._refresh_scheduled = False
        self._dispatcher = UIDispatcher(self._schedule_on_main_queue)
        self._measurements = MeasurementCache()
        self._pending_animation = None
        self._animation_driver = AnimationDriver(self._schedule_animation_frame)
        self._animation_handles: dict[int, object] = {}
        self._timeline_timer = None
        self._interactive_dismiss_disabled = False
        self._on_window_close: Optional[Callable[[], None]] = None
        self._did_apply_default_scroll = False
        self._scene_phase = ScenePhase.ACTIVE
        self._control_active_state = ControlActiveState.KEY

    # -- Public API ---------------------------------------------------------
    def show(self, width: int = 560, height: int = 420, title: str = "aUI") -> None:
        """Create the native window, build the controls and run the app loop.

        Blocks until the window is closed (like ``curses.wrapper`` blocks until
        ``q``). Pass ``run_async=True`` via :meth:`run` for a non-blocking
        window suitable for tests/embedding.
        """
        self.run(width=width, height=height, title=title, run_async=False)

    def run(self, width: int = 560, height: int = 420, title: str = "aUI",
            run_async: bool = False) -> None:
        if not _PYOBJC:  # pragma: no cover - depends on the machine
            raise RuntimeError(
                "AppKit backend requires PyObjC. Install with: "
                "python3 -m pip install pyobjc-framework-Cocoa"
            )
        self._dispatcher.adopt_current_thread()
        app = NSApplication.sharedApplication()
        self._build_window(width, height, title)
        if run_async:
            # Do not run the blocking event loop (tests / embedding).
            return
        app.activateIgnoringOtherApps_(True)
        self._window.makeKeyAndOrderFront_(None)
        self._present_pending()
        app.run()

    # -- Native construction ------------------------------------------------
    def _build_window(self, width: int, height: int, title: str) -> None:
        rect = NSMakeRect(0, 0, width, height)
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
        )
        if self._resizable:
            style |= NSWindowStyleMaskResizable
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False
        )
        self._window.setTitle_(title)
        self._window.setReleasedWhenClosed_(False)
        self._bridge = _BackendBridge.alloc().initWithBackend_(self)
        self._window.setDelegate_(self._bridge)
        # Semantic system colours keep the window correct in both Aqua and
        # Dark Aqua.  The native controls inherit the application's accent.
        try:
            self._window.setBackgroundColor_(NSColor.windowBackgroundColor())
        except Exception:
            pass

        old_view = self._view
        self._view = self._make_view()
        restore_local_state(old_view, self._view)
        self._apply_window_color_scheme(self._view)
        self._pending_presentations = []
        self._pending_file_dialogs = []
        self._pending_toolbar = None
        self._focus_controls = []
        self._submit_controls = []
        self._appear_actions = []
        self._disappear_actions = []

        # --- Layout pass ---------------------------------------------------
        # aUI lays out in a top-left-origin coordinate system (y grows down)
        # and the tree may be *much taller* than the window (the showcase is
        # ~2400pt tall in a 480pt window).  We therefore lay out at the tree's
        # *natural* height, then host the whole thing in an NSScrollView so
        # overflow scrolls instead of spilling outside the window.
        proposal_h = float(height) if isinstance(self._view, NavigationSplitView) else float("inf")
        natural = self._view.size_that_fits(Size(float(width), proposal_h))
        nat_h = natural.height if natural.height != float("inf") else float(height) * 10
        content_h = max(float(height), nat_h)
        self._content_h = float(height)   # viewport height (for scrolling)
        self._content_natural_h = content_h
        self._layout(self._view, float(width), content_h)
        # The layout pass may have expanded the content (e.g. List rows are
        # rendered at a real point height, not the character-unit height used
        # by the natural-size measurement).  Grow the document to fit it.
        content_h = max(content_h, self._content_height)

        # --- NSScrollView host --------------------------------------------
        # documentView is Flipped so its origin is top-left — matching aUI
        # exactly, so every control can be placed with 1:1 aUI coordinates and
        # the native scroll view handles overflow vertically.
        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(0, 0, float(width), float(height))
        )
        scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll.setHasVerticalScroller_(True)
        scroll.setHasHorizontalScroller_(False)
        scroll.setDrawsBackground_(False)

        content = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, float(width), content_h)
        )
        content.setFlipped_(True)
        # NSScrollView already draws the window semantic background.  Avoid a
        # CALayer CGColor conversion here: older PyObjC builds expose that
        # conversion as an untyped pointer and emit ObjCPointerWarning.
        scroll.setDocumentView_(content)
        self._scroll_view = scroll
        self._content = content

        self._configure_scroll_view(self._view)

        self._build(self._view, content, Point(0.0, 0.0), Size(float(width), content_h))
        self._apply_configured_scroll(self._view)

        wc = self._window.contentView()
        wc.addSubview_(scroll)
        scroll.setFrame_(NSMakeRect(0, 0, float(width), float(height)))
        self._window.center()
        self._install_pending_toolbar()
        self._apply_pending_focus()
        self._run_appear_actions()
        run_on_change(self._view, self._change_values)
        self._install_timeline_timer()

    def _layout(self, view: View, width: float, height: float) -> None:
        """Run the declarative layout engine, recording frames per component."""
        self._measurements.clear()
        self._frames = {}
        self._split_layout_index = 0
        self._scroll_ids = {}
        for cancel in self._scroll_cancels:
            cancel()
        self._scroll_cancels = []
        for cancel in self._async_image_cancels:
            cancel()
        self._async_image_cancels = []
        self._content_height = 0.0
        with measurement_context(self._measurements):
            self._walk(view, Point(0.0, 0.0), Size(width, height))

    # -- layout engine (shared with curses, but keeps modifier frames) ------
    def _walk(self, view: View, origin: Point, size: Size) -> None:
        if isinstance(view, EnvironmentReader):
            self._frames[id(view)] = (origin, size)
            self._walk(view.content, origin, size)
            return
        if isinstance(view, LayoutContainer):
            self._frames[id(view)] = (origin, size)
            for placement in view.placements(origin, size):
                self._walk(placement.subview.view, placement.origin, placement.size)
            return
        if isinstance(view, OutlineGroup):
            self._frames[id(view)] = (origin, size)
            self._walk(view.content_view(), origin, size)
            return
        if isinstance(view, GeometryReader):
            self._frames[id(view)] = (origin, size)
            self._walk(view.resolve(origin, size), origin, size)
            return
        if isinstance(view, ScrollViewReader):
            self._frames[id(view)] = (origin, size)
            self._scroll_cancels.append(view.proxy.subscribe(self._scroll_to))
            self._walk(view.content, origin, size)
            return
        if isinstance(view, AnyView):
            self._frames[id(view)] = (origin, size)
            self._walk(view.content, origin, size)
            return
        if isinstance(view, ViewThatFits):
            self._frames[id(view)] = (origin, size)
            self._walk(view.selected(size), origin, size)
            return
        if isinstance(view, EmptyView):
            self._frames[id(view)] = (origin, Size())
            return
        if isinstance(view, _ModifiedContent):
            # Preserve the modifier frame: the wrapped view is placed inside it.
            self._frames[id(view)] = (origin, size)
            if isinstance(view._modifier, OverlayModifier):
                self._walk(view.body(), origin, size)
                overlay_size = view._modifier.overlay.size_that_fits(size)
                from ..core.view import _aligned_offset
                dx, dy = _aligned_offset(size, overlay_size, view._modifier.alignment)
                self._walk(view._modifier.overlay,
                           Point(origin.x + dx, origin.y + dy), overlay_size)
            elif isinstance(view._modifier, PaddingModifier):
                inset = view._modifier.insets
                inner_origin = Point(origin.x + inset.leading, origin.y + inset.top)
                inner_size = size.deflated_by(inset)
                self._walk(view.body(), inner_origin, inner_size)
            elif isinstance(view._modifier, SafeAreaInsetModifier):
                inset = view._modifier.insets
                self._walk(
                    view.body(),
                    Point(origin.x + inset.leading, origin.y + inset.top),
                    size.deflated_by(inset),
                )
            elif isinstance(view._modifier, OffsetModifier):
                mod = view._modifier
                self._walk(view.body(), Point(origin.x + mod.x, origin.y + mod.y), size)
            elif isinstance(view._modifier, PositionModifier):
                mod = view._modifier
                child_size = view.body().size_that_fits(size)
                self._walk(
                    view.body(),
                    Point(origin.x + mod.x - child_size.width / 2.0,
                          origin.y + mod.y - child_size.height / 2.0),
                    child_size,
                )
            else:
                self._walk(view.body(), origin, size)
            if isinstance(view._modifier, IDModifier):
                self._scroll_ids[view._modifier.value] = (origin, size)
            return
        if isinstance(view, _Frame):
            # A frame() wrapper is an explicit fixed box — record it, and walk
            # the content inside it (content alignment handled at render time).
            self._frames[id(view)] = (origin, size)
            self._walk(view._content, origin, size)
            return
        if isinstance(view, NavigationStack):
            self._frames[id(view)] = (origin, size)
            header_height = view.header_height
            self._walk(
                view.content,
                Point(origin.x, origin.y + header_height),
                Size(size.width, max(0.0, size.height - header_height)),
            )
            return
        if isinstance(view, AppBar):
            self._walk_app_bar(view, origin, size)
            return
        if isinstance(view, NavigationSplitView):
            self._walk_split(view, origin, size)
            return
        if isinstance(view, InspectorView):
            self._walk_inspector(view, origin, size)
            return
        if isinstance(view, ControlGroup):
            self._walk_stack(view, origin, size)
            return
        if isinstance(view, Grid):
            self._walk_grid(view, origin, size)
            return
        if isinstance(view, ResponsiveRow):
            self._walk_responsive_row(view, origin, size)
            return
        if isinstance(view, ResponsiveItem):
            self._frames[id(view)] = (origin, size)
            self._walk(view.content, origin, size)
            return
        if isinstance(view, LazyVGrid):
            self._walk_lazy_grid(view, origin, size)
            return
        if isinstance(view, LazyHGrid):
            self._walk_lazy_hgrid(view, origin, size)
            return
        if isinstance(view, GridRow):
            self._walk_horizontal(view, origin, size, view._spacing)
            return
        if isinstance(view, (VStack, HStack)):
            self._walk_stack(view, origin, size)
            return
        if isinstance(view, ZStack):
            self._frames[id(view)] = (origin, size)
            for child in view.children():
                self._walk(child, origin, size)
            return
        if isinstance(view, LabeledContent):
            self._walk_horizontal(view, origin, size, view._spacing)
            return
        if isinstance(view, (ForEach, GroupBox)):
            self._walk_container(view, origin, size)
            return
        if isinstance(view, (Form, Group, Section, DisclosureGroup, ScrollView, TabView,
                             ContentUnavailableView)):
            self._walk_container(view, origin, size)
            return
        if isinstance(view, List):
            self._walk_list(view, origin, size)
            return
        if isinstance(view, Spacer):
            self._frames[id(view)] = (origin, size)
            return
        # Leaf view.
        self._frames[id(view)] = (origin, size)
        self._content_height = max(self._content_height, origin.y + size.height)

    def _walk_container(self, view: View, origin: Point, size: Size) -> None:
        """Lay out Section / DisclosureGroup / Form / Group / ScrollView / TabView.

        These are vertical containers (like VStack) with a content height that is
        *at most* the proposal (viewport) height — content that overflows the
        viewport is clipped/scrolled by the native NSScrollView at render time.
        """
        self._frames[id(view)] = (origin, size)
        children = view.children()
        spacing = float(getattr(view, "_spacing", 0) or 0)
        # Measure each child at natural height (unlimited along Y).
        sizes: list = []
        for child in children:
            if isinstance(child, Spacer):
                sizes.append(None)
            else:
                try:
                    sizes.append(self._measurements.measure(
                        child, Size(size.width, float("inf"))))
                except Exception:
                    sizes.append(Size(size.width, 24.0))
        fixed_h = sum((s.height if s else 0.0) for s in sizes)
        spacing_total = spacing * max(0, len(children) - 1)
        natural_h = fixed_h + spacing_total
        # The container viewport is at most ``size.height``.
        self._content_height = max(self._content_height, origin.y + min(natural_h, size.height))
        cursor = origin.y
        for i, child in enumerate(children):
            cs = sizes[i]
            if cs is None:
                cs = Size(size.width, max(1.0, size.height - natural_h))
            self._walk(child, Point(origin.x, cursor), cs)
            cursor += cs.height + spacing

    def _walk_stack(self, stack: View, origin: Point, size: Size) -> None:
        if isinstance(stack, VStack):
            self._walk_vertical(stack, origin, size,
                                spacing=float(getattr(stack, "_spacing", 0) or 0))
        else:
            self._walk_horizontal(stack, origin, size,
                                  spacing=float(getattr(stack, "_spacing", 0) or 0))

    def _walk_app_bar(self, view: AppBar, origin: Point, size: Size) -> None:
        self._frames[id(view)] = (origin, Size(size.width, view.height))
        cursor = origin.x + 12.0
        if view.leading is not None:
            leading_size = view.leading.size_that_fits(Size(float("inf"), view.height))
            self._walk(view.leading, Point(cursor, origin.y), leading_size)
            cursor += leading_size.width + 10.0
        title_size = view.title.size_that_fits(Size(float("inf"), view.height))
        title_x = origin.x + (size.width - title_size.width) / 2.0 if view.center_title else cursor
        self._walk(view.title, Point(title_x, origin.y), title_size)
        action_x = origin.x + size.width - 12.0
        for action in reversed(view.actions):
            action_size = action.size_that_fits(Size(float("inf"), view.height))
            action_x -= action_size.width
            self._walk(action, Point(action_x, origin.y), action_size)
            action_x -= 8.0
        self._content_height = max(self._content_height, origin.y + view.height)

    def _walk_split(self, view: NavigationSplitView, origin: Point, size: Size) -> None:
        """Lay out split columns at full height with independent widths."""
        split_key = self._split_layout_index
        self._split_layout_index += 1
        setattr(view, "_backend_split_key", split_key)
        for column, ideal in self._split_width_overrides.get(split_key, {}).items():
            name = ("sidebar", "content", "detail")[column]
            minimum, _, maximum = getattr(view, f"{name}_width")
            setattr(view, f"{name}_width", (minimum, min(maximum, max(minimum, ideal)), maximum))
        self._frames[id(view)] = (origin, size)
        cursor = origin.x
        visible_count = 0
        for child, width in zip(view.children(), view.column_widths(size.width)):
            if width > 0 and visible_count:
                cursor += view.divider_width
            self._walk(child, Point(cursor, origin.y), Size(width, size.height))
            if width > 0:
                cursor += width
                visible_count += 1
        self._content_height = max(self._content_height, origin.y + size.height)

    def resizeSplitDivider_(self, split_key: int, left_column: int,
                            delta: float) -> None:  # pragma: no cover - native callback
        """Persist a native divider drag and rebuild with the new ideal width."""
        if self._view is None:
            return
        overrides = self._split_width_overrides.setdefault(int(split_key), {})
        # The leading side of a divider is the only bounded width that needs
        # updating; the following column absorbs the inverse delta.
        if left_column not in (0, 1):
            return
        names = ("sidebar", "content")
        split = self._find_split_by_key(int(split_key))
        if split is None:
            return
        minimum, ideal, maximum = getattr(split, f"{names[left_column]}_width")
        current = overrides.get(left_column, ideal)
        overrides[left_column] = min(maximum, max(minimum, current + float(delta)))
        self._refresh_content()

    def _find_split_by_key(self, split_key: int) -> Optional[NavigationSplitView]:
        """Return the split view assigned during the most recent layout pass."""
        def walk(node):
            if isinstance(node, NavigationSplitView) and getattr(node, "_backend_split_key", None) == split_key:
                return node
            for child in node.children():
                result = walk(child)
                if result is not None:
                    return result
            return None
        return walk(self._view) if self._view is not None else None

    def _walk_inspector(self, view: InspectorView, origin: Point, size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        main, panel = view.column_widths(size.width)
        self._walk(view.content, origin, Size(main, size.height))
        panel_x = origin.x if main == 0 else origin.x + main + view.divider_width
        self._walk(view.inspector_content, Point(panel_x, origin.y), Size(panel, size.height))
        self._content_height = max(self._content_height, origin.y + size.height)

    def _walk_grid(self, view: Grid, origin: Point, size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        columns, heights = view.metrics(size)
        y = origin.y
        for row, row_height in zip(view.children(), heights):
            row_width = sum(columns) + view.horizontal_spacing * max(0, len(columns) - 1)
            self._frames[id(row)] = (Point(origin.x, y), Size(row_width, row_height))
            x = origin.x
            for index, child in enumerate(row.children()):
                self._walk(child, Point(x, y), Size(columns[index], row_height))
                x += columns[index] + view.horizontal_spacing
            y += row_height + view.vertical_spacing
        self._content_height = max(self._content_height, y)

    def _walk_responsive_row(self, view: ResponsiveRow, origin: Point, size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        for item, point, item_size in view.placements(origin, size):
            self._walk(item, point, item_size)
        self._content_height = max(self._content_height, max(
            (point.y + item_size.height for _, point, item_size in view.placements(origin, size)),
            default=origin.y,
        ))

    def _walk_lazy_grid(self, view: LazyVGrid, origin: Point, size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        placements = view.placements(origin, size)
        for child, point, child_size in placements:
            self._walk(child, point, child_size)
        self._content_height = max(self._content_height,
                                   max((point.y + child_size.height
                                        for _, point, child_size in placements),
                                       default=origin.y))

    def _walk_lazy_hgrid(self, view: LazyHGrid, origin: Point, size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        for child, point, child_size in view.placements(origin, size):
            self._walk(child, point, child_size)

    def _walk_vertical(self, view: View, origin: Point, size: Size, spacing: float) -> None:
        self._frames[id(view)] = (origin, size)
        children = view.children()
        sizes: list = []
        flexible: list = []
        for i, child in enumerate(children):
            if isinstance(child, (Spacer, List)):
                sizes.append(None)
                flexible.append(i)
            else:
                try:
                    sizes.append(self._measurements.measure(
                        child, Size(size.width, float("inf"))))
                except Exception:
                    sizes.append(Size(size.width, 24.0))
        fixed_h = sum((s.height if s else 0.0) for s in sizes)
        spacing_total = spacing * max(0, len(children) - 1)
        free = max(0.0, size.height - fixed_h - spacing_total)
        flex_h = (free / len(flexible)) if flexible else 0.0
        cursor = origin.y
        for i, child in enumerate(children):
            cs = sizes[i]
            if cs is None:
                cs = Size(size.width, max(1.0, flex_h))
            self._walk(child, Point(origin.x, cursor), cs)
            cursor += cs.height + spacing

    def _walk_horizontal(self, stack: View, origin: Point, size: Size, spacing: float) -> None:
        self._frames[id(stack)] = (origin, size)
        children = stack.children()
        sizes: list = []
        for child in children:
            if isinstance(child, Spacer):
                sizes.append(None)
            else:
                try:
                    sizes.append(self._measurements.measure(
                        child, Size(size.width, float("inf"))))
                except Exception:
                    sizes.append(Size(60.0, 24.0))
        spacers = [i for i, s in enumerate(sizes) if s is None]
        fixed_w = sum((s.width if s else 0.0) for s in sizes)
        spacing_total = spacing * max(0, len(children) - 1)
        free = max(0.0, size.width - fixed_w - spacing_total)
        spacer_w = (free / len(spacers)) if spacers else 0.0
        cursor = origin.x
        for i, child in enumerate(children):
            cs = sizes[i]
            if cs is None:
                cs = Size(max(0.0, spacer_w), 24.0)
            self._walk(child, Point(cursor, origin.y), cs)
            cursor += cs.width + spacing

    def _walk_list(self, view: List, origin: Point, size: Size) -> None:
        self._frames[id(view)] = (origin, size)
        # AppKit works in points.  aUI List row heights may be expressed in
        # character rows (1 = one terminal line, as the curses backend expects)
        # — convert those to a readable point height so rows are not 1px tall.
        row_h = view.effective_row_height(size.width)
        if row_h < 14.0:
            row_h = 24.0  # treat a character-unit height as a full row
        step = row_h + float(getattr(view, "_spacing", 2.0) or 2.0)
        offset = view.current_offset()
        cursor = origin.y
        for row in view.rows[offset:]:
            # The outer NSScrollView scrolls the whole document, so render all
            # rows (not just the ones inside the List's viewport slot).
            self._walk(row, Point(origin.x, cursor), Size(size.width, row_h))
            cursor += step
        # Extend the document height to cover the rows actually rendered
        # (the natural-height pass measured them with the character row height).
        self._content_height = max(self._content_height, cursor - origin.y)

    # -- Native control mapping --------------------------------------------
    # The document view is Flipped (origin top-left, y grows down), which matches
    # the aUI coordinate system exactly — so every control is placed with its
    # aUI frame directly, with no per-control y flip.  The NSScrollView host
    # handles overflow vertically.

    def _build(self, view: View, parent: "NSView", origin: Point, size: Size) -> None:
        if isinstance(view, EnvironmentReader):
            self._build(view.content, parent, origin, size)
            return
        if isinstance(view, LayoutContainer):
            self._build_container(view, parent, origin, size)
            return
        if isinstance(view, OutlineGroup):
            frame = self._frames.get(id(view), (origin, size))
            self._add_outline_group(view, parent, frame[0].x, frame[0].y,
                                    frame[1].width, frame[1].height)
            return
        if isinstance(view, GeometryReader):
            frame = self._frames.get(id(view), (origin, size))
            self._build(view.resolve(*frame), parent, origin, size)
            return
        if isinstance(view, ScrollViewReader):
            self._build(view.content, parent, origin, size)
            return
        if isinstance(view, (PhaseAnimator, KeyframeAnimator)):
            self._build(view.content, parent, origin, size)
            return
        if isinstance(view, TimelineView):
            self._build(view.content, parent, origin, size)
            return
        if isinstance(view, AnyView):
            self._build(view.content, parent, origin, size)
            return
        if isinstance(view, ViewThatFits):
            frame = self._frames.get(id(view), (origin, size))
            self._build(view.selected(frame[1]), parent, origin, size)
            return
        if isinstance(view, EmptyView):
            return
        if isinstance(view, _ModifiedContent):
            self._build_modified(view, parent, origin, size)
            return
        if isinstance(view, _Frame):
            self._build_frame(view, parent, origin, size)
            return
        if isinstance(view, ResponsiveItem):
            self._build(view.content, parent, origin, size)
            return
        frame = self._frames.get(id(view))
        if frame is None:
            for child in view.children():
                self._build(child, parent, origin, size)
            return
        pos, fsize = frame
        x, y = pos.x, pos.y
        if fsize.width <= 0.0 or fsize.height <= 0.0:
            return

        if isinstance(view, NavigationStack):
            self._add_nav_header(view, parent, x, y, fsize.width)
            for child in view.children():
                self._build(child, parent, origin, size)
            return
        if isinstance(view, AppBar):
            bar = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, fsize.width, fsize.height))
            bar.setBoxType_(NSBoxCustom)
            bar.setTitlePosition_(NSNoTitle)
            bar.setBorderWidth_(0)
            bar.setFillColor_(NSColor.controlBackgroundColor())
            parent.addSubview_(bar)
            self._build_container(view, parent, origin, size)
            return
        if isinstance(view, NavigationRail):
            self._add_navigation_rail(view, parent, x, y, fsize.width, fsize.height)
            return
        if isinstance(view, InspectorView):
            self._add_inspector_surface(view, parent)
            self._build_container(view, parent, origin, size)
            return
        if isinstance(view, ControlGroup):
            self._add_control_group_surface(view, parent)
            self._build_container(view, parent, origin, size)
            return
        if isinstance(view, (VStack, HStack, ZStack, Form, Group, Section,
                             DisclosureGroup, ScrollView, TabView, List,
                             NavigationSplitView, Grid, GridRow, ResponsiveRow, LabeledContent,
                             ContentUnavailableView, ForEach, GroupBox,
                             LazyHGrid, LazyVGrid)):
            self._build_container(view, parent, origin, size)
            return

        self._build_leaf(view, parent, x, y, fsize)

    def _scroll_to(self, view_id, anchor: str = "top") -> None:  # pragma: no cover
        frame = self._scroll_ids.get(view_id)
        if frame is None or self._scroll_view is None:
            return
        point, size = frame
        viewport = float(self._content_h)
        if anchor == "center":
            target = point.y - (viewport - size.height) / 2.0
        elif anchor == "bottom":
            target = point.y - viewport + size.height
        else:
            target = point.y
        document_h = float(self._content.frame().size.height)
        target = max(0.0, min(target, max(0.0, document_h - viewport)))
        clip = self._scroll_view.contentView()
        clip.scrollToPoint_((0.0, target))
        self._scroll_view.reflectScrolledClipView_(clip)

    def _configure_scroll_view(self, view: View) -> None:  # pragma: no cover
        configuration = find_scroll_configuration(view)
        if configuration is None or self._scroll_view is None:
            return
        if configuration.indicators == ScrollIndicatorVisibility.HIDDEN:
            self._scroll_view.setHasVerticalScroller_(False)
            self._scroll_view.setHasHorizontalScroller_(False)
        elif configuration.indicators == ScrollIndicatorVisibility.VISIBLE:
            self._scroll_view.setHasVerticalScroller_(True)
            try:
                self._scroll_view.setAutohidesScrollers_(False)
            except Exception:
                pass
        try:
            self._content.layer().setMasksToBounds_(not configuration.clip_disabled)
        except Exception:
            pass

    def _apply_configured_scroll(self, view: View) -> None:  # pragma: no cover
        configuration = find_scroll_configuration(view)
        if configuration is None:
            return
        target = configuration.position.wrapped_value if configuration.position is not None else None
        if target is not None:
            self._scroll_to(target, configuration.position_anchor)
            return
        if self._did_apply_default_scroll or configuration.default_anchor == "top":
            return
        document_h = float(self._content.frame().size.height)
        viewport = float(self._content_h)
        maximum = max(0.0, document_h - viewport)
        offset = maximum / 2.0 if configuration.default_anchor == "center" else maximum
        clip = self._scroll_view.contentView()
        clip.scrollToPoint_((0.0, offset))
        self._scroll_view.reflectScrolledClipView_(clip)
        self._did_apply_default_scroll = True

    def _build_container(self, view: View, parent: "NSView", origin: Point,
                         size: Size) -> None:
        """Build a container.

        The whole document view shares a single global coordinate space (it is
        Flipped, matching aUI).  Every child therefore goes directly into the
        ``parent`` at its global frame; the outer NSScrollView clips anything
        that overflows the visible viewport.
        """
        if isinstance(view, NavigationSplitView):
            self._add_split_surfaces(view, parent)
        form_style_value = style_value(view, "form_style", FormStyle.AUTOMATIC)
        group_style_value = style_value(view, "group_box_style", GroupBoxStyle.AUTOMATIC)
        list_style_value = style_value(view, "list_style", ListStyle.AUTOMATIC)
        if ((isinstance(view, Form) and form_style_value != FormStyle.COLUMNS)
                or isinstance(view, Section)
                or (isinstance(view, GroupBox) and group_style_value != GroupBoxStyle.PLAIN)
                or (isinstance(view, List) and list_style_value in {
                    ListStyle.GROUPED, ListStyle.INSET_GROUPED, ListStyle.SIDEBAR
                })):
            self._add_card(view, parent)
        children = view.z_ordered_children() if isinstance(view, LayoutContainer) else [
            child for _, child in z_ordered(view.children())
        ]
        for child in children:
            if isinstance(view, List):
                if id(child) not in self._frames:
                    continue
            self._build(child, parent, origin, size)

    def _add_split_surfaces(self, view: NavigationSplitView, parent: "NSView") -> None:
        """Add semantic sidebar/content surfaces and native separators."""
        pos, size = self._frames[id(view)]
        widths = view.column_widths(size.width)
        cursor = pos.x
        visible_count = 0
        visible_total = sum(width > 0 for width in widths)
        for index, width in enumerate(widths):
            if width <= 0.0: continue
            if visible_count:
                cursor += view.divider_width
            surface = NSBox.alloc().initWithFrame_(
                NSMakeRect(cursor, pos.y, width, size.height)
            )
            surface.setBoxType_(NSBoxCustom)
            surface.setTitlePosition_(NSNoTitle)
            surface.setBorderWidth_(0)
            if index == 0:
                try:
                    surface.setFillColor_(NSColor.controlBackgroundColor())
                except Exception:
                    surface.setFillColor_(NSColor.windowBackgroundColor())
            else:
                surface.setFillColor_(NSColor.windowBackgroundColor())
            parent.addSubview_(surface)
            cursor += width
            visible_count += 1
            if visible_count < visible_total and view.divider_width > 0:
                divider = NSBox.alloc().initWithFrame_(
                    NSMakeRect(cursor, pos.y, max(1.0, view.divider_width), size.height)
                )
                divider.setBoxType_(NSBoxCustom)
                divider.setFillColor_(NSColor.separatorColor())
                divider.setBorderWidth_(0)
                parent.addSubview_(divider)
                # Keep the visual separator hairline-thin while offering a
                # comfortable native drag target, like NSSplitView.
                split_key = getattr(view, "_backend_split_key", None)
                if _SplitDividerView is not None and split_key is not None:
                    hit_width = 10.0
                    hit = _SplitDividerView.alloc().initWithBackend_splitKey_leftColumn_(
                        self, split_key, index
                    )
                    hit.setFrame_(NSMakeRect(
                        cursor - (hit_width - view.divider_width) / 2.0,
                        pos.y, hit_width, size.height,
                    ))
                    parent.addSubview_(hit)

    def _add_inspector_surface(self, view: InspectorView, parent: "NSView") -> None:
        pos, size = self._frames[id(view)]
        main, panel = view.column_widths(size.width)
        if panel <= 0:
            return
        x = pos.x if main == 0 else pos.x + main + view.divider_width
        surface = NSBox.alloc().initWithFrame_(NSMakeRect(x, pos.y, panel, size.height))
        surface.setBoxType_(NSBoxCustom)
        surface.setTitlePosition_(NSNoTitle)
        surface.setBorderWidth_(0)
        surface.setFillColor_(self._ns_color(view.background) if view.background
                              else NSColor.controlBackgroundColor())
        parent.addSubview_(surface)
        if main > 0:
            divider = NSBox.alloc().initWithFrame_(NSMakeRect(
                x - view.divider_width, pos.y, view.divider_width, size.height
            ))
            divider.setBoxType_(NSBoxCustom)
            divider.setTitlePosition_(NSNoTitle)
            divider.setBorderWidth_(0)
            divider.setFillColor_(NSColor.separatorColor())
            parent.addSubview_(divider)

    def _add_control_group_surface(self, view: ControlGroup, parent: "NSView") -> None:
        pos, size = self._frames[id(view)]
        style = style_value(view, "control_group_style", ControlGroupStyle.AUTOMATIC)
        box = NSBox.alloc().initWithFrame_(NSMakeRect(
            pos.x - 3, pos.y - 2, size.width + 6, size.height + 4
        ))
        box.setBoxType_(NSBoxCustom); box.setTitlePosition_(NSNoTitle)
        box.setCornerRadius_(7.0); box.setBorderWidth_(0.5)
        box.setBorderColor_(NSColor.separatorColor())
        if style == ControlGroupStyle.NAVIGATION:
            box.setFillColor_(NSColor.clearColor())
        else:
            box.setFillColor_(NSColor.controlBackgroundColor())
        parent.addSubview_(box)

    def _add_card(self, view: View, parent: "NSView") -> None:
        """Draw a grouped, adaptive surface behind form-like containers."""
        pos, size = self._frames[id(view)]
        if size.width <= 0 or size.height <= 0:
            return
        card = NSBox.alloc().initWithFrame_(
            NSMakeRect(pos.x, pos.y, size.width, size.height)
        )
        card.setBoxType_(NSBoxCustom)
        card.setTitlePosition_(NSNoTitle)
        card.setCornerRadius_(self.theme.card_radius)
        try:
            card.setFillColor_(NSColor.controlBackgroundColor())
            card.setBorderColor_(NSColor.separatorColor().colorWithAlphaComponent_(
                self.theme.card_border_alpha
            ))
            card.setBorderWidth_(0.5)
            # NSBox provides the native rounded surface and border itself.
            # Deliberately do not add a CALayer shadow: CGColor conversion
            # produces ObjCPointerWarning on several supported PyObjC builds.
        except Exception:
            pass
        # Called before the container's children, so ordinary AppKit subview
        # ordering naturally keeps the card behind its controls.
        parent.addSubview_(card)

    def _build_modified(self, view: _ModifiedContent, parent: "NSView",
                        origin: Point, size: Size) -> None:
        """Render a modifier wrapper: apply visuals, then draw the content."""
        frame = self._frames.get(id(view)) or (origin, size)
        x, y = frame[0].x, frame[0].y
        w, h = frame[1].width, frame[1].height
        mod = view._modifier
        before = list(parent.subviews())

        if isinstance(mod, (SheetModifier, AlertModifier, SnackBarModifier)):
            self._pending_presentations.append(mod)
        if isinstance(mod, ToolbarModifier):
            self._pending_toolbar = mod

        # Decorative modifiers that must be drawn behind / around the content.
        if isinstance(mod, HiddenModifier):
            return  # hidden content is skipped entirely

        if isinstance(mod, BackgroundModifier):
            box = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
            box.setBoxType_(NSBoxCustom)
            box.setFillColor_(self._ns_color(mod.color))
            box.setBorderColor_(NSColor.clearColor())
            box.setBorderWidth_(0)
            box.setTitlePosition_(NSNoTitle)
            parent.addSubview_(box)

        if isinstance(mod, ListRowBackgroundModifier):
            box = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
            box.setBoxType_(NSBoxCustom); box.setTitlePosition_(NSNoTitle)
            box.setFillColor_(self._ns_color(mod.color)); box.setBorderWidth_(0)
            parent.addSubview_(box)

        if isinstance(mod, MaterialBackgroundModifier):
            from AppKit import (
                NSVisualEffectBlendingModeWithinWindow, NSVisualEffectStateActive,
                NSVisualEffectView,
            )
            material = NSVisualEffectView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
            material.setBlendingMode_(NSVisualEffectBlendingModeWithinWindow)
            material.setState_(NSVisualEffectStateActive)
            material_values = {
                Material.ULTRA_THIN: 1,
                Material.THIN: 2,
                Material.REGULAR: 8,
                Material.THICK: 9,
                Material.ULTRA_THICK: 10,
                Material.SIDEBAR: 7,
            }
            try:
                material.setMaterial_(material_values[mod.material])
            except Exception:
                pass
            parent.addSubview_(material)

        if isinstance(mod, BorderModifier):
            box = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
            box.setBoxType_(NSBoxCustom)
            box.setFillColor_(NSColor.clearColor())
            box.setBorderColor_(self._ns_color(mod.color))
            box.setBorderWidth_(mod.width)
            box.setTitlePosition_(NSNoTitle)
            parent.addSubview_(box)

        if isinstance(mod, ListRowSeparatorModifier) and mod.visibility != "hidden":
            separator = NSBox.alloc().initWithFrame_(NSMakeRect(x, y + max(0, h - 1), w, 1))
            separator.setBoxType_(NSBoxCustom); separator.setTitlePosition_(NSNoTitle)
            separator.setFillColor_(NSColor.separatorColor()); separator.setBorderWidth_(0)
            parent.addSubview_(separator)

        if isinstance(mod, CornerRadiusModifier):
            try:
                box = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
                box.setBoxType_(NSBoxCustom)
                box.setCornerRadius_(mod.radius)
                box.setFillColor_(NSColor.clearColor())
                box.setBorderColor_(NSColor.clearColor())
                parent.addSubview_(box)
            except Exception:
                pass

        if isinstance(mod, OpacityModifier):
            pass  # applied to the native descendants after content is built

        # Draw the content (its own frame exists from _walk).
        self._build(view.body(), parent, origin, size)
        if isinstance(mod, BadgeModifier):
            badge_text = str(mod.value)
            badge_width = max(18.0, len(badge_text) * 7.0 + 10.0)
            badge_frame = NSMakeRect(x + max(0.0, w - badge_width), y,
                                     badge_width, min(18.0, h))
            badge_surface = NSBox.alloc().initWithFrame_(badge_frame)
            badge_surface.setBoxType_(NSBoxCustom)
            badge_surface.setTitlePosition_(NSNoTitle)
            badge_surface.setFillColor_(self._ns_color(self.theme.accent))
            badge_surface.setBorderColor_(NSColor.clearColor())
            badge_surface.setBorderWidth_(0)
            badge_surface.setCornerRadius_(9.0)
            parent.addSubview_(badge_surface)
            badge = NSTextField.labelWithString_(badge_text)
            badge.setFrame_(badge_frame)
            badge.setAlignment_(1)
            badge.setTextColor_(NSColor.whiteColor())
            parent.addSubview_(badge)
        if isinstance(mod, PopoverModifier):
            added = [item for item in parent.subviews()
                     if all(item is not old for old in before)]
            if added:
                self._pending_presentations.append((mod, added[-1]))
        if isinstance(mod, (FileImporterModifier, FileExporterModifier)):
            if bool(mod.is_presented.value):
                self._pending_file_dialogs.append(mod)
        if isinstance(mod, OverlayModifier):
            self._build(mod.overlay, parent, origin, size)
        if isinstance(mod, ShadowModifier):
            for native in (item for item in parent.subviews()
                           if all(item is not old for old in before)):
                try:
                    native.setWantsLayer_(True)
                    layer = native.layer()
                    # Leave the layer's default shadow colour in place.  On
                    # several supported PyObjC builds converting NSColor to
                    # CGColor produces an ObjCPointerWarning for every view.
                    layer.setShadowOpacity_(mod.color.alpha)
                    layer.setShadowRadius_(mod.radius)
                    layer.setShadowOffset_((mod.x, -mod.y))
                except Exception:
                    pass
        if isinstance(mod, SemanticModifier):
            added = [item for item in parent.subviews()
                     if all(item is not old for old in before)]
            if mod.key == "help":
                for native in added:
                    try:
                        native.setToolTip_(mod.value)
                    except Exception:
                        pass
        if isinstance(mod, AccessibilityModifier):
            added = [item for item in parent.subviews()
                     if all(item is not old for old in before)]
            for native in added:
                try:
                    if isinstance(mod, AccessibilityLabelModifier):
                        native.setAccessibilityLabel_(mod.label)
                    elif isinstance(mod, AccessibilityHintModifier):
                        native.setAccessibilityHelp_(mod.hint)
                    elif isinstance(mod, AccessibilityValueModifier):
                        native.setAccessibilityValue_(mod.value)
                    elif isinstance(mod, AccessibilityHiddenModifier):
                        native.setAccessibilityElement_(not mod.hidden)
                    elif isinstance(mod, IdentifierModifier):
                        native.setAccessibilityIdentifier_(mod.identifier)
                    elif isinstance(mod, SortPriorityModifier):
                        native.setAccessibilitySortPriority_(mod.priority)
                    elif isinstance(mod, InputLabelsModifier):
                        native.setAccessibilityUserInputLabels_(list(mod.labels))
                    elif isinstance(mod, HeadingModifier):
                        native.setAccessibilityRoleDescription_(f"Heading level {mod.level}")
                except Exception:
                    pass
        if isinstance(mod, GestureModifier) and isinstance(mod.gesture, GestureHandler):
            base = mod.gesture.gesture
            if isinstance(base, (TapGesture, SpatialTapGesture)):
                added = [item for item in parent.subviews()
                         if all(item is not old for old in before)]
                for native in added:
                    try:
                        from AppKit import NSClickGestureRecognizer
                        recognizer = NSClickGestureRecognizer.alloc().initWithTarget_action_(
                            self, "gestureRecognized:"
                        )
                        recognizer.setNumberOfClicksRequired_(base.count)
                        native.addGestureRecognizer_(recognizer)
                        self._gesture_handlers[id(recognizer)] = mod.gesture
                    except Exception:
                        pass
        if isinstance(mod, ContextMenuModifier):
            menu = self._native_context_menu(mod.resolve())
            for native in (item for item in parent.subviews()
                           if all(item is not old for old in before)):
                try: native.setMenu_(menu)
                except Exception: pass
        if isinstance(mod, ListRowEditingModifier) and mod.kind == "swipe_actions":
            actions, _edge, _allows_full_swipe = mod.value
            menu = Menu("Row Actions", [
                Button(action.title, action.action,
                       role="destructive" if action.role == "destructive" else None)
                for action in actions
            ])
            native_menu = self._native_context_menu(menu)
            for native in (item for item in parent.subviews()
                           if all(item is not old for old in before)):
                try: native.setMenu_(native_menu)
                except Exception: pass
        if isinstance(mod, HitTestingModifier) and not mod.enabled:
            for native in (item for item in parent.subviews()
                           if all(item is not old for old in before)):
                try:
                    if isinstance(native, NSControl): native.setEnabled_(False)
                except Exception: pass
        if isinstance(mod, HoverEffectModifier):
            for native in (item for item in parent.subviews()
                           if all(item is not old for old in before)):
                try:
                    native.setWantsLayer_(True)
                    if mod.effect == "lift": native.layer().setShadowOpacity_(0.18)
                except Exception: pass
        if isinstance(mod, OnHoverModifier):
            for native in (item for item in parent.subviews()
                           if all(item is not old for old in before)):
                try:
                    from AppKit import (NSTrackingActiveAlways, NSTrackingArea,
                                       NSTrackingInVisibleRect, NSTrackingMouseEnteredAndExited)
                    options = NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways | NSTrackingInVisibleRect
                    area = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
                        native.bounds(), options, self, None
                    )
                    native.addTrackingArea_(area)
                    self._hover_handlers[id(area)] = mod.action
                except Exception: pass
        if isinstance(mod, SensoryFeedbackModifier):
            key = mod.key or mod.feedback.kind
            previous = self._sensory_values.get(key, mod.trigger)
            self._sensory_values[key] = mod.trigger
            changed = previous != mod.trigger
            if changed and (mod.condition is None or mod.condition(previous, mod.trigger)):
                self._perform_sensory_feedback(mod.feedback)
        if isinstance(mod, OpacityModifier):
            for native in (item for item in parent.subviews()
                           if all(item is not old for old in before)):
                try:
                    native.setAlphaValue_(mod.opacity)
                except Exception:
                    pass
        if isinstance(mod, (ScaleEffectModifier, RotationEffectModifier,
                            Rotation3DEffectModifier, FilterModifier,
                            BlendModeModifier, CompositingModifier,
                            ClipModifier, MaskModifier)):
            added = [item for item in parent.subviews()
                     if all(item is not old for old in before)]
            self._apply_rendering_modifier(mod, added)
        if isinstance(mod, FocusedModifier):
            if isinstance(mod, DefaultFocusModifier):
                mod.activate_if_needed()
            added = [item for item in parent.subviews()
                     if all(item is not old for old in before)]
            controls = [item for item in added if isinstance(item, NSControl)]
            if controls:
                self._focus_controls.append((controls[-1], mod))
        if isinstance(mod, KeyboardShortcutModifier):
            added = [item for item in parent.subviews()
                     if all(item is not old for old in before)]
            controls = [item for item in added if isinstance(item, NSButton)]
            if controls:
                shortcut = mod.shortcut
                controls[-1].setKeyEquivalent_(shortcut.key)
                try:
                    from AppKit import (
                        NSEventModifierFlagCommand, NSEventModifierFlagControl,
                        NSEventModifierFlagOption, NSEventModifierFlagShift,
                    )
                    flags = {"command": NSEventModifierFlagCommand,
                             "option": NSEventModifierFlagOption,
                             "control": NSEventModifierFlagControl,
                             "shift": NSEventModifierFlagShift}
                    mask = 0
                    for name in shortcut.modifiers:
                        mask |= flags[name]
                    controls[-1].setKeyEquivalentModifierMask_(mask)
                except Exception:
                    pass
        if isinstance(mod, (OnSubmitModifier, SubmitLabelModifier)):
            added = [item for item in parent.subviews()
                     if all(item is not old for old in before)]
            controls = [item for item in added if isinstance(item, NSControl)]
            if controls:
                self._submit_controls.append((controls[-1], mod))
                if isinstance(mod, SubmitLabelModifier):
                    try:
                        controls[-1].setToolTip_(f"Return key: {mod.label}")
                    except Exception:
                        pass
        if isinstance(mod, OnAppearModifier):
            self._appear_actions.append(mod.action)
        elif isinstance(mod, OnDisappearModifier):
            self._disappear_actions.append(mod.action)

    def _apply_rendering_modifier(self, modifier, native_views) -> None:
        """Apply SwiftUI-like visual effects with Core Animation/Core Image."""
        import math
        for native in native_views:
            try:
                native.setWantsLayer_(True)
                layer = native.layer()
                if isinstance(modifier, ScaleEffectModifier):
                    from Quartz import CATransform3DMakeScale
                    layer.setTransform_(CATransform3DMakeScale(modifier.x, modifier.y, 1.0))
                elif isinstance(modifier, RotationEffectModifier):
                    from Quartz import CATransform3DMakeRotation
                    layer.setTransform_(CATransform3DMakeRotation(
                        math.radians(modifier.degrees), 0.0, 0.0, 1.0
                    ))
                elif isinstance(modifier, Rotation3DEffectModifier):
                    from Quartz import CATransform3DMakeRotation
                    x, y, z = modifier.axis
                    transform = CATransform3DMakeRotation(math.radians(modifier.degrees), x, y, z)
                    try:
                        transform.m34 = -modifier.perspective
                    except Exception:
                        pass
                    layer.setTransform_(transform)
                elif isinstance(modifier, FilterModifier):
                    from Quartz import CIFilter
                    names = {
                        "blur": ("CIGaussianBlur", "inputRadius", modifier.amount),
                        "brightness": ("CIColorControls", "inputBrightness", modifier.amount),
                        "contrast": ("CIColorControls", "inputContrast", modifier.amount),
                        "saturation": ("CIColorControls", "inputSaturation", modifier.amount),
                        "grayscale": ("CIColorControls", "inputSaturation", 1.0 - modifier.amount),
                        "hueRotation": ("CIHueAdjust", "inputAngle", math.radians(modifier.amount)),
                    }
                    name, key, value = names[modifier.kind]
                    effect = CIFilter.filterWithName_(name)
                    effect.setDefaults()
                    effect.setValue_forKey_(value, key)
                    layer.setFilters_([effect])
                elif isinstance(modifier, BlendModeModifier):
                    filters = {
                        "multiply": "multiplyBlendMode", "screen": "screenBlendMode",
                        "overlay": "overlayBlendMode", "darken": "darkenBlendMode",
                        "lighten": "lightenBlendMode", "difference": "differenceBlendMode",
                        "exclusion": "exclusionBlendMode",
                    }
                    layer.setCompositingFilter_(filters.get(modifier.mode))
                elif isinstance(modifier, CompositingModifier):
                    layer.setShouldRasterize_(modifier.drawing)
                    if modifier.drawing:
                        layer.setRasterizationScale_(2.0)
                    layer.setOpaque_(modifier.opaque)
                elif isinstance(modifier, (ClipModifier, MaskModifier)):
                    layer.setMasksToBounds_(True)
                    if isinstance(modifier, ClipModifier) and modifier.shape is not None:
                        radius = getattr(modifier.shape, "corner_radius_value", 0.0)
                        if radius:
                            layer.setCornerRadius_(radius)
            except Exception:
                # Older macOS versions may not expose every Core Image filter.
                pass

    def _run_appear_actions(self) -> None:
        actions, self._appear_actions = self._appear_actions, []
        for action in actions:
            action()

    @_IBAction
    def gestureRecognized_(self, sender) -> None:  # pragma: no cover - native callback
        handler = self._gesture_handlers.get(id(sender))
        if handler is None:
            return
        try:
            location = sender.locationInView_(sender.view())
            handler.emit_ended(Point(float(location.x), float(location.y)))
        except Exception:
            handler.emit_ended(Point())
        self._refresh_content()

    def _native_context_menu(self, menu: Menu):
        native_menu = NSMenu.alloc().initWithTitle_(menu.title)
        for item in menu.items:
            if isinstance(item, MenuDivider):
                native_menu.addItem_(NSMenuItem.separatorItem()); continue
            native = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                item.title, "menuItemSelected:", item.shortcut.key if item.shortcut else ""
            )
            native.setTarget_(self._bridge); native.setEnabled_(item.is_enabled)
            native_menu.addItem_(native); self._menu_items.append((native, item))
        return native_menu

    def mouseEntered_(self, event) -> None:  # pragma: no cover
        action = self._hover_handlers.get(id(event.trackingArea()))
        if action: action(True)

    def mouseExited_(self, event) -> None:  # pragma: no cover
        action = self._hover_handlers.get(id(event.trackingArea()))
        if action: action(False)

    @staticmethod
    def _perform_sensory_feedback(feedback) -> None:  # pragma: no cover
        try:
            from AppKit import (
                NSHapticFeedbackManager, NSHapticFeedbackPatternGeneric,
                NSHapticFeedbackPerformanceTimeNow,
            )
            NSHapticFeedbackManager.defaultPerformer().performFeedbackPattern_performanceTime_(
                NSHapticFeedbackPatternGeneric, NSHapticFeedbackPerformanceTimeNow
            )
        except Exception:
            try:
                from AppKit import NSBeep
                NSBeep()
            except Exception:
                pass

    def _run_disappear_actions(self) -> None:
        actions, self._disappear_actions = self._disappear_actions, []
        for action in actions:
            action()

    def windowWillClose_(self, _notification) -> None:  # pragma: no cover
        self._scene_phase = ScenePhase.BACKGROUND
        self._control_active_state = ControlActiveState.INACTIVE
        if self._timeline_timer is not None:
            self._timeline_timer.cancel()
            self._timeline_timer = None
        for handle in self._animation_handles.values():
            handle.cancel()
        self._animation_handles.clear()
        cancel_tasks(self._tasks)
        self._tasks.clear()
        for cancel in self._observation_cancels:
            cancel()
        self._observation_cancels = []
        if self._on_close is not None:
            callback, self._on_close = self._on_close, None
            callback()
        if self._on_window_close is not None:
            callback, self._on_window_close = self._on_window_close, None
            callback()

    def windowShouldClose_(self, _sender) -> bool:  # pragma: no cover
        return not self._interactive_dismiss_disabled

    def windowDidBecomeKey_(self, _notification) -> None:  # pragma: no cover
        self._set_window_environment(ScenePhase.ACTIVE, ControlActiveState.KEY)

    def windowDidResignKey_(self, _notification) -> None:  # pragma: no cover
        self._set_window_environment(ScenePhase.INACTIVE, ControlActiveState.INACTIVE)

    def windowDidMiniaturize_(self, _notification) -> None:  # pragma: no cover
        self._set_window_environment(ScenePhase.BACKGROUND, ControlActiveState.INACTIVE)

    def windowDidDeminiaturize_(self, _notification) -> None:  # pragma: no cover
        self._set_window_environment(ScenePhase.ACTIVE, ControlActiveState.ACTIVE)

    def windowDidResize_(self, _notification) -> None:  # pragma: no cover
        if self._window is None:
            return
        size = self._window.contentView().frame().size
        width, height = float(size.width), float(size.height)
        self._content_h = height
        if self._content is not None:
            current = self._content.frame().size
            self._content.setFrame_(NSMakeRect(0, 0, width, max(height, float(current.height))))
            self._refresh_content()
        if self._on_resize is not None:
            self._on_resize(Size(width, height))

    def _set_window_environment(self, phase: ScenePhase,
                                active_state: ControlActiveState) -> None:
        changed = (phase != self._scene_phase or active_state != self._control_active_state)
        self._scene_phase = phase
        self._control_active_state = active_state
        if changed and self._on_focus_changed is not None:
            self._on_focus_changed(phase == ScenePhase.ACTIVE)
        if changed:
            self._observed_value_changed()

    def _apply_pending_focus(self) -> None:  # pragma: no cover - UI behavior
        for control, modifier in self._focus_controls:
            if modifier.is_focused:
                try:
                    self._window.makeFirstResponder_(control)
                except Exception:
                    pass
                return

    def _focus_modifier_for_control(self, control):
        for native, modifier in self._focus_controls:
            if native is control:
                return modifier
        return None

    def controlTextDidBeginEditing_(self, notification) -> None:  # pragma: no cover
        modifier = self._focus_modifier_for_control(notification.object())
        if modifier is not None:
            modifier.activate()

    def controlTextDidEndEditing_(self, notification) -> None:  # pragma: no cover
        modifier = self._focus_modifier_for_control(notification.object())
        if modifier is not None:
            modifier.deactivate()

    def _present_pending(self) -> None:  # pragma: no cover - UI behavior
        """Present active modal modifiers after their host window is visible."""
        pending = list(self._pending_presentations)
        self._pending_presentations.clear()
        for pending_item in pending:
            anchor = None
            if isinstance(pending_item, tuple):
                modifier, anchor = pending_item
            else:
                modifier = pending_item
            if not bool(modifier.is_presented.wrapped_value):
                continue
            if isinstance(modifier, AlertModifier):
                self._present_alert(modifier)
            elif isinstance(modifier, SnackBarModifier):
                self._present_snack_bar(modifier)
            elif isinstance(modifier, SheetModifier):
                self._present_sheet(modifier)
            elif isinstance(modifier, PopoverModifier) and anchor is not None:
                self._present_popover(modifier, anchor)
        file_dialogs, self._pending_file_dialogs = self._pending_file_dialogs, []
        for modifier in file_dialogs:
            if not bool(modifier.is_presented.value):
                continue
            if isinstance(modifier, FileImporterModifier):
                self._present_file_importer(modifier)
            else:
                self._present_file_exporter(modifier)

    def _present_file_importer(self, modifier: FileImporterModifier) -> None:  # pragma: no cover
        from AppKit import NSModalResponseOK, NSOpenPanel
        from pathlib import Path

        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(modifier.allows_multiple)
        if modifier.allowed_extensions:
            panel.setAllowedFileTypes_(list(modifier.allowed_extensions))

        def completed(response) -> None:
            if response == NSModalResponseOK:
                paths = tuple(Path(str(url.path())) for url in panel.URLs())
                result = FileDialogResult(paths)
            else:
                result = FileDialogResult(cancelled=True)
            modifier.complete(result)
            self._refresh_content()

        panel.beginSheetModalForWindow_completionHandler_(self._window, completed)

    def _present_file_exporter(self, modifier: FileExporterModifier) -> None:  # pragma: no cover
        from AppKit import NSModalResponseOK, NSSavePanel
        from pathlib import Path

        panel = NSSavePanel.savePanel()
        panel.setNameFieldStringValue_(modifier.default_filename)

        def completed(response) -> None:
            if response != NSModalResponseOK:
                result = FileDialogResult(cancelled=True)
            else:
                path = Path(str(panel.URL().path()))
                try:
                    modifier.write_to(path)
                    result = FileDialogResult((path,))
                except Exception as exc:
                    result = FileDialogResult(error=exc)
            modifier.complete(result)
            self._refresh_content()

        panel.beginSheetModalForWindow_completionHandler_(self._window, completed)

    def _present_snack_bar(self, modifier: SnackBarModifier) -> None:  # pragma: no cover
        if self._content is None:
            return
        key = id(modifier.is_presented)
        if key in self._presented_snack_bars:
            return
        width = min(420.0, max(220.0, float(self._content.frame().size.width) - 40.0))
        height = 42.0
        x = (float(self._content.frame().size.width) - width) / 2.0
        y = max(12.0, float(self._content.frame().size.height) - height - 20.0)
        box = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, width, height))
        box.setBoxType_(NSBoxCustom); box.setTitlePosition_(NSNoTitle); box.setBorderWidth_(0)
        box.setFillColor_(NSColor.controlBackgroundColor())
        self._content.addSubview_(box)
        action_width = 84.0 if modifier.action is not None else 0.0
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(12, 10, width - 24 - action_width, 22))
        label.setStringValue_(modifier.message); label.setBezeled_(False); label.setDrawsBackground_(False)
        label.setEditable_(False); label.setSelectable_(False); label.setTextColor_(NSColor.labelColor())
        box.addSubview_(label)
        if modifier.action is not None:
            button = NSButton.alloc().initWithFrame_(NSMakeRect(width - action_width - 8, 7, action_width, 28))
            button.setTitle_(modifier.action.title); button.setBordered_(False)
            button.setTarget_(self._bridge); button.setAction_("snackBarAction:")
            box.addSubview_(button)
            self._snack_bar_actions.append((button, modifier))
        self._presented_snack_bars[key] = box

        def dismiss(_timer=None):
            self._presented_snack_bars.pop(key, None)
            modifier.is_presented.wrapped_value = False
            self._refresh_content()
        try:
            from Foundation import NSTimer
            NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
                modifier.duration, False,
                dismiss,
            )
        except Exception:
            pass

    @_IBAction
    def snackBarAction_(self, sender) -> None:  # pragma: no cover - UI callback
        for button, modifier in self._snack_bar_actions:
            if button is sender:
                modifier.is_presented.wrapped_value = False
                modifier.action.action()
                self._refresh_content()
                return

    def _present_alert(self, modifier: AlertModifier) -> None:  # pragma: no cover
        from AppKit import NSAlert, NSAlertFirstButtonReturn, NSAlertStyleCritical
        alert = NSAlert.alloc().init()
        alert.setMessageText_(modifier.title)
        alert.setInformativeText_(modifier.message)
        if any(button.role == "destructive" for button in modifier.buttons):
            alert.setAlertStyle_(NSAlertStyleCritical)
        for button in modifier.buttons:
            alert.addButtonWithTitle_(button.title)

        def completed(response) -> None:
            index = int(response) - int(NSAlertFirstButtonReturn)
            if 0 <= index < len(modifier.buttons):
                action = modifier.buttons[index].action
                if action is not None:
                    action()
            modifier.is_presented.wrapped_value = False

        alert.beginSheetModalForWindow_completionHandler_(self._window, completed)

    def _present_sheet(self, modifier: SheetModifier) -> None:  # pragma: no cover
        import inspect
        holder = {}

        def dismiss() -> None:
            child_window = holder.get("window")
            if child_window is not None:
                if holder.get("background_enabled"):
                    child = holder.get("backend")
                    if child is not None:
                        child._interactive_dismiss_disabled = False
                    child_window.performClose_(None)
                else:
                    self._window.endSheet_(child_window)

        def make_sheet_view():
            parameters = inspect.signature(modifier.content).parameters
            return modifier.content(dismiss) if parameters else modifier.content()

        configuration = modifier.configuration
        parent_size = self._window.contentView().frame().size
        if modifier.full_screen:
            width, height = float(parent_size.width), float(parent_size.height)
        else:
            width, height = modifier.size.width, modifier.size.height
            if configuration.detents:
                selected = (configuration.selection.wrapped_value
                            if configuration.selection is not None else None)
                detent = selected if selected in configuration.detents else configuration.detents[0]
                height = detent.resolve(float(parent_size.height))
                if configuration.selection is not None and selected not in configuration.detents:
                    configuration.selection.wrapped_value = detent
        child = AppKitBackend(make_sheet_view, theme=self.theme)
        child._interactive_dismiss_disabled = configuration.interactive_dismiss_disabled
        child._build_window(int(width), int(height), modifier.title)
        if configuration.corner_radius is not None:
            try:
                child._window.contentView().setWantsLayer_(True)
                child._window.contentView().layer().setCornerRadius_(configuration.corner_radius)
                child._window.contentView().layer().setMasksToBounds_(True)
            except Exception:
                pass
        if configuration.drag_indicator == "visible":
            try:
                indicator = NSBox.alloc().initWithFrame_(NSMakeRect(
                    max(0.0, width / 2.0 - 18.0), 6.0, 36.0, 4.0
                ))
                indicator.setBoxType_(NSBoxCustom)
                indicator.setBorderWidth_(0)
                indicator.setFillColor_(NSColor.tertiaryLabelColor())
                indicator.setCornerRadius_(2.0)
                child._window.contentView().addSubview_(indicator)
            except Exception:
                pass
        holder["window"] = child._window
        holder["backend"] = child
        holder["background_enabled"] = configuration.background_interaction == "enabled"
        self._presented_backends.append(child)

        def completed(_response) -> None:
            modifier.is_presented.wrapped_value = False
            if child in self._presented_backends:
                self._presented_backends.remove(child)

        if configuration.background_interaction == "enabled":
            from AppKit import NSWindowAbove
            child._on_window_close = lambda: completed(None)
            self._window.addChildWindow_ordered_(child._window, NSWindowAbove)
            child._window.makeKeyAndOrderFront_(None)
        else:
            self._window.beginSheet_completionHandler_(child._window, completed)

    def _present_popover(self, modifier: PopoverModifier, anchor) -> None:  # pragma: no cover
        import inspect
        from AppKit import (
            NSMaxXEdge, NSMaxYEdge, NSMinXEdge, NSMinYEdge, NSPopover,
            NSPopoverBehaviorTransient, NSViewController,
        )
        holder = {}

        def dismiss() -> None:
            popover = holder.get("popover")
            if popover is not None:
                popover.close()
                modifier.is_presented.wrapped_value = False

        def make_content():
            parameters = inspect.signature(modifier.content).parameters
            return modifier.content(dismiss) if parameters else modifier.content()

        child = AppKitBackend(make_content, theme=self.theme)
        child._build_window(int(modifier.size.width), int(modifier.size.height), "")
        controller = NSViewController.alloc().init()
        controller.setView_(child._window.contentView())
        popover = NSPopover.alloc().init()
        popover.setContentViewController_(controller)
        popover.setContentSize_((modifier.size.width, modifier.size.height))
        popover.setBehavior_(NSPopoverBehaviorTransient)
        popover.setDelegate_(self._bridge)
        holder["popover"] = popover
        self._popovers.append((popover, modifier, child))
        edges = {
            "top": NSMinYEdge,
            "bottom": NSMaxYEdge,
            "leading": NSMinXEdge,
            "trailing": NSMaxXEdge,
        }
        popover.showRelativeToRect_ofView_preferredEdge_(
            anchor.bounds(), anchor, edges[modifier.edge]
        )

    def popoverDidClose_(self, notification) -> None:  # pragma: no cover
        closed = notification.object()
        for popover, modifier, child in list(self._popovers):
            if popover is closed:
                modifier.is_presented.wrapped_value = False
                self._popovers.remove((popover, modifier, child))
                return

    def _install_pending_toolbar(self) -> None:  # pragma: no cover - UI behavior
        """Install toolbar items in the native macOS title bar."""
        for controller in self._toolbar_accessories:
            try:
                index = list(self._window.titlebarAccessoryViewControllers()).index(controller)
                self._window.removeTitlebarAccessoryViewControllerAtIndex_(index)
            except Exception:
                pass
        self._toolbar_accessories = []
        self._toolbar_items = []
        modifier = self._pending_toolbar
        if modifier is None or not modifier.items:
            return
        from AppKit import (
            NSLayoutAttributeRight,
            NSStackView,
            NSTitlebarAccessoryViewController,
            NSUserInterfaceLayoutOrientationHorizontal,
        )
        buttons = []
        toolbar_width = 0.0
        for item in modifier.items:
            button_width = 30.0 if item.system_name else max(56.0, len(item.label) * 8.0 + 22.0)
            button = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, button_width, 26))
            button.setTitle_("" if item.system_name else item.label)
            button.setBordered_(True)
            button.setEnabled_(item.is_enabled)
            button.setToolTip_(item.label)
            if item.system_name:
                try:
                    from AppKit import NSImage
                    image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                        item.system_name, item.label
                    )
                    if image is not None:
                        button.setImage_(image)
                except Exception:
                    pass
            button.setTarget_(self._bridge)
            button.setAction_("toolbarItemPressed:")
            self._apply_shortcut(button, item.shortcut)
            self._toolbar_items.append((button, item))
            buttons.append(button)
            toolbar_width += button_width
        stack = NSStackView.stackViewWithViews_(buttons)
        stack.setOrientation_(NSUserInterfaceLayoutOrientationHorizontal)
        stack.setSpacing_(6.0)
        stack.setFrame_(NSMakeRect(0, 0, toolbar_width + 6.0 * max(0, len(buttons) - 1), 28.0))
        controller = NSTitlebarAccessoryViewController.alloc().init()
        controller.setView_(stack)
        controller.setFullScreenMinHeight_(28.0)
        controller.setLayoutAttribute_(NSLayoutAttributeRight)
        self._window.addTitlebarAccessoryViewController_(controller)
        self._toolbar_accessories.append(controller)

    def _apply_shortcut(self, control, shortcut) -> None:
        if shortcut is None:
            return
        control.setKeyEquivalent_(shortcut.key.lower())
        try:
            from AppKit import (
                NSEventModifierFlagCommand, NSEventModifierFlagControl,
                NSEventModifierFlagOption, NSEventModifierFlagShift,
            )
            flags = 0
            mapping = {
                "command": NSEventModifierFlagCommand,
                "option": NSEventModifierFlagOption,
                "control": NSEventModifierFlagControl,
                "shift": NSEventModifierFlagShift,
            }
            for name in shortcut.modifiers:
                flags |= mapping[name]
            control.setKeyEquivalentModifierMask_(flags)
        except Exception:
            pass

    @_IBAction
    def toolbarItemPressed_(self, sender) -> None:  # pragma: no cover
        for control, item in self._toolbar_items:
            if control is sender and item.is_enabled:
                item.action()
                self._refresh_content()
                return

    def _add_menu(self, view: Menu, parent: "NSView", x: float, y: float,
                  w: float, h: float) -> None:
        popup = NSPopUpButton.alloc().initWithFrame_(
            NSMakeRect(x, y, max(72.0, w), max(24.0, h))
        )
        popup.removeAllItems()
        popup.addItemWithTitle_(view.title)
        popup.menu().addItem_(NSMenuItem.separatorItem())
        for item in view.items:
            if isinstance(item, MenuDivider):
                popup.menu().addItem_(NSMenuItem.separatorItem())
                continue
            native = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                item.title, "menuItemSelected:", item.shortcut.key if item.shortcut else ""
            )
            native.setTarget_(self._bridge)
            native.setEnabled_(item.is_enabled)
            if item.role == "destructive":
                try:
                    native.setAttributedTitle_(self._destructive_menu_title(item.title))
                except Exception:
                    pass
            if item.shortcut is not None:
                self._apply_shortcut(native, item.shortcut)
            popup.menu().addItem_(native)
            self._menu_items.append((native, item))
        popup.setEnabled_(is_enabled(view))
        parent.addSubview_(popup)

    def _destructive_menu_title(self, title: str):
        from Foundation import NSAttributedString
        from AppKit import NSForegroundColorAttributeName
        return NSAttributedString.alloc().initWithString_attributes_(
            title, {NSForegroundColorAttributeName: NSColor.systemRedColor()}
        )

    @_IBAction
    def menuItemSelected_(self, sender) -> None:  # pragma: no cover
        for native, item in self._menu_items:
            if native is sender and item.is_enabled:
                item.action()
                self._refresh_content()
                return

    def _add_table(self, view: Table, parent: "NSView", x: float, y: float,
                   w: float, h: float) -> None:
        from AppKit import NSTableColumn, NSTableView
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        scroll.setHasVerticalScroller_(True)
        scroll.setHasHorizontalScroller_(len(view.visible_columns) > 3)
        table = NSTableView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        table.setRowHeight_(view.row_height)
        table.setUsesAlternatingRowBackgroundColors_(view.alternating_rows)
        table.setAllowsEmptySelection_(True)
        table.setAllowsMultipleSelection_(view.allows_multiple_selection)
        for definition in view.visible_columns:
            column = NSTableColumn.alloc().initWithIdentifier_(definition.key)
            column.headerCell().setStringValue_(definition.title)
            fallback = max(80.0, w / max(1, len(view.visible_columns)))
            column.setMinWidth_(definition.minimum_width)
            if definition.maximum_width != float("inf"):
                column.setMaxWidth_(definition.maximum_width)
            column.setWidth_(definition.resolved_width(fallback))
            table.addTableColumn_(column)
        table.setDataSource_(self._bridge)
        table.setDelegate_(self._bridge)
        scroll.setDocumentView_(table)
        self._tables.append((table, view))
        if view.selection is not None:
            selected = view.selection.wrapped_value
            selected_values = set(selected or ()) if view.allows_multiple_selection else {selected}
            from Foundation import NSMutableIndexSet
            indexes = NSMutableIndexSet.indexSet()
            for index, row in enumerate(view.displayed_rows):
                if view.row_id(row) in selected_values:
                    indexes.addIndex_(index)
            if indexes.count():
                table.selectRowIndexes_byExtendingSelection_(indexes, False)
        parent.addSubview_(scroll)
        if not view.displayed_rows:
            placeholder = NSTextField.labelWithString_(view.empty_message)
            placeholder.setFrame_(NSMakeRect(x + 16, y + max(8, h / 2 - 10),
                                             max(40, w - 32), 20))
            placeholder.setAlignment_(1)
            placeholder.setTextColor_(NSColor.secondaryLabelColor())
            parent.addSubview_(placeholder)

    def _add_outline_group(self, view: OutlineGroup, parent: "NSView", x: float,
                           y: float, w: float, h: float) -> None:
        from AppKit import NSOutlineView, NSTableColumn
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        scroll.setHasVerticalScroller_(True)
        outline = NSOutlineView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        column = NSTableColumn.alloc().initWithIdentifier_("outline")
        column.setWidth_(w)
        outline.addTableColumn_(column)
        outline.setOutlineTableColumn_(column)
        outline.setHeaderView_(None)
        outline.setIndentationPerLevel_(view.indentation)
        outline.setAllowsMultipleSelection_(view.allows_multiple_selection)
        outline.setDataSource_(self._bridge); outline.setDelegate_(self._bridge)
        self._outlines.append((outline, view))
        scroll.setDocumentView_(outline)
        parent.addSubview_(scroll)
        outline.reloadData()
        for key in view.expanded.wrapped_value:
            outline.expandItem_(key)
        if view.selection is not None:
            selected = view.selection.wrapped_value
            values = set(selected or ()) if view.allows_multiple_selection else {selected}
            from Foundation import NSMutableIndexSet
            indexes = NSMutableIndexSet.indexSet()
            for row in range(outline.numberOfRows()):
                if outline.itemAtRow_(row) in values: indexes.addIndex_(row)
            if indexes.count(): outline.selectRowIndexes_byExtendingSelection_(indexes, False)

    def _outline_model(self, native):
        for outline, model in self._outlines:
            if outline is native: return model
        return None

    def outlineView_numberOfChildrenOfItem_(self, outline, item):  # pragma: no cover
        model = self._outline_model(outline)
        if model is None: return 0
        parent = model.item_for_key(item) if item is not None else None
        return len(model.children_for(parent) if parent is not None else model.data)

    def outlineView_child_ofItem_(self, outline, index, item):  # pragma: no cover
        model = self._outline_model(outline)
        parent = model.item_for_key(item) if item is not None else None
        values = model.children_for(parent) if parent is not None else model.data
        return model.key_for(values[index])

    def outlineView_isItemExpandable_(self, outline, item):  # pragma: no cover
        model = self._outline_model(outline)
        node = model.item_for_key(item) if model is not None else None
        return bool(node is not None and model.children_for(node))

    def outlineView_objectValueForTableColumn_byItem_(self, outline, _column,
                                                       item):  # pragma: no cover
        model = self._outline_model(outline)
        node = model.item_for_key(item) if model is not None else None
        if node is None: return ""
        content = model._content_for(node)
        return str(getattr(content, "display_content", getattr(content, "title", item)))

    def outlineViewSelectionDidChange_(self, notification) -> None:  # pragma: no cover
        outline = notification.object(); model = self._outline_model(outline)
        if model is None or model.selection is None: return
        indexes = outline.selectedRowIndexes()
        values = {outline.itemAtRow_(row) for row in range(outline.numberOfRows())
                  if indexes.containsIndex_(row)}
        model.selection.wrapped_value = values if model.allows_multiple_selection else (
            next(iter(values)) if values else None
        )
        self._refresh_content()

    def outlineViewItemDidExpand_(self, notification) -> None:  # pragma: no cover
        self._outline_expansion_changed(notification, True)

    def outlineViewItemDidCollapse_(self, notification) -> None:  # pragma: no cover
        self._outline_expansion_changed(notification, False)

    def _outline_expansion_changed(self, notification, expanded: bool) -> None:
        outline = notification.object(); model = self._outline_model(outline)
        if model is None: return
        info = notification.userInfo()
        try:
            from AppKit import NSOutlineViewItemKey
            item = info.objectForKey_(NSOutlineViewItemKey)
        except Exception:
            item = info.get("NSObject")
        values = set(model.expanded.wrapped_value)
        values.add(item) if expanded else values.discard(item)
        model.expanded.wrapped_value = values
        self._refresh_content()

    def _table_model(self, native_table):
        for table, model in self._tables:
            if table is native_table:
                return model
        return None

    def numberOfRowsInTableView_(self, table_view):  # pragma: no cover
        model = self._table_model(table_view)
        return len(model.displayed_rows) if model is not None else 0

    def tableView_objectValueForTableColumn_row_(self, table_view, column, row):  # pragma: no cover
        model = self._table_model(table_view)
        if model is None or not 0 <= row < len(model.displayed_rows):
            return ""
        identifier = str(column.identifier())
        definition = next((item for item in model.columns if item.key == identifier), None)
        return str(definition.get_value(model.displayed_rows[row])) if definition else ""

    def tableViewSelectionDidChange_(self, notification) -> None:  # pragma: no cover
        table_view = notification.object()
        model = self._table_model(table_view)
        if model is None or model.selection is None:
            return
        if model.allows_multiple_selection:
            indexes = table_view.selectedRowIndexes()
            selected = {model.row_id(row) for index, row in enumerate(model.displayed_rows)
                        if indexes.containsIndex_(index)}
            model.selection.wrapped_value = selected
        elif table_view.selectedRow() >= 0:
            model.select_row(int(table_view.selectedRow()))
        # Table selection is an interactive state transition: refresh sibling
        # views even when the view factory itself does not directly read the
        # selection Binding.
        self._refresh_content()

    def tableView_didClickTableColumn_(self, table_view, column) -> None:  # pragma: no cover
        model = self._table_model(table_view)
        if model is not None:
            model.set_sort(str(column.identifier()))
            self._refresh_content()

    def _build_frame(self, view: _Frame, parent: "NSView", origin: Point,
                     size: Size) -> None:
        """frame(): a fixed-size box around the content (aligned).

        The whole document view shares one global coordinate space (it is
        Flipped, matching aUI), so the content is placed directly into the
        parent — no nested host that would offset coordinates.
        """
        self._build(view._content, parent, origin, size)

    def _build_leaf(self, view: View, parent: "NSView", x: float, y: float, size: Size) -> None:
        w, h = size.width, size.height
        if isinstance(view, Text):
            self._add_text(view, parent, x, y, w)
            return
        if isinstance(view, AsyncImage):
            self._add_async_image(view, parent, x, y, w, h)
            return
        if isinstance(view, SettingsLink):
            view.connect(self._settings_opener)
            self._add_button(view, parent, x, y, w, h)
            return
        if isinstance(view, ShareLink):
            self._add_share_link(view, parent, x, y, w, h)
            return
        if isinstance(view, PasteButton):
            view.connect(self._pasteboard_text)
            self._add_button(view, parent, x, y, w, h)
            return
        if isinstance(view, WindowLink):
            view.connect(self._window_opener)
            self._add_button(view, parent, x, y, w, h)
            return
        if isinstance(view, DismissWindowLink):
            view.connect(self._dismiss_window_action)
            self._add_button(view, parent, x, y, w, h)
            return
        if isinstance(view, Button):
            self._add_button(view, parent, x, y, w, h)
            return
        if isinstance(view, SearchField):
            self._add_searchfield(view, parent, x, y, w, h)
            return
        if isinstance(view, TextEditor):
            self._add_texteditor(view, parent, x, y, w, h)
            return
        if isinstance(view, TextField):
            self._add_textfield(view, parent, x, y, w, h, secure=False)
            return
        if isinstance(view, SecureField):
            self._add_textfield(view, parent, x, y, w, h, secure=True)
            return
        if isinstance(view, Toggle):
            self._add_switch(view, parent, x, y, w, h)
            return
        if isinstance(view, Slider):
            self._add_slider(view, parent, x, y, w, h)
            return
        if isinstance(view, Picker) and style_value(view, "picker_style") == PickerStyle.SEGMENTED:
            self._add_segmented(view, parent, x, y, w, h)
            return
        if isinstance(view, Picker):
            self._add_picker(view, parent, x, y, w, h)
            return
        if isinstance(view, Stepper):
            self._add_stepper(view, parent, x, y, w, h)
            return
        if isinstance(view, DatePicker):
            self._add_datepicker(view, parent, x, y, w, h)
            return
        if isinstance(view, ColorPicker):
            self._add_colorpicker(view, parent, x, y, w, h)
            return
        if isinstance(view, Gauge):
            self._add_gauge(view, parent, x, y, w, h)
            return
        if isinstance(view, ProgressView):
            self._add_progress(view, parent, x, y, w, h)
            return
        if isinstance(view, Divider):
            self._add_divider(view, parent, x, y, w)
            return
        if isinstance(view, Image):
            self._add_image(view, parent, x, y, w, h)
            return
        if isinstance(view, Label):
            self._add_label_badge(view, parent, x, y, w, h)
            return
        if isinstance(view, Link):
            self._add_link(view, parent, x, y, w, h)
            return
        if isinstance(view, Shape):
            self._add_shape(view, parent, x, y, w, h)
            return
        if isinstance(view, Menu):
            self._add_menu(view, parent, x, y, w, h)
            return
        if isinstance(view, Table):
            self._add_table(view, parent, x, y, w, h)
            return
        if isinstance(view, Gradient):
            self._add_gradient(view, parent, x, y, w, h)
            return
        if isinstance(view, Canvas):
            self._add_canvas(view, parent, x, y, w, h)
            return

    def _add_canvas(self, view: Canvas, parent: "NSView", x: float, y: float,
                    w: float, h: float) -> None:
        """Render recorded Canvas paths through CAShapeLayer."""
        try:
            from Quartz import (
                CAShapeLayer, CGPathAddCurveToPoint, CGPathAddEllipseInRect,
                CGPathAddLineToPoint, CGPathAddQuadCurveToPoint, CGPathAddRect,
                CGPathCloseSubpath, CGPathCreateMutable, CGPathMoveToPoint,
            )
        except ImportError:
            self._add_canvas_surface(view, parent, x, y, w, h)
            return
        host = NSView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        host.setWantsLayer_(True)
        host.layer().setOpaque_(view.opaque)
        context = view.resolve(Size(w, h))
        caps = {"butt": "butt", "round": "round", "square": "square"}
        joins = {"miter": "miter", "round": "round", "bevel": "bevel"}
        for command in context.commands:
            path = CGPathCreateMutable()
            for item in command.path.commands:
                if item[0] == "move": CGPathMoveToPoint(path, None, item[1].x, item[1].y)
                elif item[0] == "line": CGPathAddLineToPoint(path, None, item[1].x, item[1].y)
                elif item[0] == "quad": CGPathAddQuadCurveToPoint(path, None, item[2].x, item[2].y, item[1].x, item[1].y)
                elif item[0] == "curve": CGPathAddCurveToPoint(path, None, item[2].x, item[2].y, item[3].x, item[3].y, item[1].x, item[1].y)
                elif item[0] == "close": CGPathCloseSubpath(path)
                elif item[0] in ("rect", "ellipse"):
                    rect = item[1]
                    native_rect = ((rect.origin.x, rect.origin.y), (rect.size.width, rect.size.height))
                    if item[0] == "rect": CGPathAddRect(path, None, native_rect)
                    else: CGPathAddEllipseInRect(path, None, native_rect)
            layer = CAShapeLayer.layer()
            layer.setPath_(path)
            color = self._ns_color(command.color).CGColor()
            if command.operation == "fill":
                layer.setFillColor_(color)
                layer.setStrokeColor_(NSColor.clearColor().CGColor())
            else:
                style = command.style
                layer.setFillColor_(NSColor.clearColor().CGColor())
                layer.setStrokeColor_(color)
                layer.setLineWidth_(style.line_width)
                layer.setLineCap_(caps[style.line_cap])
                layer.setLineJoin_(joins[style.line_join])
                layer.setMiterLimit_(style.miter_limit)
                if style.dash:
                    layer.setLineDashPattern_(list(style.dash))
                    layer.setLineDashPhase_(style.dash_phase)
            host.layer().addSublayer_(layer)
        parent.addSubview_(host)

    def _add_canvas_surface(self, view: Canvas, parent: "NSView", x: float, y: float,
                            w: float, h: float) -> None:
        """Keep Canvas examples usable with the documented Cocoa-only extra."""
        commands = view.resolve(Size(w, h)).commands
        color = commands[0].color if commands else Color.clear
        surface = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        surface.setBoxType_(NSBoxCustom)
        surface.setTitlePosition_(NSNoTitle)
        surface.setFillColor_(self._ns_color(color))
        surface.setBorderColor_(NSColor.separatorColor())
        surface.setBorderWidth_(1.0)
        surface.setCornerRadius_(8.0)
        parent.addSubview_(surface)
        label = NSTextField.labelWithString_("Canvas preview · install pyobjc-framework-Quartz for vector paths")
        label.setFrame_(NSMakeRect(x + 10.0, y + max(4.0, h / 2.0 - 9.0),
                                   max(1.0, w - 20.0), 18.0))
        label.setTextColor_(NSColor.secondaryLabelColor())
        label.setAlignment_(1)
        parent.addSubview_(label)

    # -- Individual control factories --------------------------------------
    def _add_text(self, view: Text, parent: "NSView", x: float, y: float, w: float) -> None:
        """Text: a non-editable label sized by the layout engine.

        AppKit's y-origin is bottom-left, so the frame is flipped vertically.
        The label height is the laid-out line height, not a fixed 24px.
        """
        frame = self._frames.get(id(view))
        h = frame[1].height if frame else 20.0
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        label.setStringValue_(view.display_content)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(text_style_value(view, "text_selection", False))
        label.setTextColor_(self._ns_color(view.effective_color) if view.effective_color
                            else NSColor.labelColor())
        font = view.effective_font
        label.setFont_(self._ns_font(Font(view.effective_font_size,
                                          font.weight, font.family)))
        if style_value(view, "header_prominence") == "increased":
            label.setFont_(NSFont.boldSystemFontOfSize_(view.effective_font_size * 1.12))
        label.setLineBreakMode_(NSLineBreakByWordWrapping)
        label.setMaximumNumberOfLines_(view.line_limit or 0)
        try:
            from AppKit import (
                NSCenterTextAlignment, NSHeadTruncatingLineBreakMode,
                NSLeftTextAlignment, NSMiddleTruncatingLineBreakMode,
                NSRightTextAlignment, NSTailTruncatingLineBreakMode,
            )
            alignments = {"leading": NSLeftTextAlignment, "center": NSCenterTextAlignment,
                          "trailing": NSRightTextAlignment}
            label.setAlignment_(alignments.get(
                text_style_value(view, "multiline_alignment"), NSLeftTextAlignment
            ))
            truncations = {"head": NSHeadTruncatingLineBreakMode,
                           "middle": NSMiddleTruncatingLineBreakMode,
                           "tail": NSTailTruncatingLineBreakMode}
            mode = text_style_value(view, "truncation_mode")
            if mode:
                label.setLineBreakMode_(truncations[mode])
            label.setAllowsDefaultTighteningForTruncation_(
                text_style_value(view, "allows_tightening", False)
            )
            if text_style_value(view, "monospaced_digit", False):
                label.setFont_(NSFont.monospacedDigitSystemFontOfSize_weight_(
                    view._font.size, self._ns_weight(view._font.weight)
                ))
            styles = getattr(view, "_resolved_text_style", {})
            if view.attributed_string is not None or any(
                key in styles for key in ("kerning", "tracking", "baseline_offset")
            ):
                from Foundation import NSMutableAttributedString, NSMakeRange
                from AppKit import NSBaselineOffsetAttributeName, NSKernAttributeName, NSLinkAttributeName
                value = NSMutableAttributedString.alloc().initWithString_(view.display_content)
                full = NSMakeRange(0, len(view.display_content))
                spacing = styles.get("kerning", styles.get("tracking"))
                if spacing is not None:
                    value.addAttribute_value_range_(NSKernAttributeName, spacing, full)
                if "baseline_offset" in styles:
                    value.addAttribute_value_range_(NSBaselineOffsetAttributeName,
                                                    styles["baseline_offset"], full)
                if view.attributed_string is not None:
                    for run in view.attributed_string.runs:
                        run_range = NSMakeRange(run.start, run.end - run.start)
                        if "link" in run.attributes:
                            value.addAttribute_value_range_(NSLinkAttributeName,
                                                            run.attributes["link"], run_range)
                label.setAttributedStringValue_(value)
        except Exception:
            pass
        self._controls[id(view)] = label
        parent.addSubview_(label)

    def _ns_font(self, font) -> "NSFont":
        if font is None:
            return NSFont.systemFontOfSize_(13)
        weight = getattr(font, "weight", "regular") or "regular"
        size = float(getattr(font, "size", 13) or 13)
        return NSFont.systemFontOfSize_weight_(size, self._ns_weight(weight))

    def _ns_weight(self, weight: str):
        try:
            from AppKit import (
                NSFontWeightBold,
                NSFontWeightMedium,
                NSFontWeightRegular,
                NSFontWeightSemibold,
            )
            return {
                "regular": NSFontWeightRegular,
                "medium": NSFontWeightMedium,
                "semibold": NSFontWeightSemibold,
                "bold": NSFontWeightBold,
            }.get(weight, NSFontWeightRegular)
        except Exception:
            return getattr(NSFont, "systemFontOfSize_")(13).fontName()

    def _ns_color(self, color: Color) -> "NSColor":
        if color is None:
            return NSColor.blackColor()
        return NSColor.colorWithSRGBRed_green_blue_alpha_(
            color.red, color.green, color.blue, color.alpha
        )

    def _add_button(self, view: Button, parent: "NSView", x: float, y: float,
                    w: float, h: float) -> None:
        """Button: native rounded control with semantic SwiftUI-like accents."""
        bw = max(48.0, w)
        bh = max(24.0, h)
        btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(x, y, bw, bh)
        )
        btn.setTitle_("" if isinstance(view, IconButton) else view.title)
        btn.setButtonType_(NSButtonTypeMomentaryPushIn)
        btn.setBezelStyle_(NSBezelStyleRounded)
        btn.setEnabled_(is_enabled(view))
        btn.setTarget_(self._bridge)
        btn.setAction_("buttonPressed:")
        if isinstance(view, IconButton):
            try:
                from AppKit import NSImage
                image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                    view.system_name, view.label
                )
                if image is not None:
                    btn.setImage_(image)
                btn.setToolTip_(view.label)
            except Exception:
                pass
        tint_color = style_value(view, "tint")
        if tint_color is not None:
            r, g, b = tint_color.red, tint_color.green, tint_color.blue
        elif view.role == "destructive":
            r, g, b = 0.85, 0.24, 0.30
        elif view.role == "cancel":
            r, g, b = 0.47, 0.50, 0.55
        else:
            r, g, b = self.theme.accent.red, self.theme.accent.green, self.theme.accent.blue
        accent = NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, 1.0)
        try:
            style = style_value(view, "button_style", ButtonStyle.AUTOMATIC)
            if style in (ButtonStyle.PLAIN, ButtonStyle.BORDERLESS, ButtonStyle.LINK):
                btn.setBordered_(False)
            elif style == ButtonStyle.BORDERED_PROMINENT:
                btn.setBezelColor_(accent)
            sizes = {ControlSize.MINI: 2, ControlSize.SMALL: 1,
                     ControlSize.REGULAR: 0, ControlSize.LARGE: 3,
                     ControlSize.EXTRA_LARGE: 3}
            btn.setControlSize_(sizes.get(style_value(view, "control_size"), 0))
            btn.setContentTintColor_(accent)
            btn.setWantsLayer_(True)
            btn.layer().setCornerRadius_(self.theme.control_radius)
        except Exception:
            pass
        self._controls[id(view)] = btn
        parent.addSubview_(btn)

    @_IBAction
    def buttonPressed_(self, sender) -> None:  # pragma: no cover - UI callback
        for v, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(v)
                if isinstance(view, Button) and is_enabled(view):
                    view.action()
                    if not isinstance(view, (SettingsLink, WindowLink, DismissWindowLink, ShareLink)):
                        self._refresh_content()
                return

    def _add_share_link(self, view: ShareLink, parent: "NSView", x: float, y: float,
                        w: float, h: float) -> None:
        self._add_button(view, parent, x, y, w, h)
        native = self._controls[id(view)]
        view.connect(lambda items, anchor=native, source=view: self._show_share_picker(
            source, anchor
        ))

    def _show_share_picker(self, view: ShareLink, anchor) -> None:  # pragma: no cover
        from pathlib import Path
        from AppKit import NSMinYEdge, NSSharingServicePicker
        from Foundation import NSURL

        values = []
        if view.subject:
            values.append(view.subject)
        if view.message:
            values.append(view.message)
        for item in view.items:
            if isinstance(item, Path):
                values.append(NSURL.fileURLWithPath_(str(item.expanduser())))
            elif isinstance(item, str) and "://" in item:
                values.append(NSURL.URLWithString_(item) or item)
            else:
                values.append(str(item))
        picker = NSSharingServicePicker.alloc().initWithItems_(values)
        picker.showRelativeToRect_ofView_preferredEdge_(anchor.bounds(), anchor, NSMinYEdge)
        self._sharing_pickers.append(picker)

    @staticmethod
    def _pasteboard_text() -> Optional[str]:  # pragma: no cover
        from AppKit import NSPasteboard, NSPasteboardTypeString
        return NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString)

    def _refresh_content(self) -> None:  # pragma: no cover - UI callback
        """Rebuild the native document after structural state/navigation changes."""
        if self._content is None:
            return
        old_view = self._view
        old_controls = dict(self._controls)
        old_frames = dict(self._frames)
        width = float(self._content.frame().size.width)
        viewport_h = float(self._content_h)
        self._refresh_scheduled = False
        self._view = self._make_view()
        self._apply_window_color_scheme(self._view)
        self._pending_presentations = []
        self._pending_file_dialogs = []
        self._pending_toolbar = None
        proposal_h = viewport_h if isinstance(self._view, NavigationSplitView) else float("inf")
        natural = self._view.size_that_fits(Size(width, proposal_h))
        content_h = max(viewport_h, natural.height if natural.height != float("inf") else viewport_h)
        self._layout(self._view, width, content_h)
        content_h = max(content_h, self._content_height)
        self._content.setFrame_(NSMakeRect(0, 0, width, content_h))
        animation, self._pending_animation = self._pending_animation, None
        if old_view is not None and self._update_native_tree(
                old_view, self._view, old_controls, old_frames, animation):
            self._configure_scroll_view(self._view)
            self._apply_configured_scroll(self._view)
            run_on_change(self._view, self._change_values)
            self._install_timeline_timer()
            self._present_pending()
            return
        self._run_disappear_actions()
        for handle in self._animation_handles.values():
            handle.cancel()
        self._animation_handles.clear()
        for subview in list(self._content.subviews()):
            subview.removeFromSuperview()
        self._controls.clear()
        self._navigation_rail_buttons.clear()
        self._snack_bar_actions.clear()
        self._presented_snack_bars.clear()
        self._gesture_handlers.clear()
        self._hover_handlers.clear()
        self._menu_items.clear()
        self._tables.clear()
        self._outlines.clear()
        self._focus_controls.clear()
        self._submit_controls.clear()
        self._appear_actions = []
        self._disappear_actions = []
        self._build(self._view, self._content, Point(0, 0), Size(width, content_h))
        self._configure_scroll_view(self._view)
        self._apply_configured_scroll(self._view)
        self._install_pending_toolbar()
        self._apply_pending_focus()
        self._run_appear_actions()
        run_on_change(self._view, self._change_values)
        self._install_timeline_timer()
        self._present_pending()

    def _install_timeline_timer(self) -> None:
        """Advance TimelineView through the AppKit main-queue scheduler."""
        if self._view is None:
            return
        if self._timeline_timer is not None:
            self._timeline_timer.cancel()
            self._timeline_timer = None
        timelines = [node for node in self._view.flatten() if isinstance(node, TimelineView)]
        if not timelines:
            return
        delays = {"live": 1.0 / 30.0, "seconds": 1.0, "minutes": 60.0}
        delay = min(delays[node.cadence] for node in timelines)

        def tick(nodes=timelines):
            self._timeline_timer = None
            if self._window is None:
                return
            for node in nodes:
                node.tick()
            self._observed_value_changed()

        self._timeline_timer = self._schedule_animation_frame(delay, tick)

    def _update_native_tree(self, old_view: View, new_view: View,
                            old_controls: dict[int, object], old_frames=None,
                            animation=None) -> bool:
        """Update compatible native leaves in place, or request a safe rebuild."""
        if (self._gesture_handlers or self._hover_handlers or self._submit_controls
                or self._focus_controls or self._tables or self._outlines):
            return False
        old_nodes, new_nodes = snapshot(old_view), snapshot(new_view)
        shared_paths = old_nodes.keys() & new_nodes.keys()
        structural_change = old_nodes.keys() != new_nodes.keys()
        if (not structural_change and any(
                type(old_nodes[path].view) is not type(new_nodes[path].view)
                for path in shared_paths)):
            return False
        if structural_change and any(
            isinstance(node.view, _ModifiedContent)
            and not isinstance(node.view._modifier,
                               (IDModifier, TransitionModifier, ContentTransitionModifier,
                                SymbolEffectModifier, MatchedGeometryEffectModifier))
            for node in tuple(old_nodes.values()) + tuple(new_nodes.values())
        ):
            return False
        for path in shared_paths:
            before, after = old_nodes[path].view, new_nodes[path].view
            if isinstance(before, Picker) and style_value(before, "picker_style") != style_value(
                    after, "picker_style"):
                return False
            if isinstance(before, ProgressView) and style_value(
                    before, "progress_view_style") != style_value(after, "progress_view_style"):
                return False
        old_paths = {id(node.view): path for path, node in old_nodes.items()}
        supported = (Text, Button, TextField, SecureField, SearchField,
                     TextEditor, Toggle, Slider, Picker, Stepper, DatePicker,
                     ColorPicker, Gauge, ProgressView)
        non_native = (Spacer, EmptyView)
        containers = (HStack, VStack, ZStack, Grid, GridRow, ResponsiveRow, NavigationSplitView,
                      Group, GroupBox, Section, Form, List, ScrollView, TabView,
                      NavigationStack, DisclosureGroup, ForEach, AnyView,
                      ViewThatFits, LazyHGrid, LazyVGrid, LayoutContainer)
        for node in tuple(old_nodes.values()) + tuple(new_nodes.values()):
            if (not node.view.children()
                    and not isinstance(node.view, supported + non_native + containers)):
                return False
        new_matched = {}
        old_source_keys = set()
        for candidate_path, node in old_nodes.items():
            if isinstance(node.view, supported):
                modifier = self._matched_geometry_for_path(old_nodes, candidate_path)
                if modifier is not None and modifier.is_source:
                    old_source_keys.add(modifier.key)
        for candidate_path, node in new_nodes.items():
            if isinstance(node.view, supported):
                modifier = self._matched_geometry_for_path(new_nodes, candidate_path)
                if modifier is not None:
                    current = new_matched.get(modifier.key)
                    if (current is None or (
                            self._matched_geometry_for_path(
                                new_nodes, current).is_source and not modifier.is_source)):
                        new_matched[modifier.key] = candidate_path
        retained = []
        removed = []
        claimed_new_paths = set()
        for old_id, native in old_controls.items():
            path = old_paths.get(old_id)
            if path is None:
                return False
            same_leaf = new_nodes.get(path)
            if (same_leaf is None or not isinstance(same_leaf.view, supported)
                    or type(same_leaf.view) is not type(old_nodes[path].view)):
                matched = self._matched_geometry_for_path(old_nodes, path)
                eligible = (matched is not None and (
                    matched.is_source or matched.key not in old_source_keys))
                destination = new_matched.get(matched.key) if eligible else None
                if destination is not None and destination not in claimed_new_paths:
                    new_leaf = new_nodes[destination].view
                    if type(new_leaf) is type(old_nodes[path].view):
                        destination_modifier = self._matched_geometry_for_path(
                            new_nodes, destination)
                        retained.append((path, destination, new_leaf, native,
                                         destination_modifier))
                        claimed_new_paths.add(destination)
                        continue
                removed.append((path, native))
                continue
            new_leaf = same_leaf.view
            retained.append((path, path, new_leaf, native, None))
            claimed_new_paths.add(path)
        retained_paths = {new_path for _, new_path, _, _, _ in retained}
        inserted = [node.view for path, node in new_nodes.items()
                    if path not in old_nodes and path not in retained_paths
                    and not node.view.children()
                    and isinstance(node.view, supported)]
        for path, node in new_nodes.items():
            if (not node.view.children() and isinstance(node.view, supported)
                    and path in old_nodes and path not in retained_paths):
                return False

        remapped: dict[int, object] = {}
        for path, native in removed:
            active = self._animation_handles.pop(id(native), None)
            if active is not None:
                active.cancel()
            old_leaf = old_nodes[path].view
            leaf_animation = resolved_animation(old_leaf, animation)
            frame = (old_frames or {}).get(id(old_leaf))
            transition = self._transition_for_path(old_nodes, path)
            if leaf_animation is not None and frame is not None and transition is not None:
                self._animate_native_transition(
                    native, frame, transition, leaf_animation, inserting=False,
                    completion=native.removeFromSuperview)
            else:
                native.removeFromSuperview()
        for old_path, path, view, native, matched in retained:
            before = old_nodes[old_path].view
            leaf_animation = resolved_animation(view, animation)
            self._update_native_leaf(view, native)
            if (leaf_animation is not None and isinstance(before, Text)
                    and isinstance(view, Text)
                    and before.display_content != view.display_content):
                content_transition = self._content_transition_for_path(new_nodes, path)
                if content_transition not in (None, ContentTransition.IDENTITY):
                    self._animate_native_text_content(
                        native, before.display_content, view.display_content,
                        content_transition, leaf_animation)
            frame = self._frames.get(id(view))
            animated_frame = False
            if frame is not None:
                origin, size = frame
                old_id = id(old_nodes[old_path].view)
                previous = (old_frames or {}).get(old_id)
                if leaf_animation is not None and previous is not None and previous != frame:
                    self._animate_native_matched_frame(
                        native, previous, frame, leaf_animation, matched)
                    animated_frame = True
                else:
                    native.setFrame_(NSMakeRect(origin.x, origin.y, size.width, size.height))
            old_symbol = self._symbol_effect_for_path(old_nodes, path)
            new_symbol = self._symbol_effect_for_path(new_nodes, path)
            motion_disabled = animations_disabled(view)
            if motion_disabled or (old_symbol is not None and new_symbol is None):
                active = self._animation_handles.pop(id(native), None)
                if active is not None:
                    active.cancel()
                if hasattr(native, "setAlphaValue_"):
                    native.setAlphaValue_(1.0)
            symbol_changed = (new_symbol is not None and (
                old_symbol is None or old_symbol.effect != new_symbol.effect
                or old_symbol.value != new_symbol.value
                or old_symbol.repeating != new_symbol.repeating))
            if not animated_frame and symbol_changed and not motion_disabled:
                symbol_animation = leaf_animation or Animation.ease_in_out(0.35)
                if new_symbol.repeating:
                    symbol_animation = symbol_animation.repeat_forever(False)
                self._animate_native_symbol(
                    native, frame, new_symbol.effect, symbol_animation)
            remapped[id(view)] = native
        self._controls = remapped
        for view in inserted:
            frame = self._frames.get(id(view))
            if frame is None:
                return False
            origin, size = frame
            self._build_leaf(view, self._content, origin.x, origin.y, size)
            path = next((item for item, node in new_nodes.items() if node.view is view), None)
            transition = self._transition_for_path(new_nodes, path) if path is not None else None
            symbol = self._symbol_effect_for_path(new_nodes, path) if path is not None else None
            native = self._controls.get(id(view))
            if native is not None:
                leaf_animation = resolved_animation(view, animation)
                if leaf_animation is not None and transition is not None:
                    self._animate_native_transition(native, frame, transition, leaf_animation)
                elif symbol is not None and not animations_disabled(view):
                    symbol_animation = leaf_animation or Animation.ease_in_out(0.35)
                    if symbol.repeating:
                        symbol_animation = symbol_animation.repeat_forever(False)
                    self._animate_native_symbol(
                        native, frame, symbol.effect, symbol_animation)
        return True

    @staticmethod
    def _transition_for_path(nodes, path):
        for length in range(len(path), 0, -1):
            node = nodes.get(path[:length])
            if (node is not None and isinstance(node.view, _ModifiedContent)
                    and isinstance(node.view._modifier, TransitionModifier)):
                return node.view._modifier.transition
        return None

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

    @staticmethod
    def _matched_geometry_for_path(nodes, path):
        for length in range(len(path), 0, -1):
            node = nodes.get(path[:length])
            if (node is not None and isinstance(node.view, _ModifiedContent)
                    and isinstance(node.view._modifier, MatchedGeometryEffectModifier)):
                return node.view._modifier
        return None

    def _update_native_leaf(self, view: View, native) -> None:
        if isinstance(view, Text):
            native.setStringValue_(view.display_content)
            native.setTextColor_(self._ns_color(view.effective_color) if view.effective_color
                                 else NSColor.labelColor())
            font = view.effective_font
            native.setFont_(self._ns_font(Font(view.effective_font_size,
                                               font.weight, font.family)))
        elif isinstance(view, Button):
            native.setTitle_(view.title)
            native.setEnabled_(is_enabled(view))
        elif isinstance(view, (TextField, SecureField, SearchField, TextEditor)):
            native.setStringValue_(str(view.text.wrapped_value))
            native.setPlaceholderString_(view.placeholder)
            native.setEnabled_(is_enabled(view))
            native.setEditable_(is_enabled(view))
        elif isinstance(view, Toggle):
            native.setState_(1 if view.is_on and bool(view.is_on.wrapped_value) else 0)
            native.setEnabled_(is_enabled(view))
        elif isinstance(view, Slider):
            lo, hi = view.range
            native.setMinValue_(lo)
            native.setMaxValue_(hi)
            if view.value is not None:
                native.setDoubleValue_(float(view.value.wrapped_value))
            native.setEnabled_(is_enabled(view))
        elif isinstance(view, Stepper):
            lo, hi = view.range
            native.setMinValue_(lo)
            native.setMaxValue_(hi)
            native.setIncrement_(view.step)
            if view.value is not None:
                native.setDoubleValue_(float(view.value.wrapped_value))
            native.setEnabled_(is_enabled(view))
        elif isinstance(view, Picker):
            selected = view.selection.wrapped_value if view.selection else None
            if style_value(view, "picker_style") == PickerStyle.SEGMENTED:
                native.setSegmentCount_(len(view.options))
                for index, option in enumerate(view.options):
                    native.setLabel_forSegment_(str(option), index)
                    native.setSelected_forSegment_(option == selected, index)
            else:
                native.removeAllItems()
                for option in view.options:
                    native.addItemWithTitle_(str(option))
                if selected is not None:
                    native.selectItemWithTitle_(str(selected))
            native.setEnabled_(is_enabled(view))
        elif isinstance(view, DatePicker):
            from AppKit import (NSDatePickerElementFlagHourMinuteSecond,
                                NSDatePickerElementFlagYearMonthDay)
            flags = (NSDatePickerElementFlagHourMinuteSecond
                     if view.displayed_components == "hourAndMinute"
                     else NSDatePickerElementFlagYearMonthDay)
            native.setDatePickerElements_(flags)
            if view.selection is not None and isinstance(view.selection.wrapped_value, datetime):
                from Foundation import NSDate
                seconds = (view.selection.wrapped_value - datetime(2001, 1, 1)).total_seconds()
                native.setDateValue_(NSDate.dateWithTimeIntervalSinceReferenceDate_(seconds))
            native.setEnabled_(is_enabled(view))
        elif isinstance(view, ColorPicker):
            if view.selection is not None and isinstance(view.selection.wrapped_value, Color):
                native.setColor_(self._ns_color(view.selection.wrapped_value))
            native.setEnabled_(is_enabled(view))
        elif isinstance(view, Gauge):
            lo, hi = view.range
            native.setMinValue_(lo)
            native.setMaxValue_(hi)
            native.setDoubleValue_(max(lo, min(hi, view.raw_value)))
        elif isinstance(view, ProgressView):
            if view.value is None:
                native.setIndeterminate_(True)
                native.startAnimation_(None)
            else:
                native.stopAnimation_(None)
                native.setIndeterminate_(False)
                native.setDoubleValue_(float(max(0.0, min(1.0, view.value))) * 100.0)

    def _make_view(self) -> View:
        for cancel in self._observation_cancels:
            cancel()
        self._observation_cancels = []
        with observation_tracking(self._observed_value_changed) as cleanups:
            view = self._view_factory()
            collect_presentation_configurations(view)
            resolve_environment_tree(view, self._system_environment())
            resolve_transaction_tree(view)
            resolve_style_tree(view)
            resolve_visual_style_tree(view)
            resolve_text_style_tree(view)
            resolve_semantic_tree(view)
            collect_preferences(view)
            start_tasks(view, self._tasks, self._observed_value_changed)
        self._observation_cancels = cleanups
        return view

    def _system_environment(self):
        return system_environment(
            phase=self._scene_phase,
            scheme=self._native_color_scheme(),
            active_state=self._control_active_state,
            open_url_action=OpenURLAction(system_opener=self._open_system_url),
            dismiss_action=DismissAction(self._dismiss_current_window),
        )

    def _native_color_scheme(self) -> ColorScheme:  # pragma: no cover - native appearance
        if not _PYOBJC or self._window is None:
            return ColorScheme.LIGHT
        try:
            appearance = NSApplication.sharedApplication().effectiveAppearance()
            name = str(appearance.name()).lower()
            return ColorScheme.DARK if "dark" in name else ColorScheme.LIGHT
        except Exception:
            return ColorScheme.LIGHT

    def _apply_window_color_scheme(self, view: View) -> None:  # pragma: no cover
        if not _PYOBJC or self._window is None:
            return
        environment = getattr(view, "_environment", None)
        scheme = environment.get(COLOR_SCHEME_KEY) if environment is not None else None
        try:
            from AppKit import NSAppearance, NSAppearanceNameAqua, NSAppearanceNameDarkAqua
            name = NSAppearanceNameDarkAqua if scheme == ColorScheme.DARK else NSAppearanceNameAqua
            self._window.setAppearance_(NSAppearance.appearanceNamed_(name))
        except Exception:
            pass

    @staticmethod
    def _open_system_url(url: str) -> bool:  # pragma: no cover - native action
        if not _PYOBJC:
            return False
        try:
            from AppKit import NSWorkspace
            from Foundation import NSURL
            value = NSURL.URLWithString_(url)
            return bool(value is not None and NSWorkspace.sharedWorkspace().openURL_(value))
        except Exception:
            return False

    def _dismiss_current_window(self) -> bool:  # pragma: no cover - native action
        if self._window is None:
            return False
        self._window.performClose_(None)
        return True

    def _observed_value_changed(self) -> None:  # pragma: no cover - UI scheduling
        if self._refresh_scheduled or self._content is None:
            return
        animation = current_animation()
        if animation is not None:
            self._pending_animation = animation
        self._refresh_scheduled = True
        if not self._dispatcher.schedule_once("refresh", self._perform_scheduled_refresh):
            self._refresh_scheduled = False

    @staticmethod
    def _schedule_on_main_queue(callback: Callable[[], None]) -> None:
        from Foundation import NSOperationQueue
        NSOperationQueue.mainQueue().addOperationWithBlock_(callback)

    @staticmethod
    def _schedule_animation_frame(delay: float, callback: Callable[[], None]):
        import threading
        def submit():
            from Foundation import NSOperationQueue
            NSOperationQueue.mainQueue().addOperationWithBlock_(callback)
        timer = threading.Timer(max(0.001, delay), submit)
        timer.daemon = True
        timer.start()
        return timer

    def _animate_native_frame(self, native, start, end, animation) -> None:
        key = id(native)
        handle = self._animation_handles.pop(key, None)
        if handle is not None:
            handle.cancel()
        start_origin, start_size = start
        end_origin, end_size = end

        def update(progress: float) -> None:
            origin = interpolate(start_origin, end_origin, progress)
            size = interpolate(start_size, end_size, progress)
            native.setFrame_(NSMakeRect(origin.x, origin.y, size.width, size.height))

        holder = {}
        def complete() -> None:
            current = holder.get("handle")
            if self._animation_handles.get(key) is current:
                self._animation_handles.pop(key, None)
        holder["handle"] = self._animation_driver.animate(
            animation, 0.0, 1.0, update,
            complete,
        )
        self._animation_handles[key] = holder["handle"]

    def _animate_native_matched_frame(self, native, start, end, animation,
                                      modifier=None) -> None:
        if modifier is None or modifier.properties == "frame":
            self._animate_native_frame(native, start, end, animation)
            return
        start_origin, start_size = start
        end_origin, end_size = end
        anchor_x, anchor_y = modifier.anchor_fraction
        if modifier.properties == "position":
            start_anchor = Point(start_origin.x + start_size.width * anchor_x,
                                 start_origin.y + start_size.height * anchor_y)
            start = (Point(start_anchor.x - end_size.width * anchor_x,
                           start_anchor.y - end_size.height * anchor_y), end_size)
        elif modifier.properties == "size":
            end_anchor = Point(end_origin.x + end_size.width * anchor_x,
                               end_origin.y + end_size.height * anchor_y)
            start = (Point(end_anchor.x - start_size.width * anchor_x,
                           end_anchor.y - start_size.height * anchor_y), start_size)
        self._animate_native_frame(native, start, end, animation)

    def _animate_native_transition(self, native, frame, transition, animation,
                                   inserting: bool = True,
                                   completion: Callable[[], None] | None = None) -> None:
        key = id(native)
        handle = self._animation_handles.pop(key, None)
        if handle is not None:
            handle.cancel()
        origin, size = frame

        def update(progress: float) -> None:
            sample = sample_transition(transition, progress, size, inserting=inserting)
            width, height = size.width * sample.scale, size.height * sample.scale
            x = origin.x + sample.offset.x + (size.width - width) / 2.0
            y = origin.y + sample.offset.y + (size.height - height) / 2.0
            native.setFrame_(NSMakeRect(x, y, width, height))
            if hasattr(native, "setAlphaValue_"):
                native.setAlphaValue_(sample.opacity)

        holder = {}
        def complete() -> None:
            current = holder.get("handle")
            if self._animation_handles.get(key) is current:
                self._animation_handles.pop(key, None)
            if completion is not None:
                completion()
        holder["handle"] = self._animation_driver.animate(
            animation, 0.0 if inserting else 1.0, 1.0 if inserting else 0.0, update,
            complete,
        )
        self._animation_handles[key] = holder["handle"]

    def _animate_native_text_content(self, native, start: str, end: str,
                                     transition: str, animation) -> None:
        key = id(native)
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
                native.setStringValue_(str(round(value)) if integer_result else f"{value:g}")
                return
            if progress < 0.5:
                native.setStringValue_(start)
                alpha = 1.0 - progress * 2.0
            else:
                native.setStringValue_(end)
                alpha = (progress - 0.5) * 2.0
            if hasattr(native, "setAlphaValue_"):
                native.setAlphaValue_(alpha)

        # Commit the initial state synchronously so an asynchronous first frame
        # cannot briefly expose the new value before the transition starts.
        update(0.0)
        holder = {}
        def complete() -> None:
            native.setStringValue_(end)
            if hasattr(native, "setAlphaValue_"):
                native.setAlphaValue_(1.0)
            current = holder.get("handle")
            if self._animation_handles.get(key) is current:
                self._animation_handles.pop(key, None)
        holder["handle"] = self._animation_driver.animate(
            animation, 0.0, 1.0, update, complete)
        self._animation_handles[key] = holder["handle"]

    def _animate_native_symbol(self, native, frame, effect: str, animation) -> None:
        if frame is None:
            return
        key = id(native)
        handle = self._animation_handles.pop(key, None)
        if handle is not None:
            handle.cancel()
        origin, size = frame

        def update(progress: float) -> None:
            sample = sample_symbol_effect(effect, progress, size)
            width, height = size.width * sample.scale, size.height * sample.scale
            x = origin.x + sample.offset.x + (size.width - width) / 2.0
            y = origin.y + sample.offset.y + (size.height - height) / 2.0
            native.setFrame_(NSMakeRect(x, y, width, height))
            if hasattr(native, "setAlphaValue_"):
                native.setAlphaValue_(sample.opacity)

        holder = {}
        def complete() -> None:
            native.setFrame_(NSMakeRect(origin.x, origin.y, size.width, size.height))
            if hasattr(native, "setAlphaValue_"):
                native.setAlphaValue_(1.0)
            current = holder.get("handle")
            if self._animation_handles.get(key) is current:
                self._animation_handles.pop(key, None)
        holder["handle"] = self._animation_driver.animate(
            animation, 0.0, 1.0, update, complete)
        self._animation_handles[key] = holder["handle"]

    def _perform_scheduled_refresh(self) -> None:  # pragma: no cover
        if self._refresh_scheduled:
            self._refresh_content()

    def _find_by_id(self, vid: int):
        for v in self._view.flatten():
            if id(v) == vid:
                return v
        return None

    def _add_textfield(self, view: View, parent: "NSView", x: float, y: float,
                       w: float, h: float, secure: bool) -> None:
        if not _PYOBJC:
            return
        rect = NSMakeRect(x, y, max(40, w), max(18, h))
        if secure:
            # NSSecureTextField is a subclass of NSTextField.
            from AppKit import NSSecureTextField
            field = NSSecureTextField.alloc().initWithFrame_(rect)
        else:
            field = NSTextField.alloc().initWithFrame_(rect)
        field.setPlaceholderString_(view.placeholder if hasattr(view, "placeholder") else "")
        text_style = style_value(view, "text_field_style", TextFieldStyle.AUTOMATIC)
        field.setBezeled_(text_style != TextFieldStyle.PLAIN)
        # Rounded native fields feel substantially closer to SwiftUI's
        # .textFieldStyle(.roundedBorder) than the legacy square bezel.
        try:
            from AppKit import NSTextFieldRoundedBezel
            field.setBezelStyle_(NSTextFieldSquareBezel if text_style == TextFieldStyle.SQUARE_BORDER
                                 else NSTextFieldRoundedBezel)
        except Exception:
            field.setBezelStyle_(NSTextFieldSquareBezel)
        field.setEditable_(is_enabled(view))
        field.setEnabled_(is_enabled(view))
        try:
            field.setFocusRingType_(1)
            field.setFont_(NSFont.systemFontOfSize_(13))
        except Exception:
            pass
        # Pre-fill the current binding value so the field shows live state.
        text = getattr(view, "text", None)
        if text is not None and hasattr(text, "wrapped_value"):
            field.setStringValue_(str(text.wrapped_value))
        if getattr(view, "validation_error", None):
            field.setToolTip_(view.validation_error)
            try:
                field.setTextColor_(NSColor.systemRedColor())
            except Exception:
                pass
        field.setTarget_(self._bridge)
        field.setAction_("fieldChanged:")
        field.setDelegate_(self._bridge)
        self._controls[id(view)] = field
        parent.addSubview_(field)

    def _add_searchfield(self, view: SearchField, parent: "NSView", x: float,
                         y: float, w: float, h: float) -> None:
        from AppKit import NSSearchField
        field = NSSearchField.alloc().initWithFrame_(
            NSMakeRect(x, y, max(120.0, w), max(24.0, h))
        )
        field.setPlaceholderString_(view.placeholder)
        field.setStringValue_(str(view.text.wrapped_value))
        field.setEnabled_(is_enabled(view))
        field.setTarget_(self._bridge)
        field.setAction_("fieldChanged:")
        field.setDelegate_(self._bridge)
        field.setSendsSearchStringImmediately_(True)
        self._controls[id(view)] = field
        parent.addSubview_(field)

    def _add_texteditor(self, view: TextEditor, parent: "NSView", x: float,
                        y: float, w: float, h: float) -> None:
        # NSTextField supports wrapped, editable multi-line content while
        # retaining the same reliable target/action binding path as TextField.
        field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(x, y, max(160.0, w), max(view.min_height, h))
        )
        field.setStringValue_(str(view.text.wrapped_value))
        field.setPlaceholderString_(view.placeholder)
        field.setEditable_(is_enabled(view))
        field.setEnabled_(is_enabled(view))
        field.setBezeled_(True)
        field.setLineBreakMode_(NSLineBreakByWordWrapping)
        field.setMaximumNumberOfLines_(0)
        field.setTarget_(self._bridge)
        field.setAction_("fieldChanged:")
        field.setDelegate_(self._bridge)
        self._controls[id(view)] = field
        parent.addSubview_(field)

    @_IBAction
    def fieldChanged_(self, sender) -> None:  # pragma: no cover - UI callback
        for v, ctrl in self._controls.items():
            if ctrl is sender:
                submitted = False
                view = self._find_by_id(v)
                if isinstance(view, (TextField, SecureField)) and hasattr(view, "text"):
                    view.text.wrapped_value = sender.stringValue()
                for control, modifier in self._submit_controls:
                    if control is sender and isinstance(modifier, OnSubmitModifier):
                        modifier.action()
                        submitted = True
                if submitted:
                    self._refresh_content()
                return

    def _add_switch(self, view: Toggle, parent: "NSView", x: float, y: float,
                    w: float, h: float) -> None:
        if not hasattr(parent, "addSubview_"):
            return
        rect = NSMakeRect(x, y, max(40, w), max(20, h))
        switch = NSSwitch.alloc().initWithFrame_(rect)
        if view.is_on is not None:
            switch.setState_(1 if bool(view.is_on.wrapped_value) else 0)
        switch.setEnabled_(is_enabled(view))
        switch.setTarget_(self._bridge)
        switch.setAction_("switchChanged:")
        self._controls[id(view)] = switch
        parent.addSubview_(switch)

    @_IBAction
    def switchChanged_(self, sender) -> None:  # pragma: no cover - UI callback
        for v, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(v)
                if isinstance(view, Toggle) and view.is_on is not None:
                    view.is_on.wrapped_value = bool(sender.state() == 1)
                return

    def _add_slider(self, view: Slider, parent: "NSView", x: float, y: float,
                    w: float, h: float) -> None:
        slider = NSSlider.alloc().initWithFrame_(NSMakeRect(x, y, max(40, w), max(18, h)))
        lo, hi = view.range
        slider.setMinValue_(lo)
        slider.setMaxValue_(hi)
        if view.step:
            slider.setNumberOfTickMarks_(0)
            slider.setAllowsTickMarkValuesOnly_(False)
        if view.value is not None:
            slider.setDoubleValue_(float(view.value.wrapped_value))
        slider.setSliderType_(NSSliderTypeLinear)
        slider.setEnabled_(bool(is_enabled(view)))
        slider.setTarget_(self._bridge)
        slider.setAction_("sliderChanged:")
        self._controls[id(view)] = slider
        parent.addSubview_(slider)

    @_IBAction
    def sliderChanged_(self, sender) -> None:  # pragma: no cover - UI callback
        for v, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(v)
                if isinstance(view, Slider) and view.value is not None:
                    view.value.wrapped_value = float(sender.doubleValue())
                return

    def _add_picker(self, view: Picker, parent: "NSView", x: float, y: float,
                    w: float, h: float) -> None:
        popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(x, y, max(60, w), max(20, h)))
        popup.removeAllItems()
        for opt in view.options:
            popup.addItemWithTitle_(str(opt))
        if view.selection is not None:
            sel = view.selection.wrapped_value
            try:
                popup.selectItemWithTitle_(str(sel))
            except Exception:
                popup.selectItemAtIndex_(0)
        popup.setEnabled_(is_enabled(view))
        popup.setTarget_(self._bridge)
        popup.setAction_("pickerChanged:")
        self._controls[id(view)] = popup
        parent.addSubview_(popup)

    def _add_segmented(self, view: Picker, parent: "NSView", x: float,
                       y: float, w: float, h: float) -> None:
        from AppKit import NSSegmentedControl, NSSegmentStyleRounded
        control = NSSegmentedControl.alloc().initWithFrame_(
            NSMakeRect(x, y, max(80.0, w), max(24.0, h))
        )
        control.setSegmentCount_(len(view.options))
        control.setSegmentStyle_(NSSegmentStyleRounded)
        selected = view.selection.wrapped_value if view.selection else None
        for index, option in enumerate(view.options):
            control.setLabel_forSegment_(str(option), index)
            if option == selected:
                control.setSelected_forSegment_(True, index)
        control.setEnabled_(is_enabled(view))
        control.setTarget_(self._bridge)
        control.setAction_("segmentChanged:")
        self._controls[id(view)] = control
        parent.addSubview_(control)

    @_IBAction
    def segmentChanged_(self, sender) -> None:  # pragma: no cover - UI callback
        for vid, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(vid)
                if isinstance(view, Picker) and view.selection is not None:
                    index = int(sender.selectedSegment())
                    if 0 <= index < len(view.options):
                        view.selection.wrapped_value = view.options[index]
                return

    @_IBAction
    def pickerChanged_(self, sender) -> None:  # pragma: no cover - UI callback
        for v, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(v)
                if isinstance(view, Picker) and view.selection is not None:
                    view.selection.wrapped_value = sender.titleOfSelectedItem()
                return

    def _add_stepper(self, view: Stepper, parent: "NSView", x: float, y: float,
                     w: float, h: float) -> None:
        stepper = NSStepper.alloc().initWithFrame_(NSMakeRect(x, y, max(32, w), max(16, h)))
        lo, hi = view.range
        stepper.setMinValue_(lo)
        stepper.setMaxValue_(hi)
        stepper.setIncrement_(view.step)
        if view.value is not None:
            stepper.setDoubleValue_(float(view.value.wrapped_value))
        stepper.setEnabled_(bool(is_enabled(view)))
        stepper.setTarget_(self._bridge)
        stepper.setAction_("stepperChanged:")
        self._controls[id(view)] = stepper
        parent.addSubview_(stepper)

    @_IBAction
    def stepperChanged_(self, sender) -> None:  # pragma: no cover - UI callback
        for v, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(v)
                if isinstance(view, Stepper) and view.value is not None:
                    view.value.wrapped_value = float(sender.doubleValue())
                return

    def _add_datepicker(self, view: DatePicker, parent: "NSView", x: float, y: float,
                        w: float, h: float) -> None:
        from AppKit import (
            NSDatePicker,
            NSDatePickerStyleTextFieldAndStepper,
            NSDatePickerElementFlagYearMonthDay,
            NSDatePickerElementFlagHourMinuteSecond,
        )
        dp = NSDatePicker.alloc().initWithFrame_(NSMakeRect(x, y, max(80, w), max(20, h)))
        dp.setDatePickerStyle_(NSDatePickerStyleTextFieldAndStepper)
        if view.displayed_components == "hourAndMinute":
            flags = NSDatePickerElementFlagHourMinuteSecond
        else:
            flags = NSDatePickerElementFlagYearMonthDay
        dp.setDatePickerElements_(flags)
        if view.selection is not None:
            val = view.selection.wrapped_value
            if isinstance(val, datetime):
                # Convert Python datetime -> NSDate (seconds since 2001-01-01).
                from Foundation import NSDate
                epoch = datetime(2001, 1, 1)
                delta = (val - epoch).total_seconds()
                dp.setDateValue_(NSDate.dateWithTimeIntervalSinceReferenceDate_(delta))
        dp.setEnabled_(bool(is_enabled(view)))
        dp.setTarget_(self._bridge)
        dp.setAction_("dateChanged:")
        self._controls[id(view)] = dp
        parent.addSubview_(dp)

    @_IBAction
    def dateChanged_(self, sender) -> None:  # pragma: no cover - UI callback
        for v, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(v)
                if isinstance(view, DatePicker) and view.selection is not None:
                    from Foundation import NSDate
                    ns = sender.dateValue().timeIntervalSinceReferenceDate()
                    epoch = datetime(2001, 1, 1)
                    view.selection.wrapped_value = epoch + __import__("datetime").timedelta(seconds=ns)
                return

    def _add_colorpicker(self, view: ColorPicker, parent: "NSView", x: float, y: float,
                         w: float, h: float) -> None:
        from AppKit import NSColorWell
        well = NSColorWell.alloc().initWithFrame_(NSMakeRect(x, y, max(28, w), max(20, h)))
        if view.selection is not None:
            col = view.selection.wrapped_value
            if isinstance(col, Color):
                well.setColor_(self._ns_color(col))
        well.setEnabled_(bool(is_enabled(view)))
        well.setTarget_(self._bridge)
        well.setAction_("colorChanged:")
        self._controls[id(view)] = well
        parent.addSubview_(well)

    @_IBAction
    def colorChanged_(self, sender) -> None:  # pragma: no cover - UI callback
        for v, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(v)
                if isinstance(view, ColorPicker) and view.selection is not None:
                    ns = sender.color()
                    r = ns.redComponent() if ns.numberOfComponents() >= 3 else 0
                    g = ns.greenComponent() if ns.numberOfComponents() >= 3 else 0
                    b = ns.blueComponent() if ns.numberOfComponents() >= 3 else 0
                    view.selection.wrapped_value = Color(r, g, b)
                return

    def _add_progress(self, view: ProgressView, parent: "NSView", x: float, y: float,
                      w: float, h: float) -> None:
        prog = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(x, y, max(40, w), max(12, h)))
        style = style_value(view, "progress_view_style", ProgressViewStyle.AUTOMATIC)
        if style == ProgressViewStyle.CIRCULAR:
            try:
                from AppKit import NSProgressIndicatorSpinningStyle
                prog.setStyle_(NSProgressIndicatorSpinningStyle)
            except Exception:
                prog.setStyle_(NSProgressIndicatorBarStyle)
        else:
            prog.setStyle_(NSProgressIndicatorBarStyle)
        if view.value is None:
            prog.setIndeterminate_(True)
            prog.startAnimation_(None)
        else:
            prog.setIndeterminate_(False)
            prog.setDoubleValue_(float(max(0.0, min(1.0, view.value))) * 100.0)
        self._controls[id(view)] = prog
        parent.addSubview_(prog)

    def _add_gauge(self, view: Gauge, parent: "NSView", x: float, y: float,
                   w: float, h: float) -> None:
        from AppKit import NSLevelIndicator, NSLevelIndicatorStyleContinuousCapacity
        gauge = NSLevelIndicator.alloc().initWithFrame_(
            NSMakeRect(x, y, max(80.0, w), max(14.0, h))
        )
        lo, hi = view.range
        gauge.setMinValue_(lo)
        gauge.setMaxValue_(hi)
        gauge.setDoubleValue_(max(lo, min(hi, view.raw_value)))
        gauge.setLevelIndicatorStyle_(NSLevelIndicatorStyleContinuousCapacity)
        self._controls[id(view)] = gauge
        parent.addSubview_(gauge)

    def _add_divider(self, view: Divider, parent: "NSView", x: float, y: float, w: float) -> None:
        from AppKit import NSBox, NSBoxSeparator
        box = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, max(1, w), 1))
        box.setBoxType_(NSBoxSeparator)
        parent.addSubview_(box)

    def _add_image(self, view: Image, parent: "NSView", x: float, y: float,
                   w: float, h: float) -> None:
        from pathlib import Path
        from AppKit import NSImage
        from Foundation import NSData
        img = None
        if view.system_name:
            if view.variable_value is not None:
                try:
                    img = NSImage.imageWithSystemSymbolName_variableValue_accessibilityDescription_(
                        view.resolved_system_name, view.variable_value,
                        view.label or view.system_name,
                    )
                except Exception:
                    pass
            if img is None:
                try:
                    img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                        view.resolved_system_name, view.label or view.system_name
                    )
                except Exception:
                    pass
            if img is None:
                img = NSImage.imageNamed_(view.resolved_system_name)
        elif view.path is not None:
            img = NSImage.alloc().initWithContentsOfFile_(str(Path(view.path).expanduser()))
        elif view.data is not None:
            data = NSData.alloc().initWithBytes_length_(view.data, len(view.data))
            img = NSImage.alloc().initWithData_(data)
        if img is None:
            return
        if view._resizable:
            try:
                from AppKit import NSEdgeInsetsMake, NSImageResizingModeStretch, NSImageResizingModeTile
                insets = view.cap_insets
                img.setCapInsets_(NSEdgeInsetsMake(insets.top, insets.leading,
                                                   insets.bottom, insets.trailing))
                img.setResizingMode_(NSImageResizingModeTile if view.resizing_mode == "tile"
                                     else NSImageResizingModeStretch)
            except Exception:
                pass
        try:
            img.setTemplate_(view._rendering_mode == "template")
        except Exception:
            pass
        iv = NSImageView.alloc().initWithFrame_(NSMakeRect(x, y, max(8, w), max(8, h)))
        iv.setImage_(img)
        self._configure_symbol_image(view, iv, img)
        if view._resizable:
            if view.content_mode == "fill":
                try:
                    iv.setWantsLayer_(True)
                    iv.layer().setContents_(img)
                    iv.layer().setContentsGravity_("resizeAspectFill")
                    iv.layer().setMasksToBounds_(True)
                except Exception:
                    iv.setImageScaling_(3)
            else:
                iv.setImageScaling_(3)
        if view._rendering_mode == "template":
            try:
                iv.setContentTintColor_(self._ns_color(view._color or self.theme.accent))
            except Exception:
                pass
        parent.addSubview_(iv)

    def _configure_symbol_image(self, view: Image, image_view, image) -> None:
        try:
            from AppKit import NSImageSymbolConfiguration
            mode = view.symbol_rendering_mode_value
            scales = {"small": 1, "medium": 2, "large": 3}
            weights = {"ultraLight": -0.8, "thin": -0.6, "light": -0.4,
                       "regular": 0.0, "medium": 0.23, "semibold": 0.3,
                       "bold": 0.4, "heavy": 0.56, "black": 0.62}
            configuration = NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
                max(view.effective_size.width, view.effective_size.height),
                weights[view.symbol_weight_value], scales[view.image_scale_value]
            )
            if mode == "hierarchical":
                colors = NSImageSymbolConfiguration.configurationWithHierarchicalColor_(
                    self._ns_color(view._color or self.theme.accent)
                )
                configuration = configuration.configurationByApplyingConfiguration_(colors)
            elif mode == "palette":
                colors = NSImageSymbolConfiguration.configurationWithPaletteColors_(
                    [self._ns_color(color) for color in view.palette_colors]
                )
                configuration = configuration.configurationByApplyingConfiguration_(colors)
            elif mode == "multicolor":
                colors = NSImageSymbolConfiguration.configurationPreferringMulticolor()
                configuration = configuration.configurationByApplyingConfiguration_(colors)
            if configuration is not None:
                image_view.setImage_(image.imageWithSymbolConfiguration_(configuration))
        except Exception:
            pass
        try:
            image_view.setWantsLayer_(True)
            filters = {"none": "nearest", "low": "linear",
                       "medium": "linear", "high": "trilinear"}
            image_view.layer().setMagnificationFilter_(filters[view.interpolation_quality])
            image_view.layer().setMinificationFilter_(filters[view.interpolation_quality])
            image_view.layer().setAllowsEdgeAntialiasing_(view.is_antialiased)
        except Exception:
            pass

    def _add_async_image(self, view: AsyncImage, parent: "NSView", x: float, y: float,
                         w: float, h: float) -> None:
        from AppKit import NSImage, NSProgressIndicator, NSProgressIndicatorSpinningStyle
        from Foundation import NSData, NSOperationQueue

        def changed(phase) -> None:
            NSOperationQueue.mainQueue().addOperationWithBlock_(self._refresh_content)

        self._async_image_cancels.append(view.subscribe(changed))
        view.start()
        if view.phase.is_empty:
            indicator = NSProgressIndicator.alloc().initWithFrame_(
                NSMakeRect(x, y, max(20, w), max(20, h))
            )
            indicator.setStyle_(NSProgressIndicatorSpinningStyle)
            indicator.startAnimation_(None)
            parent.addSubview_(indicator)
            return
        image = None
        if view.phase.is_success:
            data = NSData.alloc().initWithBytes_length_(view.phase.data, len(view.phase.data))
            image = NSImage.alloc().initWithData_(data)
        if image is None:
            image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                "exclamationmark.triangle", "Image failed to load"
            )
        image_view = NSImageView.alloc().initWithFrame_(
            NSMakeRect(x, y, max(8, w), max(8, h))
        )
        image_view.setImage_(image)
        try:
            image_view.setImageScaling_(2)
        except Exception:
            pass
        parent.addSubview_(image_view)
        parent.addSubview_(iv)

    def _add_shape(self, view: Shape, parent: "NSView", x: float, y: float,
                   w: float, h: float) -> None:
        inset = min(view.inset_amount, max(0.0, min(w, h) / 2.0))
        x, y, w, h = x + inset, y + inset, max(0.0, w - inset * 2), max(0.0, h - inset * 2)
        if isinstance(view, UnevenRoundedRectangle):
            self._add_uneven_rounded_rectangle(view, parent, x, y, w, h)
            return
        try:
            from Quartz import (
                CAShapeLayer, CGPathCreateWithEllipseInRect, CGPathCreateWithRect,
                CGPathCreateWithRoundedRect,
            )
        except ImportError:
            self._add_shape_surface(view, parent, x, y, w, h)
            return
        host = NSView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        host.setWantsLayer_(True)
        rect = ((0.0, 0.0), (w, h))
        if isinstance(view, (Circle, Ellipse)):
            path = CGPathCreateWithEllipseInRect(rect, None)
        elif isinstance(view, Capsule):
            radius = min(w, h) / 2.0
            path = CGPathCreateWithRoundedRect(rect, radius, radius, None)
        elif isinstance(view, RoundedRectangle):
            radius = min(view.corner_radius_value, min(w, h) / 2.0)
            path = CGPathCreateWithRoundedRect(rect, radius, radius, None)
        else:
            path = CGPathCreateWithRect(rect, None)
        layer = CAShapeLayer.layer()
        layer.setPath_(path)
        self._configure_shape_layer(layer, view)
        host.layer().addSublayer_(layer)
        parent.addSubview_(host)

    def _add_shape_surface(self, view: Shape, parent: "NSView", x: float, y: float,
                           w: float, h: float) -> None:
        """Render the portable Shape subset when pyobjc-Quartz is absent.

        ``pyobjc-framework-Cocoa`` is intentionally sufficient to run aUI.
        NSBox cannot express every vector-path feature, but preserves fill,
        stroke and the familiar rounded geometry instead of failing during a
        normal app build.
        """
        surface = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        surface.setBoxType_(NSBoxCustom)
        surface.setTitlePosition_(NSNoTitle)
        surface.setFillColor_(self._ns_color(view.fill_color))
        surface.setBorderColor_(self._ns_color(view.stroke_color or Color.clear))
        surface.setBorderWidth_(view.line_width if view.stroke_color else 0.0)
        if isinstance(view, (Circle, Ellipse, Capsule)):
            radius = min(w, h) / 2.0
        elif isinstance(view, RoundedRectangle):
            radius = min(view.corner_radius_value, min(w, h) / 2.0)
        else:
            radius = 0.0
        surface.setCornerRadius_(radius)
        parent.addSubview_(surface)

    def _configure_shape_layer(self, layer, view: Shape) -> None:
        layer.setFillColor_(self._ns_color(view.fill_color).CGColor())
        layer.setStrokeColor_(self._ns_color(view.stroke_color or Color.clear).CGColor())
        layer.setLineWidth_(view.line_width if view.stroke_color else 0.0)
        style = view.stroke_style
        fill_style = view.fill_style
        layer.setFillRule_("even-odd" if fill_style.eo_fill else "non-zero")
        layer.setAllowsEdgeAntialiasing_(fill_style.antialiased)
        layer.setStrokeStart_(view.trim_range[0])
        layer.setStrokeEnd_(view.trim_range[1])
        layer.setLineCap_({"butt": "butt", "round": "round", "square": "square"}[style.line_cap])
        layer.setLineJoin_({"miter": "miter", "round": "round", "bevel": "bevel"}[style.line_join])
        layer.setMiterLimit_(style.miter_limit)
        if style.dash:
            layer.setLineDashPattern_(list(style.dash))
            layer.setLineDashPhase_(style.dash_phase)

    def _add_uneven_rounded_rectangle(self, view: UnevenRoundedRectangle,
                                      parent: "NSView", x: float, y: float,
                                      w: float, h: float) -> None:
        try:
            from Quartz import (
                CAShapeLayer, CGPathAddArcToPoint, CGPathAddLineToPoint,
                CGPathCloseSubpath, CGPathCreateMutable, CGPathMoveToPoint,
            )
        except ImportError:
            self._add_shape_surface(view, parent, x, y, w, h)
            return
        host = NSView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        host.setWantsLayer_(True)
        limit = min(w, h) / 2.0
        top_leading, top_trailing, bottom_leading, bottom_trailing = (
            min(value, limit) for value in view.corner_radii
        )
        path = CGPathCreateMutable()
        CGPathMoveToPoint(path, None, top_leading, 0)
        CGPathAddLineToPoint(path, None, w - top_trailing, 0)
        CGPathAddArcToPoint(path, None, w, 0, w, top_trailing, top_trailing)
        CGPathAddLineToPoint(path, None, w, h - bottom_trailing)
        CGPathAddArcToPoint(path, None, w, h, w - bottom_trailing, h, bottom_trailing)
        CGPathAddLineToPoint(path, None, bottom_leading, h)
        CGPathAddArcToPoint(path, None, 0, h, 0, h - bottom_leading, bottom_leading)
        CGPathAddLineToPoint(path, None, 0, top_leading)
        CGPathAddArcToPoint(path, None, 0, 0, top_leading, 0, top_leading)
        CGPathCloseSubpath(path)
        layer = CAShapeLayer.layer()
        layer.setPath_(path)
        self._configure_shape_layer(layer, view)
        host.layer().addSublayer_(layer)
        parent.addSubview_(host)

    def _add_gradient(self, view: Gradient, parent: "NSView", x: float, y: float,
                      w: float, h: float) -> None:
        try:
            from math import cos, radians, sin
            from Quartz import CAGradientLayer, kCAGradientLayerConic, kCAGradientLayerRadial
            host = NSView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
            host.setWantsLayer_(True)
            layer = CAGradientLayer.layer()
            layer.setFrame_(NSMakeRect(0, 0, w, h))
            layer.setColors_([self._ns_color(stop.color).CGColor() for stop in view.stops])
            layer.setLocations_([stop.location for stop in view.stops])
            if isinstance(view, LinearGradient):
                layer.setStartPoint_(view.start_point)
                layer.setEndPoint_(view.end_point)
            elif isinstance(view, RadialGradient):
                layer.setType_(kCAGradientLayerRadial)
                layer.setStartPoint_(view.center)
                layer.setEndPoint_((view.center[0] + view.radius, view.center[1] + view.radius))
                layer.setLocations_(view.mapped_locations())
            elif isinstance(view, EllipticalGradient):
                layer.setType_(kCAGradientLayerRadial)
                layer.setStartPoint_(view.center)
                radius = view.end_radius_fraction
                layer.setEndPoint_((view.center[0] + radius, view.center[1] + radius))
                layer.setLocations_(view.mapped_locations())
            elif isinstance(view, AngularGradient):
                layer.setType_(kCAGradientLayerConic)
                layer.setStartPoint_(view.center)
                angle = radians(view.start_angle)
                layer.setEndPoint_((view.center[0] + cos(angle),
                                    view.center[1] + sin(angle)))
                sweep = min(1.0, view.sweep_angle / 360.0)
                locations = [stop.location * sweep for stop in view.stops]
                colors = [self._ns_color(stop.color).CGColor() for stop in view.stops]
                if sweep < 1.0:
                    locations.append(1.0); colors.append(colors[-1])
                layer.setLocations_(locations); layer.setColors_(colors)
            host.layer().addSublayer_(layer)
        except Exception:
            fallback = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
            fallback.setBoxType_(NSBoxCustom)
            fallback.setTitlePosition_(NSNoTitle)
            fallback.setFillColor_(self._ns_color(view.stops[0].color))
            fallback.setBorderWidth_(0)
            parent.addSubview_(fallback)
            return
        parent.addSubview_(host)

    def _add_label_badge(self, view: View, parent: "NSView", x: float, y: float,
                         w: float, h: float) -> None:
        title = view.title
        color = NSColor.secondaryLabelColor()
        label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(x, y, max(10, w), max(16, h))
        )
        label.setStringValue_(title)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setTextColor_(color)
        label.setFont_(NSFont.systemFontOfSize_(11))
        parent.addSubview_(label)

    def _add_nav_header(self, view: NavigationStack, parent: "NSView", x: float, y: float, w: float) -> None:
        if not view.header_visible:
            return
        configuration = view.navigation_configuration
        header_height = view.header_height
        if configuration.background is not None:
            background = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, w, header_height))
            background.setBoxType_(NSBoxCustom)
            background.setBorderWidth_(0.0)
            background.setFillColor_(self._ns_color(configuration.background))
            parent.addSubview_(background)
        title_x = x
        if len(view.path):
            back = NSButton.alloc().initWithFrame_(NSMakeRect(x, y, 72, header_height))
            back.setTitle_("‹ Back")
            back.setBordered_(False)
            back.setContentTintColor_(self._ns_color(self.theme.accent))
            back.setTarget_(self._bridge)
            back.setAction_("navigationBack:")
            self._controls[id(view)] = back
            parent.addSubview_(back)
            title_x += 76
        header = NSTextField.alloc().initWithFrame_(
            NSMakeRect(title_x, y, max(10, w - (title_x - x)), header_height)
        )
        header.setStringValue_(view.title)
        header.setBezeled_(False)
        header.setDrawsBackground_(False)
        header.setEditable_(False)
        header.setSelectable_(False)
        header.setTextColor_(NSColor.labelColor())
        font_size = 28 if header_height > 28 else 20
        header.setFont_(NSFont.boldSystemFontOfSize_(font_size))
        parent.addSubview_(header)

    def _add_navigation_rail(self, view: NavigationRail, parent: "NSView", x: float,
                             y: float, w: float, h: float) -> None:
        rail = NSBox.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        rail.setBoxType_(NSBoxCustom)
        rail.setTitlePosition_(NSNoTitle)
        rail.setBorderWidth_(0)
        rail.setFillColor_(NSColor.controlBackgroundColor())
        parent.addSubview_(rail)
        row_height = min(46.0, max(30.0, h / max(1, len(view.destinations))))
        for index, destination in enumerate(view.destinations):
            button = NSButton.alloc().initWithFrame_(NSMakeRect(
                6.0, 8.0 + row_height * index, max(24.0, w - 12.0), row_height - 4.0,
            ))
            active = index == view.active_index
            symbol = (destination.selected_system_name if active and destination.selected_system_name
                      else destination.system_name)
            button.setTitle_(destination.label if view.extended or not symbol else "")
            button.setBordered_(active)
            if symbol:
                try:
                    from AppKit import NSImage
                    image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol, destination.label)
                    if image is not None:
                        button.setImage_(image)
                except Exception:
                    pass
            button.setToolTip_(destination.label)
            button.setTarget_(self._bridge)
            button.setAction_("navigationRailSelected:")
            rail.addSubview_(button)
            self._navigation_rail_buttons.append((button, view, index))

    @_IBAction
    def navigationBack_(self, sender) -> None:  # pragma: no cover - UI callback
        for vid, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(vid)
                if isinstance(view, NavigationStack):
                    view.go_back()
                    self._refresh_content()
                return

    @_IBAction
    def navigationRailSelected_(self, sender) -> None:  # pragma: no cover - UI callback
        for button, rail, index in self._navigation_rail_buttons:
            if button is sender:
                rail.select(index)
                self._refresh_content()
                return

    def _add_link(self, view: Link, parent: "NSView", x: float, y: float,
                  w: float, h: float) -> None:
        from AppKit import NSBezelStyleInline
        button = NSButton.alloc().initWithFrame_(
            NSMakeRect(x, y, max(40.0, w), max(20.0, h))
        )
        button.setTitle_(view.title)
        button.setBezelStyle_(NSBezelStyleInline)
        button.setBordered_(False)
        button.setContentTintColor_(self._ns_color(self.theme.accent))
        button.setEnabled_(is_enabled(view))
        button.setTarget_(self._bridge)
        button.setAction_("linkPressed:")
        self._controls[id(view)] = button
        parent.addSubview_(button)

    @_IBAction
    def linkPressed_(self, sender) -> None:  # pragma: no cover - UI callback
        for vid, ctrl in self._controls.items():
            if ctrl is sender:
                view = self._find_by_id(vid)
                if not isinstance(view, Link) or not is_enabled(view):
                    return
                if view.action is not None:
                    view.action()
                    return
                environment = getattr(view, "_environment", None)
                action = environment.get(OPEN_URL_ACTION_KEY) if environment is not None else None
                (action if isinstance(action, OpenURLAction) else
                 OpenURLAction(system_opener=self._open_system_url))(view.url)
                return


class AppKitApplication:
    """Launch one or more declarative :class:`Window` scenes."""

    def __init__(self, scene: Window | Settings | MenuBarExtra | WindowGroup,
                 theme: Optional[AppKitTheme] = None,
                 commands: Commands | list[CommandMenu] | tuple[CommandMenu, ...] = ()):
        self.scene = scene
        self.theme = theme or DEFAULT_APPKIT_THEME
        self.commands = commands if isinstance(commands, Commands) else Commands(commands)
        self._bridge = (_ApplicationBridge.alloc().initWithApplication_(self)
                        if _ApplicationBridge is not None else None)
        self.backends: list[AppKitBackend] = []
        scenes = list(scene) if isinstance(scene, WindowGroup) else [scene]
        settings = [item for item in scenes if isinstance(item, Settings)]
        if len(settings) > 1:
            raise ValueError("AppKitApplication supports one Settings scene")
        self._scenes = scenes
        self._settings_scene = settings[0] if settings else None
        self._settings_backend: Optional[AppKitBackend] = None
        self._windows = {item.id: item for item in scenes if isinstance(item, Window)}
        self._window_backends: dict[str, AppKitBackend] = {}
        self._menu_bar_extras = [item for item in scenes if isinstance(item, MenuBarExtra)]
        self._status_items: list = []
        self._status_menu_items: list[tuple[object, MenuItem]] = []
        self._app_command_items: list[tuple[object, MenuItem]] = []

    def _launch(self, window: Window | Settings) -> AppKitBackend:
        backend = AppKitBackend(
            window.make_view,
            theme=self.theme,
            resizable=window.effective_resizable,
            settings_opener=self.open_settings,
            window_opener=self.open_window,
            window_closer=self.dismiss_window,
            scene_id=window.id,
            on_resize=window.on_resize,
            on_focus_changed=window.on_focus_changed,
            on_close=window.on_close,
        )
        backend.run(
            width=int(window.default_size.width),
            height=int(window.default_size.height),
            title=window.title,
            run_async=True,
        )
        self._apply_scene_configuration(window, backend)
        backend._window.makeKeyAndOrderFront_(None)
        backend._present_pending()
        return backend

    @staticmethod
    def _apply_scene_configuration(window: Window | Settings,
                                   backend: AppKitBackend) -> None:  # pragma: no cover
        native = backend._window
        if native is None:
            return
        try:
            native.setContentMinSize_((window.min_size.width, window.min_size.height))
            native.setContentMaxSize_((window.max_size.width, window.max_size.height))
        except Exception:
            pass
        if window.style == WindowStyle.HIDDEN_TITLE_BAR:
            try:
                from AppKit import NSWindowTitleHidden
                native.setTitleVisibility_(NSWindowTitleHidden)
                native.setTitlebarAppearsTransparent_(True)
            except Exception:
                pass
        if window.level == WindowLevel.FLOATING:
            try:
                from AppKit import NSFloatingWindowLevel
                native.setLevel_(NSFloatingWindowLevel)
            except Exception:
                pass
        if (window.restoration_behavior == WindowRestorationBehavior.AUTOMATIC
                and (window.restoration_id or window.id)):
            try:
                native.setFrameAutosaveName_(window.restoration_id or window.id)
            except Exception:
                pass
        AppKitApplication._position_window(native, window.default_position)

    @staticmethod
    def _position_window(native, position) -> None:  # pragma: no cover
        if isinstance(position, Point):
            try: native.setFrameOrigin_((position.x, position.y))
            except Exception: pass
            return
        if position == "center":
            try: native.center()
            except Exception: pass
            return
        try:
            screen = native.screen()
            visible = screen.visibleFrame()
            frame = native.frame()
            left = float(visible.origin.x)
            right = left + float(visible.size.width) - float(frame.size.width)
            bottom = float(visible.origin.y)
            top = bottom + float(visible.size.height) - float(frame.size.height)
            horizontal = {
                "topLeading": left, "bottomLeading": left,
                "top": (left + right) / 2.0, "bottom": (left + right) / 2.0,
                "topTrailing": right, "bottomTrailing": right,
            }[position]
            vertical = top if position.startswith("top") else bottom
            native.setFrameOrigin_((horizontal, vertical))
        except Exception:
            pass

    def open_window(self, window_id: str) -> bool:
        """Open or focus a declared Window scene by stable identifier."""
        window = self._windows.get(window_id)
        if window is None:
            return False
        backend = self._window_backends.get(window_id)
        if backend is None:
            backend = self._launch(window)
            self._window_backends[window_id] = backend
            self.backends.append(backend)
        else:
            backend._window.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        return True

    def dismiss_window(self, window_id: str) -> bool:
        """Dismiss an open Window or Settings scene while retaining its backend."""
        if self._settings_scene is not None and window_id == self._settings_scene.id:
            backend = self._settings_backend
        else:
            backend = self._window_backends.get(window_id)
        if backend is None or backend._window is None:
            return False
        backend._window.performClose_(None)
        return True

    def open_settings(self) -> bool:
        """Open or focus the single Settings window; return whether one exists."""
        if self._settings_scene is None:
            return False
        if self._settings_backend is None:
            self._settings_backend = self._launch(self._settings_scene)
            self.backends.append(self._settings_backend)
        else:
            self._settings_backend._window.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        return True

    @_IBAction
    def openSettings_(self, sender) -> None:  # pragma: no cover - UI callback
        self.open_settings()

    def _install_settings_menu(self, app) -> None:  # pragma: no cover - UI behavior
        if self._settings_scene is None:
            return
        main = app.mainMenu()
        if main is None:
            main = NSMenu.alloc().initWithTitle_("")
            app.setMainMenu_(main)
        app_item = main.itemAtIndex_(0) if main.numberOfItems() else None
        submenu = app_item.submenu() if app_item is not None else None
        if submenu is None:
            app_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("aUI", None, "")
            main.insertItem_atIndex_(app_item, 0)
            submenu = NSMenu.alloc().initWithTitle_("aUI")
            app_item.setSubmenu_(submenu)
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            self._settings_scene.title + "…", "openSettings:", ","
        )
        item.setTarget_(self._bridge)
        submenu.addItem_(item)

    def _ensure_main_menu(self, app):  # pragma: no cover - UI behavior
        main = app.mainMenu()
        if main is None:
            main = NSMenu.alloc().initWithTitle_("")
            app.setMainMenu_(main)
        return main

    def _install_commands(self, app) -> None:  # pragma: no cover - UI behavior
        if not self.commands.menus:
            return
        main = self._ensure_main_menu(app)
        for command_menu in self.commands:
            root = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                command_menu.title, None, ""
            )
            submenu = NSMenu.alloc().initWithTitle_(command_menu.title)
            root.setSubmenu_(submenu)
            main.addItem_(root)
            for item in command_menu.items:
                if isinstance(item, MenuDivider):
                    submenu.addItem_(NSMenuItem.separatorItem())
                    continue
                native = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    item.title, "appCommandPressed:",
                    item.shortcut.key if item.shortcut else "",
                )
                native.setTarget_(self._bridge)
                native.setEnabled_(item.is_enabled)
                if item.shortcut is not None:
                    self._apply_status_shortcut(native, item.shortcut)
                submenu.addItem_(native)
                self._app_command_items.append((native, item))

    @_IBAction
    def appCommandPressed_(self, sender) -> None:  # pragma: no cover
        for native, item in self._app_command_items:
            if native is sender and item.is_enabled:
                item.action()
                for backend in self.backends:
                    backend._refresh_content()
                return

    def _install_menu_bar_extras(self) -> None:  # pragma: no cover - UI behavior
        for extra in self._menu_bar_extras:
            status = NSStatusBar.systemStatusBar().statusItemWithLength_(
                NSVariableStatusItemLength
            )
            button = status.button()
            if extra.system_name:
                try:
                    from AppKit import NSImage
                    image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                        extra.system_name, extra.title or extra.system_name
                    )
                    button.setImage_(image)
                except Exception:
                    button.setTitle_(extra.title)
            else:
                button.setTitle_(extra.title)
            menu = NSMenu.alloc().initWithTitle_(extra.title)
            for item in extra.items:
                if isinstance(item, MenuDivider):
                    menu.addItem_(NSMenuItem.separatorItem())
                    continue
                native = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    item.title, "menuBarItemPressed:",
                    item.shortcut.key if item.shortcut else "",
                )
                native.setTarget_(self._bridge)
                native.setEnabled_(item.is_enabled)
                if item.shortcut is not None:
                    self._apply_status_shortcut(native, item.shortcut)
                menu.addItem_(native)
                self._status_menu_items.append((native, item))
            status.setMenu_(menu)
            self._status_items.append(status)

    @staticmethod
    def _apply_status_shortcut(control, shortcut) -> None:  # pragma: no cover
        try:
            from AppKit import (
                NSEventModifierFlagCommand, NSEventModifierFlagControl,
                NSEventModifierFlagOption, NSEventModifierFlagShift,
            )
            mapping = {
                "command": NSEventModifierFlagCommand,
                "option": NSEventModifierFlagOption,
                "control": NSEventModifierFlagControl,
                "shift": NSEventModifierFlagShift,
            }
            flags = 0
            for name in shortcut.modifiers:
                flags |= mapping[name]
            control.setKeyEquivalentModifierMask_(flags)
        except Exception:
            pass

    @_IBAction
    def menuBarItemPressed_(self, sender) -> None:  # pragma: no cover
        for native, item in self._status_menu_items:
            if native is sender and item.is_enabled:
                item.action()
                return

    def run(self, run_async: bool = False) -> None:
        if not _PYOBJC:  # pragma: no cover - platform dependent
            # Scene examples intentionally use ``AppKitApplication`` as their
            # native-first launcher.  Retain that single entry point on Linux
            # and Windows by delegating ordinary window scenes to the portable
            # ttk scene runner.  A status-bar extra has no portable equivalent,
            # so keep that capability failure explicit instead of silently
            # dropping user-visible application functionality.
            if self._menu_bar_extras:
                raise RuntimeError(
                    "MenuBarExtra requires the native AppKit backend; it has no "
                    "cross-platform StandardBackend equivalent"
                )
            from .standard import StandardApplication, StandardBackend
            if not StandardBackend.available():
                raise RuntimeError(
                    "AppKit application requires PyObjC, or Python with tkinter "
                    "for the StandardBackend fallback: "
                    + StandardBackend.availability_reason()
                )
            StandardApplication(self.scene, commands=self.commands).run()
            return
        app = NSApplication.sharedApplication()
        self._install_settings_menu(app)
        self._install_commands(app)
        self._install_menu_bar_extras()
        for window in self._scenes:
            if isinstance(window, (Settings, MenuBarExtra)):
                continue
            if not window.initially_presented:
                continue
            backend = self._launch(window)
            self._window_backends[window.id] = backend
            self.backends.append(backend)
        app.activateIgnoringOtherApps_(True)
        if not run_async:
            app.run()


__all__ = ["AppKitApplication", "AppKitBackend", "AppKitTheme", "available"]


def available() -> bool:
    """True when the AppKit backend can run (PyObjC importable)."""
    return _PYOBJC
