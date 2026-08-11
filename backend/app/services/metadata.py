import httpx
from app.core.config import settings

class BookCandidate:
    def __init__(
        self,
        title: str,
        author_name: str | None,
        isbn: str | None,
        cover_url: str | None,
        publication_year: int | None,
        page_count: int | None,
    ):
        self.title = title
        self.author_name = author_name
        self.isbn = isbn
        self.cover_url = cover_url
        self.publication_year = publication_year
        self.page_count = page_count
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author_name": self.author_name,
            "isbn": self.isbn,
            "cover_url": self.cover_url,
            "publication_year": self.publication_year,
            "page_count": self.page_count,
        }

def search_by_title(query: str, limit: int = 10) -> list[BookCandidate]:
    if not query or not query.strip():
        return []
    try:
        response = httpx.get(
            f"{settings.open_library_base_url}/search.json",
            params={"title": query, "limit": limit},
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    data = response.json()
    candidates = []
    for doc in data.get("docs", []):
        isbn_list = doc.get("isbn", [])
        cover_id = doc.get("cover_i")
        candidates.append(
            BookCandidate(
                title=doc.get("title", ""),
                author_name=(doc.get("author_name") or [None])[0],
                isbn=isbn_list[0] if isbn_list else None,
                cover_url=(
                    f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                    if cover_id
                    else None
                ),
                publication_year=doc.get("first_publish_year"),
                page_count=doc.get("number_of_pages_median"),
            )
        )
    return candidates
