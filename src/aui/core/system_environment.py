"""SwiftUI-like system environment values and callable environment actions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
from urllib.parse import urlparse
import webbrowser

from .environment import environment
from .state import Environment, EnvironmentValue
from .view import View


class ScenePhase(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BACKGROUND = "background"


class ColorScheme(str, Enum):
    LIGHT = "light"
    DARK = "dark"


class ControlActiveState(str, Enum):
    KEY = "key"
    ACTIVE = "active"
    INACTIVE = "inactive"


class OpenURLDisposition(str, Enum):
    HANDLED = "handled"
    DISCARDED = "discarded"
    SYSTEM_ACTION = "systemAction"


@dataclass(frozen=True)
class OpenURLResult:
    disposition: OpenURLDisposition
    url: Optional[str] = None

    @classmethod
    def handled(cls) -> "OpenURLResult":
        return cls(OpenURLDisposition.HANDLED)

    @classmethod
    def discarded(cls) -> "OpenURLResult":
        return cls(OpenURLDisposition.DISCARDED)

    @classmethod
    def system_action(cls, url: Optional[str] = None) -> "OpenURLResult":
        return cls(OpenURLDisposition.SYSTEM_ACTION, url)


def _valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and (parsed.netloc or parsed.path))


class OpenURLAction:
    """Callable URL policy, mirroring SwiftUI's environment ``openURL`` action."""

    def __init__(self, handler: Optional[Callable[[str], object]] = None,
                 system_opener: Optional[Callable[[str], object]] = None):
        if handler is not None and not callable(handler):
            raise TypeError("OpenURLAction handler must be callable")
        if system_opener is not None and not callable(system_opener):
            raise TypeError("OpenURLAction system_opener must be callable")
        self._handler = handler
        self._system_opener = system_opener or webbrowser.open

    def __call__(self, url: str) -> OpenURLResult:
        value = str(url).strip()
        if not _valid_url(value):
            return OpenURLResult.discarded()
        result = self._handler(value) if self._handler is not None else OpenURLResult.system_action()
        normalized = self._normalize(result)
        if normalized.disposition is OpenURLDisposition.SYSTEM_ACTION:
            target = normalized.url or value
            try:
                return (OpenURLResult.handled() if self._system_opener(target)
                        else OpenURLResult.discarded())
            except Exception:
                return OpenURLResult.discarded()
        return normalized

    @staticmethod
    def _normalize(value: object) -> OpenURLResult:
        if isinstance(value, OpenURLResult):
            return value
        if value is True:
            return OpenURLResult.handled()
        if value is False or value is None:
            return OpenURLResult.discarded()
        raise TypeError("OpenURLAction handler must return OpenURLResult, bool, or None")


class DismissAction:
    """Callable environment action that dismisses the current presentation/window."""

    def __init__(self, callback: Optional[Callable[[], object]] = None):
        if callback is not None and not callable(callback):
            raise TypeError("DismissAction callback must be callable")
        self._callback = callback

    def __call__(self) -> bool:
        if self._callback is None:
            return False
        result = self._callback()
        return True if result is None else bool(result)


SCENE_PHASE_KEY = "scenePhase"
COLOR_SCHEME_KEY = "colorScheme"
CONTROL_ACTIVE_STATE_KEY = "controlActiveState"
OPEN_URL_ACTION_KEY = "openURL"
DISMISS_ACTION_KEY = "dismiss"

scene_phase = EnvironmentValue(SCENE_PHASE_KEY, ScenePhase.ACTIVE)
color_scheme = EnvironmentValue(COLOR_SCHEME_KEY, ColorScheme.LIGHT)
control_active_state = EnvironmentValue(CONTROL_ACTIVE_STATE_KEY, ControlActiveState.KEY)
open_url = EnvironmentValue(OPEN_URL_ACTION_KEY, OpenURLAction())
dismiss = EnvironmentValue(DISMISS_ACTION_KEY, DismissAction())


def system_environment(*, phase: ScenePhase = ScenePhase.ACTIVE,
                       scheme: ColorScheme = ColorScheme.LIGHT,
                       active_state: ControlActiveState = ControlActiveState.KEY,
                       open_url_action: Optional[OpenURLAction] = None,
                       dismiss_action: Optional[DismissAction] = None) -> Environment:
    return Environment({
        SCENE_PHASE_KEY: ScenePhase(phase),
        COLOR_SCHEME_KEY: ColorScheme(scheme),
        CONTROL_ACTIVE_STATE_KEY: ControlActiveState(active_state),
        OPEN_URL_ACTION_KEY: open_url_action or OpenURLAction(),
        DISMISS_ACTION_KEY: dismiss_action or DismissAction(),
    })


def preferred_color_scheme(view: View, scheme: ColorScheme | str) -> View:
    return environment(view, COLOR_SCHEME_KEY, ColorScheme(scheme))


def scene_phase_override(view: View, phase: ScenePhase | str) -> View:
    return environment(view, SCENE_PHASE_KEY, ScenePhase(phase))


def control_active_state_override(view: View, state: ControlActiveState | str) -> View:
    return environment(view, CONTROL_ACTIVE_STATE_KEY, ControlActiveState(state))


def open_url_action(view: View, action: OpenURLAction | Callable[[str], object]) -> View:
    value = action if isinstance(action, OpenURLAction) else OpenURLAction(action)
    return environment(view, OPEN_URL_ACTION_KEY, value)


def dismiss_action(view: View, action: DismissAction | Callable[[], object]) -> View:
    value = action if isinstance(action, DismissAction) else DismissAction(action)
    return environment(view, DISMISS_ACTION_KEY, value)


__all__ = [
    "ColorScheme", "ControlActiveState", "DismissAction", "OpenURLAction",
    "OpenURLDisposition", "OpenURLResult", "ScenePhase", "color_scheme",
    "control_active_state", "control_active_state_override", "dismiss",
    "dismiss_action", "open_url", "open_url_action", "preferred_color_scheme",
    "scene_phase", "scene_phase_override", "system_environment",
]
