"""Desktop, terminal and headless render backends for aUI.

All built-in backends are importable from this module.  Optional native
bridges (AppKit/PyObjC) remain safe to import when their platform dependency
is unavailable; use ``available()`` before launching them.
"""

from .ascii import AsciiBackend
from .curses import CursesBackend
from .appkit import AppKitApplication, AppKitBackend, AppKitTheme, available as appkit_available
from .standard import StandardApplication, StandardBackend, available as standard_available
from .standard_theme import StandardTheme

__all__ = [
    "AppKitApplication", "AppKitBackend", "AppKitTheme", "appkit_available",
    "AsciiBackend", "CursesBackend",
    "StandardApplication", "StandardBackend", "StandardTheme", "standard_available",
]
