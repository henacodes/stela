import flet as ft
import asyncio
from typing import Any, cast
from contexts.app_context import AppContext
from components.library_header import LibraryHeader
from components.library_grid import LibraryGrid

@ft.component
def LibraryView():
    state = ft.use_context(AppContext)
    resume_modal_visible, set_resume_modal_visible = ft.use_state(False)
    resume_modal_checked, set_resume_modal_checked = ft.use_state(False)

    last_read_book_path = ft.use_memo(
        lambda: state.get_last_read_book_path(),
        [state.route, len(state.library)],
    )

    def maybe_show_resume_modal():
        if resume_modal_checked:
            return
        set_resume_modal_checked(True)
        if not state.resume_prompt_pending:
            return
        state.consume_resume_prompt()
        if not last_read_book_path:
            return
        in_library = any(book.path == last_read_book_path for book in state.library)
        if in_library:
            set_resume_modal_visible(True)

    ft.on_updated(maybe_show_resume_modal, [resume_modal_checked, last_read_book_path, len(state.library)])

    async def handle_import_files_click(_):
        files = await ft.FilePicker().pick_files(
            allow_multiple=True,
            allowed_extensions=["pdf", "epub"]
        )

        if files:
            selected_paths = [f.path for f in files if f.path]
            await state.import_books_async(cast(list[str], selected_paths))

    async def handle_import_folder_click(_):
        folder_path = await ft.FilePicker().get_directory_path()
        if folder_path:
            await state.import_folder_async(folder_path)

    async def handle_open_book(path: str):
        state.opening_book_path = path
        if ft.context.page:
            ft.context.page.update()
        await asyncio.sleep(0.05)
        state.open_book(path)

    async def handle_fetch_cover(path: str):
        await state.refresh_cover_async(path)
        if ft.context.page:
            ft.context.page.update()

    async def handle_resume_last_book(_):
        if not last_read_book_path:
            set_resume_modal_visible(False)
            return
        set_resume_modal_visible(False)
        await handle_open_book(last_read_book_path)

    def handle_browse_library(_):
        set_resume_modal_visible(False)

    controls: list[ft.Control] = [
        LibraryHeader(
            on_import_files_click=handle_import_files_click,
            on_import_folder_click=handle_import_folder_click,
        ),
    ]

    if state.import_status:
        controls.append(
            cast(Any, ft.Container)(
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=8,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                content=ft.Text(value=state.import_status, size=12),
            )
        )

    if state.import_in_progress:
        progress_value = 0.0
        if state.import_total > 0:
            progress_value = state.import_done / state.import_total
        controls.append(
            cast(Any, ft.Container)(
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=8,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                content=cast(Any, ft.Column)(
                    spacing=6,
                    controls=cast(list[ft.Control], [
                        ft.Text(
                            value=(
                            f"Indexing {state.import_done}/{state.import_total}"
                            + (f" • {state.import_current_book}" if state.import_current_book else "")
                            ),
                            size=12,
                        ),
                        ft.ProgressBar(value=progress_value),
                    ]),
                ),
            )
        )

    controls.append(LibraryGrid(books=state.library, on_open=handle_open_book, on_fetch_cover=handle_fetch_cover))

    return cast(Any, ft.Stack)(
        expand=True,
        controls=cast(
            list[ft.Control],
            [
            cast(Any, ft.Container)(
                expand=True,
                padding=24,
                content=ft.Column(
                    expand=True,
                    spacing=16,
                    controls=cast(list[ft.Control], controls),
                ),
            ),
            cast(Any, ft.Container)(
                expand=True,
                visible=bool(state.opening_book_path),
                bgcolor=ft.Colors.with_opacity(0.45, ft.Colors.BLACK),
                alignment=ft.Alignment(0, 0),
                content=cast(Any, ft.Row)(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                    controls=cast(list[ft.Control], [
                        ft.ProgressRing(width=18, height=18, stroke_width=2, color=ft.Colors.WHITE),
                        ft.Text(value="Opening book...", color=ft.Colors.WHITE),
                    ]),
                ),
            ),
            cast(Any, ft.Container)(
                expand=True,
                visible=resume_modal_visible and not bool(state.opening_book_path),
                bgcolor=ft.Colors.with_opacity(0.45, ft.Colors.BLACK),
                alignment=ft.Alignment(0, 0),
                content=cast(Any, ft.Column)(
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=cast(list[ft.Control], [
                        cast(Any, ft.Container)(
                            width=460,
                            padding=20,
                            border_radius=12,
                            bgcolor=ft.Colors.SURFACE,
                            content=cast(Any, ft.Column)(
                                spacing=14,
                                controls=cast(list[ft.Control], [
                                    ft.Text(value="Resume last book?", size=18, weight=ft.FontWeight.BOLD),
                                    ft.Text(
                                        value="Do you want to continue where you left off, or browse your library?",
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                    cast(Any, ft.Row)(
                                        alignment=ft.MainAxisAlignment.END,
                                        controls=cast(list[ft.Control], [
                                            ft.OutlinedButton("Browse library", on_click=handle_browse_library),
                                            ft.Button("Resume", on_click=handle_resume_last_book),
                                        ]),
                                    ),
                                ]),
                            ),
                        ),
                    ]),
                ),
            ),
        ],
        ),
    )