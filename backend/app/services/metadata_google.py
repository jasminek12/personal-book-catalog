import json
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from app.services.metadata_models import BookCandidate

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"

def search_google_books(
    title: str,
    max_results: int = 10,
) -> list[BookCandidate]:
    if not title.strip():
        return []

    query = f"intitle:{title.strip()}"

    url = (
        f"{GOOGLE_BOOKS_URL}"
        f"?q={quote(query)}"
        f"&maxResults={min(max_results, 40)}"
        f"&printType=books"
        f"&orderBy=relevance"
    )

    request = Request(
        url,
        headers={
            "User-Agent": "MyBookVault/1.0",
        },
    )

    try:
        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

    except HTTPError as exc:
        if exc.code == 429:
            print(
                "Google Books rate limit reached; "
                "using other metadata sources."
            )
        else:
            print(
                f"Google Books HTTP error: "
                f"{exc.code} {exc.reason}"
            )
        return []

    except URLError as exc:
        print(f"Google Books URL error: {exc.reason}")
        return []

    except TimeoutError:
        print("Google Books request timed out")
        return []

    except json.JSONDecodeError as exc:
        print(f"Google Books returned invalid JSON: {exc}")
        return []

    candidates: list[BookCandidate] = []

    for item in data.get("items", []):
        volume_info = item.get("volumeInfo", {})

        candidate_title = volume_info.get("title")

        if not candidate_title:
            continue

        authors = volume_info.get("authors") or []
        author_name = authors[0] if authors else None

        published_date = volume_info.get("publishedDate")
        publication_year = None

        if published_date:
            try:
                publication_year = int(published_date[:4])
            except (ValueError, TypeError):
                publication_year = None

        isbn = None

        for identifier in volume_info.get("industryIdentifiers", []):
            identifier_type = identifier.get("type")
            identifier_value = identifier.get("identifier")

            if identifier_type == "ISBN_13":
                isbn = identifier_value
                break

            if identifier_type == "ISBN_10" and isbn is None:
                isbn = identifier_value

        image_links = volume_info.get("imageLinks") or {}

        cover_url = (
            image_links.get("thumbnail")
            or image_links.get("smallThumbnail")
        )

        page_count = volume_info.get("pageCount")

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