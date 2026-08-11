from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.api.deps import get_db
from app.services.ocr import extract_text, extract_title
from app.services.metadata import search_by_title
from app.services.matching import rank_candidates
from app.schemas.scan import ScanIdentifyResponse, ScanConfirmRequest, CandidateOut
from app.schemas.book import BookOut
from app.models.book import Book, IdentificationMethod
from app.api.books import _get_or_create_author, _get_or_create_genres, _book_query

router = APIRouter(prefix="/scan", tags=["scan"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

@router.post("/identify", response_model=ScanIdentifyResponse)
async def identify_book(image: UploadFile = File(...)):
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=400,
            detail="Upload a JPEG, PNG, or WEBP image",
        )

    image_bytes = await image.read()

    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Image too large (max 10MB)",
        )

    raw_text = extract_text(image_bytes)

    if not raw_text:
        return ScanIdentifyResponse(
            raw_ocr_text="",
            candidates=[],
        )

    extracted_title = extract_title(image_bytes)

    if not extracted_title:
        return ScanIdentifyResponse(
            raw_ocr_text=raw_text,
            candidates=[],
        )

    metadata_candidates = search_by_title(extracted_title)
    ranked = rank_candidates(extracted_title, metadata_candidates)

    return ScanIdentifyResponse(
        raw_ocr_text=raw_text,
        candidates=[CandidateOut(**r.to_dict()) for r in ranked],
    )

@router.post("/confirm", response_model=BookOut, status_code=201)
def confirm_book(payload: ScanConfirmRequest, db: Session = Depends(get_db)):
    author = _get_or_create_author(db, payload.author_name)
    genres = _get_or_create_genres(db, payload.genre_names)

    book = Book(
        title=payload.title,
        author=author,
        genres=genres,
        isbn=payload.isbn,
        cover_url=payload.cover_url,
        publication_year=payload.publication_year,
        page_count=payload.page_count,
        identification_method=IdentificationMethod.OCR_SINGLE,
        ocr_confidence=payload.ocr_confidence,
        raw_ocr_text=payload.raw_ocr_text,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return db.scalar(_book_query(db).where(Book.id == book.id))
