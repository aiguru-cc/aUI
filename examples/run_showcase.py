#!/usr/bin/env python3
"""Run the aUI full-feature showcase (native curses backend, no Tk).

``examples/showcase_curses.py`` demonstrates every component and feature of
aUI in a single interactive terminal window, using the standard-library
``curses`` backend — no Tkinter, no display server, no third-party
dependencies.

This runner:

    1. curses   — interactive terminal window (the native backend; works in
                  any terminal). Requires a real TTY; degrades to ASCII when
                  stdin is not a TTY (e.g. piped / CI).
    2. ASCII    — always works: renders the *same* full view tree as text art
                  plus the accessibility hierarchy (zero dependencies).

If no interactive TTY is available the script keeps running and falls back to
the ASCII render instead of failing.

Usage::

    python3 examples/run_showcase.py             # auto: curses (or ASCII)
    python3 examples/run_showcase.py --ascii     # force the headless ASCII render
    python3 examples/run_showcase.py --check     # report the environment only
    python3 examples/run_showcase.py --python /path/to/python3   # explicit interpreter
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOWCASE = os.path.join(PROJECT_ROOT, "examples", "showcase_curses.py")
SHOWCASE_APPKIT = os.path.join(PROJECT_ROOT, "examples", "showcase_appkit.py")
MIN_PY = (3, 10)


def _default_candidates() -> list[str]:
    """Interpreter paths to try, best first (current one first)."""
    return [
        sys.executable,
        "/usr/bin/python3",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "python3.13",
        "python3.12",
        "python3.11",
        "python3.10",
        "python3",
    ]


def _version_of(py: str):
    """Return (major, minor) of ``py``, or None if it cannot run."""
    try:
        r = subprocess.run(
            [py, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode != 0:
            return None
        major, minor = r.stdout.strip().split(".")
        return (int(major), int(minor))
    except Exception:
        return None


def _has_curses(py: str) -> bool:
    """curses ships with CPython on macOS/Linux (windows has ``windows-curses``)."""
    try:
        r = subprocess.run(
            [py, "-c", "import curses"],
            capture_output=True, text=True, timeout=20,
        )
        return r.returncode == 0
    except Exception:
        return False


def _has_appkit(py: str) -> bool:
    """True when ``py`` can import the PyObjC AppKit backend (native window)."""
    try:
        r = subprocess.run(
            [py, "-c", "import objc, AppKit"],
            capture_output=True, text=True, timeout=20,
        )
        return r.returncode == 0
    except Exception:
        return False


def _interpreter_report() -> list[str]:
    lines = []
    seen = set()
    import shutil
    for py in _default_candidates():
        resolved = shutil.which(py) or py
        if resolved in seen:
            continue
        seen.add(resolved)
        ver = _version_of(py)
        cu = _has_curses(py) if ver else False
        ak = _has_appkit(py) if ver else False
        ver_s = ".".join(map(str, ver)) if ver else "-"
        state = "usable"
        if ver is None:
            state = "not found"
        elif ver < MIN_PY:
            state = "too old (aUI needs >= 3.10)"
        elif not cu:
            state = "no curses -> ASCII fallback"
        else:
            state = "usable -> curses GUI"
        extra = f" appkit={'yes' if ak else 'no'}"
        lines.append(
            f"  {py:<26} python {ver_s:<8} curses={'yes' if cu else 'no':<4}{extra} {state}"
        )
    return lines


def _run(py: str, extra: list[str] | None = None) -> int:
    cmd = [py, SHOWCASE] + (extra or [])
    print(f"[run_showcase] exec: {' '.join(cmd)}")
    return subprocess.call(cmd)


def _run_appkit(py: str) -> int:
    cmd = [py, SHOWCASE_APPKIT]
    print(f"[run_showcase] exec: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ascii", action="store_true",
                   help="force the headless ASCII render (no terminal).")
    p.add_argument("--appkit", action="store_true",
                   help="force the native macOS AppKit window (requires PyObjC).")
    p.add_argument("--check", action="store_true",
                   help="report the environment and exit.")
    p.add_argument("--python", default=None, metavar="PY",
                   help="explicit Python interpreter to use for the showcase.")
    args = p.parse_args(argv)

    if args.check:
        print("Environment report (aUI showcase):")
        print("\n".join(_interpreter_report()))
        isatty = sys.stdin.isatty()
        print(f"\nstdin is a TTY: {'yes' if isatty else 'no'}")
        print("Backends: curses (terminal, stdlib) · appkit (native macOS window,"
              " PyObjC) · ascii (headless). No Tk.")
        return 0

    if args.appkit:
        # Force the native window. Pick a Python that has AppKit.
        candidates = [args.python] if args.python else _default_candidates()
        for py in candidates:
            ver = _version_of(py)
            if ver is None or ver < MIN_PY:
                continue
            if _has_appkit(py):
                if py != sys.executable:
                    print(f"[run_showcase] using {py} (has PyObjC) for the native window.\n")
                return _run_appkit(py)
        print("[run_showcase] no Python with PyObjC (AppKit) found.")
        print("[run_showcase] install with:  python3 -m pip install pyobjc-framework-Cocoa\n")
        return _run_appkit(args.python or sys.executable)

    if args.ascii:
        # Force headless ASCII; honour an explicit interpreter if given.
        return _run(args.python or sys.executable, ["--ascii"])

    # Pick the first interpreter that is >= 3.10 AND has curses.
    candidates = [args.python] if args.python else _default_candidates()
    usable = None
    for py in candidates:
        ver = _version_of(py)
        if args.python:
            if ver is not None and _has_curses(py):
                usable = py
                break
            continue
        if ver is None or ver < MIN_PY:
            continue
        if _has_curses(py):
            usable = py
            break

    if usable is None:
        print("[run_showcase] no Python with curses (>= 3.10) found.")
        print("[run_showcase] running the showcase headless instead — it will "
              "render the full component tree as ASCII art plus the "
              "accessibility hierarchy.\n")
        return _run(args.python if args.python else sys.executable)

    if usable != sys.executable:
        print(f"[run_showcase] using {usable} (has curses) for the interactive showcase.\n")

    if not sys.stdin.isatty():
        # No TTY: curses cannot run interactively; the showcase detects this
        # and renders ASCII with an accurate reason. On a macOS graphical
        # session with PyObjC installed you can instead run:
        #   python3 examples/run_showcase.py --appkit
        print("[run_showcase] stdin is not a TTY (piped/CI) — the showcase "
              "will render as ASCII instead of opening an interactive window.")
        print("[run_showcase] on a macOS desktop session you can open the native "
              "window with:  python3 examples/run_showcase.py --appkit\n")
    return _run(usable)


if __name__ == "__main__":
    raise SystemExit(main())
