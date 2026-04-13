import flet as ft
from typing import cast
from contexts.app_context import AppContext

@ft.component
def LibraryView():
    state = ft.use_context(AppContext)

    # The new async handler based on your docs
    async def handle_import_click(_):
        # The docs show pick_files() is now an awaitable method 
        # that returns the list of files directly
        files = await ft.FilePicker().pick_files(
            allow_multiple=False,
            allowed_extensions=["pdf", "epub"]
        )
        
        if files:
            # files[0].path gives us the local path we need
            selected_path = files[0].path
            if selected_path:
                state.import_book(selected_path)
                state.open_book(selected_path)

    grid_controls: list[ft.Control] = [
        ft.Container(
            content=ft.Text(path.split("/")[-1], text_align=ft.TextAlign.CENTER),
            on_click=lambda _, p=path: state.open_book(p),
            padding=20,
            border=ft.border.all(1, "#e4e4e7"),
            border_radius=8,
            bgcolor="white",
        )
        for path in state.library
    ]

    return ft.Column(
        cast(list[ft.Control], [
            ft.Text("My Stela", size=32, weight=ft.FontWeight.BOLD),
            ft.Button(
                "Import Book", 
                icon=ft.Icons.UPLOAD_FILE, 
                on_click=handle_import_click # Flet handles the async call automatically
            ),
            ft.GridView(
                expand=True,
                runs_count=4,
                spacing=20,
                controls=grid_controls,
            ),
        ])
    )