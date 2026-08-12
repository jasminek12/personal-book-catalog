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
    title = title.replace("’", "'")
    title = title.replace("â€œ", '"')
    title = title.replace("â€", '"')

    title = re.sub(r"[^a-z0-9\s']", " ", title)

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


def _build_search_queries(
    title: str,
) -> list[str]:
    """
    Build several progressively cleaner searches from noisy OCR.

    Book covers often contain:
      - title
      - author
      - tagline
      - publisher information
      - OCR garbage

    Therefore we generate several interpretations instead of
    assuming the entire OCR string is the title.
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

    # ---------------------------------------------------------
    # 1. Full OCR/title candidate
    # ---------------------------------------------------------

    add_query(normalized)

    # ---------------------------------------------------------
    # 2. Remove obvious cover noise
    # ---------------------------------------------------------

    noise_words = {
        "new",
        "york",
        "times",
        "bestseller",
        "best",
        "seller",
        "author",
        "written",
        "novel",
        "edition",
        "copyright",
        "published",
        "publisher",
        "press",
        "isbn",
        "hardcover",
        "paperback",
        "paper",
        "pages",
        "volume",
        "vol",
        "book",
        "books",
        "with",
        "introduction",
        "foreword",
        "illustrated",
        "phd",
        "scholastic",
    }

    meaningful_words = [
        word
        for word in words
        if len(word) >= 3
        and word not in noise_words
    ]

    # Remove obvious OCR garbage such as:
    # "qz", "xh", "bq", etc.
    meaningful_words = [
        word
        for word in meaningful_words
        if not (
            len(word) <= 3
            and not any(
                char in "aeiou"
                for char in word
            )
        )
    ]

    # ---------------------------------------------------------
    # 3. Meaningful words
    # ---------------------------------------------------------

    if len(meaningful_words) >= 2:
        add_query(
            " ".join(meaningful_words)
        )

    # ---------------------------------------------------------
    # 4. Last words
    #
    # Useful when OCR contains:
    #
    # "garbage garbage Taken Tortured Ransomed Wilbur Smith"
    # ---------------------------------------------------------

    if len(meaningful_words) >= 4:
        add_query(
            " ".join(
                meaningful_words[-4:]
            )
        )

    if len(meaningful_words) >= 3:
        add_query(
            " ".join(
                meaningful_words[-3:]
            )
        )

    if len(meaningful_words) >= 2:
        add_query(
            " ".join(
                meaningful_words[-2:]
            )
        )

    # ---------------------------------------------------------
    # 5. Individual meaningful words
    #
    # This is important for covers where the actual title
    # isn't recognized as a phrase.
    #
    # Example:
    #
    # "Taken Tortured Ransomed Wilbur Smith"
    #
    # Searching "Wilbur Smith" gives us all Wilbur Smith
    # books, including Those in Peril.
    # ---------------------------------------------------------
    for word in meaningful_words:
        if len(word) >= 5:
            add_query(word)

    return queries


def search_by_title(
    title: str,
    max_results_per_source: int = 20,
) -> list[BookCandidate]:

    if not title or not title.strip():
        return []

    queries = _build_search_queries(title)

    all_candidates: list[BookCandidate] = []

    # OpenLibrary is currently the most useful source for us.
    # Search it for every interpretation instead of stopping
    # after the first successful query.
    for query in queries:
        try:
            open_library_candidates = search_open_library(
                query,
                max_results=max_results_per_source,
            )

            all_candidates.extend(
                open_library_candidates
            )

        except Exception:
            pass

    # Google Books can be rate-limited, so do not hammer it
    # once for every OCR interpretation.
    #
    # One request using the strongest query is enough.
    if queries:
        try:
            google_candidates = search_google_books(
                queries[0],
                max_results=max_results_per_source,
            )

            all_candidates.extend(
                google_candidates
            )

        except Exception:
            pass

    return _deduplicate_candidates(
        all_candidates
    )