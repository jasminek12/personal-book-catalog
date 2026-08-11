from dataclasses import dataclass

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