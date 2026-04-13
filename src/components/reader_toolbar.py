import flet as ft
from typing import Callable


@ft.component
def ReaderToolbar(
    current_page: int,
    page_count: int,
    zoom: float,
    is_vertical: bool,
    position_label: str,
    show_zoom_controls: bool,
    show_reading_mode_toggle: bool,
    toc_available: bool,
    show_toc: bool,
    on_back: Callable[[ft.Event[ft.IconButton]], None],
    on_prev_page: Callable[[ft.Event[ft.IconButton]], None],
    on_next_page: Callable[[ft.Event[ft.IconButton]], None],
    on_toggle_toc: Callable[[ft.Event[ft.IconButton]], None],
    on_toggle_reading_mode: Callable[[ft.Event[ft.IconButton]], None],
    on_zoom_in: Callable[[ft.Event[ft.IconButton]], None],
    on_zoom_out: Callable[[ft.Event[ft.IconButton]], None],
):
    right_controls: list[ft.Control] = []
    if show_zoom_controls:
        right_controls.extend(
            [
                ft.IconButton(icon=ft.Icons.REMOVE, on_click=on_zoom_out, tooltip="Zoom out"),
                ft.Text(f"{zoom:.2f}x", size=12, width=56, text_align=ft.TextAlign.CENTER),
                ft.IconButton(icon=ft.Icons.ADD, on_click=on_zoom_in, tooltip="Zoom in"),
            ]
        )

    if show_reading_mode_toggle:
        right_controls.append(
            ft.IconButton(
                icon=ft.Icons.VIEW_STREAM if is_vertical else ft.Icons.VIEW_CAROUSEL,
                tooltip="Switch reading mode",
                on_click=on_toggle_reading_mode,
            )
        )

    right_controls.append(
        ft.IconButton(
            icon=ft.Icons.MENU_BOOK,
            selected=show_toc,
            selected_icon=ft.Icons.MENU_BOOK_OUTLINED,
            disabled=not toc_available,
            tooltip="Toggle table of contents",
            on_click=on_toggle_toc,
        )
    )

    return ft.Container(
        padding=10,
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=4,
                    controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=on_back, tooltip="Back to library"),
                        ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=on_prev_page, tooltip="Previous"),
                        ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=on_next_page, tooltip="Next"),
                        ft.Text(f"{position_label} {current_page + 1} / {page_count}", weight=ft.FontWeight.BOLD),
                    ],
                ),
                ft.Row(
                    width=460,
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=right_controls,
                ),
            ],
        ),
    )
