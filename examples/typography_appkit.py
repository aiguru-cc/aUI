"""AttributedString, Markdown, and native typography modifiers."""
from aui import AttributedString, Font, Text, VStack, Window
from appkit_support import run_window


def content():
    markdown = AttributedString.markdown(
        "**Native typography** with *emphasis*, `code`, and [links](https://python.org)"
    )
    return VStack([
        Text(markdown).font(Font.title()).text_selection(),
        Text("Tracking and baseline").tracking(1.4).baseline_offset(2),
        Text("1234567890").monospaced_digit(),
        Text("A long title that can tighten and truncate in the middle")
        .truncation_mode("middle").allows_tightening().minimum_scale_factor(0.7),
        Text("centered\nmultiline text").multiline_text_alignment("center"),
    ])


if __name__ == "__main__":
    run_window("Typography", content, width=620, height=340)
