"""aUI — a Python UI library that replicates the SwiftUI syntax and features."""

from .core.animation import Animation, animate, current_animation, with_animation
from .core.geometry import Color, EdgeInsets, Font, Point, Size
from .core.state import Binding, Environment, ObservableObject, State, observable
from .core.view import View, ViewModifier
from .core.layout import HStack, Spacer, VStack, ZStack
from .core.components import (
    Button,
    DatePicker,
    Divider,
    Form,
    Group,
    Image,
    List,
    NavigationStack,
    Picker,
    ProgressView,
    Slider,
    Stepper,
    Text,
    TextField,
    Toggle,
)
from .core.modifiers import (
    animation,
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
    # animation
    "Animation", "animate", "current_animation", "with_animation",
    # geometry
    "Color", "EdgeInsets", "Font", "Point", "Size",
    # state
    "Binding", "Environment", "ObservableObject", "State", "observable",
    # view
    "View", "ViewModifier",
    # layout
    "HStack", "Spacer", "VStack", "ZStack",
    # components
    "Button", "DatePicker", "Divider", "Form", "Group", "Image", "List", "NavigationStack",
    "Picker", "ProgressView", "Slider", "Stepper", "Text", "TextField", "Toggle",
    # modifiers
    "animation", "background", "border", "corner_radius", "font", "foreground_color",
    "frame", "hidden", "on_tap_gesture", "opacity", "padding",
    "__version__",
]
