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
    visible_indices: range,
    jump_target_page: int | None,
    current_src: str,
    get_page_base64: Callable[[int], str | None],
    on_visible_page_change: Callable[[int], None],
    on_jump_handled: Callable[[], None],
):
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
                await list_view.scroll_to(offset=target_offset, duration=220)
            except RuntimeError:
                # Session can be closed while async scroll is in flight.
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
            on_scroll=handle_vertical_scroll,
            controls=cast(
                list[ft.Control],
                [
                    cast(Any, ft.Container)(
                        key=f"pdf-page-{i}",
                        alignment=ft.Alignment(0, 0),
                        height=rendered_page_height,
                        content=ft.Image(
                            src=get_page_base64(i) or "",
                            width=rendered_page_width,
                            height=rendered_page_height,
                        )
                        if i in visible_indices
                        else ft.Container(),
                    )
                    for i in range(page_count)
                ],
            ),
        )

    return cast(Any, ft.Column)(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=cast(
            list[ft.Control],
            [
            cast(Any, ft.Row)(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=cast(
                    list[ft.Control],
                    [
                    cast(Any, ft.Container)(
                        padding=10,
                        content=ft.Image(
                            src=current_src,
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
