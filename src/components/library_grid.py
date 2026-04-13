import flet as ft
from typing import Awaitable, Callable, cast

from models.library_book import LibraryBook
from components.library_book_card import LibraryBookCard


@ft.component
def LibraryGrid(
    books: list[LibraryBook],
    on_open: Callable[[str], None | Awaitable[None]],
    on_fetch_cover: Callable[[str], None | Awaitable[None]],
):
    if not books:
        return ft.Column(
            expand=True,
            controls=cast(
                list[ft.Control],
                [
                ft.Icon(ft.Icons.LIBRARY_BOOKS_OUTLINED, size=40, color=ft.Colors.OUTLINE),
                ft.Text("No books yet", size=18, weight=ft.FontWeight.W_600),
                ft.Text("Import PDF or EPUB files to get started", color=ft.Colors.ON_SURFACE_VARIANT),
                ],
            ),
        )

    return ft.GridView(
        expand=True,
        runs_count=3,
        spacing=14,
        run_spacing=14,
        max_extent=260,
        child_aspect_ratio=0.6,
        controls=cast(
            list[ft.Control],
            [LibraryBookCard(book=book, on_open=on_open, on_fetch_cover=on_fetch_cover) for book in books],
        ),
    )
