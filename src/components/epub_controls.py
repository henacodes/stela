import flet as ft
from typing import Callable


@ft.component
def EpubControls(
    font_size: int,
    line_height: float,
    text_align: ft.TextAlign,
    on_font_size_change: Callable[[int], None],
    on_line_height_change: Callable[[float], None],
    on_text_align_change: Callable[[ft.TextAlign], None],
):
    group_bg = ft.Colors.SURFACE_CONTAINER_HIGHEST

    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
        content=ft.Row(
            wrap=False,
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            controls=[
                ft.Text("EPUB", weight=ft.FontWeight.BOLD),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=6, vertical=4),
                    border_radius=10,
                    bgcolor=group_bg,
                    content=ft.Row(
                        spacing=2,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.IconButton(icon=ft.Icons.TEXT_DECREASE, tooltip="Smaller text", on_click=lambda _: on_font_size_change(-1)),
                            ft.Text(f"{font_size}px", width=48, text_align=ft.TextAlign.CENTER),
                            ft.IconButton(icon=ft.Icons.TEXT_INCREASE, tooltip="Larger text", on_click=lambda _: on_font_size_change(1)),
                        ],
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=6, vertical=4),
                    border_radius=10,
                    bgcolor=group_bg,
                    content=ft.Row(
                        spacing=2,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.FORMAT_ALIGN_LEFT,
                                selected=text_align == ft.TextAlign.LEFT,
                                tooltip="Align left",
                                on_click=lambda _: on_text_align_change(ft.TextAlign.LEFT),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.FORMAT_ALIGN_CENTER,
                                selected=text_align == ft.TextAlign.CENTER,
                                tooltip="Align center",
                                on_click=lambda _: on_text_align_change(ft.TextAlign.CENTER),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.FORMAT_ALIGN_JUSTIFY,
                                selected=text_align == ft.TextAlign.JUSTIFY,
                                tooltip="Justify",
                                on_click=lambda _: on_text_align_change(ft.TextAlign.JUSTIFY),
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=6, vertical=4),
                    border_radius=10,
                    bgcolor=group_bg,
                    content=ft.Row(
                        spacing=2,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.REMOVE,
                                tooltip="Decrease line spacing",
                                on_click=lambda _: on_line_height_change(-0.1),
                            ),
                            ft.Text(f"{line_height:.1f}", width=34, text_align=ft.TextAlign.CENTER),
                            ft.IconButton(
                                icon=ft.Icons.ADD,
                                tooltip="Increase line spacing",
                                on_click=lambda _: on_line_height_change(0.1),
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )
