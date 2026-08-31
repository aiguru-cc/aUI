"""UI components for aUI.

Mirrors SwiftUI's core controls: ``Text``, ``Button``, ``TextField``,
``Toggle``, ``Slider``, ``Picker``, ``Image``, ``Divider`` and ``List``.
Components are declarative descriptions; the render backend turns them into
native widgets.
"""
from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence

from .geometry import Color, EdgeInsets, Font, Point, Size
from .state import Binding
from .view import View


class Text(View):
    """Static or dynamic text with multi-line layout (mirrors SwiftUI Text).

    Supports explicit line breaks (``\\n``), word-wrapping to a proposal width,
    ``line_limit`` truncation and ``line_spacing``. Text measurement accounts
    for CJK full-width characters (double width) vs. ASCII (single width).
    """

    def __init__(
        self,
        content: Any = "",
        font: Optional[Font] = None,
        color: Optional[Color] = None,
        line_limit: Optional[int] = None,
        line_spacing: float = 0.0,
        format=None,
    ):
        from .localization import LocalizedStringKey
        from .text import AttributedString
        self._attributed = content if isinstance(content, AttributedString) else None
        self._localized = content if isinstance(content, LocalizedStringKey) else None
        self._format_style = format
        self._raw_value = content
        if format is not None:
            from .formats import FormatStyle
            if not isinstance(format, FormatStyle): raise TypeError("Text format must be a FormatStyle")
        self._content = content.text if self._attributed is not None else str(content)
        self._font = font or Font.body()
        self._color = color
        self._line_limit = line_limit
        self._line_spacing = line_spacing
        self._children = []

    @property
    def content(self) -> str:
        return self._content

    @property
    def display_content(self) -> str:
        from .localization import LOCALE_KEY, semantic_value
        from .text import text_style_value
        content = self._content
        if self._format_style is not None:
            environment = getattr(self, "_environment", None)
            locale_value = environment.get(LOCALE_KEY) if environment else None
            content = self._format_style.format(self._raw_value, locale_value)
        if self._localized is not None:
            environment = getattr(self, "_environment", None)
            content = self._localized.resolve(environment.get(LOCALE_KEY) if environment else None)
        if semantic_value(self, "redacted"):
            return "█" * max(3, len(content))
        case = text_style_value(self, "text_case")
        if case == "uppercase":
            return content.upper()
        if case == "lowercase":
            return content.lower()
        return content

    @property
    def effective_font_size(self) -> float:
        from .localization import DYNAMIC_TYPE_SCALE, DYNAMIC_TYPE_SIZE_KEY, DynamicTypeSize
        environment = getattr(self, "_environment", None)
        size = environment.get(DYNAMIC_TYPE_SIZE_KEY, DynamicTypeSize.LARGE) if environment else DynamicTypeSize.LARGE
        return self.effective_font.size * DYNAMIC_TYPE_SCALE.get(size, 1.0)

    @property
    def effective_font(self) -> Font:
        from .modifiers import visual_style_value
        return visual_style_value(self, "font", self._font)

    @property
    def effective_color(self) -> Optional[Color]:
        from .modifiers import visual_style_value
        return visual_style_value(self, "foreground_color", self._color)

    @property
    def attributed_string(self):
        return self._attributed

    @property
    def line_limit(self) -> Optional[int]:
        return self._line_limit

    @property
    def line_spacing(self) -> float:
        return self._line_spacing

    # -- Text measurement ---------------------------------------------------
    @staticmethod
    def _char_width(ch: str, font_size: float) -> float:
        """Approximate glyph width: CJK full-width chars are double width."""
        if ord(ch) > 0x2E7F:  # CJK / full-width ranges
            return font_size
        return font_size * 0.55

    def _measure_line(self, line: str) -> float:
        return sum(self._char_width(ch, self.effective_font_size) for ch in line)

    def _wrap_line(self, line: str, max_width: float) -> list:
        """Greedy word wrap of a single logical line into visual lines."""
        if max_width == float("inf") or max_width <= 0:
            return [line] if line else [""]
        words = line.split(" ")
        if not words:
            return [""]
        lines: list = []
        current = ""
        current_w = 0.0
        for word in words:
            word_w = self._measure_line(word)
            sep_w = self._char_width(" ", self.effective_font_size)
            if current and current_w + sep_w + word_w > max_width:
                lines.append(current)
                current = word
                current_w = word_w
            else:
                if current:
                    current += " "
                    current_w += sep_w
                current += word
                current_w += word_w
        if current:
            lines.append(current)
        return lines or [""]

    def _layout_lines(self, proposal_width: float) -> list:
        """Return the visual lines (wrapped, truncated) for this text."""
        content = self.display_content
        if not content:
            return []
        lines: list = []
        for logical in content.split("\n"):
            lines.extend(self._wrap_line(logical, proposal_width))
        if self._line_limit is not None and len(lines) > self._line_limit:
            lines = lines[: self._line_limit]
        return lines

    def size_that_fits(self, proposal: Size) -> Size:
        lines = self._layout_lines(proposal.width)
        if not lines:
            return Size(0.0, 0.0)
        width = max(self._measure_line(line) for line in lines)
        line_height = self.effective_font_size * 1.4
        height = line_height * len(lines) + self._line_spacing * max(0, len(lines) - 1)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Button(View):
    """A clickable button with SwiftUI ``destructive``/``cancel`` roles."""

    ROLES = (None, "destructive", "cancel")

    def __init__(
        self,
        title: str,
        action: Callable[[], None],
        role: Optional[str] = None,
    ):
        if role not in self.ROLES:
            raise ValueError("Button role must be None, destructive, or cancel")
        self._title = title
        self._action = action
        self._role = role
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def action(self) -> Callable[[], None]:
        return self._action

    @property
    def role(self) -> Optional[str]:
        return self._role

    def size_that_fits(self, proposal: Size) -> Size:
        width = max(64.0, len(self._title) * 8.0 + 24.0)
        return Size(width, 32.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class IconButton(Button):
    """A compact button backed by an SF Symbol (Flet's IconButton analogue)."""

    def __init__(self, system_name: str, action: Callable[[], None], *, label: str = "",
                 role: Optional[str] = None):
        if not str(system_name):
            raise ValueError("IconButton system_name cannot be empty")
        self.system_name = str(system_name)
        self.label = str(label) or self.system_name
        super().__init__(self.label, action, role)

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(34.0, 32.0)


class ShareLink(Button):
    """A button that presents the platform sharing services for one or more items."""

    def __init__(self, item: Any, title: str = "Share…", subject: str = "",
                 message: str = "",
                 share_handler: Optional[Callable[[tuple[Any, ...]], None]] = None):
        items = tuple(item) if isinstance(item, (list, tuple)) else (item,)
        if not items:
            raise ValueError("ShareLink requires at least one item")
        self.items = items
        self.subject = str(subject)
        self.message = str(message)
        self._share_handler = share_handler
        super().__init__(title, self._share)

    def _share(self) -> None:
        if self._share_handler is not None:
            self._share_handler(self.items)

    def connect(self, handler: Optional[Callable[[tuple[Any, ...]], None]]) -> None:
        self._share_handler = handler


class PasteButton(Button):
    """Read text from the platform pasteboard into a Binding or callback."""

    def __init__(self, title: str = "Paste", text: Optional[Binding[str]] = None,
                 on_paste: Optional[Callable[[str], None]] = None,
                 provider: Optional[Callable[[], Optional[str]]] = None):
        if text is None and on_paste is None:
            raise ValueError("PasteButton requires a text binding or on_paste callback")
        if on_paste is not None and not callable(on_paste):
            raise TypeError("PasteButton on_paste must be callable")
        self.text = text
        self.on_paste = on_paste
        self._paste_provider = provider
        super().__init__(title, self._paste)

    def _paste(self) -> None:
        if self._paste_provider is None:
            return
        value = self._paste_provider()
        if value is None:
            return
        value = str(value)
        if self.text is not None:
            self.text.value = value
        if self.on_paste is not None:
            self.on_paste(value)

    def connect(self, provider: Optional[Callable[[], Optional[str]]]) -> None:
        self._paste_provider = provider


class TextField(View):
    """A single-line text input (mirrors SwiftUI TextField).

    Use the inherited ``.disabled()`` modifier to block editing.
    """

    def __init__(self, text: Optional[Binding[str]] = None, placeholder: str = "",
                 *, value: Optional[Binding] = None, format=None):
        if (text is None) == (value is None):
            raise ValueError("TextField requires exactly one of text or value")
        if value is not None:
            from .formats import ParseableFormatStyle
            if not isinstance(format, ParseableFormatStyle):
                raise TypeError("value TextField requires a ParseableFormatStyle")
        elif format is not None:
            raise ValueError("format is only valid with a value binding")
        self._value_binding = value
        self._format_style = format
        self._validation_error = None
        self._text = text if text is not None else Binding(
            getter=self._formatted_value,
            setter=self._parse_value,
        )
        self._placeholder = placeholder
        self._children = []

    def _locale(self):
        from .localization import LOCALE_KEY
        environment = getattr(self, "_environment", None)
        return environment.get(LOCALE_KEY) if environment else None

    def _formatted_value(self) -> str:
        return self._format_style.format(self._value_binding.wrapped_value, self._locale())

    def _parse_value(self, text: str) -> None:
        try:
            value = self._format_style.parse(text, self._locale())
        except (TypeError, ValueError) as exc:
            self._validation_error = str(exc)
            return
        self._validation_error = None
        self._value_binding.wrapped_value = value

    @property
    def value(self):
        return self._value_binding

    @property
    def validation_error(self):
        return self._validation_error

    @property
    def text(self) -> Binding[str]:
        return self._text

    @property
    def placeholder(self) -> str:
        return self._placeholder

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(160.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Toggle(View):
    """An on/off switch (mirrors SwiftUI Toggle).

    Use the inherited ``.disabled()`` modifier to block toggling.
    """

    def __init__(self, title: str = "", is_on: Optional[Binding[bool]] = None):
        self._title = title
        self._is_on = is_on
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def is_on(self) -> Optional[Binding[bool]]:
        return self._is_on

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(90.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Slider(View):
    """A horizontal value slider (mirrors SwiftUI Slider).

    Use the inherited ``.disabled()`` modifier to block adjusting.
    """

    def __init__(
        self,
        value: Optional[Binding[float]] = None,
        in_range: tuple = (0.0, 1.0),
        step: Optional[float] = None,
    ):
        self._value = value
        self._range = in_range
        self._step = step
        self._children = []

    @property
    def value(self) -> Optional[Binding[float]]:
        return self._value

    @property
    def range(self) -> tuple:
        return self._range

    @property
    def step(self) -> Optional[float]:
        return self._step

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(160.0, 24.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Picker(View):
    """A dropdown selector (mirrors SwiftUI Picker).

    Use the inherited ``.disabled()`` modifier to block changing the
    selection.
    """

    def __init__(
        self,
        title: str,
        selection: Optional[Binding] = None,
        options: Sequence[Any] = (),
    ):
        self._title = title
        self._selection = selection
        self._options = list(options)
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def selection(self) -> Optional[Binding]:
        return self._selection

    @property
    def options(self) -> List[Any]:
        return self._options

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(140.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class ImageInterpolation:
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VALUES = {NONE, LOW, MEDIUM, HIGH}


class ImageResizingMode:
    STRETCH = "stretch"
    TILE = "tile"
    VALUES = {STRETCH, TILE}


class ImageScale:
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    VALUES = {SMALL, MEDIUM, LARGE}


class SymbolRenderingMode:
    MONOCHROME = "monochrome"
    HIERARCHICAL = "hierarchical"
    PALETTE = "palette"
    MULTICOLOR = "multicolor"
    VALUES = {MONOCHROME, HIERARCHICAL, PALETTE, MULTICOLOR}


class Image(View):
    """An SF Symbol, local-file, or in-memory image description."""

    def __init__(self, system_name: str = "", color: Optional[Color] = None,
                 size: float | Size = 24.0, *, path=None, data: Optional[bytes] = None,
                 label: str = "", decorative: bool = False,
                 aspect_ratio: Optional[float] = None,
                 variable_value: Optional[float] = None):
        sources = int(bool(system_name)) + int(path is not None) + int(data is not None)
        if sources > 1:
            raise ValueError("Image accepts only one of system_name, path, or data")
        if data is not None and not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("Image data must be bytes-like")
        if data is not None and not data:
            raise ValueError("Image data cannot be empty")
        if variable_value is not None and not system_name:
            raise ValueError("variable_value requires a system image")
        if variable_value is not None and not 0.0 <= float(variable_value) <= 1.0:
            raise ValueError("Image variable_value must be between 0 and 1")
        self._system_name = system_name
        self._path = path
        self._data = bytes(data) if data is not None else None
        self._color = color
        self._size = size if isinstance(size, Size) else Size(float(size), float(size))
        self.label = str(label)
        self.decorative = bool(decorative)
        self.aspect_ratio = float(aspect_ratio) if aspect_ratio is not None else (
            self._size.width / self._size.height if self._size.height else 1.0
        )
        self._variable_value = (float(variable_value)
                                if variable_value is not None else None)
        self._resizable = False
        self._content_mode = "fit"
        self._rendering_mode = "template" if system_name else "original"
        self._interpolation = ImageInterpolation.MEDIUM
        self._antialiased = True
        self._symbol_variants: tuple[str, ...] = ()
        self._symbol_rendering_mode = SymbolRenderingMode.MONOCHROME
        self._palette: tuple[Color, ...] = ()
        self._cap_insets = EdgeInsets()
        self._resizing_mode = ImageResizingMode.STRETCH
        self._image_scale = ImageScale.MEDIUM
        self._symbol_weight = "regular"
        self._children = []

    @property
    def system_name(self) -> str:
        return self._system_name

    @property
    def path(self):
        return self._path

    @property
    def data(self) -> Optional[bytes]:
        return self._data

    @property
    def content_mode(self) -> str:
        return self._content_mode

    @property
    def resolved_system_name(self) -> str:
        suffixes = [item for item in self._symbol_variants
                    if not self._system_name.endswith(f".{item}")]
        return ".".join((self._system_name, *suffixes)) if suffixes else self._system_name

    @property
    def interpolation_quality(self) -> str:
        return self._interpolation

    @property
    def is_antialiased(self) -> bool:
        return self._antialiased

    @property
    def symbol_rendering_mode_value(self) -> str:
        return self._symbol_rendering_mode

    @property
    def palette_colors(self) -> tuple[Color, ...]:
        return self._palette

    @property
    def cap_insets(self) -> EdgeInsets:
        return self._cap_insets

    @property
    def resizing_mode(self) -> str:
        return self._resizing_mode

    @property
    def image_scale_value(self) -> str:
        return self._image_scale

    @property
    def symbol_weight_value(self) -> str:
        return self._symbol_weight

    @property
    def variable_value(self) -> Optional[float]:
        return self._variable_value

    @property
    def effective_size(self) -> Size:
        factor = ({ImageScale.SMALL: 0.8, ImageScale.MEDIUM: 1.0,
                   ImageScale.LARGE: 1.35}[self._image_scale]
                  if self._system_name else 1.0)
        return Size(self._size.width * factor, self._size.height * factor)

    @classmethod
    def from_file(cls, path, **kwargs) -> "Image":
        return cls(path=path, **kwargs)

    @classmethod
    def from_data(cls, data: bytes, **kwargs) -> "Image":
        return cls(data=data, **kwargs)

    def _copy(self, **changes) -> "Image":
        result = Image(
            self._system_name, self._color, self._size, path=self._path,
            data=self._data, label=self.label, decorative=self.decorative,
            aspect_ratio=self.aspect_ratio,
            variable_value=changes.get("variable_value", self._variable_value),
        )
        result._resizable = changes.get("resizable", self._resizable)
        result._content_mode = changes.get("content_mode", self._content_mode)
        result._rendering_mode = changes.get("rendering_mode", self._rendering_mode)
        result._interpolation = changes.get("interpolation", self._interpolation)
        result._antialiased = changes.get("antialiased", self._antialiased)
        result._symbol_variants = changes.get("symbol_variants", self._symbol_variants)
        result._symbol_rendering_mode = changes.get("symbol_rendering_mode", self._symbol_rendering_mode)
        result._palette = changes.get("palette", self._palette)
        result._cap_insets = changes.get("cap_insets", self._cap_insets)
        result._resizing_mode = changes.get("resizing_mode", self._resizing_mode)
        result._image_scale = changes.get("image_scale", self._image_scale)
        result._symbol_weight = changes.get("symbol_weight", self._symbol_weight)
        return result

    def resizable(self, value: bool = True, cap_insets: Optional[EdgeInsets] = None,
                  resizing_mode: str = ImageResizingMode.STRETCH) -> "Image":
        if cap_insets is not None and not isinstance(cap_insets, EdgeInsets):
            raise TypeError("Image cap_insets must be EdgeInsets")
        if resizing_mode not in ImageResizingMode.VALUES:
            raise ValueError("Image resizing mode must be stretch or tile")
        return self._copy(resizable=bool(value),
                          cap_insets=cap_insets or EdgeInsets(),
                          resizing_mode=resizing_mode)

    def scaled_to_fit(self) -> "Image":
        return self._copy(resizable=True, content_mode="fit")

    def scaled_to_fill(self) -> "Image":
        return self._copy(resizable=True, content_mode="fill")

    def rendering_mode(self, mode: str) -> "Image":
        if mode not in ("original", "template"):
            raise ValueError("Image rendering mode must be original or template")
        return self._copy(rendering_mode=mode)

    def interpolation(self, quality: str) -> "Image":
        if quality not in ImageInterpolation.VALUES:
            raise ValueError("Image interpolation must be none, low, medium, or high")
        return self._copy(interpolation=quality)

    def antialiased(self, value: bool = True) -> "Image":
        return self._copy(antialiased=bool(value))

    def symbol_variant(self, *variants: str) -> "Image":
        allowed = {"none", "fill", "circle", "square", "rectangle", "slash"}
        if not self._system_name:
            raise ValueError("symbol_variant requires a system image")
        if not variants or any(item not in allowed for item in variants):
            raise ValueError("unsupported symbol variant")
        values = () if "none" in variants else tuple(dict.fromkeys(
            (*self._symbol_variants, *(item for item in variants if item != "none"))
        ))
        return self._copy(symbol_variants=values)

    def symbol_rendering_mode(self, mode: str, palette: Sequence[Color] = ()) -> "Image":
        if not self._system_name:
            raise ValueError("symbol_rendering_mode requires a system image")
        if mode not in SymbolRenderingMode.VALUES:
            raise ValueError("unsupported symbol rendering mode")
        colors = tuple(palette)
        if mode == SymbolRenderingMode.PALETTE and not colors:
            raise ValueError("palette symbol rendering requires colors")
        if not all(isinstance(color, Color) for color in colors):
            raise TypeError("symbol palette must contain Color values")
        return self._copy(symbol_rendering_mode=mode, palette=colors)

    def image_scale(self, scale: str) -> "Image":
        if scale not in ImageScale.VALUES:
            raise ValueError("Image scale must be small, medium, or large")
        return self._copy(image_scale=scale)

    def symbol_weight(self, weight: str) -> "Image":
        values = {"ultraLight", "thin", "light", "regular", "medium",
                  "semibold", "bold", "heavy", "black"}
        if not self._system_name:
            raise ValueError("symbol_weight requires a system image")
        if weight not in values:
            raise ValueError("unsupported symbol weight")
        return self._copy(symbol_weight=weight)

    def variable_symbol(self, value: Optional[float]) -> "Image":
        """Return a system symbol configured with a normalized variable value."""
        if not self._system_name:
            raise ValueError("variable_symbol requires a system image")
        if value is not None and not 0.0 <= float(value) <= 1.0:
            raise ValueError("Image variable value must be between 0 and 1")
        return self._copy(variable_value=None if value is None else float(value))

    def size_that_fits(self, proposal: Size) -> Size:
        if not self._resizable:
            return self.effective_size
        width = self._size.width if proposal.width == float("inf") else proposal.width
        height = self._size.height if proposal.height == float("inf") else proposal.height
        if self._content_mode == "fill":
            return Size(width, height)
        if width <= 0 or height <= 0:
            return Size(width, height)
        if width / height > self.aspect_ratio:
            width = height * self.aspect_ratio
        else:
            height = width / self.aspect_ratio
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Divider(View):
    """A thin horizontal separator line (mirrors SwiftUI Divider)."""

    def __init__(self, color: Optional[Color] = None):
        self._color = color
        self._children = []

    @property
    def color(self) -> Optional[Color]:
        return self._color

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(proposal.width if proposal.width != float("inf") else 200.0, 1.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class List(View):
    """A vertical list of rows (mirrors SwiftUI List).

    Supports **lazy virtualisation** (ADR-0008): only the rows inside the
    visible viewport are laid out and rendered. ``scroll_offset`` is the index
    of the first visible row (optionally bound to a ``State``); ``row_height``
    fixes the row height so the viewport size can be derived from the container
    height. When ``row_height`` is None it is measured from the first row.
    """

    def __init__(
        self,
        rows: Sequence[View] = (),
        spacing: float = 2.0,
        scroll_offset: Optional[Binding[int]] = None,
        row_height: Optional[float] = None,
        selection: Optional[Binding] = None,
        id: Optional[Callable[[View], Any]] = None,
        edit_mode: Optional[Binding[str]] = None,
        on_delete: Optional[Callable[[tuple[int, ...]], None]] = None,
        on_move: Optional[Callable[[tuple[int, ...], int], None]] = None,
    ):
        self._rows = list(rows)
        self._spacing = spacing
        self._scroll_offset = scroll_offset
        self._row_height = row_height
        if selection is not None and not isinstance(selection, Binding): raise TypeError("List selection must be a Binding")
        if edit_mode is not None and not isinstance(edit_mode, Binding): raise TypeError("List edit_mode must be a Binding")
        if id is not None and not callable(id): raise TypeError("List id must be callable")
        if on_delete is not None and not callable(on_delete): raise TypeError("List on_delete must be callable")
        if on_move is not None and not callable(on_move): raise TypeError("List on_move must be callable")
        if edit_mode is not None:
            from .list_editing import EditMode
            EditMode.validate(edit_mode.wrapped_value)
        self.selection, self.id_provider, self.edit_mode = selection, id, edit_mode
        self.on_delete, self.on_move = on_delete, on_move
        selected = selection.wrapped_value if selection is not None else None
        self.allows_multiple_selection = isinstance(selected, (set, frozenset))
        self._internal_offset = 0
        self._children = list(rows)

    def row_id(self, row: View, index: Optional[int] = None):
        if self.id_provider is not None: return self.id_provider(row)
        from .scrolling import IDModifier
        from .view import _ModifiedContent
        node = row
        while isinstance(node, _ModifiedContent):
            if isinstance(node._modifier, IDModifier): return node._modifier.value
            node = node._content
        return self._rows.index(row) if index is None else index

    def select_row(self, index: int, extending: bool = False) -> None:
        if self.selection is None or not 0 <= index < len(self._rows): return
        value = self.row_id(self._rows[index], index)
        if self.allows_multiple_selection:
            values = set(self.selection.wrapped_value or ())
            if extending and value in values: values.remove(value)
            elif extending: values.add(value)
            else: values = {value}
            self.selection.wrapped_value = values
        else: self.selection.wrapped_value = value

    def delete_rows(self, indices) -> tuple[View, ...]:
        from .list_editing import list_row_editing
        values = tuple(sorted({int(index) for index in indices}))
        allowed = tuple(index for index in values if 0 <= index < len(self._rows)
                        and not list_row_editing(self._rows[index]).get("delete_disabled", False))
        removed = tuple(self._rows[index] for index in allowed)
        removed_ids = {self.row_id(self._rows[index], index) for index in allowed}
        for index in reversed(allowed): del self._rows[index]
        self._children = list(self._rows)
        self.scroll_to(min(self.current_offset(), max(0, len(self._rows) - 1)))
        if removed_ids and self.selection is not None:
            selected = self.selection.wrapped_value
            if self.allows_multiple_selection:
                self.selection.wrapped_value = set(selected or ()) - removed_ids
            elif selected in removed_ids:
                self.selection.wrapped_value = None
        if allowed and self.on_delete is not None: self.on_delete(allowed)
        return removed

    def move_rows(self, indices, destination: int) -> None:
        from .list_editing import list_row_editing
        values = tuple(sorted({int(index) for index in indices}))
        if any(not 0 <= index < len(self._rows) or list_row_editing(self._rows[index]).get("move_disabled", False)
               for index in values): return
        moving = [self._rows[index] for index in values]
        remaining = [row for index, row in enumerate(self._rows) if index not in values]
        adjusted = max(0, min(int(destination) - sum(index < destination for index in values), len(remaining)))
        self._rows = remaining[:adjusted] + moving + remaining[adjusted:]
        self._children = list(self._rows)
        if self.on_move is not None: self.on_move(values, int(destination))

    @property
    def is_editing(self) -> bool:
        if self.edit_mode is None:
            return True
        from .list_editing import EditMode
        return self.edit_mode.wrapped_value in (EditMode.TRANSIENT, EditMode.ACTIVE)

    @property
    def rows(self) -> List[View]:
        return self._rows

    @property
    def scroll_offset(self) -> Optional[Binding[int]]:
        return self._scroll_offset

    @property
    def row_height(self) -> Optional[float]:
        return self._row_height

    def effective_row_height(self, proposal_width: float) -> float:
        """The fixed row height used for viewport math (measured if unset)."""
        if self._row_height is not None and self._row_height > 0:
            return self._row_height
        if not self._rows:
            return 24.0
        first = self._rows[0].size_that_fits(Size(proposal_width, float("inf")))
        return first.height if first.height > 0 else 24.0

    def current_offset(self) -> int:
        """Current first-visible-row index (from binding or internal default)."""
        if self._scroll_offset is not None:
            return max(0, int(self._scroll_offset.wrapped_value))
        return max(0, getattr(self, "_internal_offset", 0))

    def scroll_to(self, offset: int) -> None:
        """Set the scroll offset (writes through to the binding if present)."""
        n = max(0, min(offset, max(0, len(self._rows) - 1)))
        if self._scroll_offset is not None:
            self._scroll_offset.wrapped_value = n
        else:
            # Without a binding we keep the offset on the List itself.
            self._internal_offset = n

    def visible_rows(self, viewport_height: float, proposal_width: float) -> List[View]:
        """The rows inside the visible viewport (lazy window).

        ``viewport_height`` is the height available to the list; only the rows
        that intersect it are returned. This is what backends render.
        """
        if not self._rows or viewport_height <= 0:
            return []
        row_h = self.effective_row_height(proposal_width)
        step = row_h + self._spacing
        offset = self.current_offset()
        count = max(1, int(viewport_height // step) + 1)
        end = min(len(self._rows), offset + count)
        return self._rows[offset:end]

    def size_that_fits(self, proposal: Size) -> Size:
        if not self._rows:
            return Size()
        # List is virtual: measuring every row here would turn an otherwise
        # bounded viewport render into O(n) work.  SwiftUI-style lists use a
        # stable estimated row metric until a renderer lays out visible cells;
        # aUI uses the first row for the same deterministic estimate.
        first = self._rows[0].size_that_fits(Size(proposal.width, float("inf")))
        row_height = self.effective_row_height(proposal.width)
        height = row_height * len(self._rows) + self._spacing * max(0, len(self._rows) - 1)
        return Size(first.width, height)

    def place(self, origin: Point, size: Size) -> None:
        # Only lay out the visible window (lazy).
        cursor = origin.y
        for row in self.visible_rows(size.height, size.width):
            row_size = row.size_that_fits(Size(size.width, float("inf")))
            row.place(Point(origin.x, cursor), row_size)
            cursor += row_size.height + self._spacing

    def children(self) -> Sequence[View]:
        return self._children


class Group(View):
    """A container that groups children without adding layout (mirrors Group)."""

    def __init__(self, children: Sequence[View] = ()):
        self._children = list(children)

    def size_that_fits(self, proposal: Size) -> Size:
        width = 0.0
        height = 0.0
        for child in self._children:
            s = child.size_that_fits(proposal)
            width = max(width, s.width)
            height += s.height
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        cursor = origin.y
        for child in self._children:
            child_size = child.size_that_fits(Size(size.width, float("inf")))
            child.place(Point(origin.x, cursor), child_size)
            cursor += child_size.height

    def children(self) -> Sequence[View]:
        return self._children


class Stepper(View):
    """A value stepper with +/- buttons (mirrors SwiftUI Stepper).

    ``value`` is an optional two-way binding; when absent the ``on_increment`` /
    ``on_decrement`` callbacks are used. ``.disabled()`` renders the stepper
    greyed out and blocks changing the value.
    """

    def __init__(
        self,
        title: str = "",
        value: Optional[Binding[float]] = None,
        in_range: tuple = (0.0, 100.0),
        step: float = 1.0,
        on_increment: Optional[Callable[[], None]] = None,
        on_decrement: Optional[Callable[[], None]] = None,
    ):
        self._title = title
        self._value = value
        self._range = in_range
        self._step = step
        self._on_increment = on_increment
        self._on_decrement = on_decrement
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def value(self) -> Optional[Binding[float]]:
        return self._value

    @property
    def range(self) -> tuple:
        return self._range

    @property
    def step(self) -> float:
        return self._step

    def increment(self) -> None:
        from .styles import is_enabled
        if not is_enabled(self):
            return
        if self._on_increment is not None:
            self._on_increment()
        elif self._value is not None:
            lo, hi = self._range
            self._value.wrapped_value = min(hi, self._value.wrapped_value + self._step)

    def decrement(self) -> None:
        from .styles import is_enabled
        if not is_enabled(self):
            return
        if self._on_decrement is not None:
            self._on_decrement()
        elif self._value is not None:
            lo, hi = self._range
            self._value.wrapped_value = max(lo, self._value.wrapped_value - self._step)

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(120.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class ProgressView(View):
    """A determinate progress bar (mirrors SwiftUI ProgressView).

    ``value`` is a float in ``[0, 1]`` (or a Binding); when None the view is
    indeterminate (animated spinner in some backends).
    """

    def __init__(self, value: Optional[float] = None, label: str = ""):
        self._value = value
        self._label = label
        self._children = []

    @property
    def value(self) -> Optional[float]:
        return self._value

    @property
    def label(self) -> str:
        return self._label

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(160.0, 20.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Form(View):
    """A grouped vertical container for settings-style forms (mirrors Form).

    Renders children stacked vertically with a subtle section feel.
    """

    def __init__(self, children: Sequence[View] = (), spacing: float = 4.0):
        self._children = list(children)
        self._spacing = spacing

    def size_that_fits(self, proposal: Size) -> Size:
        width = 0.0
        height = 0.0
        for child in self._children:
            s = child.size_that_fits(Size(proposal.width, float("inf")))
            width = max(width, s.width)
            height += s.height
        height += self._spacing * max(0, len(self._children) - 1)
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        cursor = origin.y
        for child in self._children:
            child_size = child.size_that_fits(Size(size.width, float("inf")))
            child.place(Point(origin.x, cursor), child_size)
            cursor += child_size.height + self._spacing

    def children(self) -> Sequence[View]:
        return self._children


class NavigationStack(View):
    """A navigation container whose title is supplied by ``navigation_title``."""

    def __init__(self, content: View, path=None):
        from .navigation import NavigationPath
        if not isinstance(content, View):
            raise TypeError("NavigationStack content must be a View")
        self._root_content = content
        self._content = content
        self._path = path if path is not None else NavigationPath()
        if not isinstance(self._path, NavigationPath):
            raise TypeError("NavigationStack path must be a NavigationPath")
        self._destinations: dict[type, Callable[[Any], View]] = {}
        self._active_key = object()
        self._active_view: Optional[View] = None
        self._children = [content]

    @property
    def title(self) -> str:
        from .navigation import navigation_configuration
        return navigation_configuration(self.active_content).title

    @property
    def navigation_configuration(self):
        from .navigation import navigation_configuration
        return navigation_configuration(self.active_content)

    @property
    def header_visible(self) -> bool:
        return self.navigation_configuration.visible

    @property
    def header_height(self) -> float:
        from .navigation import NavigationBarTitleDisplayMode
        if not self.header_visible:
            return 0.0
        return 44.0 if self.navigation_configuration.display_mode == NavigationBarTitleDisplayMode.LARGE else 28.0

    @property
    def content(self) -> View:
        return self.active_content

    @property
    def path(self):
        return self._path

    @property
    def active_content(self) -> View:
        if not self._path:
            return self._root_content
        value = self._path.last
        if self._active_view is not None and self._active_key == value:
            return self._active_view
        for value_type, builder in self._destinations.items():
            if isinstance(value, value_type):
                self._active_key = value
                self._active_view = builder(value)
                return self._active_view
        return self._root_content

    def navigation_destination(self, value_type: type,
                               builder: Callable[[Any], View]) -> "NavigationStack":
        """Register a destination builder for values of ``value_type``."""
        if not isinstance(value_type, type) or not callable(builder):
            raise TypeError("navigation_destination expects a type and callable builder")
        self._destinations[value_type] = builder
        self._active_view = None
        return self

    def go_back(self) -> None:
        if len(self._path):
            self._path.remove_last()
            self._active_view = None

    def size_that_fits(self, proposal: Size) -> Size:
        inner = self.active_content.size_that_fits(proposal)
        header = self.header_height
        return Size(inner.width, inner.height + header)

    def place(self, origin: Point, size: Size) -> None:
        content = self.active_content
        inner_size = content.size_that_fits(size)
        content.place(Point(origin.x, origin.y + self.header_height), inner_size)

    def children(self) -> Sequence[View]:
        return [self.active_content]


class NavigationLink(Button):
    """A button that appends a value to a :class:`NavigationPath`."""

    def __init__(self, title: str, value: Any, path=None):
        self._value = value
        self._path = path
        super().__init__(title, action=self.activate)

    @property
    def value(self) -> Any:
        return self._value

    @property
    def path(self):
        return self._path

    def activate(self) -> None:
        from .styles import is_enabled
        if is_enabled(self) and self._path is not None:
            self._path.append(self._value)


class DatePicker(View):
    """A date selection control (mirrors SwiftUI DatePicker).

    ``selection`` is a two-way binding to a ``datetime.datetime``. The
    ``displayed_components`` selects which parts of the date are editable:
    ``"date"`` (year/month/day), ``"hourAndMinute"`` (time), or ``"date"`` +
    ``"hourAndMinute"`` (both). ``in_range`` optionally restricts the allowed
    range. Use ``.disabled()`` to block editing.
    """

    _VALID_COMPONENTS = ("date", "hourAndMinute")

    def __init__(
        self,
        title: str = "",
        selection: Optional[Binding] = None,
        displayed_components: str = "date",
        in_range: Optional[tuple] = None,
    ):
        self._title = title
        self._selection = selection
        self._displayed_components = displayed_components
        self._in_range = in_range
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def selection(self) -> Optional[Binding]:
        return self._selection

    @property
    def displayed_components(self) -> str:
        return self._displayed_components

    @property
    def in_range(self) -> Optional[tuple]:
        return self._in_range

    def _current(self) -> str:
        """The current value formatted for display."""
        if self._selection is None:
            return ""
        value = self._selection.wrapped_value
        if value is None:
            return ""
        if self._displayed_components == "hourAndMinute":
            return value.strftime("%H:%M")
        if self._displayed_components == "date":
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%d %H:%M")

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(160.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Label(View):
    """A title + icon label (mirrors SwiftUI Label).

    ``title`` is the text; ``system_name`` is an optional icon name that the
    backend renders next to the title.
    """

    def __init__(self, title: str, system_name: str = ""):
        self._title = title
        self._system_name = system_name
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def system_name(self) -> str:
        return self._system_name

    def size_that_fits(self, proposal: Size) -> Size:
        width = len(self._title) * 8.0 + (18.0 if self._system_name else 0.0)
        return Size(max(24.0, width), 24.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class SecureField(View):
    """A password-style text input (mirrors SwiftUI SecureField).

    Renders typed characters as bullets (``*``) while keeping the real value
    in the binding.
    """

    def __init__(self, text: Binding[str], placeholder: str = ""):
        self._text = text
        self._placeholder = placeholder
        self._children = []

    @property
    def text(self) -> Binding[str]:
        return self._text

    @property
    def placeholder(self) -> str:
        return self._placeholder

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(160.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class ColorPicker(View):
    """A colour selection control (mirrors SwiftUI ColorPicker).

    ``selection`` is a two-way binding to a ``Color``. The ``supports_opacity``
    flag mirrors SwiftUI; the backend renders a small swatch.
    """

    def __init__(self, title: str = "", selection: Optional[Binding] = None,
                 supports_opacity: bool = False):
        self._title = title
        self._selection = selection
        self._supports_opacity = supports_opacity
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def selection(self) -> Optional[Binding]:
        return self._selection

    @property
    def supports_opacity(self) -> bool:
        return self._supports_opacity

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(120.0, 28.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class SearchField(TextField):
    """A single-line search input backed by ``NSSearchField`` on macOS."""

    def __init__(self, text: Binding[str], placeholder: str = "Search"):
        super().__init__(text=text, placeholder=placeholder)


class TextEditor(TextField):
    """A multi-line text editor with a two-way text binding."""

    def __init__(self, text: Binding[str], placeholder: str = "",
                 min_height: float = 96.0):
        super().__init__(text=text, placeholder=placeholder)
        self._min_height = max(44.0, float(min_height))

    @property
    def min_height(self) -> float:
        return self._min_height

    def size_that_fits(self, proposal: Size) -> Size:
        width = min(320.0, proposal.width) if proposal.width != float("inf") else 320.0
        return Size(max(160.0, width), self._min_height)


class Link(View):
    """A link label that opens ``url`` using the platform URL handler."""

    def __init__(self, title: str, url: str,
                 action: Optional[Callable[[], None]] = None):
        self._title = str(title)
        self._url = str(url)
        self._action = action
        self._children = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def url(self) -> str:
        return self._url

    @property
    def action(self) -> Optional[Callable[[], None]]:
        return self._action

    def size_that_fits(self, proposal: Size) -> Size:
        return Size(max(40.0, len(self._title) * 8.0), 24.0)

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Gauge(ProgressView):
    """A bounded value indicator rendered as ``NSLevelIndicator`` on macOS."""

    def __init__(self, value: float, in_range: tuple = (0.0, 1.0),
                 label: str = ""):
        lo, hi = in_range
        if hi <= lo:
            raise ValueError("Gauge range upper bound must exceed lower bound")
        self._raw_value = float(value)
        self._range = (float(lo), float(hi))
        ratio = (self._raw_value - lo) / (hi - lo)
        super().__init__(value=max(0.0, min(1.0, ratio)), label=label)

    @property
    def raw_value(self) -> float:
        return self._raw_value

    @property
    def range(self) -> tuple:
        return self._range


class Shape(View):
    """Base for simple SwiftUI-like filled and stroked vector shapes."""

    def __init__(self, fill: Color = Color.clear, stroke: Optional[Color] = None,
                 line_width: float = 1.0, size: Size = Size(48.0, 48.0),
                 inset: float = 0.0, stroke_style=None, fill_style=None,
                 trim: tuple[float, float] = (0.0, 1.0)):
        from .canvas import FillStyle, StrokeStyle
        if stroke_style is not None and not isinstance(stroke_style, StrokeStyle):
            raise TypeError("shape stroke_style must be a StrokeStyle")
        if fill_style is not None and not isinstance(fill_style, FillStyle):
            raise TypeError("shape fill_style must be a FillStyle")
        start, end = (float(value) for value in trim)
        if not 0.0 <= start <= end <= 1.0:
            raise ValueError("shape trim range must satisfy 0 <= from <= to <= 1")
        self._fill = fill
        self._stroke = stroke
        self._line_width = max(0.0, float(line_width))
        self._size = size
        self._inset = max(0.0, float(inset))
        self._stroke_style = stroke_style or StrokeStyle(self._line_width)
        self._fill_style = fill_style or FillStyle()
        self._trim = (start, end)
        self._children = []

    @property
    def fill_color(self) -> Color:
        return self._fill

    @property
    def stroke_color(self) -> Optional[Color]:
        return self._stroke

    @property
    def line_width(self) -> float:
        return self._line_width

    @property
    def inset_amount(self) -> float:
        return self._inset

    @property
    def stroke_style(self):
        return self._stroke_style

    @property
    def fill_style(self):
        return self._fill_style

    @property
    def trim_range(self) -> tuple[float, float]:
        return self._trim

    def _copy(self, *, fill: Color, stroke: Optional[Color],
              line_width: float) -> "Shape":
        kwargs = dict(fill=fill, stroke=stroke, line_width=line_width,
                      size=self._size, inset=self._inset,
                      stroke_style=self._stroke_style, fill_style=self._fill_style,
                      trim=self._trim)
        if isinstance(self, Capsule):
            return Capsule(**kwargs)
        if isinstance(self, UnevenRoundedRectangle):
            return UnevenRoundedRectangle(*self.corner_radii, style=self.style, **kwargs)
        if isinstance(self, RoundedRectangle):
            return RoundedRectangle(corner_radius=self.corner_radius_value, **kwargs)
        return type(self)(**kwargs)

    def fill(self, color: Color, style=None) -> "Shape":
        """Return a copy filled with ``color`` (SwiftUI ``Shape.fill``)."""
        from .canvas import FillStyle
        if style is not None and not isinstance(style, FillStyle):
            raise TypeError("shape fill style must be a FillStyle")
        result = self._copy(fill=color, stroke=self._stroke, line_width=self._line_width)
        if style is not None:
            result._fill_style = style
        return result

    def stroke(self, color: Color, line_width: float = 1.0, style=None) -> "Shape":
        """Return a copy outlined with ``color``."""
        from .canvas import StrokeStyle
        if isinstance(line_width, StrokeStyle) and style is None:
            style, line_width = line_width, line_width.line_width
        if style is not None and not isinstance(style, StrokeStyle):
            raise TypeError("shape stroke style must be a StrokeStyle")
        effective = style or StrokeStyle(max(0.0, float(line_width)))
        result = self._copy(fill=self._fill, stroke=color,
                            line_width=effective.line_width)
        result._stroke_style = effective
        return result

    def inset(self, amount: float) -> "Shape":
        """Return an inset copy, matching SwiftUI's ``InsettableShape``."""
        result = self._copy(fill=self._fill, stroke=self._stroke,
                            line_width=self._line_width)
        result._inset = max(0.0, self._inset + float(amount))
        return result

    def trim(self, from_: float = 0.0, to: float = 1.0) -> "Shape":
        """Return a copy restricted to a normalized portion of its path."""
        start, end = float(from_), float(to)
        if not 0.0 <= start <= end <= 1.0:
            raise ValueError("shape trim range must satisfy 0 <= from <= to <= 1")
        result = self._copy(fill=self._fill, stroke=self._stroke,
                            line_width=self._line_width)
        result._trim = (start, end)
        return result

    def stroke_border(self, color: Color, line_width: float = 1.0,
                      style=None) -> "Shape":
        """Stroke fully inside the shape boundary instead of centering the line."""
        from .canvas import StrokeStyle
        if isinstance(line_width, StrokeStyle) and style is None:
            style, line_width = line_width, line_width.line_width
        if style is not None and not isinstance(style, StrokeStyle):
            raise TypeError("shape stroke border style must be a StrokeStyle")
        effective = style or StrokeStyle(max(0.0, float(line_width)))
        width = effective.line_width
        result = self._copy(fill=self._fill, stroke=color, line_width=width)
        result._stroke_style = effective
        result._inset = self._inset + width / 2.0
        return result

    def size_that_fits(self, proposal: Size) -> Size:
        return self._size

    def place(self, origin: Point, size: Size) -> None:
        return None

    def children(self) -> Sequence[View]:
        return self._children


class Rectangle(Shape):
    """A rectangular vector shape."""


class RoundedRectangle(Shape):
    """A rectangular vector shape with a configurable corner radius."""

    def __init__(self, corner_radius: float = 10.0, **kwargs):
        super().__init__(**kwargs)
        self._corner_radius = max(0.0, float(corner_radius))

    @property
    def corner_radius_value(self) -> float:
        return self._corner_radius


class UnevenRoundedRectangle(Shape):
    """Rectangle with independent top-leading/trailing and bottom corners."""

    def __init__(self, top_leading: float = 0.0, top_trailing: float = 0.0,
                 bottom_leading: float = 0.0, bottom_trailing: float = 0.0,
                 style: str = "continuous", **kwargs):
        super().__init__(**kwargs)
        if style not in ("circular", "continuous"):
            raise ValueError("rounded corner style must be circular or continuous")
        self._corner_radii = tuple(max(0.0, float(value)) for value in (
            top_leading, top_trailing, bottom_leading, bottom_trailing
        ))
        self.style = style

    @property
    def corner_radii(self) -> tuple[float, float, float, float]:
        return self._corner_radii


class Circle(Shape):
    """An ellipse constrained to a square frame."""

    def size_that_fits(self, proposal: Size) -> Size:
        side = min(self._size.width, self._size.height)
        return Size(side, side)


class Ellipse(Shape):
    """An elliptical vector shape that follows its proposed frame."""


class Capsule(RoundedRectangle):
    """A rounded rectangle whose radius is half its shortest edge."""

    def __init__(self, **kwargs):
        super().__init__(corner_radius=0.0, **kwargs)

    def size_that_fits(self, proposal: Size) -> Size:
        return self._size


class LabeledContent(View):
    """A label/value pair commonly used in settings and inspector views."""

    def __init__(self, label: Any, content: Any, spacing: float = 16.0):
        self.label = label if isinstance(label, View) else Text(str(label))
        self.content = content if isinstance(content, View) else Text(str(content))
        self._spacing = max(0.0, float(spacing))
        self._children = [self.label, self.content]

    def size_that_fits(self, proposal: Size) -> Size:
        left = self.label.size_that_fits(proposal)
        right = self.content.size_that_fits(proposal)
        return Size(left.width + self._spacing + right.width, max(left.height, right.height))

    def place(self, origin: Point, size: Size) -> None:
        left = self.label.size_that_fits(size)
        right = self.content.size_that_fits(size)
        self.label.place(origin, left)
        self.content.place(Point(origin.x + max(left.width + self._spacing,
                                                size.width - right.width), origin.y), right)

    def children(self) -> Sequence[View]:
        return self._children


class ContentUnavailableView(View):
    """A standard empty/error/search state with title and optional guidance."""

    def __init__(self, title: str, system_name: str = "", description: str = ""):
        self.title = title
        self.system_name = system_name
        self.description = description
        children: list[View] = []
        if system_name:
            children.append(Image(system_name=system_name, size=36))
        children.append(Text(title, font=Font.headline()))
        if description:
            children.append(Text(description, font=Font.body(), color=Color.secondary))
        self._children = children
        self._spacing = 8.0

    def size_that_fits(self, proposal: Size) -> Size:
        sizes = [child.size_that_fits(proposal) for child in self._children]
        return Size(max((s.width for s in sizes), default=0.0),
                    sum(s.height for s in sizes) + self._spacing * max(0, len(sizes) - 1))

    def place(self, origin: Point, size: Size) -> None:
        y = origin.y
        for child in self._children:
            measured = child.size_that_fits(size)
            child.place(Point(origin.x + (size.width - measured.width) / 2.0, y), measured)
            y += measured.height + self._spacing

    def children(self) -> Sequence[View]:
        return self._children


class Section(View):
    """A titled section with an optional footer (mirrors SwiftUI Section).

    ``header`` and ``footer`` are ``View`` instances rendered above/below the
    children; ``collapsible`` controls whether the header shows a disclosure
    affordance.
    """

    def __init__(self, header: View, children: Sequence[View] = (),
                 footer: Optional[View] = None, collapsible: bool = False):
        self._header = header
        self._children = list(children)
        self._footer = footer
        self._collapsible = collapsible

    @property
    def header(self) -> View:
        return self._header

    @property
    def footer(self) -> Optional[View]:
        return self._footer

    @property
    def collapsible(self) -> bool:
        return self._collapsible

    def size_that_fits(self, proposal: Size) -> Size:
        from .styles import style_value
        spacing = style_value(self, "section_spacing", 0.0)
        hs = self._header.size_that_fits(proposal)
        w, h = hs.width, hs.height
        for child in self._children:
            s = child.size_that_fits(proposal)
            w = max(w, s.width)
            h += s.height
        if self._footer is not None:
            fs = self._footer.size_that_fits(proposal)
            w = max(w, fs.width)
            h += fs.height
        h += spacing * max(0, len(self.children()) - 1)
        return Size(w, h)

    def place(self, origin: Point, size: Size) -> None:
        from .styles import style_value
        spacing = style_value(self, "section_spacing", 0.0)
        cursor = origin.y
        hs = self._header.size_that_fits(size)
        self._header.place(Point(origin.x, cursor), hs)
        cursor += hs.height + spacing
        for child in self._children:
            cs = child.size_that_fits(Size(size.width, float("inf")))
            child.place(Point(origin.x, cursor), cs)
            cursor += cs.height + spacing
        if self._footer is not None:
            fs = self._footer.size_that_fits(size)
            self._footer.place(Point(origin.x, cursor), fs)

    def children(self) -> Sequence[View]:
        result = [self._header]
        result.extend(self._children)
        if self._footer is not None:
            result.append(self._footer)
        return result


class DisclosureGroup(View):
    """A collapsible group with a label (mirrors SwiftUI DisclosureGroup).

    ``is_expanded`` is an optional binding; when ``None`` the group starts
    expanded. ``label`` is the header view.
    """

    def __init__(self, label: View, children: Sequence[View] = (),
                 is_expanded: Optional[Binding[bool]] = None):
        self._label = label
        self._children = list(children)
        self._is_expanded = is_expanded
        self._internal_expanded = True

    @property
    def label(self) -> View:
        return self._label

    @property
    def is_expanded(self) -> Optional[Binding[bool]]:
        return self._is_expanded

    @property
    def expanded(self) -> bool:
        if self._is_expanded is not None:
            return bool(self._is_expanded.wrapped_value)
        return self._internal_expanded

    def toggle(self) -> None:
        if self._is_expanded is not None:
            self._is_expanded.wrapped_value = not bool(self._is_expanded.wrapped_value)
        else:
            self._internal_expanded = not self._internal_expanded

    def size_that_fits(self, proposal: Size) -> Size:
        label_size = self._label.size_that_fits(proposal)
        if not self.expanded:
            return label_size
        height = label_size.height
        width = label_size.width
        for child in self._children:
            s = child.size_that_fits(proposal)
            width = max(width, s.width)
            height += s.height
        return Size(width, height)

    def place(self, origin: Point, size: Size) -> None:
        ls = self._label.size_that_fits(size)
        self._label.place(origin, ls)
        if not self.expanded:
            return
        cursor = origin.y + ls.height
        for child in self._children:
            cs = child.size_that_fits(Size(size.width, float("inf")))
            child.place(Point(origin.x, cursor), cs)
            cursor += cs.height

    def children(self) -> Sequence[View]:
        result = [self._label]
        if self.expanded:
            result.extend(self._children)
        return result


class ScrollView(View):
    """A scrollable container (mirrors SwiftUI ScrollView).

    Unlike ``List`` (which virtualises a fixed-height row stream), this is a
    generic scrollable container: the content is laid out at its natural size
    and the viewport clips it. ``axis`` is ``"vertical"`` or ``"horizontal"``.
    """

    def __init__(self, content: View, axis: str = "vertical"):
        self._content = content
        self._axis = axis
        self._children = [content]

    @property
    def content(self) -> View:
        return self._content

    @property
    def axis(self) -> str:
        return self._axis

    def size_that_fits(self, proposal: Size) -> Size:
        natural = self._content.size_that_fits(Size(proposal.width, float("inf")))
        if self._axis == "horizontal":
            return Size(min(proposal.width, natural.width), natural.height)
        return Size(natural.width, min(proposal.height, natural.height))

    def place(self, origin: Point, size: Size) -> None:
        natural = self._content.size_that_fits(size)
        self._content.place(origin, natural)

    def children(self) -> Sequence[View]:
        return self._children


class TabView(View):
    """A tabbed container (mirrors SwiftUI TabView).

    Each ``tab`` is a ``(title, view)`` pair; ``selection`` optionally binds
    the active tab index.
    """

    def __init__(self, tabs: Sequence[tuple] = (), selection: Optional[Binding[int]] = None):
        self._tabs = [(str(t[0]), t[1]) for t in tabs]
        self._selection = selection
        self._internal = 0
        self._children = [view for _, view in self._tabs]

    @property
    def tabs(self) -> List[tuple]:
        return list(self._tabs)

    @property
    def selection(self) -> Optional[Binding[int]]:
        return self._selection

    def _active_index(self) -> int:
        if self._selection is not None:
            return max(0, min(int(self._selection.wrapped_value), len(self._tabs) - 1))
        return max(0, min(self._internal, len(self._tabs) - 1))

    def select(self, index: int) -> None:
        if self._selection is not None:
            self._selection.wrapped_value = index
        else:
            self._internal = index

    def size_that_fits(self, proposal: Size) -> Size:
        if not self._tabs:
            return Size(0, 0)
        active = self._tabs[self._active_index()][1]
        return active.size_that_fits(proposal)

    def place(self, origin: Point, size: Size) -> None:
        if not self._tabs:
            return
        active = self._tabs[self._active_index()][1]
        active.place(origin, size)

    def children(self) -> Sequence[View]:
        return [self._tabs[self._active_index()][1]] if self._tabs else []


class NavigationRailDestination:
    """A labelled, optionally symbolic destination in a :class:`NavigationRail`."""

    def __init__(self, label: str, system_name: str = "", selected_system_name: str = ""):
        if not str(label):
            raise ValueError("NavigationRailDestination label cannot be empty")
        self.label = str(label)
        self.system_name = str(system_name)
        self.selected_system_name = str(selected_system_name)


class NavigationRail(View):
    """Persistent primary navigation, modelled after Flet's NavigationRail."""

    def __init__(self, destinations: Sequence[NavigationRailDestination],
                 selected_index: Optional[Binding[int]] = None, *, extended: bool = False):
        self.destinations = tuple(destinations)
        if not self.destinations or not all(isinstance(item, NavigationRailDestination)
                                            for item in self.destinations):
            raise TypeError("NavigationRail requires NavigationRailDestination values")
        if selected_index is not None and not isinstance(selected_index, Binding):
            raise TypeError("NavigationRail selected_index must be a Binding")
        self.selected_index = selected_index
        self.extended = bool(extended)
        self._internal_index = 0
        self._children = []

    @property
    def active_index(self) -> int:
        value = self.selected_index.wrapped_value if self.selected_index is not None else self._internal_index
        return max(0, min(int(value), len(self.destinations) - 1))

    def select(self, index: int) -> None:
        if not 0 <= int(index) < len(self.destinations):
            raise IndexError("NavigationRail destination index is out of range")
        if self.selected_index is not None:
            self.selected_index.wrapped_value = int(index)
        else:
            self._internal_index = int(index)

    def size_that_fits(self, proposal: Size) -> Size:
        width = 184.0 if self.extended else 72.0
        height = proposal.height if proposal.height != float("inf") else len(self.destinations) * 52.0
        return Size(width, max(52.0, height))

    def place(self, origin: Point, size: Size) -> None:
        return None


class AppBar(View):
    """A persistent top application bar, compatible with Flet's AppBar role."""

    def __init__(self, title: str | View, *, leading: Optional[View] = None,
                 actions: Sequence[View] = (), center_title: bool = False,
                 height: float = 52.0):
        self.title = title if isinstance(title, View) else Text(str(title), font=Font.headline())
        if not isinstance(self.title, View):
            raise TypeError("AppBar title must be a string or View")
        if leading is not None and not isinstance(leading, View):
            raise TypeError("AppBar leading must be a View")
        if not all(isinstance(item, View) for item in actions):
            raise TypeError("AppBar actions must be Views")
        if float(height) <= 0:
            raise ValueError("AppBar height must be positive")
        self.leading = leading
        self.actions = tuple(actions)
        self.center_title = bool(center_title)
        self.height = float(height)
        self._children = ([leading] if leading is not None else []) + [self.title] + list(self.actions)

    def size_that_fits(self, proposal: Size) -> Size:
        width = proposal.width if proposal.width != float("inf") else sum(
            child.size_that_fits(Size(float("inf"), self.height)).width for child in self._children
        )
        return Size(width, self.height)

    def place(self, origin: Point, size: Size) -> None:
        cursor = origin.x + 12.0
        if self.leading is not None:
            leading_size = self.leading.size_that_fits(Size(float("inf"), size.height))
            self.leading.place(Point(cursor, origin.y), leading_size)
            cursor += leading_size.width + 10.0
        title_size = self.title.size_that_fits(Size(float("inf"), size.height))
        title_x = (origin.x + (size.width - title_size.width) / 2.0 if self.center_title
                   else cursor)
        self.title.place(Point(title_x, origin.y), title_size)
        action_x = origin.x + size.width - 12.0
        for action in reversed(self.actions):
            action_size = action.size_that_fits(Size(float("inf"), size.height))
            action_x -= action_size.width
            action.place(Point(action_x, origin.y), action_size)
            action_x -= 8.0
