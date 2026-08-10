import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.api.deps import get_db
from app.models.book import Book, ReadStatus
from app.models.author import Author
from app.models.genre import Genre
from app.models.series import Series
from app.schemas.book import BookCreate, BookUpdate, BookOut

router = APIRouter(prefix="/books", tags=["books"])

def _get_or_create_author(db: Session, name: str | None) -> Author | None:
    if not name:
        return None
    author = db.scalar(select(Author).where(Author.name == name))
    if not author:
        author = Author(name=name)
        db.add(author)
        db.flush()
    return author

def _get_or_create_series(db: Session, name: str | None) -> Series | None:
    if not name:
        return None
    series = db.scalar(select(Series).where(Series.name == name))
    if not series:
        series = Series(name=name)
        db.add(series)
        db.flush()
    return series

def _get_or_create_genres(db: Session, names: list[str]) -> list[Genre]:
    genres = []
    for name in names:
        if not name:
            continue
        genre = db.scalar(select(Genre).where(Genre.name == name))
        if not genre:
            genre = Genre(name=name)
            db.add(genre)
            db.flush()
        genres.append(genre)
    return genres

def _book_query(db: Session):
    return select(Book).options(
        selectinload(Book.author),
        selectinload(Book.series),
        selectinload(Book.genres),
    )

@router.get("", response_model=list[BookOut])
def list_books(
    db: Session = Depends(get_db),
    read_status: ReadStatus | None = None,
    genre: str | None = Query(default=None, description="Filter by genre name"),
    search: str | None = Query(default=None, description="Case-insensitive title search"),
):
    stmt = _book_query(db)
    if read_status:
        stmt = stmt.where(Book.read_status == read_status)
    if search:
        stmt = stmt.where(Book.title.ilike(f"%{search}%"))
    if genre:
        stmt = stmt.join(Book.genres).where(Genre.name == genre)
    books = db.scalars(stmt).unique().all()
    return books

@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: uuid.UUID, db: Session = Depends(get_db)):
    book = db.scalar(_book_query(db).where(Book.id == book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.post("", response_model=BookOut, status_code=201)
def create_book(payload: BookCreate, db: Session = Depends(get_db)):
    author = _get_or_create_author(db, payload.author_name)
    series = _get_or_create_series(db, payload.series_name)
    genres = _get_or_create_genres(db, payload.genre_names)

    book = Book(
        title=payload.title,
        author=author,
        series=series,
        series_number=payload.series_number,
        genres=genres,
        isbn=payload.isbn,
        cover_url=payload.cover_url,
        description=payload.description,
        page_count=payload.page_count,
        publication_year=payload.publication_year,
        read_status=payload.read_status,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return db.scalar(_book_query(db).where(Book.id == book.id))

@router.put("/{book_id}", response_model=BookOut)
def update_book(book_id: uuid.UUID, payload: BookUpdate, db: Session = Depends(get_db)):
    book = db.scalar(select(Book).where(Book.id == book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    data = payload.model_dump(exclude_unset=True)

    if "author_name" in data:
        book.author = _get_or_create_author(db, data.pop("author_name"))
    if "series_name" in data:
        book.series = _get_or_create_series(db, data.pop("series_name"))
    if "genre_names" in data:
        book.genres = _get_or_create_genres(db, data.pop("genre_names") or [])

    for field, value in data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return db.scalar(_book_query(db).where(Book.id == book.id))

@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: uuid.UUID, db: Session = Depends(get_db)):
    book = db.scalar(select(Book).where(Book.id == book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
