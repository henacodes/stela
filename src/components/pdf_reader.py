import flet as ft
import asyncio
from typing import Any, Callable, cast


@ft.component
def PdfReader(
    page_count: int,
    current_page: int,
    is_vertical: bool,
    rendered_page_width: float,
    rendered_page_height: float,
    page_item_extent: int,
    jump_target_page: int | None,
    render_page_indices: list[int],
    current_src: str,
    get_page_base64: Callable[[int], str | None],
    on_visible_page_change: Callable[[int], None],
    on_jump_handled: Callable[[], None],
):
    render_set = set(render_page_indices)

    list_ref = ft.use_memo(lambda: ft.Ref[ft.ListView](), [])

    def scroll_to_target_page():
        if not is_vertical or jump_target_page is None or not list_ref.current:
            return

        list_view = list_ref.current
        if not list_view:
            return

        target_offset = max(0, jump_target_page * max(1, page_item_extent))

        async def _scroll():
            try:
                await list_view.scroll_to(offset=target_offset, duration=180)
            except RuntimeError:
                pass
            finally:
                on_jump_handled()

        try:
            task = asyncio.create_task(_scroll())
            task.add_done_callback(lambda t: t.exception())
        except Exception:
            on_jump_handled()

    ft.on_updated(scroll_to_target_page, [jump_target_page, is_vertical, page_item_extent])

    if is_vertical:
        def handle_vertical_scroll(e: ft.OnScrollEvent):
            new_page = int(e.pixels / max(1, page_item_extent))
            if 0 <= new_page < page_count and new_page != current_page:
                on_visible_page_change(new_page)

        return cast(Any, ft.ListView)(
            ref=list_ref,
            expand=True,
            spacing=12,
            item_extent=page_item_extent,
            scroll=ft.ScrollMode.AUTO,
            on_scroll=handle_vertical_scroll,
            controls=cast(
                list[ft.Control],
                [
                    cast(Any, ft.Container)(
                        key=f"pdf-page-{i}",
                        alignment=ft.Alignment(0, 0),
                        height=rendered_page_height,
                        content=ft.Image(
                            src=(
                                current_src
                                if i == current_page
                                else (get_page_base64(i) or "")
                            ),
                            width=rendered_page_width,
                            height=rendered_page_height,
                        )
                        if i in render_set
                        else cast(Any, ft.Container)(
                            alignment=ft.Alignment(0, 0),
                            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                            content=ft.Text(
                                value=f"Page {i + 1}",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=11,
                            ),
                        ),
                    )
                    for i in range(page_count)
                ],
            ),
        )

    return cast(Any, ft.ListView)(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=cast(
            list[ft.Control],
            [
                cast(Any, ft.Row)(
                    scroll=ft.ScrollMode.AUTO,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=cast(
                        list[ft.Control],
                        [
                            cast(Any, ft.Container)(
                                padding=10,
                                content=ft.Image(
                                    src=current_src or (get_page_base64(current_page) or ""),
                                    width=rendered_page_width,
                                    height=rendered_page_height,
                                ),
                            )
                        ],
                    ),
                )
            ],
        ),
    )
