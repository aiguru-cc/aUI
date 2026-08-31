"""SwiftUI-inspired appearance tokens for the native AppKit backend.

The theme is intentionally made of plain Python values.  Importing and testing
it does not require macOS or PyObjC; the AppKit backend performs the small
conversion to dynamic Cocoa colours at render time.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from ..core.geometry import Color


@dataclass(frozen=True)
class AppKitTheme:
    """Visual design tokens used by :class:`AppKitBackend`.

    ``accent`` is the only fixed colour. Surfaces and text use AppKit semantic
    colours, so they automatically follow macOS light/dark appearance and
    accessibility contrast settings.
    """

    accent: Color = Color(0.04, 0.48, 1.0)
    content_inset: float = 20.0
    section_spacing: float = 14.0
    card_radius: float = 12.0
    control_radius: float = 8.0
    card_border_alpha: float = 0.12
    card_shadow_alpha: float = 0.10
    material: str = "contentBackground"

    def with_accent(self, color: Color) -> "AppKitTheme":
        """Return a copy with a custom app accent colour."""
        return replace(self, accent=color)


DEFAULT_APPKIT_THEME = AppKitTheme()


__all__ = ["AppKitTheme", "DEFAULT_APPKIT_THEME"]
