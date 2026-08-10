import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models.genre import book_genres

class ReadStatus(str, enum.Enum):
    UNREAD = "unread"
    READING = "reading"
    READ = "read"


class IdentificationMethod(str, enum.Enum):
    MANUAL = "manual"
    OCR_SINGLE = "ocr_single"
    OCR_BATCH = "ocr_batch"

class Book(Base):
    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authors.id"), nullable=True
    )
    author: Mapped["Author"] = relationship(back_populates="books")

    series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("series.id"), nullable=True
    )
    series: Mapped["Series"] = relationship(back_populates="books")
    series_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    genres: Mapped[list["Genre"]] = relationship(secondary=book_genres, back_populates="books")

    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    cover_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    read_status: Mapped[ReadStatus] = mapped_column(
        Enum(ReadStatus, name="read_status_enum"), default=ReadStatus.UNREAD, nullable=False
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    date_finished: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    identification_method: Mapped[IdentificationMethod] = mapped_column(
        Enum(IdentificationMethod, name="identification_method_enum"),
        default=IdentificationMethod.MANUAL,
        nullable=False,
    )
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
