from pydantic import BaseModel

class CandidateOut(BaseModel):
    title: str
    author_name: str | None
    isbn: str | None
    cover_url: str | None
    publication_year: int | None
    page_count: int | None
    confidence: float

class ScanIdentifyResponse(BaseModel):
    raw_ocr_text: str
    candidates: list[CandidateOut]

class ScanConfirmRequest(BaseModel):
    title: str
    author_name: str | None = None
    isbn: str | None = None
    cover_url: str | None = None
    publication_year: int | None = None
    page_count: int | None = None
    genre_names: list[str] = []
    raw_ocr_text: str | None = None
    ocr_confidence: float | None = None
