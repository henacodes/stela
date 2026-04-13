from __future__ import annotations

from hashlib import sha1
from pathlib import Path
import posixpath
from urllib.parse import unquote
import zipfile
import xml.etree.ElementTree as ET

import fitz


class CoverStore:
    def __init__(self, covers_root: str | None = None):
        default_root = Path.home() / ".stela" / "covers"
        self.covers_root = Path(covers_root) if covers_root else default_root
        self.covers_root.mkdir(parents=True, exist_ok=True)

    def save_cover(self, book_path: str, fmt: str) -> str | None:
        path = Path(book_path)
        if not path.exists():
            return None

        token = self._cover_token(path)
        if fmt == "pdf":
            target = self.covers_root / f"{token}.jpg"
            if target.exists():
                return str(target)
            data = self._extract_pdf_cover(path)
            if data is None:
                return None
            target.write_bytes(data)
            return str(target)

        if fmt == "epub":
            data, ext = self._extract_epub_cover(path)
            if data is None or ext is None:
                return None
            target = self.covers_root / f"{token}.{ext}"
            if target.exists():
                return str(target)
            target.write_bytes(data)
            return str(target)

        return None

    def _cover_token(self, path: Path) -> str:
        stat = path.stat()
        source = f"{path.resolve()}|{stat.st_size}|{int(stat.st_mtime)}"
        return sha1(source.encode("utf-8")).hexdigest()

    def _extract_pdf_cover(self, path: Path) -> bytes | None:
        try:
            with fitz.open(str(path)) as doc:
                if len(doc) == 0:
                    return None
                page = doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(0.45, 0.45), alpha=False)
                return pix.tobytes("jpg")
        except Exception:
            return None

    def _extract_epub_cover(self, path: Path) -> tuple[bytes | None, str | None]:
        def normalize_href(href: str) -> str:
            base = unquote(href.split("#", 1)[0]).strip()
            if not base:
                return ""
            return posixpath.normpath(base.lstrip("./"))

        try:
            with zipfile.ZipFile(path, "r") as zf:
                container_xml = zf.read("META-INF/container.xml")
                container_root = ET.fromstring(container_xml)
                rootfile_elem = container_root.find(".//{*}rootfile")
                if rootfile_elem is None:
                    return None, None

                opf_path = normalize_href(rootfile_elem.attrib.get("full-path", ""))
                if not opf_path:
                    return None, None

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
                    manifest[item_id] = {
                        "href": normalize_href(posixpath.join(opf_dir, href)),
                        "media_type": media_type,
                        "properties": properties,
                    }

                cover_item = next(
                    (it for it in manifest.values() if "cover-image" in it.get("properties", "").split()),
                    None,
                )

                if cover_item is None:
                    metadata_elem = opf_root.find(f".//{opf_tag('metadata')}")
                    cover_id = None
                    if metadata_elem is not None:
                        for meta in metadata_elem.findall(opf_tag("meta")):
                            if (meta.attrib.get("name") or "").lower() == "cover":
                                cover_id = meta.attrib.get("content")
                                break
                    if cover_id:
                        cover_item = manifest.get(cover_id)

                if cover_item is None:
                    cover_item = next(
                        (it for it in manifest.values() if (it.get("media_type") or "").startswith("image/")),
                        None,
                    )

                if cover_item is None:
                    return None, None

                href = cover_item.get("href", "")
                media_type = cover_item.get("media_type", "")
                if not href:
                    return None, None

                ext = self._media_type_to_ext(media_type, href)
                data = zf.read(href)
                return data, ext
        except Exception:
            return None, None

    def _media_type_to_ext(self, media_type: str, href: str) -> str:
        mt = media_type.lower()
        if mt == "image/jpeg":
            return "jpg"
        if mt == "image/png":
            return "png"
        if mt == "image/webp":
            return "webp"
        if mt == "image/gif":
            return "gif"
        suffix = Path(href).suffix.lower().lstrip(".")
        return suffix or "img"
