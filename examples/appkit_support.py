"""Shared, SwiftUI-scene launcher for the native AppKit examples.

Each example remains directly executable after an editable aUI install.  The
default is AppKit on macOS; passing ``--standard`` selects the portable ttk
backend for Windows, Linux, or development machines without PyObjC.
"""
from __future__ import annotations

import sys
from typing import Callable

from aui import Size, View, Window, WindowGroup
from aui.backends.appkit import AppKitApplication, available as appkit_available
from aui.backends.standard import StandardApplication, StandardBackend


def run_window(title: str, content: Callable[[], View] | View, *,
               width: int = 560, height: int = 420) -> None:
    """Run one declarative scene with native-first, explicit fallback policy."""
    scene = Window(title, content, default_size=Size(float(width), float(height)))
    if "--standard" not in sys.argv and appkit_available():
        AppKitApplication(scene).run()
        return
    if not StandardBackend.available():
        reason = StandardBackend.availability_reason()
        raise RuntimeError(
            "No graphical backend is available. Install PyObjC on macOS or use "
            f"a Python distribution with tkinter. {reason}"
        )
    StandardApplication(scene).run()


def run_scenes(scenes: WindowGroup) -> None:
    """Run a multi-window scene set with the same backend selection policy."""
    if "--standard" not in sys.argv and appkit_available():
        AppKitApplication(scenes).run()
        return
    if not StandardBackend.available():
        reason = StandardBackend.availability_reason()
        raise RuntimeError(
            "No graphical backend is available. Install PyObjC on macOS or use "
            f"a Python distribution with tkinter. {reason}"
        )
    StandardApplication(scenes).run()


__all__ = ["run_scenes", "run_window"]
