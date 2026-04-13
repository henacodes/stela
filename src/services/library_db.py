from __future__ import annotations

from pathlib import Path
import re
import sqlite3
from typing import Callable, Iterable

from models.book_document import BookDocument
from models.library_book import LibraryBook
from services.cover_store import CoverStore


class LibraryDB:
    def __init__(self, db_path: str | None = None):
        default_path = Path.home() / ".stela" / "library.db"
        self.db_path = Path(db_path) if db_path else default_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._cover_store = CoverStore()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL UNIQUE,
                    format TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    author TEXT NOT NULL DEFAULT '',
                    language TEXT NOT NULL DEFAULT '',
                    publisher TEXT NOT NULL DEFAULT '',
                    identifier TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    cover_path TEXT,
                    total_units INTEGER NOT NULL DEFAULT 0,
                    estimated_word_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_opened_at TEXT,
                    deleted_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reader_session (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_book_path TEXT,
                    pdf_zoom REAL NOT NULL DEFAULT 1.0,
                    pdf_is_vertical INTEGER NOT NULL DEFAULT 1,
                    pdf_show_toc INTEGER NOT NULL DEFAULT 1,
                    epub_font_size INTEGER NOT NULL DEFAULT 16,
                    epub_line_height REAL NOT NULL DEFAULT 1.6,
                    epub_text_align TEXT NOT NULL DEFAULT 'left',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    theme_mode TEXT NOT NULL DEFAULT 'light',
                    seed_color TEXT NOT NULL DEFAULT '#18181b',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(books)").fetchall()
            }
            if "cover_path" not in columns:
                conn.execute("ALTER TABLE books ADD COLUMN cover_path TEXT")
            if "last_position" not in columns:
                conn.execute("ALTER TABLE books ADD COLUMN last_position INTEGER NOT NULL DEFAULT 0")
            if "published_year" not in columns:
                conn.execute("ALTER TABLE books ADD COLUMN published_year INTEGER")
            if "pdf_is_heavy" not in columns:
                conn.execute("ALTER TABLE books ADD COLUMN pdf_is_heavy INTEGER")
            conn.execute("INSERT OR IGNORE INTO reader_session (id) VALUES (1)")
            conn.execute("INSERT OR IGNORE INTO app_settings (id) VALUES (1)")

    def get_pdf_is_heavy(self, path: str) -> bool | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT pdf_is_heavy
                FROM books
                WHERE path = ?
                """,
                (path,),
            ).fetchone()
        if not row:
            return None
        value = row["pdf_is_heavy"]
        if value is None:
            return None
        return bool(int(value))

    def set_pdf_is_heavy(self, path: str, is_heavy: bool):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE books
                SET pdf_is_heavy = ?, updated_at = CURRENT_TIMESTAMP
                WHERE path = ?
                """,
                (1 if is_heavy else 0, path),
            )

    def _extract_year(self, raw_value: str) -> int | None:
        if not raw_value:
            return None
        match = re.search(r"(18|19|20)\d{2}", raw_value)
        if not match:
            return None
        try:
            return int(match.group(0))
        except ValueError:
            return None

    def upsert_document(self, doc: BookDocument, cover_path: str | None = None):
        published_year = self._extract_year(doc.metadata.created_at)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO books (
                    path, format, title, author, language, publisher, identifier, description,
                    cover_path, published_year, total_units, estimated_word_count, deleted_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, CURRENT_TIMESTAMP)
                ON CONFLICT(path) DO UPDATE SET
                    format=excluded.format,
                    title=excluded.title,
                    author=excluded.author,
                    language=excluded.language,
                    publisher=excluded.publisher,
                    identifier=excluded.identifier,
                    description=excluded.description,
                    cover_path=excluded.cover_path,
                    published_year=excluded.published_year,
                    total_units=excluded.total_units,
                    estimated_word_count=excluded.estimated_word_count,
                    deleted_at=NULL,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    doc.path,
                    doc.format,
                    doc.metadata.title,
                    doc.metadata.author,
                    doc.metadata.language,
                    doc.metadata.publisher,
                    doc.metadata.identifier,
                    doc.metadata.description,
                    cover_path,
                    published_year,
                    doc.total_units,
                    doc.estimated_word_count,
                ),
            )

    def list_books(self) -> list[LibraryBook]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT path, format, title, author, published_year, cover_path, total_units, estimated_word_count, last_position, last_opened_at
                FROM books
                WHERE deleted_at IS NULL
                ORDER BY COALESCE(last_opened_at, updated_at) DESC, title COLLATE NOCASE ASC
                """
            ).fetchall()

        return [
            LibraryBook(
                path=str(row["path"]),
                format=str(row["format"]),
                title=str(row["title"]),
                author=str(row["author"]),
                published_year=int(row["published_year"]) if row["published_year"] else None,
                cover_path=str(row["cover_path"]) if row["cover_path"] else None,
                total_units=int(row["total_units"]),
                estimated_word_count=int(row["estimated_word_count"]),
                last_position=int(row["last_position"]),
                last_opened_at=str(row["last_opened_at"]) if row["last_opened_at"] else None,
            )
            for row in rows
        ]

    def import_folder(
        self,
        folder_path: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[int, int]:
        supported = self.list_supported_files(folder_path)
        if not supported:
            return 0, 0
        return self.import_paths(supported, progress_callback=progress_callback)

    def list_supported_files(self, folder_path: str) -> list[str]:
        folder = Path(folder_path).expanduser()
        if not folder.exists() or not folder.is_dir():
            return []
        return [
            str(p)
            for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in {".pdf", ".epub"}
        ]

    def mark_opened(self, path: str):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE books
                SET last_opened_at = CURRENT_TIMESTAMP
                WHERE path = ?
                """,
                (path,),
            )

    def import_paths(
        self,
        paths: Iterable[str],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[int, int]:
        imported = 0
        failed = 0
        path_list = list(paths)
        total = len(path_list)

        for i, path in enumerate(path_list, start=1):
            if progress_callback:
                progress_callback(i, total, path)
            if self.import_path(path):
                imported += 1
            else:
                failed += 1

        return imported, failed

    def import_path(self, path: str) -> bool:
        try:
            doc = BookDocument(path).load()
            if not doc.is_supported:
                return False
            cover_path = self._cover_store.save_cover(doc.path, doc.format)
            self.upsert_document(doc, cover_path=cover_path)
            return True
        except Exception:
            return False

    def refresh_cover_for_book(self, path: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT path, format
                FROM books
                WHERE path = ?
                """,
                (path,),
            ).fetchone()

        if not row:
            return False

        cover_path = self._cover_store.save_cover(str(row["path"]), str(row["format"]))
        if not cover_path:
            return False

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE books
                SET cover_path = ?, updated_at = CURRENT_TIMESTAMP
                WHERE path = ?
                """,
                (cover_path, path),
            )
        return True

    def get_last_position(self, path: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT last_position
                FROM books
                WHERE path = ?
                """,
                (path,),
            ).fetchone()
        if not row or row["last_position"] is None:
            return 0
        return max(0, int(row["last_position"]))

    def set_last_position(self, path: str, position: int):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE books
                SET last_position = ?, updated_at = CURRENT_TIMESTAMP
                WHERE path = ?
                """,
                (max(0, int(position)), path),
            )

    def save_reader_session(
        self,
        *,
        last_book_path: str | None,
        pdf_zoom: float,
        pdf_is_vertical: bool,
        pdf_show_toc: bool,
        epub_font_size: int,
        epub_line_height: float,
        epub_text_align: str,
    ):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO reader_session (
                    id, last_book_path, pdf_zoom, pdf_is_vertical, pdf_show_toc,
                    epub_font_size, epub_line_height, epub_text_align, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    last_book_path=excluded.last_book_path,
                    pdf_zoom=excluded.pdf_zoom,
                    pdf_is_vertical=excluded.pdf_is_vertical,
                    pdf_show_toc=excluded.pdf_show_toc,
                    epub_font_size=excluded.epub_font_size,
                    epub_line_height=excluded.epub_line_height,
                    epub_text_align=excluded.epub_text_align,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    last_book_path,
                    float(pdf_zoom),
                    1 if pdf_is_vertical else 0,
                    1 if pdf_show_toc else 0,
                    int(epub_font_size),
                    float(epub_line_height),
                    epub_text_align,
                ),
            )

    def get_reader_session(self) -> dict[str, object]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT last_book_path, pdf_zoom, pdf_is_vertical, pdf_show_toc,
                       epub_font_size, epub_line_height, epub_text_align
                FROM reader_session
                WHERE id = 1
                """
            ).fetchone()

        if not row:
            return {
                "last_book_path": None,
                "pdf_zoom": 1.0,
                "pdf_is_vertical": True,
                "pdf_show_toc": True,
                "epub_font_size": 16,
                "epub_line_height": 1.6,
                "epub_text_align": "left",
            }

        return {
            "last_book_path": str(row["last_book_path"]) if row["last_book_path"] else None,
            "pdf_zoom": float(row["pdf_zoom"]),
            "pdf_is_vertical": bool(row["pdf_is_vertical"]),
            "pdf_show_toc": bool(row["pdf_show_toc"]),
            "epub_font_size": int(row["epub_font_size"]),
            "epub_line_height": float(row["epub_line_height"]),
            "epub_text_align": str(row["epub_text_align"]),
        }

    def save_app_settings(self, *, theme_mode: str, seed_color: str):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (id, theme_mode, seed_color, updated_at)
                VALUES (1, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    theme_mode=excluded.theme_mode,
                    seed_color=excluded.seed_color,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (theme_mode, seed_color),
            )

    def get_app_settings(self) -> dict[str, str]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT theme_mode, seed_color
                FROM app_settings
                WHERE id = 1
                """
            ).fetchone()

        if not row:
            return {"theme_mode": "light", "seed_color": "#18181b"}
        return {
            "theme_mode": str(row["theme_mode"] or "light"),
            "seed_color": str(row["seed_color"] or "#18181b"),
        }
