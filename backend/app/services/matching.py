from dataclasses import dataclass
import re

from rapidfuzz import fuzz

from app.services.metadata_models import BookCandidate


@dataclass
class ScoredCandidate:
    candidate: BookCandidate
    confidence: float

    def to_dict(self) -> dict:
        return {
            **self.candidate.to_dict(),
            "confidence": round(
                self.confidence,
                1,
            ),
        }


def _normalize(text: str) -> str:
    text = text.lower()

    text = text.replace(
        "â€™",
        "'",
    )

    text = re.sub(
        r"[^a-z0-9\s']",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


def _words(text: str) -> list[str]:
    return re.findall(
        r"[a-z]{2,}",
        _normalize(text),
    )


def _useful_ocr_text(
    ocr_text: str,
) -> str:
    """
    Remove common book-cover noise while keeping actual title words.
    """

    words = _words(ocr_text)

    noise = {
        "new",
        "york",
        "times",
        "bestseller",
        "best",
        "seller",
        "author",
        "written",
        "novel",
        "edition",
        "copyright",
        "published",
        "press",
        "publisher",
        "phd",
        "isbn",
    }

    useful = [
        word
        for word in words
        if word not in noise
        and len(word) >= 2
    ]

    return " ".join(useful)


def _token_overlap_score(
    ocr_text: str,
    candidate_title: str,
) -> float:
    ocr_words = _words(
        ocr_text
    )

    candidate_words = _words(
        candidate_title
    )

    if not ocr_words or not candidate_words:
        return 0.0

    matched = 0.0

    for candidate_word in candidate_words:

        best = max(
            (
                fuzz.ratio(
                    candidate_word,
                    ocr_word,
                )
                for ocr_word in ocr_words
            ),
            default=0.0,
        )

        # Only count reasonably strong word matches.
        if best >= 70:
            matched += best

    return (
        matched
        / len(candidate_words)
    )


def _score_candidate(
    ocr_text: str,
    candidate: BookCandidate,
) -> float:
    normalized_ocr = _normalize(
        ocr_text
    )

    normalized_title = _normalize(
        candidate.title
    )

    if not normalized_ocr or not normalized_title:
        return 0.0

    useful_ocr = _useful_ocr_text(
        ocr_text
    )

    # Whole-string similarity.
    full_ratio = fuzz.token_set_ratio(
        normalized_ocr,
        normalized_title,
    )

    # Partial matching is especially useful
    # when OCR contains lots of extra cover text.
    partial_ratio = fuzz.partial_ratio(
        normalized_ocr,
        normalized_title,
    )

    # Compare individual title words against OCR words.
    overlap = _token_overlap_score(
        useful_ocr,
        normalized_title,
    )

    # Compare only the useful OCR text.
    useful_ratio = (
        fuzz.token_set_ratio(
            useful_ocr,
            normalized_title,
        )
        if useful_ocr
        else 0.0
    )

    # Weighted score.
    score = (
        full_ratio * 0.20
        + partial_ratio * 0.20
        + overlap * 0.40
        + useful_ratio * 0.20
    )

    # Small bonus when multiple title words occur
    # directly in the OCR.
    ocr_words = set(
        _words(useful_ocr)
    )

    title_words = set(
        _words(normalized_title)
    )

    exact_matches = len(
        ocr_words & title_words
    )

    score += min(
        exact_matches * 3,
        15,
    )

    return min(
        score,
        100.0,
    )


def rank_candidates(
    ocr_text: str,
    candidates: list[BookCandidate],
    top_n: int = 3,
) -> list[ScoredCandidate]:

    if not ocr_text or not candidates:
        return []

    scored = []

    for candidate in candidates:

        confidence = _score_candidate(
            ocr_text,
            candidate,
        )

        scored.append(
            ScoredCandidate(
                candidate=candidate,
                confidence=confidence,
            )
        )

    scored.sort(
        key=lambda item: item.confidence,
        reverse=True,
    )

    return scored[:top_n]