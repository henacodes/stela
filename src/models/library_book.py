from dataclasses import dataclass


@dataclass(slots=True)
class LibraryBook:
    path: str
    format: str
    title: str
    author: str
    published_year: int | None
    cover_path: str | None
    total_units: int
    estimated_word_count: int
    last_position: int = 0
    last_opened_at: str | None = None

    @property
    def display_title(self) -> str:
        return self.title.strip() if self.title.strip() else self.path.split("/")[-1]

    @property
    def subtitle(self) -> str:
        parts: list[str] = []
        if self.author:
            parts.append(self.author)
        if self.published_year:
            parts.append(str(self.published_year))
        if self.total_units > 0:
            unit_label = "pages" if self.format == "pdf" else "sections"
            parts.append(f"{self.total_units} {unit_label}")
        return " • ".join(parts)

    @property
    def progress_percent(self) -> float:
        if self.total_units <= 0:
            return 0.0
        current = max(0, min(self.total_units - 1, self.last_position))
        return round(((current + 1) / self.total_units) * 100.0, 1)
