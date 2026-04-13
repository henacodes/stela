import flet as ft
from typing import Callable, cast


@ft.component
def TocPanel(
    width: float,
    current_page: int,
    entries: list[tuple[int, str, int]],
    on_jump_to_page: Callable[[int], None],
):
    toc_controls = cast(
        list[ft.Control],
        [
            ft.Container(
                padding=ft.padding.only(left=max(0, (level - 1) * 14), right=8),
                content=ft.TextButton(
                    title,
                    style=ft.ButtonStyle(
                        alignment=ft.Alignment(-1, 0),
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    ),
                    on_click=lambda _, p=page_index: on_jump_to_page(p),
                ),
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if page_index == current_page else None,
                border_radius=8,
            )
            for level, title, page_index in entries
        ],
    )

    return ft.Container(
        width=width,
        padding=10,
        content=ft.Column(
            spacing=8,
            controls=cast(
                list[ft.Control],
                [
                    ft.Text("Table of Contents", weight=ft.FontWeight.BOLD),
                    ft.Divider(height=8),
                    ft.Text("No table of contents found.") if not entries else ft.ListView(expand=True, controls=toc_controls),
                ],
            ),
            expand=True,
        ),
    )
