"""aUI — a Python UI library that replicates the SwiftUI syntax and features."""

from .core.accessibility import (
    AccessibilityInfo,
    CHILDREN_COMBINE,
    CHILDREN_CONTAIN,
    CHILDREN_IGNORE,
    describe_accessibility,
)
from .core.capabilities import Capability
from .core.animation import (
    Animation, Transaction, with_animation, with_transaction,
)
from .core.animation_modifiers import Namespace
from .core.transitions import (
    ContentTransition, Keyframe, KeyframeAnimator, PhaseAnimator, SymbolEffect,
    Transition,
)
from .core.rendering import BlendMode
from .core.canvas import (
    Canvas, DrawCommand, FillStyle, GraphicsContext, Path, StrokeStyle, TimelineContext,
    TimelineView,
)
from .core.text import (
    AttributeRun, AttributedString,
)
from .core.localization import (
    DynamicTypeSize, Locale, LocalizedStringKey,
)
from .core.preferences import PreferenceKey
from .core.transfer import (
    DataRepresentation, DropInfo, FileRepresentation, TransferPayload, Transferable, UTType,
)
from .core.formats import (
    ByteCountFormatStyle, DateFormatStyle, FormatStyle, ListFormatStyle,
    NumberFormatStyle, ParseableFormatStyle,
)
from .core.interaction import (
    HoverEffect, SensoryFeedback,
)
from .core.container_styles import (
    DisclosureGroupStyle, FormStyle, GroupBoxStyle, ListStyle,
)
from .core.control_group import ControlGroup
from .core.list_editing import (
    EditMode, ListRowAction,
)
from .core.search import DismissSearchAction, SearchToken
from .core.async_actions import RefreshAction, TaskHandle, TaskPhase
from .core.gestures import (
    DragGesture,
    ExclusiveGesture,
    Gesture,
    GestureHandler,
    GestureState,
    LongPressGesture,
    MagnifyGesture,
    MagnifyGestureValue,
    RotateGesture,
    RotateGestureValue,
    SequenceGesture,
    SimultaneousGesture,
    SpatialTapGesture,
    TapGesture,
)
from .core.geometry import Color, EdgeInsets, Font, Point, Rect, Size
from .core.state import (
    Binding, Environment, EnvironmentObject, EnvironmentValue, ObservableObject,
    ObservedObject, State, StateObject, observable,
)
from .core.environment import EnvironmentReader
from .core.system_environment import (
    ColorScheme, ControlActiveState, DismissAction, OpenURLAction,
    OpenURLDisposition, OpenURLResult, ScenePhase, color_scheme,
    control_active_state, dismiss, open_url, scene_phase,
)
from .core.custom_layout import (
    AnyLayout, HStackLayout, Layout, LayoutContainer, LayoutPlacement,
    LayoutSubview, VStackLayout, ZStackLayout,
)
from .core.view import View, ViewModifier
from .core.styles import (
    ButtonStyle, ControlGroupStyle, ControlSize, LabelStyle, PickerStyle,
    ProgressViewStyle, TextFieldStyle, ToggleStyle,
)
from .core.layout import (
    GeometryProxy, GeometryReader, Grid, GridRow, HStack, NavigationSplitView,
    NavigationSplitViewColumn, NavigationSplitViewStyle,
    NavigationSplitViewVisibility, ResponsiveBreakpoint, ResponsiveItem, ResponsiveRow,
    Spacer, VStack, ZStack,
)
from .core.scenes import (
    DismissWindowAction, DismissWindowLink, MenuBarExtra, OpenWindowAction, Settings,
    SettingsLink, Window, WindowGroup, WindowLevel, WindowLink, WindowResizability,
    WindowRestorationBehavior, WindowStyle,
)
from .core.navigation import (
    NavigationBarTitleDisplayMode, NavigationPath,
)
from .core.presentation import PresentationDetent, SnackBarModifier
from .core.commands import (
    CommandMenu, Commands, KeyboardShortcut, Menu, ToolbarItem,
)
from .core.table import SortOrder, Table, TableColumn
from .core.visual_effects import (
    AngularGradient, EllipticalGradient, GradientStop, LinearGradient, Material, RadialGradient,
)
from .core.structural import AnyView, EmptyView, ForEach, GroupBox, OutlineGroup, ViewThatFits
from .core.lazy import GridItem, LazyHGrid, LazyHStack, LazyVGrid, LazyVStack
from .core.scrolling import (
    ScrollIndicatorVisibility, ScrollTargetBehavior, ScrollViewProxy, ScrollViewReader,
)
from .core.focus import FocusState
from .core.inspector import InspectorView
from .core.keyboard import KeyPress, KeyPressResult
from .core.storage import AppStorage, JSONStore, MemoryStore, SceneStorage
from .core.file_dialogs import FileDialogResult
from .core.async_image import AsyncImage, AsyncImagePhase
from .core.components import (
    Button,
    AppBar,
    Capsule,
    Circle,
    ColorPicker,
    DatePicker,
    Ellipse,
    ContentUnavailableView,
    DisclosureGroup,
    Divider,
    Form,
    Group,
    Image,
    IconButton,
    ImageInterpolation,
    ImageResizingMode,
    ImageScale,
    Label,
    LabeledContent,
    Link,
    List,
    NavigationRail,
    NavigationRailDestination,
    NavigationStack,
    NavigationLink,
    Picker,
    PasteButton,
    ProgressView,
    Rectangle,
    RoundedRectangle,
    Gauge,
    ShareLink,
    ScrollView,
    Section,
    SecureField,
    Slider,
    Stepper,
    TabView,
    Text,
    TextField,
    TextEditor,
    Toggle,
    SymbolRenderingMode,
    UnevenRoundedRectangle,
)
__version__ = "0.1.0"

__all__ = [
    # accessibility
    "AccessibilityInfo", "CHILDREN_COMBINE", "CHILDREN_CONTAIN", "CHILDREN_IGNORE",
    "describe_accessibility",
    "Capability",
    # animation
    "Animation", "Transaction",
    "with_animation", "with_transaction", "Namespace",
    "ContentTransition", "Keyframe", "KeyframeAnimator", "PhaseAnimator",
    "SymbolEffect", "Transition",
    "BlendMode",
    "Canvas", "DrawCommand", "FillStyle", "GraphicsContext", "Path", "StrokeStyle",
    "TimelineContext", "TimelineView",
    "AttributeRun", "AttributedString",
    "DynamicTypeSize", "Locale", "LocalizedStringKey",
    "PreferenceKey",
    "DataRepresentation", "DropInfo", "FileRepresentation", "TransferPayload", "Transferable",
    "UTType",
    "ByteCountFormatStyle", "DateFormatStyle", "FormatStyle", "ListFormatStyle",
    "NumberFormatStyle", "ParseableFormatStyle",
    "HoverEffect", "SensoryFeedback",
    "DisclosureGroupStyle", "FormStyle", "GroupBoxStyle", "ListStyle",
    "EditMode", "ListRowAction",
    "DismissSearchAction", "SearchToken",
    "RefreshAction", "TaskHandle", "TaskPhase",
    # gestures
    "DragGesture", "LongPressGesture",
    "ExclusiveGesture", "Gesture", "GestureHandler", "GestureState",
    "MagnifyGesture", "MagnifyGestureValue", "RotateGesture", "RotateGestureValue",
    "SequenceGesture", "SimultaneousGesture", "SpatialTapGesture", "TapGesture",
    # geometry
    "Color", "EdgeInsets", "Font", "Point", "Rect", "Size",
    # state
    "Binding", "Environment", "EnvironmentObject", "EnvironmentReader",
    "EnvironmentValue", "ObservableObject", "ObservedObject", "State",
    "StateObject", "observable",
    "ColorScheme", "ControlActiveState", "DismissAction", "OpenURLAction",
    "OpenURLDisposition", "OpenURLResult", "ScenePhase", "color_scheme",
    "control_active_state", "dismiss", "open_url", "scene_phase",
    # view
    "View", "ViewModifier",
    "ButtonStyle", "ControlGroupStyle", "ControlSize", "LabelStyle", "PickerStyle",
    "ProgressViewStyle", "TextFieldStyle", "ToggleStyle",
    # layout
    "GeometryProxy", "GeometryReader", "Grid", "GridRow", "HStack",
    "NavigationSplitView", "NavigationSplitViewColumn", "NavigationSplitViewStyle",
    "NavigationSplitViewVisibility", "ResponsiveBreakpoint", "ResponsiveItem",
    "ResponsiveRow", "Spacer", "VStack", "ZStack",
    "AnyLayout", "HStackLayout", "Layout", "LayoutContainer", "LayoutPlacement",
    "LayoutSubview", "VStackLayout", "ZStackLayout",
    # scenes
    "DismissWindowAction", "DismissWindowLink", "MenuBarExtra", "OpenWindowAction", "Settings",
    "SettingsLink", "Window", "WindowGroup", "WindowLink",
    "WindowLevel", "WindowResizability", "WindowRestorationBehavior", "WindowStyle",
    "NavigationBarTitleDisplayMode", "NavigationPath",
    # presentation
    "PresentationDetent", "SnackBarModifier",
    # commands
    "CommandMenu", "Commands", "KeyboardShortcut", "Menu", "ToolbarItem",
    # table
    "SortOrder", "Table", "TableColumn",
    # visual effects
    "AngularGradient", "EllipticalGradient", "GradientStop", "LinearGradient", "Material", "RadialGradient",
    # structural views
    "AnyView", "EmptyView", "ForEach", "GroupBox", "OutlineGroup", "ViewThatFits",
    # lazy layouts
    "GridItem", "LazyHGrid", "LazyHStack", "LazyVGrid", "LazyVStack",
    # programmatic scrolling
    "ScrollIndicatorVisibility", "ScrollTargetBehavior", "ScrollViewProxy",
    "ScrollViewReader",
    # focus
    "FocusState", "InspectorView", "KeyPress", "KeyPressResult",
    # file dialogs
    "FileDialogResult",
    # asynchronous images
    "AsyncImage", "AsyncImagePhase",
    # storage
    "AppStorage", "JSONStore", "MemoryStore", "SceneStorage",
    # components
    "AppBar", "Button", "Capsule", "Circle", "ColorPicker", "ContentUnavailableView", "ControlGroup",
    "DatePicker", "DisclosureGroup", "Divider", "Ellipse",
    "Form", "Gauge", "Group", "Image", "IconButton", "ImageInterpolation", "ImageResizingMode", "ImageScale", "Label", "LabeledContent", "Link", "List",
    "NavigationLink", "NavigationRail", "NavigationRailDestination", "NavigationStack", "PasteButton", "Picker", "ProgressView", "Rectangle", "RoundedRectangle",
    "ScrollView", "ShareLink",
    "Section", "SecureField", "Slider", "Stepper",
    "SymbolRenderingMode", "TabView", "Text", "TextEditor", "TextField", "Toggle", "UnevenRoundedRectangle",
    # modifiers are exposed through View methods
    "__version__",
]
