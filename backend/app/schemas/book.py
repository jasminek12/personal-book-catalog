import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.book import ReadStatus, IdentificationMethod

class GenreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str

class AuthorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str

class SeriesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str

class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    author_name: str | None = None
    genre_names: list[str] = Field(default_factory=list)
    series_name: str | None = None
    series_number: int | None = None
    isbn: str | None = None
    cover_url: str | None = None
    description: str | None = None
    page_count: int | None = None
    publication_year: int | None = None
    read_status: ReadStatus = ReadStatus.UNREAD

class BookUpdate(BaseModel):
    title: str | None = None
    author_name: str | None = None
    genre_names: list[str] | None = None
    series_name: str | None = None
    series_number: int | None = None
    isbn: str | None = None
    cover_url: str | None = None
    description: str | None = None
    page_count: int | None = None
    publication_year: int | None = None
    read_status: ReadStatus | None = None
    rating: int | None = None
    notes: str | None = None
    date_finished: datetime | None = None

class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    author: AuthorOut | None
    series: SeriesOut | None
    series_number: int | None
    genres: list[GenreOut]
    isbn: str | None
    cover_url: str | None
    description: str | None
    page_count: int | None
    publication_year: int | None
    read_status: ReadStatus
    rating: int | None
    notes: str | None
    date_added: datetime
    date_finished: datetime | None
    identification_method: IdentificationMethod
    ocr_confidence: float | None
    raw_ocr_text: str | None
