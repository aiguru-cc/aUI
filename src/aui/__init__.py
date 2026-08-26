"""aUI — a Python UI library that replicates the SwiftUI syntax and features."""

from .core.geometry import Color, EdgeInsets, Font, Point, Size
from .core.state import Binding, Environment, ObservableObject, State, observable
from .core.view import View, ViewModifier
from .core.layout import HStack, Spacer, VStack, ZStack
from .core.components import (
    Button,
    Divider,
    Group,
    Image,
    List,
    Picker,
    Slider,
    Text,
    TextField,
    Toggle,
)
from .core.modifiers import (
    background,
    border,
    corner_radius,
    font,
    foreground_color,
    frame,
    hidden,
    on_tap_gesture,
    opacity,
    padding,
)

__version__ = "0.1.0"

__all__ = [
    # geometry
    "Color", "EdgeInsets", "Font", "Point", "Size",
    # state
    "Binding", "Environment", "ObservableObject", "State", "observable",
    # view
    "View", "ViewModifier",
    # layout
    "HStack", "Spacer", "VStack", "ZStack",
    # components
    "Button", "Divider", "Group", "Image", "List", "Picker", "Slider",
    "Text", "TextField", "Toggle",
    # modifiers
    "background", "border", "corner_radius", "font", "foreground_color",
    "frame", "hidden", "on_tap_gesture", "opacity", "padding",
    "__version__",
]
