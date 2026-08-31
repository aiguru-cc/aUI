"""Phase and keyframe animation descriptions rendered with native AppKit."""
from aui import (
    Animation, Button, ButtonStyle, HStack, Keyframe, KeyframeAnimator,
    PhaseAnimator, SymbolEffect, Text, Transition, VStack, Window,
)
from appkit_support import run_window


phase = PhaseAnimator(
    ["Ready", "Set", "Go"],
    lambda value: Text(value).symbol_effect(SymbolEffect.BOUNCE, value=value),
    animation=Animation.spring(),
)
timeline = KeyframeAnimator(
    0.0,
    [Keyframe(1.0, 0.2, "easeOut"), Keyframe(0.85, 0.15), Keyframe(1.0, 0.2)],
    lambda value: Text(f"Scale value: {value:.2f}"),
)


def content():
    return VStack([
        phase.transition(Transition.asymmetric(Transition.scale(), Transition.opacity())),
        timeline,
        HStack([
            Button("Next phase", phase.advance).button_style(ButtonStyle.BORDERED_PROMINENT),
            Button("End keyframes", lambda: timeline.seek(1.0)),
        ]),
    ])


if __name__ == "__main__":
    run_window("Advanced Animation", content, width=520, height=280)
