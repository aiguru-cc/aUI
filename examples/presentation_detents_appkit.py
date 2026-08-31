"""Configured sheets and full-screen covers on AppKit."""

from aui import (
    Button, PresentationDetent, Size, State, Text, VStack, Window,
)
from aui.backends.appkit import AppKitApplication


show_sheet = State(False)
show_cover = State(False)
selected_detent = State(PresentationDetent.medium())


def make_view():
    sheet_host = Button("Show detent sheet", lambda: setattr(show_sheet, "value", True)).sheet(
        show_sheet.binding(),
        lambda dismiss: VStack([Text("Resizable presentation"), Button("Done", dismiss)], spacing=16).padding(length=24),
        title="Details",
    ).presentation_detents(
        [PresentationDetent.medium(), PresentationDetent.large()], selected_detent.binding()
    ).presentation_drag_indicator("visible").presentation_corner_radius(18)

    cover_host = Button("Show cover", lambda: setattr(show_cover, "value", True)).full_screen_cover(
        show_cover.binding(),
        lambda dismiss: VStack([Text("Full-screen cover"), Button("Close", dismiss)], spacing=16).padding(length=30),
    ).interactive_dismiss_disabled()
    return VStack([sheet_host, cover_host], spacing=16).padding(length=24)


if __name__ == "__main__":
    AppKitApplication(Window(
        "aUI · Presentations", make_view, default_size=Size(560, 460)
    )).run()
