from unittest.mock import patch
from app.services.metadata_models import BookCandidate
from app.services.metadata import search_by_title

def test_search_by_title_combines_sources():
    google_candidate = BookCandidate(
        title="Don't Sweat the Small Stuff",
        author_name="Richard Carlson",
        isbn="1234567890",
        cover_url="https://example.com/google.jpg",
        publication_year=1997,
        page_count=224,
    )

    open_library_candidate = BookCandidate(
        title="The Hobbit",
        author_name="J.R.R. Tolkien",
        isbn="0987654321",
        cover_url="https://example.com/openlibrary.jpg",
        publication_year=1937,
        page_count=310,
    )

    with patch(
        "app.services.metadata.search_google_books",
        return_value=[google_candidate],
    ), patch(
        "app.services.metadata.search_open_library",
        return_value=[open_library_candidate],
    ):
        results = search_by_title("test")

    assert len(results) == 2
    assert results[0].title == "The Hobbit"
    assert results[1].title == "Don't Sweat the Small Stuff"

def test_search_by_title_deduplicates_same_title_and_author():
    first = BookCandidate(
        title="The Hobbit",
        author_name="J.R.R. Tolkien",
        isbn="123",
        cover_url=None,
        publication_year=1937,
        page_count=310,
    )

    duplicate = BookCandidate(
        title="THE HOBBIT",
        author_name="J.R.R. Tolkien",
        isbn="456",
        cover_url=None,
        publication_year=1937,
        page_count=310,
    )

    with patch(
        "app.services.metadata.search_google_books",
        return_value=[first],
    ), patch(
        "app.services.metadata.search_open_library",
        return_value=[duplicate],
    ):
        results = search_by_title("The Hobbit")

    assert len(results) == 1
    assert results[0].title == "THE HOBBIT"