from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.deps import get_db

router = APIRouter(tags=["health"])

@router.get("/health")
def health(db: Session = Depends(get_db)):
    # Confirm API and DB connection
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
