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

    title = re.sub(
        r"[^a-z0-9\s]",
        " ",
        title,
    )

    return " ".join(title.split())


def _deduplicate_candidates(
    candidates: list[BookCandidate],
) -> list[BookCandidate]:
    seen: set[tuple[str, str]] = set()
    result: list[BookCandidate] = []

    for candidate in candidates:
        normalized_title = _normalize_title(
            candidate.title
        )

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


def _build_search_queries(
    title: str,
) -> list[str]:
    """
    Build several progressively broader queries from noisy OCR.

    OCR is allowed to contain spelling errors, so we don't rely on
    Open Library understanding the entire OCR string.
    """

    normalized = _normalize_title(title)

    if not normalized:
        return []

    words = normalized.split()

    queries: list[str] = []

    def add_query(query: str) -> None:
        query = " ".join(query.split())

        if query and query not in queries:
            queries.append(query)

    # 1. Full OCR string.
    add_query(normalized)

    # Remove obvious cover boilerplate.
    noise_words = {
        "new",
        "york",
        "times",
        "bestseller",
        "best",
        "seller",
        "author",
        "written",
        "edition",
        "copyright",
        "published",
        "publisher",
        "press",
        "phd",
        "isbn",
        "scholastic",
    }

    useful_words = [
        word
        for word in words
        if len(word) >= 2
        and word not in noise_words
    ]

    # 2. Cleaned OCR string.
    if len(useful_words) >= 2:
        add_query(
            " ".join(useful_words)
        )

    # 3. Strongest trailing words.
    #
    # Book titles are often grouped together on the cover,
    # so the final meaningful words are useful.
    for count in (5, 4, 3, 2):
        if len(useful_words) >= count:
            add_query(
                " ".join(
                    useful_words[-count:]
                )
            )

    # 4. Individual longer words.
    #
    # This is important when one OCR word is badly misspelled.
    # Open Library may still return useful candidates from another
    # recognizable word.
    for word in useful_words:
        if len(word) >= 5:
            add_query(word)

    return queries


def search_by_title(
    title: str,
    max_results_per_source: int = 10,
) -> list[BookCandidate]:
    if not title.strip():
        return []

    queries = _build_search_queries(
        title
    )

    all_candidates: list[
        BookCandidate
    ] = []

    for query in queries:

        try:
            google_candidates = (
                search_google_books(
                    query,
                    max_results=max_results_per_source,
                )
            )

            all_candidates.extend(
                google_candidates
            )
        except Exception:
            pass

        try:
            open_library_candidates = (
                search_open_library(
                    query,
                    max_results=max_results_per_source,
                )
            )

            all_candidates.extend(
                open_library_candidates
            )
        except Exception:
            pass

    return _deduplicate_candidates(
        all_candidates
    )