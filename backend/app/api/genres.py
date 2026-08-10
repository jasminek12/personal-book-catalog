from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.genre import Genre
from app.schemas.book import GenreOut

router = APIRouter(prefix="/genres", tags=["genres"])

@router.get("", response_model=list[GenreOut])
def list_genres(db: Session = Depends(get_db)):
    return db.scalars(select(Genre).order_by(Genre.name)).all()
