"""Cross-platform visual tokens for the standard desktop backend."""
from __future__ import annotations

from dataclasses import dataclass

from ..core.geometry import Color


@dataclass(frozen=True)
class StandardTheme:
    background: Color = Color(0.965, 0.965, 0.975)
    surface: Color = Color(1.0, 1.0, 1.0)
    primary: Color = Color(0.11, 0.11, 0.12)
    secondary: Color = Color(0.42, 0.42, 0.46)
    accent: Color = Color(0.0, 0.478, 1.0)
    separator: Color = Color(0.82, 0.82, 0.85)
    destructive: Color = Color(1.0, 0.23, 0.19)
    font_family: str = "TkDefaultFont"
    font_size: int = 13
    control_height: int = 28
    corner_radius: int = 8
    spacing: int = 8
    content_padding: int = 16
    # SwiftUI Dynamic Type analogue.  A single scale keeps typography
    # consistent across every native control created by StandardBackend.
    font_scale: float = 1.0

    def __post_init__(self) -> None:
        if not 0.5 <= float(self.font_scale) <= 3.0:
            raise ValueError("font_scale must be between 0.5 and 3.0")

    def scaled_font_size(self, size: float | None = None) -> int:
        """Return a clamped, platform-friendly point size."""
        base = self.font_size if size is None else size
        return max(8, round(float(base) * self.font_scale))


DEFAULT_STANDARD_THEME = StandardTheme()


def color_hex(color: Color) -> str:
    values = (color.red, color.green, color.blue)
    return "#" + "".join(f"{round(max(0.0, min(1.0, value)) * 255):02x}" for value in values)


__all__ = ["DEFAULT_STANDARD_THEME", "StandardTheme", "color_hex"]
