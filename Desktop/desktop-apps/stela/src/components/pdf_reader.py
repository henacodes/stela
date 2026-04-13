import flet as ft
from typing import Callable, cast


@ft.component
def PdfReader(
    page_count: int,
    current_page: int,
    is_vertical: bool,
    rendered_page_width: float,
    rendered_page_height: float,
    page_item_extent: int,
    visible_indices: range,
    current_src: str,
    get_page_base64: Callable[[int], str | None],
    on_visible_page_change: Callable[[int], None],
):
    if is_vertical:
        def handle_vertical_scroll(e: ft.OnScrollEvent):
            new_page = int(e.pixels / max(1, page_item_extent))
            if 0 <= new_page < page_count and new_page != current_page:
                on_visible_page_change(new_page)

        return ft.ListView(
            expand=True,
            spacing=12,
            item_extent=page_item_extent,
            on_scroll=handle_vertical_scroll,
            controls=cast(
                list[ft.Control],
                [
                    ft.Container(
                        key=f"pdf-page-{i}",
                        alignment=ft.Alignment(0, 0),
                        height=rendered_page_height,
                        content=ft.Image(
                            src=get_page_base64(i) or "",
                            width=rendered_page_width,
                            height=rendered_page_height,
                        )
                        if i in visible_indices
                        else ft.ProgressRing(scale=0.55),
                    )
                    for i in range(page_count)
                ],
            ),
        )

    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Container(
                        padding=10,
                        content=ft.Image(
                            src=current_src,
                            width=rendered_page_width,
                            height=rendered_page_height,
                        ),
                    )
                ],
            )
        ],
    )
