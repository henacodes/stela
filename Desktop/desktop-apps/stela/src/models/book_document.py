from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import posixpath
from typing import Literal
from urllib.parse import unquote
import zipfile
import xml.etree.ElementTree as ET

import fitz


BookFormat = Literal["pdf", "epub", "unknown"]


@dataclass(slots=True)
class TocEntry:
    level: int
    title: str
    unit_index: int
    href: str | None = None


@dataclass(slots=True)
class BookMetadata:
    title: str = ""
    author: str = ""
    language: str = ""
    publisher: str = ""
    identifier: str = ""
    description: str = ""
    created_at: str = ""
    modified_at: str = ""
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class BookDocument:
    path: str
    format: BookFormat = "unknown"
    metadata: BookMetadata = field(default_factory=BookMetadata)
    toc: list[TocEntry] = field(default_factory=list)
    total_units: int = 0
    estimated_word_count: int = 0
    loaded_at: datetime | None = None

    def __post_init__(self):
        self.path = str(Path(self.path).expanduser())
        self.format = self.detect_format(self.path)

    @staticmethod
    def detect_format(path: str) -> BookFormat:
        suffix = Path(path).suffix.lower()
        if suffix == ".pdf":
            return "pdf"
        if suffix == ".epub":
            return "epub"
        return "unknown"

    @property
    def is_supported(self) -> bool:
        return self.format in {"pdf", "epub"}

    @property
    def file_name(self) -> str:
        return Path(self.path).name

    @property
    def display_title(self) -> str:
        if self.metadata.title.strip():
            return self.metadata.title.strip()
        return Path(self.path).stem

    @property
    def position_label(self) -> str:
        return "Page" if self.format == "pdf" else "Section"

    def load(self) -> BookDocument:
        self.toc = []
        self.total_units = 0
        self.estimated_word_count = 0

        if self.format == "pdf":
            self._load_pdf()
        elif self.format == "epub":
            self._load_epub()

        self.loaded_at = datetime.utcnow()
        return self

    def progress_percent(self, current_index: int) -> float:
        if self.total_units <= 0:
            return 0.0
        idx = self.clamp_index(current_index)
        return round(((idx + 1) / self.total_units) * 100.0, 2)

    def clamp_index(self, index: int) -> int:
        if self.total_units <= 0:
            return 0
        return max(0, min(self.total_units - 1, index))

    def format_position(self, current_index: int) -> str:
        if self.total_units <= 0:
            return f"{self.position_label} 0 / 0"
        idx = self.clamp_index(current_index)
        return f"{self.position_label} {idx + 1} / {self.total_units}"

    def estimated_reading_minutes(self, words_per_minute: int = 220) -> int:
        if words_per_minute <= 0:
            words_per_minute = 220
        if self.estimated_word_count <= 0:
            return 0
        return max(1, round(self.estimated_word_count / words_per_minute))

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "format": self.format,
            "metadata": {
                "title": self.metadata.title,
                "author": self.metadata.author,
                "language": self.metadata.language,
                "publisher": self.metadata.publisher,
                "identifier": self.metadata.identifier,
                "description": self.metadata.description,
                "created_at": self.metadata.created_at,
                "modified_at": self.metadata.modified_at,
                "extras": dict(self.metadata.extras),
            },
            "toc": [
                {
                    "level": t.level,
                    "title": t.title,
                    "unit_index": t.unit_index,
                    "href": t.href,
                }
                for t in self.toc
            ],
            "total_units": self.total_units,
            "estimated_word_count": self.estimated_word_count,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
        }

    def _load_pdf(self):
        with fitz.open(self.path) as doc:
            self.total_units = len(doc)
            raw = doc.metadata or {}
            self.metadata = BookMetadata(
                title=str(raw.get("title") or ""),
                author=str(raw.get("author") or ""),
                publisher=str(raw.get("producer") or ""),
                identifier=str(raw.get("format") or ""),
                created_at=str(raw.get("creationDate") or ""),
                modified_at=str(raw.get("modDate") or ""),
                extras={k: str(v) for k, v in raw.items() if v is not None},
            )

            entries: list[TocEntry] = []
            try:
                for item in doc.get_toc(simple=True):
                    if len(item) < 3:
                        continue
                    level = int(item[0])
                    title = str(item[1]).strip()
                    page_1 = int(item[2])
                    page_index = page_1 - 1
                    if title and 0 <= page_index < self.total_units:
                        entries.append(TocEntry(level=level, title=title, unit_index=page_index))
            except Exception:
                entries = []

            self.toc = entries

    def _load_epub(self):
        metadata = BookMetadata()
        toc_entries: list[TocEntry] = []
        estimated_words = 0
        total_sections = 0

        def normalize_href(href: str) -> str:
            base = unquote(href.split("#", 1)[0]).strip()
            if not base:
                return ""
            return posixpath.normpath(base.lstrip("./"))

        with zipfile.ZipFile(self.path, "r") as zf:
            container_xml = zf.read("META-INF/container.xml")
            container_root = ET.fromstring(container_xml)
            rootfile_elem = container_root.find(".//{*}rootfile")
            if rootfile_elem is None:
                self.metadata = metadata
                self.toc = []
                self.total_units = 0
                return

            opf_path = normalize_href(rootfile_elem.attrib.get("full-path", ""))
            if not opf_path:
                self.metadata = metadata
                self.toc = []
                self.total_units = 0
                return

            opf_root = ET.fromstring(zf.read(opf_path))
            ns = ""
            if opf_root.tag.startswith("{"):
                ns = opf_root.tag.split("}")[0][1:]

            def opf_tag(name: str) -> str:
                return f"{{{ns}}}{name}" if ns else name

            opf_dir = posixpath.dirname(opf_path)

            # Metadata
            md_elem = opf_root.find(f".//{opf_tag('metadata')}")
            if md_elem is not None:
                dc_ns = "http://purl.org/dc/elements/1.1/"
                title = md_elem.find(f"{{{dc_ns}}}title")
                creator = md_elem.find(f"{{{dc_ns}}}creator")
                language = md_elem.find(f"{{{dc_ns}}}language")
                publisher = md_elem.find(f"{{{dc_ns}}}publisher")
                identifier = md_elem.find(f"{{{dc_ns}}}identifier")
                description = md_elem.find(f"{{{dc_ns}}}description")
                date = md_elem.find(f"{{{dc_ns}}}date")

                metadata.title = "".join(title.itertext()).strip() if title is not None else ""
                metadata.author = "".join(creator.itertext()).strip() if creator is not None else ""
                metadata.language = "".join(language.itertext()).strip() if language is not None else ""
                metadata.publisher = "".join(publisher.itertext()).strip() if publisher is not None else ""
                metadata.identifier = "".join(identifier.itertext()).strip() if identifier is not None else ""
                metadata.description = "".join(description.itertext()).strip() if description is not None else ""
                metadata.created_at = "".join(date.itertext()).strip() if date is not None else ""

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

            href_to_index: dict[str, int] = {}
            html_media_types = {"application/xhtml+xml", "text/html", "application/html+xml"}

            for item_id in spine_ids:
                item_data = manifest.get(item_id)
                if not item_data or item_data.get("media_type") not in html_media_types:
                    continue
                href = item_data.get("href", "")
                if not href:
                    continue
                total_sections += 1
                href_to_index[href] = total_sections - 1
                href_to_index[posixpath.basename(href)] = total_sections - 1
                try:
                    text = zf.read(href).decode("utf-8", errors="ignore")
                    estimated_words += len(text.split())
                except Exception:
                    pass

            self.total_units = total_sections
            self.estimated_word_count = estimated_words

            if self.total_units <= 0:
                self.metadata = metadata
                self.toc = []
                return

            def href_to_index_from_source(href: str | None, source_doc: str) -> int | None:
                if not href:
                    return None
                source_dir = posixpath.dirname(source_doc)
                normalized = normalize_href(posixpath.join(source_dir, href))
                if normalized in href_to_index:
                    return href_to_index[normalized]
                return href_to_index.get(posixpath.basename(normalized))

            def append_toc(level: int, title: str, href: str | None, source_doc: str):
                idx = href_to_index_from_source(href, source_doc)
                clean = title.strip()
                if clean and idx is not None:
                    toc_entries.append(TocEntry(level=level, title=clean, unit_index=idx, href=href))

            nav_candidates = [
                item for item in manifest.values() if "nav" in item.get("properties", "").split()
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

                        def walk_ol(ol_node: ET.Element, level: int):
                            for li in ol_node.findall(x_tag("li")):
                                a = li.find(x_tag("a"))
                                span = li.find(x_tag("span"))
                                node = a if a is not None else span
                                title = "".join(node.itertext()).strip() if node is not None else "Untitled"
                                href = a.attrib.get("href") if a is not None else None
                                append_toc(level, title, href, nav_href)
                                child_ol = li.find(x_tag("ol"))
                                if child_ol is not None:
                                    walk_ol(child_ol, level + 1)

                        if toc_nav is not None:
                            top_ol = toc_nav.find(x_tag("ol"))
                            if top_ol is not None:
                                walk_ol(top_ol, 1)
                    except Exception:
                        pass

            if not toc_entries:
                ncx_item = next(
                    (i for i in manifest.values() if i.get("media_type") == "application/x-dtbncx+xml"),
                    None,
                )
                if ncx_item and ncx_item.get("href"):
                    ncx_href = ncx_item["href"]
                    try:
                        ncx_root = ET.fromstring(zf.read(ncx_href))
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
                            append_toc(level, title, href, ncx_href)
                            for child in node.findall(n_tag("navPoint")):
                                walk_nav_point(child, level + 1)

                        nav_map = ncx_root.find(n_tag("navMap"))
                        if nav_map is not None:
                            for nav_point in nav_map.findall(n_tag("navPoint")):
                                walk_nav_point(nav_point, 1)
                    except Exception:
                        pass

            if not toc_entries:
                toc_entries = [
                    TocEntry(level=1, title=f"Section {idx + 1}", unit_index=idx)
                    for idx in range(self.total_units)
                ]

        self.metadata = metadata
        self.toc = toc_entries
