"""Print the explicit feature matrix for the installed aUI renderers."""

from aui import Capability
from aui.backends.appkit import AppKitBackend
from aui.backends.ascii import AsciiBackend
from aui.backends.curses import CursesBackend
from aui.backends.standard import StandardBackend


def main() -> int:
    features = sorted(Capability.ALL)
    renderers = (
        ("AppKit", AppKitBackend), ("Standard", StandardBackend),
        ("ASCII", AsciiBackend), ("Curses", CursesBackend),
    )
    print("feature".ljust(24), *(name.ljust(10) for name, _ in renderers))
    for feature in features:
        values = ("native" if renderer.supports(feature) else "—"
                  for _, renderer in renderers)
        print(feature.ljust(24), *(value.ljust(10) for value in values))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
