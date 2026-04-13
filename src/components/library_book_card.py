import flet as ft
import inspect
from typing import Any, cast

from models.library_book import LibraryBook


@ft.component
def LibraryBookCard(book: LibraryBook, on_open, on_fetch_cover):
    format_chip_color = ft.Colors.BLUE_100 if book.format == "pdf" else ft.Colors.GREEN_100
    card_width = 240
    cover_height = 220
    unit_label = "pages" if book.format == "pdf" else "sections"

    preview = (
        ft.Container(
            width=card_width,
            height=cover_height,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            alignment=ft.Alignment(0, 0),
            content=ft.Image(
                src=book.cover_path,
                width=card_width,
                height=cover_height,
                fit=ft.BoxFit.CONTAIN,
            ),
        )
        if book.cover_path
        else ft.Container(
            width=card_width,
            height=cover_height,
            alignment=ft.Alignment(0, 0),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            content=ft.Icon(ft.Icons.MENU_BOOK, size=40, color=ft.Colors.OUTLINE),
        )
    )

    async def handle_open(_):
        result = on_open(book.path)
        if inspect.isawaitable(result):
            await result

    async def handle_fetch_cover(_):
        result = on_fetch_cover(book.path)
        if inspect.isawaitable(result):
            await result

    return ft.Container(
        width=card_width,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        ink=True,
        on_click=handle_open,
        content=ft.Column(
            spacing=0,
            controls=cast(list[ft.Control], [
                preview,
                ft.Container(
                    padding=12,
                    content=cast(Any, ft.Column)(
                        spacing=8,
                        controls=cast(list[ft.Control], [
                            cast(Any, ft.Row)(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(value=book.display_title, weight=ft.FontWeight.W_600, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                                    ft.Container(
                                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                        border_radius=999,
                                        bgcolor=format_chip_color,
                                        content=ft.Text(value=book.format.upper(), size=11, weight=ft.FontWeight.W_600),
                                    ),
                                ],
                            ),
                            ft.Button(
                                "Check cover image",
                                icon=ft.Icons.IMAGE_SEARCH,
                                visible=book.cover_path is None,
                                on_click=handle_fetch_cover,
                            ),
                            ft.Text(
                                value=(book.author or "Unknown author") + (f" • {book.published_year}" if book.published_year else ""),
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                value=f"{book.total_units} {unit_label}",
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                value=f"Format: {book.format.upper()}",
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            cast(Any, ft.Row)(
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.ProgressBar(value=min(1.0, max(0.0, book.progress_percent / 100.0)), expand=True),
                                    ft.Text(value=f"{book.progress_percent:.1f}%", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                            ),
                        ]),
                    ),
                ),
            ]),
        ),
    )
