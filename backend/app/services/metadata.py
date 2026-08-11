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

    title = title.replace("â€™", "'")
    title = title.replace("â€œ", '"')
    title = title.replace("â€ ", '"')

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


def _build_search_queries(title: str) -> list[str]:
    """
    Build progressively simpler queries for noisy OCR.

    Example:
        "qi and th eSokcerers Stone"

    becomes:
        "qi and th eSokcerers Stone"
        "and th eSokcerers Stone"
        "and eSokcerers Stone"
        "eSokcerers Stone"
        "Stone"
    """

    normalized = _normalize_title(title)

    if not normalized:
        return []

    words = normalized.split()

    queries: list[str] = []

    def add_query(query: str) -> None:
        query = " ".join(query.split())

        if not query:
            return

        if query not in queries:
            queries.append(query)

    # First try the complete OCR title.
    add_query(normalized)

    # Remove very short/noisy words.
    meaningful_words = [
        word
        for word in words
        if len(word) >= 4
    ]

    if len(meaningful_words) >= 2:
        add_query(" ".join(meaningful_words))

    # Try the last several meaningful words.
    if len(meaningful_words) >= 3:
        add_query(" ".join(meaningful_words[-3:]))

    if len(meaningful_words) >= 2:
        add_query(" ".join(meaningful_words[-2:]))

    return queries


def search_by_title(
    title: str,
    max_results_per_source: int = 10,
) -> list[BookCandidate]:
    if not title.strip():
        return []

    queries = _build_search_queries(title)

    all_candidates: list[BookCandidate] = []

    for query in queries:
        google_candidates = search_google_books(
            query,
            max_results=max_results_per_source,
        )

        open_library_candidates = search_open_library(
            query,
            max_results=max_results_per_source,
        )

        all_candidates.extend(google_candidates)
        all_candidates.extend(open_library_candidates)

        # Once we have results, stop sending increasingly noisy
        # queries to the metadata APIs.
        if all_candidates:
            break

    return _deduplicate_candidates(all_candidates)