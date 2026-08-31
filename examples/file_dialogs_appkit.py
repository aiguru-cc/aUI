"""Native SwiftUI-style file importer and exporter modifiers."""

from aui import Button, Size, State, Text, VStack, Window
from aui.backends.appkit import AppKitApplication


show_importer = State(False)
show_exporter = State(False)
status = State("No file operation yet")


def imported(result):
    if result.cancelled:
        status._set("Import cancelled")
    elif result.error:
        status._set(f"Import failed: {result.error}")
    else:
        status._set("Imported: " + ", ".join(path.name for path in result.urls))


def exported(result):
    status._set("Export cancelled" if result.cancelled else f"Exported: {result.urls[0]}")


def make_view():
    content = VStack([
        Text("File Importer & Exporter"),
        Button("Import JSON or Text…", lambda: show_importer._set(True)),
        Button("Export Report…", lambda: show_exporter._set(True)),
        Text(status.value),
    ], spacing=16, alignment="leading").padding(length=24)
    return content.file_importer(
        show_importer.binding(), ["json", "txt"], imported, allows_multiple=True
    ).file_exporter(
        show_exporter.binding(), lambda: "aUI export\n", "aUI-report.txt", exported
    )


def main():
    AppKitApplication(
        Window("aUI · File Dialogs", make_view, default_size=Size(600, 380))
    ).run()


if __name__ == "__main__":
    main()
