import flet as ft
import fitz  # PyMuPDF
import base64
from dataclasses import dataclass
from html.parser import HTMLParser
import posixpath
import re
from urllib.parse import unquote
import zipfile
import xml.etree.ElementTree as ET
from contexts.app_context import AppContext
from typing import cast
from components.reader_toolbar import ReaderToolbar
from components.toc_panel import TocPanel
from components.pdf_reader import PdfReader
from components.epub_reader import EpubReader, EpubRenderableSection
from components.epub_controls import EpubControls


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


@dataclass
class EpubSection:
    title: str
    content: str


class EpubTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0
        self._current_heading: str | None = None
        self.heading: str = ""
        self.title: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag in {"script", "style"}:
            self._skip_depth += 1
        if tag in {"h1", "h2", "h3", "title"}:
            self._current_heading = tag

    def handle_endtag(self, tag: str):
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in {"h1", "h2", "h3", "title"}:
            self._current_heading = None
        if tag in {"p", "div", "section", "article", "br", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return
        clean = data.strip()
        if not clean:
            return
        self.parts.append(clean)
        if self._current_heading in {"h1", "h2", "h3"} and not self.heading:
            self.heading = clean
        if self._current_heading == "title" and not self.title:
            self.title = clean

@ft.component
def ReaderView():
    state = ft.use_context(AppContext)
    reader_session = ft.use_memo(
        lambda: state.get_reader_session(),
        [state.selected_book],
    )

    def parse_text_align(value: object) -> ft.TextAlign:
        raw = str(value or "left").lower()
        if raw == "center":
            return ft.TextAlign.CENTER
        if raw == "justify":
            return ft.TextAlign.JUSTIFY
        return ft.TextAlign.LEFT

    initial_position = ft.use_memo(
        lambda: state.get_last_position(state.selected_book),
        [state.selected_book],
    )
    current_page, set_current_page = ft.use_state(initial_position)
    pending_jump_target, set_pending_jump_target = ft.use_state(-1)
    zoom, set_zoom = ft.use_state(_as_float(reader_session.get("pdf_zoom"), 1.0))
    is_vertical, set_is_vertical = ft.use_state(_as_bool(reader_session.get("pdf_is_vertical"), True))
    show_toc, set_show_toc = ft.use_state(_as_bool(reader_session.get("pdf_show_toc"), True))
    epub_font_size, set_epub_font_size = ft.use_state(_as_int(reader_session.get("epub_font_size"), 16))
    epub_line_height, set_epub_line_height = ft.use_state(_as_float(reader_session.get("epub_line_height"), 1.6))
    epub_text_align, set_epub_text_align = ft.use_state(parse_text_align(reader_session.get("epub_text_align", "left")))
    toc_width = 320.0
    is_pdf = bool(state.selected_book and state.selected_book.lower().endswith(".pdf"))
    effective_is_vertical = is_vertical if is_pdf else False
    
    # Debugging: Check if the path is reaching the view
    if state.selected_book:
        print(f"DEBUG: ReaderView opening: {state.selected_book}")

    # Memoize the PDF document so we don't reload on every render
    doc = ft.use_memo(
        lambda: fitz.open(state.selected_book) if (state.selected_book and is_pdf) else None,
        [state.selected_book, is_pdf]
    )

    def normalize_href(href: str) -> str:
        base = unquote(href.split("#", 1)[0]).strip()
        if not base:
            return ""
        return posixpath.normpath(base.lstrip("./"))

    def parse_html_section(content: str, fallback_name: str, index: int) -> EpubSection:
        extractor = EpubTextExtractor()
        extractor.feed(content)
        raw_text = " ".join(extractor.parts)
        normalized_text = re.sub(r"\n{3,}", "\n\n", raw_text).strip()
        title = extractor.heading or extractor.title or f"Section {index}"
        return EpubSection(title=title, content=normalized_text)

    def parse_epub() -> tuple[list[EpubRenderableSection], list[tuple[int, str, int]]]:
        if not state.selected_book or is_pdf:
            return [], []

        try:
            zf = zipfile.ZipFile(state.selected_book, "r")
        except Exception as e:
            print(f"EPUB open error: {e}")
            return [], []

        sections: list[EpubRenderableSection] = []
        href_to_index: dict[str, int] = {}

        try:
            container_xml = zf.read("META-INF/container.xml")
            container_root = ET.fromstring(container_xml)
            rootfile_elem = container_root.find(".//{*}rootfile")
            if rootfile_elem is None:
                return [], []

            opf_path = normalize_href(rootfile_elem.attrib.get("full-path", ""))
            if not opf_path:
                return [], []

            opf_root = ET.fromstring(zf.read(opf_path))
            ns = ""
            if opf_root.tag.startswith("{"):
                ns = opf_root.tag.split("}")[0][1:]

            def opf_tag(name: str) -> str:
                return f"{{{ns}}}{name}" if ns else name

            opf_dir = posixpath.dirname(opf_path)
            manifest: dict[str, dict[str, str]] = {}
            for item in opf_root.findall(f".//{opf_tag('manifest')}/{opf_tag('item')}"):
                item_id = item.attrib.get("id", "")
                href = item.attrib.get("href", "")
                media_type = item.attrib.get("media-type", "")
                properties = item.attrib.get("properties", "")
                if not item_id or not href:
                    continue
                full_href = normalize_href(posixpath.join(opf_dir, href))
                manifest[item_id] = {
                    "href": full_href,
                    "media_type": media_type,
                    "properties": properties,
                }

            spine_ids: list[str] = [
                itemref.attrib.get("idref", "")
                for itemref in opf_root.findall(f".//{opf_tag('spine')}/{opf_tag('itemref')}")
                if itemref.attrib.get("idref")
            ]

            html_media_types = {"application/xhtml+xml", "text/html", "application/html+xml"}
            for item_id in spine_ids:
                doc_item = manifest.get(item_id)
                if not doc_item or doc_item.get("media_type") not in html_media_types:
                    continue
                href = doc_item.get("href", "")
                if not href:
                    continue
                try:
                    html = zf.read(href).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                section_data = parse_html_section(html, href, len(sections) + 1)
                if not section_data.content:
                    continue
                href_to_index[href] = len(sections)
                href_to_index[posixpath.basename(href)] = len(sections)
                sections.append(EpubRenderableSection(title=section_data.title, content=section_data.content))

            if not sections:
                return [], []

            def href_to_page(href: str | None, source_doc: str) -> int | None:
                if not href:
                    return None
                source_dir = posixpath.dirname(source_doc)
                normalized = normalize_href(posixpath.join(source_dir, href))
                if normalized in href_to_index:
                    return href_to_index[normalized]
                basename = posixpath.basename(normalized)
                return href_to_index.get(basename)

            toc_entries: list[tuple[int, str, int]] = []

            def append_toc_entry(level: int, title: str, href: str | None, source_doc: str):
                page_index = href_to_page(href, source_doc)
                clean_title = title.strip()
                if clean_title and page_index is not None:
                    toc_entries.append((level, clean_title, page_index))

            nav_candidates = [
                item for item in manifest.values()
                if "nav" in item.get("properties", "").split()
            ]
            if nav_candidates:
                nav_href = nav_candidates[0].get("href", "")
                if nav_href:
                    try:
                        nav_root = ET.fromstring(zf.read(nav_href))
                        xhtml_ns = ""
                        if nav_root.tag.startswith("{"):
                            xhtml_ns = nav_root.tag.split("}")[0][1:]

                        def x_tag(name: str) -> str:
                            return f"{{{xhtml_ns}}}{name}" if xhtml_ns else name

                        nav_nodes = nav_root.findall(f".//{x_tag('nav')}")
                        toc_nav = None
                        for nav in nav_nodes:
                            nav_type = (
                                nav.attrib.get("{http://www.idpf.org/2007/ops}type", "")
                                or nav.attrib.get("type", "")
                                or nav.attrib.get("epub:type", "")
                            )
                            if "toc" in nav_type.lower() or toc_nav is None:
                                toc_nav = nav

                        def walk_nav_ol(ol_node: ET.Element, level: int):
                            for li in ol_node.findall(x_tag("li")):
                                a = li.find(x_tag("a"))
                                span = li.find(x_tag("span"))
                                label_node = a if a is not None else span
                                title = "".join(label_node.itertext()).strip() if label_node is not None else "Untitled"
                                href = a.attrib.get("href") if a is not None else None
                                append_toc_entry(level, title, href, nav_href)
                                child_ol = li.find(x_tag("ol"))
                                if child_ol is not None:
                                    walk_nav_ol(child_ol, level + 1)

                        if toc_nav is not None:
                            top_ol = toc_nav.find(x_tag("ol"))
                            if top_ol is not None:
                                walk_nav_ol(top_ol, 1)
                    except Exception as e:
                        print(f"EPUB nav TOC parse error: {e}")

            if not toc_entries:
                ncx_item = next(
                    (item for item in manifest.values() if item.get("media_type") == "application/x-dtbncx+xml"),
                    None,
                )
                if ncx_item and ncx_item.get("href"):
                    try:
                        ncx_root = ET.fromstring(zf.read(ncx_item["href"]))
                        ncx_ns = ""
                        if ncx_root.tag.startswith("{"):
                            ncx_ns = ncx_root.tag.split("}")[0][1:]

                        def n_tag(name: str) -> str:
                            return f"{{{ncx_ns}}}{name}" if ncx_ns else name

                        def walk_nav_point(node: ET.Element, level: int):
                            label_elem = node.find(f"{n_tag('navLabel')}/{n_tag('text')}")
                            content_elem = node.find(n_tag("content"))
                            title = "".join(label_elem.itertext()).strip() if label_elem is not None else "Untitled"
                            href = content_elem.attrib.get("src") if content_elem is not None else None
                            append_toc_entry(level, title, href, ncx_item["href"])
                            for child in node.findall(n_tag("navPoint")):
                                walk_nav_point(child, level + 1)

                        nav_map = ncx_root.find(n_tag("navMap"))
                        if nav_map is not None:
                            for nav_point in nav_map.findall(n_tag("navPoint")):
                                walk_nav_point(nav_point, 1)
                    except Exception as e:
                        print(f"EPUB NCX TOC parse error: {e}")

            if not toc_entries:
                toc_entries = [(1, section.title, i) for i, section in enumerate(sections)]

            return sections, toc_entries
        finally:
            zf.close()

    epub_sections, epub_toc_entries = ft.use_memo(
        parse_epub,
        [state.selected_book, is_pdf],
    )

    def reset_reader_state():
        saved_position = state.get_last_position(state.selected_book)
        session = state.get_reader_session()
        set_current_page(saved_position)
        set_zoom(_as_float(session.get("pdf_zoom"), 1.0))
        set_is_vertical(_as_bool(session.get("pdf_is_vertical"), True))
        set_show_toc(_as_bool(session.get("pdf_show_toc"), True))
        set_pending_jump_target(saved_position if is_pdf else -1)
        set_epub_font_size(_as_int(session.get("epub_font_size"), 16))
        set_epub_line_height(_as_float(session.get("epub_line_height"), 1.6))
        set_epub_text_align(parse_text_align(session.get("epub_text_align", "left")))

    ft.on_updated(reset_reader_state, [state.selected_book])
    
    if is_pdf and not doc:
        return ft.Text(value="No book selected or file error", color="red")

    if not is_pdf and not epub_sections:
        return ft.Text(value="No readable EPUB sections found", color="red")

    page_count = len(doc) if is_pdf and doc else len(epub_sections)

    def clamp_current_page_to_book_bounds():
        if page_count <= 0:
            return
        if current_page < 0:
            set_current_page(0)
            return
        if current_page >= page_count:
            set_current_page(page_count - 1)

    ft.on_updated(clamp_current_page_to_book_bounds, [page_count, state.selected_book])

    def get_toc_entries() -> list[tuple[int, str, int]]:
        if not is_pdf:
            return epub_toc_entries
        if not doc:
            return []

        entries: list[tuple[int, str, int]] = []
        try:
            for item in doc.get_toc(simple=True):
                if len(item) < 3:
                    continue
                level, title, page_1_based = int(item[0]), str(item[1]).strip(), int(item[2])
                page_index = page_1_based - 1
                if title and 0 <= page_index < page_count:
                    entries.append((level, title, page_index))
        except Exception as e:
            print(f"TOC parse error: {e}")
        return entries

    toc_entries = ft.use_memo(get_toc_entries, [state.selected_book, is_pdf, epub_toc_entries])
    base_page_width = ft.use_memo(
        lambda: float(doc.load_page(0).rect.width) if (is_pdf and page_count > 0 and doc) else 600.0,
        [state.selected_book, is_pdf],
    )
    base_page_height = ft.use_memo(
        lambda: float(doc.load_page(0).rect.height) if (is_pdf and page_count > 0 and doc) else 800.0,
        [state.selected_book, is_pdf],
    )

    def calculate_max_zoom(with_toc: bool) -> float:
        if not is_pdf:
            return 2.5
        return 5.0

    max_zoom = calculate_max_zoom(show_toc)

    def clamp_zoom_to_layout():
        if zoom > max_zoom:
            set_zoom(round(max_zoom, 2))

    ft.on_updated(clamp_zoom_to_layout, [show_toc, state.selected_book, max_zoom])

    def get_page_base64(page_index: int):
        """Standard Base64 conversion with Data URI prefix for stable rendering."""
        try:
            if not doc:
                return None
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            encoded = base64.b64encode(pix.tobytes("png")).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
        except Exception as e:
            print(f"Error rendering page {page_index}: {e}")
            return None

    def on_prev_page(_: ft.Event[ft.IconButton]):
        if current_page > 0:
            set_current_page(current_page - 1)

    def on_next_page(_: ft.Event[ft.IconButton]):
        if current_page < page_count - 1:
            set_current_page(current_page + 1)

    def on_toggle_toc(_: ft.Event[ft.IconButton]):
        next_show_toc = not show_toc
        set_show_toc(next_show_toc)
        set_zoom(min(zoom, round(calculate_max_zoom(next_show_toc), 2)))
        if is_pdf and effective_is_vertical:
            set_pending_jump_target(current_page)

    def on_toggle_reading_mode(_: ft.Event[ft.IconButton]):
        set_is_vertical(not is_vertical)

    def on_zoom_in(_: ft.Event[ft.IconButton]):
        set_zoom(min(round(max_zoom, 2), round(zoom + 0.25, 2)))

    def on_zoom_out(_: ft.Event[ft.IconButton]):
        min_zoom = 0.7 if not is_pdf else 0.5
        set_zoom(max(min_zoom, round(zoom - 0.25, 2)))

    def on_jump_to_page(page_index: int):
        if 0 <= page_index < page_count:
            set_current_page(page_index)
            if is_pdf and effective_is_vertical:
                set_pending_jump_target(page_index)

    def persist_reader_position():
        state.save_last_position(current_page)

    ft.on_updated(persist_reader_position, [current_page, state.selected_book])

    def persist_reader_session():
        align_label = "left"
        if epub_text_align == ft.TextAlign.CENTER:
            align_label = "center"
        elif epub_text_align == ft.TextAlign.JUSTIFY:
            align_label = "justify"

        state.save_reader_session(
            pdf_zoom=zoom,
            pdf_is_vertical=is_vertical,
            pdf_show_toc=show_toc,
            epub_font_size=epub_font_size,
            epub_line_height=epub_line_height,
            epub_text_align=align_label,
        )

    ft.on_updated(
        persist_reader_session,
        [zoom, is_vertical, show_toc, epub_font_size, epub_line_height, epub_text_align, state.selected_book],
    )

    rendered_page_width = max(1.0, base_page_width * zoom) if is_pdf else 0.0
    rendered_page_height = max(1.0, base_page_height * zoom) if is_pdf else 0.0
    page_item_extent = int(rendered_page_height + 12)
    visible_indices = range(max(0, current_page - 2), min(page_count, current_page + 3))

    current_src = ft.use_memo(
        lambda: get_page_base64(current_page) or "",
        [current_page, zoom, state.selected_book, is_pdf],
    )

    body_controls = cast(list[ft.Control], [])

    if show_toc and len(toc_entries) > 0:
        body_controls.append(
            TocPanel(
                width=toc_width,
                current_page=current_page,
                entries=toc_entries,
                on_jump_to_page=on_jump_to_page,
            )
        )
        body_controls.append(
            ft.VerticalDivider(width=1)
        )

    if is_pdf:
        body_controls.append(
            PdfReader(
                page_count=page_count,
                current_page=current_page,
                is_vertical=effective_is_vertical,
                rendered_page_width=rendered_page_width,
                rendered_page_height=rendered_page_height,
                page_item_extent=page_item_extent,
                visible_indices=visible_indices,
                jump_target_page=pending_jump_target if pending_jump_target >= 0 else None,
                current_src=current_src,
                get_page_base64=get_page_base64,
                on_visible_page_change=set_current_page,
                on_jump_handled=lambda: set_pending_jump_target(-1),
            )
        )
    else:
        body_controls.append(
            EpubReader(
                sections=epub_sections,
                current_page=current_page,
                is_vertical=False,
                font_size=epub_font_size,
                line_height=epub_line_height,
                text_align=epub_text_align,
                on_visible_section_change=set_current_page,
            )
        )

    def on_epub_font_size_change(delta: int):
        set_epub_font_size(max(12, min(32, epub_font_size + delta)))

    def on_epub_line_height_change(delta: float):
        set_epub_line_height(max(1.0, min(2.4, round(epub_line_height + delta, 1))))

    def on_epub_text_align_change(value: ft.TextAlign):
        set_epub_text_align(value)

    return ft.Column(
        expand=True,
        spacing=0,
        controls=cast(list[ft.Control], [
            ReaderToolbar(
                current_page=current_page,
                page_count=page_count,
                zoom=zoom,
                is_vertical=effective_is_vertical,
                position_label="Page" if is_pdf else "Section",
                show_zoom_controls=is_pdf,
                show_reading_mode_toggle=is_pdf,
                toc_available=len(toc_entries) > 0,
                show_toc=show_toc,
                on_back=lambda _: state.navigate("/"),
                on_prev_page=on_prev_page,
                on_next_page=on_next_page,
                on_toggle_toc=on_toggle_toc,
                on_toggle_reading_mode=on_toggle_reading_mode,
                on_zoom_in=on_zoom_in,
                on_zoom_out=on_zoom_out,
            ),
            EpubControls(
                font_size=epub_font_size,
                line_height=epub_line_height,
                text_align=epub_text_align,
                on_font_size_change=on_epub_font_size_change,
                on_line_height_change=on_epub_line_height_change,
                on_text_align_change=on_epub_text_align_change,
            ) if not is_pdf else ft.Container(),
            ft.Row(
                expand=True,
                spacing=0,
                controls=body_controls,
            ),
        ])
    )