from dataclasses import dataclass
from rapidfuzz import fuzz
from app.services.metadata_models import BookCandidate

@dataclass
class ScoredCandidate:
    candidate: BookCandidate
    confidence: float
    def to_dict(self) -> dict:
        return {**self.candidate.to_dict(), "confidence": round(self.confidence, 1)}

def rank_candidates(
    ocr_text: str, candidates: list[BookCandidate], top_n: int = 3
) -> list[ScoredCandidate]:
    if not ocr_text or not candidates:
        return []
    scored = [
        ScoredCandidate(
            candidate=c,
            confidence=fuzz.token_sort_ratio(ocr_text.lower(), c.title.lower()),
        )
        for c in candidates
    ]
    scored.sort(key=lambda s: s.confidence, reverse=True)
    return scored[:top_n]
