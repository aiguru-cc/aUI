"""View lifecycle and native text-field submission example."""

from aui import FocusState, Size, State, Text, TextField, VStack, Window
from aui.backends.appkit import AppKitApplication

query = State("")
last_submission = State("Nothing submitted")
focus = FocusState("query")


def submit():
    last_submission._set(f"Submitted: {query.wrapped_value or '(empty)'}")
    focus._set(None)


def make_view():
    return VStack([
        Text("Lifecycle & Submit"),
        TextField(query.binding(), "Search")
        .focused(focus.binding(), "query")
        .on_submit(submit)
        .submit_label("search"),
        Text(last_submission.wrapped_value),
    ], spacing=16, alignment="leading").padding(length=24).on_appear(
        lambda: print("content appeared")
    ).on_disappear(
        lambda: print("content disappeared")
    )


def main():
    AppKitApplication(
        Window("aUI · Lifecycle", make_view, default_size=Size(540, 340))
    ).run()


if __name__ == "__main__":
    main()
