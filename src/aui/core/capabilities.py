"""Explicit renderer capability names used for portable aUI feature checks."""


class Capability:
    NATIVE_SYMBOLS = "native_symbols"
    TOOLBAR = "toolbar"
    SPLIT_DIVIDER_DRAG = "split_divider_drag"
    SNACK_BAR = "snack_bar"
    SNACK_BAR_ACTION = "snack_bar_action"
    WINDOW_EVENTS = "window_events"
    RESPONSIVE_ROW = "responsive_row"
    NAVIGATION_RAIL = "navigation_rail"
    APP_BAR = "app_bar"
    FILE_DIALOGS = "file_dialogs"
    DRAG_AND_DROP = "drag_and_drop"

    ALL = frozenset(value for name, value in vars().items()
                    if name.isupper() and isinstance(value, str))
