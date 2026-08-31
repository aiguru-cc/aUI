"""Open and focus lazily created secondary windows by scene ID."""

from aui import DismissWindowLink, Size, Text, VStack, Window, WindowGroup, WindowLink
from aui.backends.appkit import AppKitApplication


def main_view():
    return VStack([
        Text("Workspace"),
        WindowLink("Show Inspector", "inspector"),
        WindowLink("Show Activity", "activity"),
    ], spacing=16, alignment="leading").padding(length=24)


def inspector_view():
    return VStack([
        Text("Inspector"),
        Text("A second click focuses this same window."),
        DismissWindowLink("Close Inspector"),
    ], spacing=12, alignment="leading").padding(length=24)


def main():
    AppKitApplication(WindowGroup([
        Window("aUI · Workspace", main_view, default_size=Size(600, 400)),
        Window("Inspector", inspector_view, id="inspector",
               default_size=Size(380, 420), initially_presented=False),
        Window("Activity", lambda: Text("Background activity").padding(length=24),
               id="activity", default_size=Size(420, 280), initially_presented=False),
    ])).run()


if __name__ == "__main__":
    main()
