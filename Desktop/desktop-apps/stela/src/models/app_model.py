from dataclasses import dataclass, field
import asyncio
import flet as ft
from models.library_book import LibraryBook
from services.library_db import LibraryDB


def _as_float(value: object, default: float) -> float:
    try:
        if isinstance(value, (int, float, str)):
            return float(value)
        return default
    except (TypeError, ValueError):
        return default


def _as_int(value: object, default: int) -> int:
    try:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            return int(float(value))
        return default
    except (TypeError, ValueError):
        return default


def _as_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _as_str(value: object, default: str) -> str:
    if isinstance(value, str):
        return value
    return default

@ft.observable
@dataclass
class AppModel:
    route: str = "/"
    library: list[LibraryBook] = field(default_factory=list)
    selected_book: str | None = None
    # Default to Light to match your 'Tweakon' Graphite reference start
    theme_mode: ft.ThemeMode = ft.ThemeMode.LIGHT
    import_status: str | None = None
    import_in_progress: bool = False
    import_total: int = 0
    import_done: int = 0
    import_current_book: str | None = None
    opening_book_path: str | None = None
    resume_prompt_pending: bool = True

    def __post_init__(self):
        self._library_db = LibraryDB()
        self.refresh_library()

    def navigate(self, new_route: str):
        """Standard navigation handler."""
        self.route = new_route
        if new_route != "/reader":
            self.opening_book_path = None
        if ft.context.page:
            ft.context.page.route = new_route
            ft.context.page.update()

    def route_change(self, e: ft.RouteChangeEvent):
        """Syncs the model when the browser/system route changes."""
        self.route = e.route

    def view_popped(self, e: ft.ViewPopEvent):
        """Handles back-button logic."""
        self.navigate("/")

    def toggle_theme(self):
        """Switches between slick light and graphite dark modes."""
        self.theme_mode = (
            ft.ThemeMode.DARK 
            if self.theme_mode == ft.ThemeMode.LIGHT 
            else ft.ThemeMode.LIGHT
        )

    def import_book(self, path: str):
        """Imports one book and refreshes the indexed library."""
        if not path:
            return
        self.import_books([path])

    def import_books(self, paths: list[str]):
        """Imports multiple books (PDF/EPUB), stores metadata, and refreshes library."""
        filtered_paths = [p for p in paths if p]
        if not filtered_paths:
            return

        self.import_in_progress = True
        self.import_total = len(filtered_paths)
        self.import_done = 0
        self.import_current_book = None

        def on_progress(done: int, total: int, path: str):
            self.import_done = done
            self.import_total = total
            self.import_current_book = path.split("/")[-1]
            if ft.context.page:
                ft.context.page.update()

        imported, failed = self._library_db.import_paths(filtered_paths, progress_callback=on_progress)
        self.refresh_library()
        self.import_status = f"Imported {imported} book(s)" + (f", {failed} failed" if failed else "")
        self.import_in_progress = False
        self.import_current_book = None

    async def import_books_async(self, paths: list[str]):
        filtered_paths = [p for p in paths if p]
        if not filtered_paths:
            return

        self.import_in_progress = True
        self.import_total = len(filtered_paths)
        self.import_done = 0
        self.import_current_book = None
        imported = 0
        failed = 0

        for i, path in enumerate(filtered_paths, start=1):
            self.import_done = i
            self.import_current_book = path.split("/")[-1]
            if ft.context.page:
                ft.context.page.update()

            ok = await asyncio.to_thread(self._library_db.import_path, path)
            if ok:
                imported += 1
            else:
                failed += 1

        self.refresh_library()
        self.import_status = f"Imported {imported} book(s)" + (f", {failed} failed" if failed else "")
        self.import_in_progress = False
        self.import_current_book = None

    def import_folder(self, folder_path: str):
        """Recursively imports all supported books from a folder."""
        if not folder_path:
            return
        self.import_in_progress = True
        self.import_done = 0
        self.import_total = 0
        self.import_current_book = None

        def on_progress(done: int, total: int, path: str):
            self.import_done = done
            self.import_total = total
            self.import_current_book = path.split("/")[-1]
            if ft.context.page:
                ft.context.page.update()

        imported, failed = self._library_db.import_folder(folder_path, progress_callback=on_progress)
        self.refresh_library()
        self.import_status = f"Imported {imported} book(s) from folder" + (f", {failed} failed" if failed else "")
        self.import_in_progress = False
        self.import_current_book = None

    async def import_folder_async(self, folder_path: str):
        if not folder_path:
            return

        file_paths = await asyncio.to_thread(self._library_db.list_supported_files, folder_path)
        if not file_paths:
            self.import_status = "No PDF/EPUB files found in folder"
            return

        await self.import_books_async(file_paths)
        self.import_status = f"Imported {self.import_done} book(s) from folder"

    def refresh_library(self):
        """Reloads books from local metadata store."""
        self.library = self._library_db.list_books()

    def open_book(self, path: str):
        """Selects a book and moves to the reader view."""
        self.opening_book_path = path
        if ft.context.page:
            ft.context.page.update()
        self.selected_book = path
        self._library_db.mark_opened(path)
        session = self._library_db.get_reader_session()
        self._library_db.save_reader_session(
            last_book_path=path,
            pdf_zoom=_as_float(session.get("pdf_zoom"), 1.0),
            pdf_is_vertical=_as_bool(session.get("pdf_is_vertical"), True),
            pdf_show_toc=_as_bool(session.get("pdf_show_toc"), True),
            epub_font_size=_as_int(session.get("epub_font_size"), 16),
            epub_line_height=_as_float(session.get("epub_line_height"), 1.6),
            epub_text_align=_as_str(session.get("epub_text_align"), "left"),
        )
        self.navigate("/reader")

    def get_last_position(self, path: str | None) -> int:
        if not path:
            return 0
        return self._library_db.get_last_position(path)

    def save_last_position(self, position: int):
        if not self.selected_book:
            return
        self._library_db.set_last_position(self.selected_book, position)

    def get_reader_session(self) -> dict[str, object]:
        return self._library_db.get_reader_session()

    def save_reader_session(
        self,
        *,
        pdf_zoom: float,
        pdf_is_vertical: bool,
        pdf_show_toc: bool,
        epub_font_size: int,
        epub_line_height: float,
        epub_text_align: str,
    ):
        self._library_db.save_reader_session(
            last_book_path=self.selected_book,
            pdf_zoom=pdf_zoom,
            pdf_is_vertical=pdf_is_vertical,
            pdf_show_toc=pdf_show_toc,
            epub_font_size=epub_font_size,
            epub_line_height=epub_line_height,
            epub_text_align=epub_text_align,
        )

    def get_last_read_book_path(self) -> str | None:
        session = self.get_reader_session()
        path = session.get("last_book_path")
        return path if isinstance(path, str) else None

    def consume_resume_prompt(self):
        self.resume_prompt_pending = False