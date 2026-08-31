"""Declarative application scenes and native window descriptions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Union

from .components import Button
from .commands import MenuDivider, MenuItem, normalize_menu_items
from .geometry import Point, Size
from .view import View

ViewSource = Union[View, Callable[[], View]]


class WindowStyle:
    AUTOMATIC = "automatic"
    TITLE_BAR = "titleBar"
    HIDDEN_TITLE_BAR = "hiddenTitleBar"


class WindowResizability:
    AUTOMATIC = "automatic"
    CONTENT_SIZE = "contentSize"
    CONTENT_MIN_SIZE = "contentMinSize"


class WindowLevel:
    NORMAL = "normal"
    FLOATING = "floating"


class WindowRestorationBehavior:
    AUTOMATIC = "automatic"
    DISABLED = "disabled"


def _validate_window_configuration(scene) -> None:
    if scene.style not in (WindowStyle.AUTOMATIC, WindowStyle.TITLE_BAR,
                            WindowStyle.HIDDEN_TITLE_BAR):
        raise ValueError("unsupported window style")
    if scene.window_resizability not in (
        WindowResizability.AUTOMATIC, WindowResizability.CONTENT_SIZE,
        WindowResizability.CONTENT_MIN_SIZE,
    ):
        raise ValueError("unsupported window resizability")
    if scene.level not in (WindowLevel.NORMAL, WindowLevel.FLOATING):
        raise ValueError("unsupported window level")
    if scene.restoration_behavior not in (
        WindowRestorationBehavior.AUTOMATIC, WindowRestorationBehavior.DISABLED,
    ):
        raise ValueError("unsupported window restoration behavior")
    if not isinstance(scene.default_position, (str, Point)):
        raise TypeError("default_position must be a named position or Point")
    if isinstance(scene.default_position, str) and scene.default_position not in (
        "center", "topLeading", "top", "topTrailing", "bottomLeading", "bottom",
        "bottomTrailing",
    ):
        raise ValueError("unsupported default window position")
    if scene.min_size.width > scene.max_size.width or scene.min_size.height > scene.max_size.height:
        raise ValueError("window min_size cannot exceed max_size")
    for name in ("on_resize", "on_focus_changed", "on_close"):
        callback = getattr(scene, name, None)
        if callback is not None and not callable(callback):
            raise TypeError(f"{name} must be callable")


@dataclass(frozen=True)
class Window:
    """A platform window and the root view it presents."""

    title: str
    content: ViewSource
    id: str = "main"
    default_size: Size = Size(900.0, 640.0)
    resizable: bool = True
    initially_presented: bool = True
    style: str = WindowStyle.AUTOMATIC
    window_resizability: str = WindowResizability.AUTOMATIC
    default_position: str | Point = "center"
    min_size: Size = Size(160.0, 120.0)
    max_size: Size = Size(float("inf"), float("inf"))
    level: str = WindowLevel.NORMAL
    restoration_behavior: str = WindowRestorationBehavior.AUTOMATIC
    restoration_id: str = ""
    on_resize: Optional[Callable[[Size], None]] = None
    on_focus_changed: Optional[Callable[[bool], None]] = None
    on_close: Optional[Callable[[], None]] = None

    def __post_init__(self) -> None:
        _validate_window_configuration(self)

    @property
    def effective_resizable(self) -> bool:
        if self.window_resizability == WindowResizability.CONTENT_SIZE:
            return False
        return self.resizable

    def make_view(self) -> View:
        return self.content() if callable(self.content) else self.content


@dataclass(frozen=True)
class Settings:
    """A lazily opened, single-instance application settings scene."""

    content: ViewSource
    title: str = "Settings"
    id: str = "settings"
    default_size: Size = Size(620.0, 480.0)
    resizable: bool = True
    style: str = WindowStyle.AUTOMATIC
    window_resizability: str = WindowResizability.AUTOMATIC
    default_position: str | Point = "center"
    min_size: Size = Size(320.0, 220.0)
    max_size: Size = Size(float("inf"), float("inf"))
    level: str = WindowLevel.NORMAL
    restoration_behavior: str = WindowRestorationBehavior.AUTOMATIC
    restoration_id: str = ""
    on_resize: Optional[Callable[[Size], None]] = None
    on_focus_changed: Optional[Callable[[bool], None]] = None
    on_close: Optional[Callable[[], None]] = None

    def __post_init__(self) -> None:
        _validate_window_configuration(self)

    @property
    def effective_resizable(self) -> bool:
        if self.window_resizability == WindowResizability.CONTENT_SIZE:
            return False
        return self.resizable

    def make_view(self) -> View:
        return self.content() if callable(self.content) else self.content


@dataclass(frozen=True)
class MenuBarExtra:
    """A native macOS menu-bar status item scene."""

    title: str
    items: Sequence[View]
    id: str = "menu-bar-extra"
    system_name: str = ""

    def __post_init__(self) -> None:
        if not self.title and not self.system_name:
            raise ValueError("MenuBarExtra requires a title or system_name")
        object.__setattr__(self, "items", normalize_menu_items(self.items))


class SettingsLink(Button):
    """A button that asks the current application to open its Settings scene."""

    def __init__(self, title: str = "Settings…"):
        self._settings_opener: Optional[Callable[[], None]] = None
        super().__init__(title, self._open)

    def _open(self) -> None:
        if self._settings_opener is not None:
            self._settings_opener()

    def connect(self, opener: Optional[Callable[[], None]]) -> None:
        self._settings_opener = opener


class OpenWindowAction:
    """Callable environment-style action for opening a scene by identifier."""

    def __init__(self, action: Callable[[str], bool]):
        if not callable(action):
            raise TypeError("OpenWindowAction requires a callable")
        self._action = action

    def __call__(self, window_id: str) -> bool:
        if not window_id:
            raise ValueError("window_id cannot be empty")
        return bool(self._action(window_id))


class DismissWindowAction:
    """Callable environment-style action for dismissing a window scene."""

    def __init__(self, action: Callable[[Optional[str]], bool], current_id: Optional[str] = None):
        if not callable(action):
            raise TypeError("DismissWindowAction requires a callable")
        self._action = action
        self.current_id = current_id

    def __call__(self, window_id: Optional[str] = None) -> bool:
        target = window_id or self.current_id
        if not target:
            return False
        return bool(self._action(target))


class WindowLink(Button):
    """A button that opens or focuses a declared Window by ID."""

    def __init__(self, title: str, window_id: str):
        if not window_id:
            raise ValueError("WindowLink window_id cannot be empty")
        self.window_id = window_id
        self._window_opener: Optional[Callable[[str], bool]] = None
        super().__init__(title, self._open)

    def _open(self) -> None:
        if self._window_opener is not None:
            self._window_opener(self.window_id)

    def connect(self, opener: Optional[Callable[[str], bool]]) -> None:
        self._window_opener = opener


class DismissWindowLink(Button):
    """A button that dismisses the current or a specifically identified window."""

    def __init__(self, title: str = "Close", window_id: Optional[str] = None):
        self.window_id = window_id
        self._dismiss_action: Optional[DismissWindowAction] = None
        super().__init__(title, self._dismiss)

    def _dismiss(self) -> None:
        if self._dismiss_action is not None:
            self._dismiss_action(self.window_id)

    def connect(self, action: Optional[DismissWindowAction]) -> None:
        self._dismiss_action = action


class WindowGroup:
    """A declarative collection of windows launched in one application."""

    def __init__(self, windows: Sequence[Window | Settings | MenuBarExtra]):
        self.windows = list(windows)
        ids = [window.id for window in self.windows]
        if len(ids) != len(set(ids)):
            raise ValueError("Scene ids must be unique within a WindowGroup")

    def __iter__(self):
        return iter(self.windows)


__all__ = [
    "DismissWindowAction", "DismissWindowLink", "MenuBarExtra", "OpenWindowAction",
    "Settings", "SettingsLink", "Window", "WindowGroup", "WindowLevel", "WindowLink",
    "WindowResizability", "WindowRestorationBehavior", "WindowStyle",
]
