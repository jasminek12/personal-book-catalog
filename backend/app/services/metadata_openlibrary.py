import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from app.services.metadata import BookCandidate

OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"

def search_open_library(
    title: str,
    max_results: int = 10,
) -> list[BookCandidate]:
    if not title.strip():
        return []

    params = {
        "title": title.strip(),
        "limit": min(max_results, 100),
        "fields": (
            "title,author_name,first_publish_year,"
            "isbn,cover_i,number_of_pages_median,publisher"
        ),
    }

    url = f"{OPEN_LIBRARY_URL}?{urlencode(params)}"

    request = Request(
        url,
        headers={
            "User-Agent": "MyBookVault/1.0",
        },
    )

    try:
        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []

    candidates: list[BookCandidate] = []

    for document in data.get("docs", []):
        candidate_title = document.get("title")

        if not candidate_title:
            continue

        authors = document.get("author_name") or []
        author_name = authors[0] if authors else None

        isbns = document.get("isbn") or []
        isbn = isbns[0] if isbns else None

        cover_id = document.get("cover_i")

        cover_url = None

        if cover_id:
            cover_url = (
                f"https://covers.openlibrary.org/b/id/"
                f"{cover_id}-L.jpg"
            )

        publication_year = document.get("first_publish_year")

        page_count = document.get("number_of_pages_median")

        candidates.append(
            BookCandidate(
                title=candidate_title,
                author_name=author_name,
                isbn=isbn,
                cover_url=cover_url,
                publication_year=publication_year,
                page_count=page_count,
            )
        )

    return candidates