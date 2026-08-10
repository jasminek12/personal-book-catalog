from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.author import Author
from app.schemas.book import AuthorOut

router = APIRouter(prefix="/authors", tags=["authors"])

@router.get("", response_model=list[AuthorOut])
def list_authors(db: Session = Depends(get_db)):
    return db.scalars(select(Author).order_by(Author.name)).all()
