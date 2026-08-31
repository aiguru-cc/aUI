"""The core View protocol and base view types for aUI.

This module defines the declarative contract that every aUI view implements.
It mirrors SwiftUI's `View` protocol: a view knows how to propose a size to
its children, receive a size, and render itself.
"""
from __future__ import annotations

import abc
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .geometry import EdgeInsets, Point, Size


class View(abc.ABC):
    """Base class for all aUI views.

    A view is a lightweight, immutable description of a piece of UI. It is
    evaluated (``body``) and laid out by a backend, never stored directly in a
    widget tree. This mirrors SwiftUI's value-semantics views.
    """

    #: Cached list of child views (subclasses fill this in ``__init__``).
    _children: List["View"] = []

    #: Modifiers applied to this view, in application order.
    modifiers: List["ViewModifier"] = []

    def __new__(cls, *args, **kwargs):
        """Give every view independent runtime storage, including custom views.

        Subclasses aren't required to call ``super().__init__``. Initialising
        here prevents the mutable class defaults from leaking children or
        modifiers between instances.
        """
        instance = super().__new__(cls)
        instance._children = []
        instance.modifiers = []
        return instance

    def body(self) -> "View":  # pragma: no cover - overridden by subclasses
        return self

    def _content(self) -> "View":
        """The effective content after applying modifiers."""
        content: View = self
        for mod in self.modifiers:
            content = mod.body(content)
        return content

    # -- Layout protocol (mirrors SwiftUI's proposal/response) -------------
    def size_that_fits(self, proposal: Size) -> Size:
        """Return the size this view would take given a size proposal."""
        raise NotImplementedError

    def place(self, origin: Point, size: Size) -> None:
        """Position this view within its allocated frame. No-op by default."""
        return None

    # -- Tree helpers -------------------------------------------------------
    def children(self) -> Sequence["View"]:
        return self._children

    def flatten(self) -> List["View"]:
        """Depth-first list of this view and all descendants."""
        result: List[View] = [self]
        for child in self.children():
            result.extend(child.flatten())
        return result

    def find(self, predicate: Callable[["View"], bool]) -> Optional["View"]:
        for view in self.flatten():
            if predicate(view):
                return view
        return None

    # -- SwiftUI-style chained modifiers ------------------------------------
    # Every method returns a new wrapped view, so calls can be chained:
    #   Text("hi").font(...).foreground_color(...).padding(...)

    def padding(self, edges=None, length: float = 8.0) -> "View":
        from .modifiers import padding as _padding
        return _padding(self, edges, length)

    def background(self, color) -> "View":
        from .modifiers import background as _background
        return _background(self, color)

    def foreground_color(self, color) -> "View":
        from .modifiers import foreground_color as _foreground_color
        return _foreground_color(self, color)

    def font(self, font) -> "View":
        from .modifiers import font as _font
        return _font(self, font)

    def border(self, color, width: float = 1.0) -> "View":
        from .modifiers import border as _border
        return _border(self, color, width)

    def corner_radius(self, radius: float) -> "View":
        from .modifiers import corner_radius as _corner_radius
        return _corner_radius(self, radius)

    def opacity(self, value: float) -> "View":
        from .modifiers import opacity as _opacity
        return _opacity(self, value)

    def hidden(self) -> "View":
        from .modifiers import hidden as _hidden
        return _hidden(self)

    def frame(self, width=None, height=None, alignment: str = "center") -> "View":
        from .modifiers import frame as _frame
        return _frame(self, width=width, height=height, alignment=alignment)

    def layout_priority(self, value: float) -> "View":
        from .layout_modifiers import layout_priority
        return layout_priority(self, value)

    def fixed_size(self, horizontal: bool = True, vertical: bool = True) -> "View":
        from .layout_modifiers import fixed_size
        return fixed_size(self, horizontal, vertical)

    def offset(self, x: float = 0.0, y: float = 0.0) -> "View":
        from .layout_modifiers import offset
        return offset(self, x, y)

    def position(self, x: float, y: float) -> "View":
        from .layout_modifiers import position
        return position(self, x, y)

    def z_index(self, value: float) -> "View":
        from .layout_modifiers import z_index
        return z_index(self, value)

    def aspect_ratio(self, ratio=None, content_mode: str = "fit") -> "View":
        from .layout_modifiers import aspect_ratio
        return aspect_ratio(self, ratio, content_mode)

    def safe_area_inset(self, edge: str, length: float) -> "View":
        from .layout_modifiers import safe_area_inset
        return safe_area_inset(self, edge, length)

    def ignores_safe_area(self, edges="all") -> "View":
        from .layout_modifiers import ignores_safe_area
        return ignores_safe_area(self, edges)

    def button_style(self, style: str) -> "View":
        from .styles import button_style
        return button_style(self, style)

    def toggle_style(self, style: str) -> "View":
        from .styles import toggle_style
        return toggle_style(self, style)

    def picker_style(self, style: str) -> "View":
        from .styles import picker_style
        return picker_style(self, style)

    def label_style(self, style: str) -> "View":
        from .styles import label_style
        return label_style(self, style)

    def progress_view_style(self, style: str) -> "View":
        from .styles import progress_view_style
        return progress_view_style(self, style)

    def text_field_style(self, style: str) -> "View":
        from .styles import text_field_style
        return text_field_style(self, style)

    def control_group_style(self, style: str) -> "View":
        from .styles import control_group_style
        return control_group_style(self, style)

    def tint(self, color) -> "View":
        from .styles import tint
        return tint(self, color)

    def control_size(self, size: str) -> "View":
        from .styles import control_size
        return control_size(self, size)

    def disabled(self, value: bool = True) -> "View":
        from .styles import disabled
        return disabled(self, value)

    def labels_hidden(self, hidden: bool = True) -> "View":
        from .styles import labels_hidden
        return labels_hidden(self, hidden)

    def badge(self, value) -> "View":
        from .badges import badge
        return badge(self, value)

    def on_tap_gesture(self, action: Callable[[], None]) -> "View":
        from .modifiers import on_tap_gesture as _on_tap
        return _on_tap(self, action)

    def on_long_press_gesture(self, action: Callable[[], None], minimum_duration: float = 0.5) -> "View":
        from .gestures import on_long_press_gesture as _on_long
        return _on_long(self, action, minimum_duration=minimum_duration)

    def on_drag_gesture(self, action, minimum_distance: float = 10.0) -> "View":
        from .gestures import on_drag_gesture as _on_drag
        return _on_drag(self, action, minimum_distance=minimum_distance)

    def gesture(self, value, including: str = "all") -> "View":
        from .gestures import gesture
        return gesture(self, value, including)

    def high_priority_gesture(self, value, including: str = "all") -> "View":
        from .gestures import high_priority_gesture
        return high_priority_gesture(self, value, including)

    def simultaneous_gesture(self, value, including: str = "all") -> "View":
        from .gestures import simultaneous_gesture
        return simultaneous_gesture(self, value, including)

    def animation(self, animation) -> "View":
        from .modifiers import animation as _animation
        return _animation(self, animation)

    def transition(self, value) -> "View":
        from .transitions import transition
        return transition(self, value)

    def content_transition(self, value: str) -> "View":
        from .transitions import content_transition
        return content_transition(self, value)

    def symbol_effect(self, effect: str, value=None, repeating: bool = False) -> "View":
        from .transitions import symbol_effect
        return symbol_effect(self, effect, value, repeating)

    def transaction(self, transform) -> "View":
        from .animation_modifiers import transaction
        return transaction(self, transform)

    def matched_geometry_effect(self, matched_id, namespace, properties: str = "frame",
                                anchor: str = "center", is_source: bool = True) -> "View":
        from .animation_modifiers import matched_geometry_effect
        return matched_geometry_effect(
            self, matched_id, namespace, properties=properties,
            anchor=anchor, is_source=is_source,
        )

    def accessibility_reduce_motion(self, enabled: bool = True) -> "View":
        from .animation_modifiers import accessibility_reduce_motion
        return accessibility_reduce_motion(self, enabled)

    def scale_effect(self, scale: float = 1.0, y=None, anchor: str = "center") -> "View":
        from .rendering import scale_effect
        return scale_effect(self, scale, y, anchor)

    def rotation_effect(self, degrees: float, anchor: str = "center") -> "View":
        from .rendering import rotation_effect
        return rotation_effect(self, degrees, anchor)

    def rotation_3d_effect(self, degrees: float, axis=(0.0, 1.0, 0.0),
                           perspective: float = 1.0 / 500.0) -> "View":
        from .rendering import rotation_3d_effect
        return rotation_3d_effect(self, degrees, axis, perspective)

    def blur(self, radius: float = 3.0) -> "View":
        from .rendering import blur
        return blur(self, radius)

    def brightness(self, amount: float) -> "View":
        from .rendering import brightness
        return brightness(self, amount)

    def contrast(self, amount: float) -> "View":
        from .rendering import contrast
        return contrast(self, amount)

    def saturation(self, amount: float) -> "View":
        from .rendering import saturation
        return saturation(self, amount)

    def grayscale(self, amount: float = 1.0) -> "View":
        from .rendering import grayscale
        return grayscale(self, amount)

    def hue_rotation(self, degrees: float) -> "View":
        from .rendering import hue_rotation
        return hue_rotation(self, degrees)

    def blend_mode(self, mode: str) -> "View":
        from .rendering import blend_mode
        return blend_mode(self, mode)

    def compositing_group(self) -> "View":
        from .rendering import compositing_group
        return compositing_group(self)

    def drawing_group(self, opaque: bool = False, color_mode: str = "nonLinear") -> "View":
        from .rendering import drawing_group
        return drawing_group(self, opaque, color_mode)

    def clipped(self, antialiased: bool = True) -> "View":
        from .rendering import clipped
        return clipped(self, antialiased)

    def clip_shape(self, shape, antialiased: bool = True) -> "View":
        from .rendering import clip_shape
        return clip_shape(self, shape, antialiased)

    def mask(self, mask_view) -> "View":
        from .rendering import mask
        return mask(self, mask_view)

    def kerning(self, value: float) -> "View":
        from .text import kerning
        return kerning(self, value)

    def tracking(self, value: float) -> "View":
        from .text import tracking
        return tracking(self, value)

    def baseline_offset(self, value: float) -> "View":
        from .text import baseline_offset
        return baseline_offset(self, value)

    def text_case(self, value) -> "View":
        from .text import text_case
        return text_case(self, value)

    def multiline_text_alignment(self, value: str) -> "View":
        from .text import multiline_text_alignment
        return multiline_text_alignment(self, value)

    def truncation_mode(self, value: str) -> "View":
        from .text import truncation_mode
        return truncation_mode(self, value)

    def minimum_scale_factor(self, value: float) -> "View":
        from .text import minimum_scale_factor
        return minimum_scale_factor(self, value)

    def allows_tightening(self, value: bool = True) -> "View":
        from .text import allows_tightening
        return allows_tightening(self, value)

    def monospaced_digit(self) -> "View":
        from .text import monospaced_digit
        return monospaced_digit(self)

    def text_selection(self, enabled: bool = True) -> "View":
        from .text import text_selection
        return text_selection(self, enabled)

    def locale(self, value) -> "View":
        from .localization import locale
        return locale(self, value)

    def layout_direction(self, value: str) -> "View":
        from .localization import layout_direction
        return layout_direction(self, value)

    def dynamic_type_size(self, value: str) -> "View":
        from .localization import dynamic_type_size
        return dynamic_type_size(self, value)

    def redacted(self, reason: str = "placeholder") -> "View":
        from .localization import redacted
        return redacted(self, reason)

    def privacy_sensitive(self, value: bool = True) -> "View":
        from .localization import privacy_sensitive
        return privacy_sensitive(self, value)

    def help(self, text: str) -> "View":
        from .localization import help
        return help(self, text)

    def preference(self, key, value) -> "View":
        from .preferences import preference
        return preference(self, key, value)

    def transform_preference(self, key, transform) -> "View":
        from .preferences import transform_preference
        return transform_preference(self, key, transform)

    def on_preference_change(self, key, action) -> "View":
        from .preferences import on_preference_change
        return on_preference_change(self, key, action)

    def draggable(self, item, preview=None) -> "View":
        from .transfer import draggable
        return draggable(self, item, preview)

    def drop_destination(self, item_type, action, is_targeted=None) -> "View":
        from .transfer import drop_destination
        return drop_destination(self, item_type, action, is_targeted)

    def context_menu(self, menu) -> "View":
        from .interaction import context_menu
        return context_menu(self, menu)

    def on_hover(self, action) -> "View":
        from .interaction import on_hover
        return on_hover(self, action)

    def hover_effect(self, effect="automatic") -> "View":
        from .interaction import hover_effect
        return hover_effect(self, effect)

    def allows_hit_testing(self, enabled: bool = True) -> "View":
        from .interaction import allows_hit_testing
        return allows_hit_testing(self, enabled)

    def content_shape(self, shape, kind: str = "interaction") -> "View":
        from .interaction import content_shape
        return content_shape(self, shape, kind)

    def sensory_feedback(self, feedback, trigger, condition=None, key: str = "") -> "View":
        from .interaction import sensory_feedback
        return sensory_feedback(self, feedback, trigger, condition, key)

    def list_style(self, style: str) -> "View":
        from .container_styles import list_style
        return list_style(self, style)

    def form_style(self, style: str) -> "View":
        from .container_styles import form_style
        return form_style(self, style)

    def group_box_style(self, style: str) -> "View":
        from .container_styles import group_box_style
        return group_box_style(self, style)

    def disclosure_group_style(self, style: str) -> "View":
        from .container_styles import disclosure_group_style
        return disclosure_group_style(self, style)

    def section_spacing(self, value: float) -> "View":
        from .container_styles import section_spacing
        return section_spacing(self, value)

    def header_prominence(self, value: str) -> "View":
        from .container_styles import header_prominence
        return header_prominence(self, value)

    def list_row_background(self, color) -> "View":
        from .container_styles import list_row_background
        return list_row_background(self, color)

    def list_row_separator(self, visibility: str = "automatic") -> "View":
        from .container_styles import list_row_separator
        return list_row_separator(self, visibility)

    def list_row_insets(self, insets) -> "View":
        from .container_styles import list_row_insets
        return list_row_insets(self, insets)

    def swipe_actions(self, actions, edge: str = "trailing",
                      allows_full_swipe: bool = True) -> "View":
        from .list_editing import swipe_actions
        return swipe_actions(self, actions, edge, allows_full_swipe)

    def delete_disabled(self, disabled: bool = True) -> "View":
        from .list_editing import delete_disabled
        return delete_disabled(self, disabled)

    def move_disabled(self, disabled: bool = True) -> "View":
        from .list_editing import move_disabled
        return move_disabled(self, disabled)

    def searchable(self, text, prompt: str = "Search", placement: str = "automatic",
                   suggestions=(), scopes=(), scope=None, tokens=(),
                   is_presented=None, on_submit=None) -> "View":
        from .search import searchable
        return searchable(self, text, prompt, placement, suggestions, scopes, scope,
                          tokens, is_presented, on_submit)

    def task(self, action, task_id=None, priority: str = "userInitiated",
             key: str = "") -> "View":
        from .async_actions import task
        return task(self, action, task_id, priority, key)

    def refreshable(self, action) -> "View":
        from .async_actions import refreshable
        return refreshable(self, action)

    def scroll_indicators(self, visibility: str) -> "View":
        from .scrolling import scroll_indicators
        return scroll_indicators(self, visibility)

    def default_scroll_anchor(self, anchor: str) -> "View":
        from .scrolling import default_scroll_anchor
        return default_scroll_anchor(self, anchor)

    def scroll_target_behavior(self, behavior: str) -> "View":
        from .scrolling import scroll_target_behavior
        return scroll_target_behavior(self, behavior)

    def scroll_clip_disabled(self, disabled: bool = True) -> "View":
        from .scrolling import scroll_clip_disabled
        return scroll_clip_disabled(self, disabled)

    def content_margins(self, margins) -> "View":
        from .scrolling import content_margins
        return content_margins(self, margins)

    def scroll_position(self, position, anchor: str = "top") -> "View":
        from .scrolling import scroll_position
        return scroll_position(self, position, anchor)

    def sheet(self, is_presented, content, title: str = "", size=None) -> "View":
        from .geometry import Size
        from .presentation import sheet as _sheet
        return _sheet(self, is_presented, content, title,
                      size if size is not None else Size(520.0, 360.0))

    def full_screen_cover(self, is_presented, content, title: str = "") -> "View":
        from .presentation import full_screen_cover
        return full_screen_cover(self, is_presented, content, title)

    def presentation_detents(self, detents, selection=None) -> "View":
        from .presentation import presentation_detents
        return presentation_detents(self, detents, selection)

    def presentation_drag_indicator(self, visibility: str) -> "View":
        from .presentation import presentation_drag_indicator
        return presentation_drag_indicator(self, visibility)

    def interactive_dismiss_disabled(self, disabled: bool = True) -> "View":
        from .presentation import interactive_dismiss_disabled
        return interactive_dismiss_disabled(self, disabled)

    def presentation_background_interaction(self, behavior: str) -> "View":
        from .presentation import presentation_background_interaction
        return presentation_background_interaction(self, behavior)

    def presentation_corner_radius(self, radius: float) -> "View":
        from .presentation import presentation_corner_radius
        return presentation_corner_radius(self, radius)

    def inspector(self, is_presented, content, minimum: float = 220.0,
                  ideal: float = 280.0, maximum: float = 420.0,
                  compact_threshold: float = 600.0) -> "View":
        from .inspector import inspector
        return inspector(self, is_presented, content, minimum, ideal, maximum,
                         compact_threshold)

    def alert(self, title: str, is_presented, message: str = "", buttons=None) -> "View":
        from .components import Button
        from .presentation import alert as _alert
        actual_buttons = buttons if buttons is not None else (Button("OK", lambda: None),)
        return _alert(self, title, is_presented, message, actual_buttons)

    def confirmation_dialog(self, title: str, is_presented, message: str = "",
                            buttons=None) -> "View":
        from .presentation import confirmation_dialog as _dialog
        return _dialog(self, title, is_presented, message, buttons or ())

    def popover(self, is_presented, content, size=None, edge: str = "bottom") -> "View":
        from .geometry import Size
        from .presentation import popover as _popover
        return _popover(self, is_presented, content,
                        size if size is not None else Size(320.0, 240.0), edge)

    def snack_bar(self, message: str, is_presented, *, action=None, duration: float = 4.0) -> "View":
        from .presentation import snack_bar
        return snack_bar(self, message, is_presented, action=action, duration=duration)

    def toolbar(self, items) -> "View":
        from .commands import toolbar as _toolbar
        return _toolbar(self, items)

    def material_background(self, material="regular") -> "View":
        from .visual_effects import material_background as _material
        return _material(self, material)

    def shadow(self, color=None, radius: float = 6.0, x: float = 0.0,
               y: float = 2.0) -> "View":
        from .geometry import Color
        from .visual_effects import shadow as _shadow
        return _shadow(self, color or Color(0, 0, 0, 0.25), radius, x, y)

    def overlay(self, overlay_view: "View", alignment: str = "center") -> "View":
        from .visual_effects import overlay as _overlay
        return _overlay(self, overlay_view, alignment)

    def id(self, value) -> "View":
        from .scrolling import view_id as _view_id
        return _view_id(self, value)

    def focused(self, binding, equals=True) -> "View":
        from .focus import focused as _focused
        return _focused(self, binding, equals)

    def default_focus(self, binding, equals=True) -> "View":
        from .keyboard import default_focus
        return default_focus(self, binding, equals)

    def focus_section(self, section_id=None) -> "View":
        from .keyboard import focus_section
        return focus_section(self, section_id)

    def keyboard_shortcut(self, shortcut, modifiers=("command",)) -> "View":
        from .keyboard import keyboard_shortcut
        return keyboard_shortcut(self, shortcut, modifiers)

    def on_key_press(self, keys=None, action=None) -> "View":
        from .keyboard import on_key_press
        return on_key_press(self, keys, action)

    def on_appear(self, action: Callable[[], None]) -> "View":
        from .events import on_appear as _on_appear
        return _on_appear(self, action)

    def on_disappear(self, action: Callable[[], None]) -> "View":
        from .events import on_disappear as _on_disappear
        return _on_disappear(self, action)

    def on_change(self, value, action: Callable, initial: bool = False, key=None) -> "View":
        from .events import on_change as _on_change
        return _on_change(self, value, action, initial, key)

    def on_submit(self, action: Callable[[], None]) -> "View":
        from .events import on_submit as _on_submit
        return _on_submit(self, action)

    def submit_label(self, label: str) -> "View":
        from .events import submit_label as _submit_label
        return _submit_label(self, label)

    def file_importer(self, is_presented, allowed_extensions, on_completion,
                      allows_multiple: bool = False) -> "View":
        from .file_dialogs import file_importer as _file_importer
        return _file_importer(
            self, is_presented, allowed_extensions, on_completion, allows_multiple
        )

    def file_exporter(self, is_presented, document, default_filename,
                      on_completion) -> "View":
        from .file_dialogs import file_exporter as _file_exporter
        return _file_exporter(
            self, is_presented, document, default_filename, on_completion
        )

    def environment(self, key: str, value) -> "View":
        from .environment import environment as _environment
        return _environment(self, key, value)

    def environment_object(self, value) -> "View":
        from .environment import environment_object as _environment_object
        return _environment_object(self, value)

    def preferred_color_scheme(self, scheme) -> "View":
        from .system_environment import preferred_color_scheme
        return preferred_color_scheme(self, scheme)

    def scene_phase(self, phase) -> "View":
        from .system_environment import scene_phase_override
        return scene_phase_override(self, phase)

    def control_active_state(self, state) -> "View":
        from .system_environment import control_active_state_override
        return control_active_state_override(self, state)

    def open_url_action(self, action) -> "View":
        from .system_environment import open_url_action
        return open_url_action(self, action)

    def dismiss_action(self, action) -> "View":
        from .system_environment import dismiss_action
        return dismiss_action(self, action)

    def navigation_title(self, title: str) -> "View":
        from .navigation import navigation_title
        return navigation_title(self, title)

    def navigation_bar_title_display_mode(self, mode: str) -> "View":
        from .navigation import navigation_bar_title_display_mode
        return navigation_bar_title_display_mode(self, mode)

    def navigation_bar_hidden(self, hidden: bool = True) -> "View":
        from .navigation import navigation_bar_hidden
        return navigation_bar_hidden(self, hidden)

    def navigation_bar_background(self, color) -> "View":
        from .navigation import navigation_bar_background
        return navigation_bar_background(self, color)

    def accessibility_label(self, label: str) -> "View":
        from .accessibility import accessibility_label as _label
        return _label(self, label)

    def accessibility_hint(self, hint: str) -> "View":
        from .accessibility import accessibility_hint as _hint
        return _hint(self, hint)

    def accessibility_value(self, value: str) -> "View":
        from .accessibility import accessibility_value as _value
        return _value(self, value)

    def accessibility_hidden(self, hidden: bool = True) -> "View":
        from .accessibility import accessibility_hidden as _hidden
        return _hidden(self, hidden)

    def accessibility_element(self, children: str = "contain") -> "View":
        from .accessibility import accessibility_element as _element
        return _element(self, children)

    def accessibility_add_traits(self, traits) -> "View":
        from .accessibility import accessibility_add_traits
        return accessibility_add_traits(self, traits)

    def accessibility_remove_traits(self, traits) -> "View":
        from .accessibility import accessibility_remove_traits
        return accessibility_remove_traits(self, traits)

    def accessibility_sort_priority(self, priority: float) -> "View":
        from .accessibility import accessibility_sort_priority
        return accessibility_sort_priority(self, priority)

    def accessibility_identifier(self, identifier: str) -> "View":
        from .accessibility import accessibility_identifier
        return accessibility_identifier(self, identifier)

    def accessibility_heading(self, level: int = 1) -> "View":
        from .accessibility import accessibility_heading
        return accessibility_heading(self, level)

    def accessibility_input_labels(self, labels) -> "View":
        from .accessibility import accessibility_input_labels
        return accessibility_input_labels(self, labels)

    def accessibility_custom_content(self, key: str, value: str,
                                     importance: str = "default") -> "View":
        from .accessibility import accessibility_custom_content
        return accessibility_custom_content(self, key, value, importance)

    def accessibility_action(self, name: str, action) -> "View":
        from .accessibility import accessibility_action
        return accessibility_action(self, name, action)

    def accessibility_adjustable_action(self, action) -> "View":
        from .accessibility import accessibility_adjustable_action
        return accessibility_adjustable_action(self, action)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__}>"


class ViewModifier(abc.ABC):
    """Base class for view modifiers (mirrors SwiftUI's ViewModifier)."""

    def body(self, content: View) -> View:
        return content


class _ModifiedContent(View):
    """Wraps a content view together with a modifier (internal)."""

    def __init__(self, content: View, modifier: ViewModifier):
        self._content = content
        self._modifier = modifier
        self.modifiers = list(content.modifiers) + [modifier]
        self._children = [content]

    def body(self) -> View:
        # Use the base View._content explicitly: subclasses (e.g. Text) store
        # their payload in a ``_content`` attribute that shadows the method.
        return View._content(self._content)

    def size_that_fits(self, proposal: Size) -> Size:
        return self._modifier.size_that_fits(self._content, proposal)

    def place(self, origin: Point, size: Size) -> None:
        self._modifier.place(self._content, origin, size)

    def children(self) -> Sequence[View]:
        return self._children


def _apply(view: View, modifier: ViewModifier) -> View:
    """Attach a modifier to a view, returning the (possibly wrapped) view."""
    if isinstance(modifier, FrameModifier):
        return modifier.apply(view)
    wrapped = _ModifiedContent(view, modifier)
    return wrapped


class FrameModifier(ViewModifier):
    """The .frame() modifier — the only modifier that must wrap structurally."""

    def __init__(
        self,
        width: Optional[float] = None,
        height: Optional[float] = None,
        alignment: str = "center",
    ):
        self.width = width
        self.height = height
        self.alignment = alignment

    def apply(self, content: View) -> View:
        return _Frame(content, self.width, self.height, self.alignment)

    def body(self, content: View) -> View:
        return _Frame(content, self.width, self.height, self.alignment)


class _Frame(View):
    """A view that proposes a fixed size to its child and aligns it."""

    def __init__(self, content: View, width: Optional[float], height: Optional[float], alignment: str):
        self._content = content
        self._width = width
        self._height = height
        self._alignment = alignment
        self._children = [content]

    def size_that_fits(self, proposal: Size) -> Size:
        w = self._width if self._width is not None else proposal.width
        h = self._height if self._height is not None else proposal.height
        return Size(w, h)

    def place(self, origin: Point, size: Size) -> None:
        child_size = self._content.size_that_fits(size)
        x, y = _aligned_offset(size, child_size, self._alignment)
        self._content.place(Point(origin.x + x, origin.y + y), child_size)

    def children(self) -> Sequence[View]:
        return self._children


def _aligned_offset(container: Size, child: Size, alignment: str) -> Tuple[float, float]:
    """Compute the offset of a child within a container for an alignment."""
    alignments = {
        "topLeading": (0.0, 0.0),
        "top": (0.5, 0.0),
        "topTrailing": (1.0, 0.0),
        "leading": (0.0, 0.5),
        "center": (0.5, 0.5),
        "trailing": (1.0, 0.5),
        "bottomLeading": (0.0, 1.0),
        "bottom": (0.5, 1.0),
        "bottomTrailing": (1.0, 1.0),
    }
    fx, fy = alignments.get(alignment, (0.5, 0.5))
    return (container.width - child.width) * fx, (container.height - child.height) * fy
