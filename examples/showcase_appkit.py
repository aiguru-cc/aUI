"""Example: aUI in a **native macOS window** (AppKit / Cocoa, no Tk).

Run:  python3 examples/showcase_appkit.py
     (or) python3 examples/run_showcase.py --appkit

This opens a real, resizable macOS window rendered entirely with the native
AppKit framework through PyObjC — the same framework SwiftUI wraps on macOS.
There is **no Tkinter and no third-party GUI toolkit**: every control is a
genuine Cocoa ``NSControl`` (``NSButton``, ``NSSwitch``, ``NSSlider``,
``NSPopUpButton``, ``NSStepper``, ``NSDatePicker``, ``NSColorWell``,
``NSProgressIndicator`` …).

The view tree is the *same* ``make_view()`` from ``examples/showcase_view.py``
used by the curses terminal and ASCII backends, so the native window and the
terminal demonstrate identical components. All state is two-way bound: editing
a native control writes straight back into the aUI ``State`` / ``Binding``.

Prerequisite::

    python3 -m pip install pyobjc-framework-Cocoa

Usage::

    python3 examples/showcase_appkit.py                # open the window
    python3 examples/showcase_appkit.py --check        # report availability

Controls: the window is a real macOS window — use the mouse/trackpad and the
standard macOS controls (text fields, switches, sliders, pop-up menus, …).
"""
import sys

from showcase_view import make_view

from aui.backends.appkit import AppKitBackend, AppKitTheme, available
from aui import Color


def _check() -> int:
    print(f"PyObjC (AppKit) available : {'yes' if available() else 'no'}")
    if not available():
        print("Install with:  python3 -m pip install pyobjc-framework-Cocoa")
        return 1
    from AppKit import NSApplication
    app = NSApplication.sharedApplication()
    print(f"NSApplication            : {app!r}")
    print(f"backend available()      : {AppKitBackend.available()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if "--check" in args:
        return _check()
    if not available():
        return _check()
    theme = AppKitTheme().with_accent(Color.indigo)
    backend = AppKitBackend(make_view, theme=theme)
    print("[showcase_appkit] opening native AppKit window …")
    print("[showcase_appkit] close the window (⌘W) or press ⌘Q to quit.")
    backend.run(width=620, height=480, title="aUI · Native AppKit Window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
