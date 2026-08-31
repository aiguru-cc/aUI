"""Contracts for the SwiftUI-native API after removing Bootstrap shims."""
import pytest

import aui
from aui import (
    Button, ButtonStyle, Color, ControlSize, ProgressView, Slider, State,
    Text, TextField, Toggle, describe_accessibility,
)
from aui.backends.ascii import AsciiBackend
from aui.core.badges import BadgeModifier
from aui.core.styles import is_enabled, style_value


def test_bootstrap_component_and_chain_methods_are_removed():
    assert not hasattr(aui, "Badge")
    assert not hasattr(aui, "SegmentedControl")
    assert not hasattr(aui, "SearchField")
    for name in (
        "animation", "background", "border", "corner_radius", "font",
        "foreground_color", "frame", "hidden", "on_tap_gesture", "opacity",
        "padding", "badge", "button_style", "control_group_style", "control_size",
        "disabled", "label_style", "labels_hidden", "picker_style",
        "progress_view_style", "text_field_style", "tint", "toggle_style",
        "aspect_ratio", "fixed_size", "ignores_safe_area", "layout_priority",
        "offset", "position", "safe_area_inset", "z_index",
        "blend_mode", "blur", "brightness", "clip_shape", "clipped",
        "compositing_group", "contrast", "drawing_group", "grayscale",
        "hue_rotation", "mask", "rotation_3d_effect", "rotation_effect",
        "saturation", "scale_effect", "allows_tightening", "baseline_offset",
        "kerning", "minimum_scale_factor", "monospaced_digit",
        "multiline_text_alignment", "text_case", "text_selection", "tracking",
        "truncation_mode", "dynamic_type_size", "help", "layout_direction",
        "locale", "privacy_sensitive", "redacted", "disclosure_group_style",
        "form_style", "group_box_style", "header_prominence",
        "list_row_background", "list_row_insets", "list_row_separator",
        "list_style", "section_spacing",
        "navigation_bar_background", "navigation_bar_hidden",
        "navigation_bar_title_display_mode", "navigation_title", "alert",
        "confirmation_dialog", "full_screen_cover",
        "interactive_dismiss_disabled", "popover",
        "presentation_background_interaction", "presentation_corner_radius",
        "presentation_detents", "presentation_drag_indicator", "sheet",
        "on_appear", "on_change", "on_disappear", "on_submit", "submit_label",
        "FullScreenCoverModifier", "collect_presentation_configurations",
        "environment", "environment_object",
        "dismiss_action", "open_url_action", "preferred_color_scheme",
        "content_margins", "default_scroll_anchor",
        "scroll_clip_disabled", "scroll_indicators", "scroll_position",
        "scroll_target_behavior", "focused", "inspector", "default_focus",
        "focus_section", "keyboard_shortcut", "on_key_press", "refreshable",
        "task", "file_exporter", "file_importer", "DefaultFocusModifier",
        "FocusSectionModifier", "KeyboardShortcutModifier", "OnKeyPressModifier",
        "content_transition", "symbol_effect", "transition", "delete_disabled",
        "move_disabled", "swipe_actions", "searchable", "SearchableView",
        "material_background", "overlay", "shadow",
        "on_preference_change", "preference", "transform_preference",
        "draggable", "drop_destination", "allows_hit_testing", "content_shape",
        "context_menu", "hover_effect", "on_hover", "sensory_feedback",
        "DraggableModifier", "DropDestinationModifier",
        "accessibility_action", "accessibility_add_traits",
        "accessibility_adjustable_action", "accessibility_custom_content",
        "accessibility_element", "accessibility_heading", "accessibility_hidden",
        "accessibility_hint", "accessibility_identifier", "accessibility_input_labels",
        "accessibility_label", "accessibility_reduce_motion",
        "accessibility_remove_traits", "accessibility_sort_priority",
        "accessibility_value", "gesture", "high_priority_gesture",
        "on_drag_gesture", "on_long_press_gesture", "simultaneous_gesture",
        "matched_geometry_effect", "transaction", "toolbar",
        "animate", "current_animation", "current_transaction",
        "collect_preferences", "preference_value", "payload_for", "simulate_drop",
        "cancel_tasks", "start_tasks", "NavigationConfiguration",
        "navigation_configuration", "PresentationConfiguration",
        "ScrollConfiguration", "find_scroll_configuration", "scroll_configuration",
        "refresh", "control_active_state_override", "scene_phase_override",
        "system_environment", "view_id",
        "AlertButton",
        "MenuItem", "MenuDivider",
    ):
        assert not hasattr(aui, name)
    for view in (Button("Save", lambda: None), Toggle("On", State(True).binding()),
                 ProgressView(0.5)):
        assert not hasattr(view, "variant")
    button = Button("Save", lambda: None)
    for name in ("button_size", "outlined", "as_block", "as_pill", "with_shadow"):
        assert not hasattr(button, name)


def test_button_only_accepts_swiftui_roles():
    assert Button("Delete", lambda: None, role="destructive").role == "destructive"
    assert Button("Cancel", lambda: None, role="cancel").role == "cancel"
    assert Button("Save", lambda: None).role is None
    with pytest.raises(ValueError, match="destructive"):
        Button("Old", lambda: None, role="success")


def test_swiftui_styles_replace_bootstrap_chains():
    view = (Button("Save", lambda: None)
            .button_style(ButtonStyle.BORDERED_PROMINENT)
            .control_size(ControlSize.LARGE)
            .tint(Color.green))
    from aui.core.styles import resolve_style_tree
    resolve_style_tree(view)
    leaf = view.find(lambda item: isinstance(item, Button))
    assert style_value(leaf, "button_style") == ButtonStyle.BORDERED_PROMINENT
    assert style_value(leaf, "control_size") == ControlSize.LARGE
    assert style_value(leaf, "tint") is Color.green


def test_disabled_is_the_swiftui_view_modifier():
    view = Button("Save", lambda: None).disabled()
    from aui.core.styles import resolve_style_tree
    resolve_style_tree(view)
    leaf = view.find(lambda item: isinstance(item, Button))
    assert not is_enabled(leaf)


def test_controls_reject_legacy_enabled_constructor_argument():
    constructors = (
        lambda: Button("Save", lambda: None, enabled=False),
        lambda: TextField(State("").binding(), enabled=False),
        lambda: Toggle("On", State(True).binding(), enabled=False),
        lambda: Slider(State(0.5).binding(), enabled=False),
    )
    for constructor in constructors:
        with pytest.raises(TypeError, match="enabled"):
            constructor()


def test_badge_is_a_modifier_with_rendering_and_accessibility():
    view = Text("Inbox").badge(7)
    assert isinstance(view._modifier, BadgeModifier)
    assert "[7]" in AsciiBackend(width=30, height=3).render(view)
    assert describe_accessibility(view).value == "badge 7"
