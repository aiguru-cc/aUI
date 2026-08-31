"""Native context menu, hover tracking, hit testing and sensory feedback."""
from aui import (
    Button, Divider, HoverEffect, Menu, RoundedRectangle,
    SensoryFeedback, State, Text, VStack, Window,
)
from appkit_support import run_window


saved = State(0)
hovered = State(False)


def save():
    saved.wrapped_value += 1


actions = Menu("Actions", [
    Button("Save", save),
    Divider(),
    Button("Delete", lambda: None, role="destructive"),
])


def content():
    return VStack([
        Text("Hovering" if hovered.wrapped_value else "Hover over this card")
        .padding(length=18)
        .content_shape(RoundedRectangle(14))
        .hover_effect(HoverEffect.LIFT)
        .on_hover(hovered._set)
        .context_menu(actions),
        Button("Save", save)
        .sensory_feedback(SensoryFeedback.success(), saved.wrapped_value, key="save"),
        Text(f"Saved {saved.wrapped_value} times"),
    ])


if __name__ == "__main__":
    run_window("Interaction Feedback", content, width=540, height=320)
