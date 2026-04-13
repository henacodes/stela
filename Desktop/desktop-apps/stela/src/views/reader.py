import flet as ft
from typing import cast
from flet import Icons
from contexts.app_context import AppContext

@ft.component
def ReaderView():
    state = ft.use_context(AppContext)

    header_controls = cast(list[ft.Control], [
        ft.IconButton(Icons.ARROW_BACK, on_click=lambda _: state.navigate("/")),
        ft.Text(state.selected_book.split("/")[-1] if state.selected_book else "No Book", size=20),
    ])

    column_controls = cast(list[ft.Control], [
        ft.Row(controls=header_controls),
        ft.Divider(),
        ft.Container(
            content=ft.Text("PDF Rendering Engine will go here"),
            alignment=ft.Alignment(0, 0),
            expand=True,
        ),
    ])

    return ft.Column(controls=column_controls)