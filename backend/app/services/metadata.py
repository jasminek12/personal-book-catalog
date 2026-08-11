from dataclasses import dataclass
import re
from app.services.metadata_google import search_google_books
from app.services.metadata_openlibrary import search_open_library

@dataclass
class BookCandidate:
    title: str
    author_name: str | None
    isbn: str | None
    cover_url: str | None
    publication_year: int | None
    page_count: int | None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author_name": self.author_name,
            "isbn": self.isbn,
            "cover_url": self.cover_url,
            "publication_year": self.publication_year,
            "page_count": self.page_count,
        }

def _normalize_title(title: str) -> str:
    title = title.lower()

    title = title.replace("’", "'")
    title = title.replace("“", '"')
    title = title.replace("”", '"')

    title = re.sub(r"[^a-z0-9\s]", " ", title)

    return " ".join(title.split())

def _deduplicate_candidates(
    candidates: list[BookCandidate],
) -> list[BookCandidate]:
    seen: set[tuple[str, str]] = set()
    result: list[BookCandidate] = []

    for candidate in candidates:
        normalized_title = _normalize_title(candidate.title)

        normalized_author = _normalize_title(
            candidate.author_name or ""
        )

        key = (
            normalized_title,
            normalized_author,
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(candidate)

    return result

def search_by_title(
    title: str,
    max_results_per_source: int = 10,
) -> list[BookCandidate]:
    if not title.strip():
        return []

    google_candidates = search_google_books(
        title,
        max_results=max_results_per_source,
    )

    open_library_candidates = search_open_library(
        title,
        max_results=max_results_per_source,
    )

    combined = google_candidates + open_library_candidates

    return _deduplicate_candidates(combined)