"""StateObject, EnvironmentObject, scoped values and automatic observation."""

from aui import (
    Button, EnvironmentObject, EnvironmentReader, EnvironmentValue, Size,
    StateObject, Text, TextField, VStack, Window, observable,
)
from aui.backends.appkit import AppKitApplication


@observable
class AppModel:
    count = 0
    name = "Guest"


model = StateObject(AppModel)


def model_content(value):
    return VStack([
        Text(f"Hello, {value.name}"),
        Text(f"Count: {value.count}"),
        TextField(model.binding("name"), placeholder="Name"),
        Button("Increment", lambda: setattr(value, "count", value.count + 1)),
        EnvironmentReader(
            EnvironmentValue("accent_name", "System"),
            lambda accent: Text(f"Scoped accent: {accent}"),
        ),
    ], spacing=16, alignment="leading").on_change(
        value.count,
        lambda old, new: print(f"count changed: {old} -> {new}"),
        key="model-count",
    )


def make_view():
    content = EnvironmentReader(EnvironmentObject(AppModel), model_content)
    return content.environment_object(model.value).environment(
        "accent_name", "Indigo"
    ).padding(length=24)


def main():
    AppKitApplication(
        Window("aUI · Observation", make_view, default_size=Size(560, 420))
    ).run()


if __name__ == "__main__":
    main()
