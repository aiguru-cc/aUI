"""Example: the aUI showcase — every component and feature in one window.

Native curses backend (no Tk, no display server, no third-party deps).

Run:  python3 examples/run_showcase.py
     (or) python3 examples/showcase_curses.py

The view tree lives in ``examples/showcase_view.py`` and is shared by every
backend (curses terminal / ASCII headless / AppKit native window), so the
terminal and the native macOS window demonstrate exactly the same components.

Controls
--------
    Tab / Up / Down     move focus between interactive components
    Enter               activate the focused button / toggle / tap
    Left / Right        adjust focused slider / picker / stepper / date / color
    Type / Backspace    edit the focused text field / secure field
    PageUp / PageDown   scroll the page (or the focused list)
    h                   help
    q                   quit
"""

from showcase_view import (
    animated_index,
    color_choice,
    color_value,
    deadline,
    disabled_flag,
    drag,
    enabled,
    expanded,
    held,
    make_view,
    model,
    name,
    password,
    progress,
    qty,
    settings,
    tab_index,
    taps,
    volume,
)
from aui.backends.curses import CursesBackend

__all__ = ["make_view"]


def _run_ascii(reason: str | None = None) -> None:
    """Headless render of the full showcase view tree as text art.

    Uses the curses backend's ``render_to_string`` (correct layout, multi-line
    text, all components) on the exact same ``make_view()`` tree — only the
    interaction is disabled.
    """
    backend = CursesBackend(make_view)
    print(backend.render_to_string(width=96, height=52))
    print("\n== Accessibility tree (roles/labels/hints/values) ==")
    info = backend.describe_accessibility()
    print(info.summary())
    if reason:
        print(f"\n[headless] ASCII render because: {reason}")
    print(
        "\n[headless] Interactive window needs a real TTY. "
        "Run inside a terminal to open the interactive curses UI: "
        "python3 examples/run_showcase.py\n"
    )


def main() -> None:
    import sys

    # Honour the same CLI surface as run_showcase.py.
    ascii_mode = "--ascii" in sys.argv
    reason = None
    if not ascii_mode:
        if not sys.stdin.isatty():
            reason = "stdin is not a TTY (piped/CI)"
            ascii_mode = True

    if ascii_mode:
        return _run_ascii(reason)

    backend = CursesBackend(make_view)

    # Connect every State / observable to a re-render hook that also prints
    # the accessibility tree, so you can watch the semantics update live.
    def on_state_change() -> None:
        try:
            print(backend.describe_accessibility().summary())
        except Exception:
            pass

    owner_type = type("Owner", (), {"_invalidate": staticmethod(on_state_change)})
    for s in (
        name, password, enabled, volume, qty, color_choice, color_value, deadline,
        progress, animated_index, taps, held, drag, disabled_flag, expanded, tab_index,
    ):
        s._owner = owner_type()
    model.add_listener(on_state_change)
    settings.add_listener(on_state_change)

    backend.run()


if __name__ == "__main__":
    main()
