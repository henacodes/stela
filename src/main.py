import flet as ft
import os
import sys
from components.app import App


def _extract_initial_open_path() -> str | None:
    supported = {".pdf", ".epub"}
    for raw in sys.argv[1:]:
        arg = raw.strip().strip('"').strip("'")
        if not arg:
            continue
        lower = arg.lower()
        if lower.startswith("--"):
            continue
        if lower.startswith("file://"):
            return arg
        if os.path.splitext(lower)[1] in supported:
            return arg
    return None

def main(page: ft.Page):
    # Minimal Shadcn-ish Theme Config
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(primary="#18181b", surface="#ffffff")
    )
    initial_open_path = _extract_initial_open_path()
    # Using render_views for the reactive Gallery-style flow
    page.render_views(lambda: App(initial_open_path=initial_open_path))

if __name__ == "__main__":
    ft.run(main)