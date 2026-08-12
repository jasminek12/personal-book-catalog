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


COVER_NOISE = {
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
    "publisher",
    "press",
    "isbn",
    "hardcover",
    "paperback",
    "paper",
    "pages",
    "volume",
    "vol",
    "book",
    "books",
    "with",
    "introduction",
    "foreword",
    "illustrated",
    "phd",
    "scholastic",
}


def _normalize(text: str) -> str:
    text = text.lower()

    text = text.replace("â€™", "'")
    text = text.replace("’", "'")

    text = re.sub(
        r"[^a-z0-9\s']",
        " ",
        text,
    )

    return " ".join(text.split())


def _words(text: str) -> list[str]:
    return re.findall(
        r"[a-z]{2,}",
        _normalize(text),
    )


def _useful_ocr_words(
    ocr_text: str,
) -> list[str]:

    return [
        word
        for word in _words(ocr_text)
        if word not in COVER_NOISE
    ]


def _best_word_match(
    word: str,
    other_words: list[str],
) -> float:

    if not other_words:
        return 0.0

    return max(
        (
            fuzz.ratio(word, other)
            for other in other_words
        ),
        default=0.0,
    )


def _title_word_score(
    ocr_words: list[str],
    title_words: list[str],
) -> float:

    if not ocr_words or not title_words:
        return 0.0

    scores = []

    for title_word in title_words:

        best = _best_word_match(
            title_word,
            ocr_words,
        )

        if best >= 90:
            scores.append(100.0)

        elif best >= 75:
            scores.append(best)

        else:
            scores.append(0.0)

    return sum(scores) / len(scores)


def _exact_title_word_ratio(
    ocr_words: list[str],
    title_words: list[str],
) -> float:

    if not title_words:
        return 0.0

    ocr_set = set(ocr_words)

    matched = sum(
        1
        for word in title_words
        if word in ocr_set
    )

    return (
        matched
        / len(title_words)
        * 100
    )


def _phrase_similarity(
    ocr_text: str,
    title: str,
) -> float:

    ocr = _normalize(ocr_text)
    title = _normalize(title)

    if not ocr or not title:
        return 0.0

    return max(
        fuzz.partial_ratio(
            ocr,
            title,
        ),
        fuzz.token_set_ratio(
            ocr,
            title,
        ),
    )


def _author_exact_score(
    ocr_text: str,
    candidate: BookCandidate,
) -> float:

    if not candidate.author_name:
        return 0.0

    ocr_words = set(
        _words(ocr_text)
    )

    author_words = [
        word
        for word in _words(
            candidate.author_name
        )
        if len(word) >= 3
    ]

    if not author_words:
        return 0.0

    matched = sum(
        1
        for word in author_words
        if word in ocr_words
    )

    return (
        matched
        / len(author_words)
        * 100
    )


def _author_fuzzy_score(
    ocr_text: str,
    candidate: BookCandidate,
) -> float:

    if not candidate.author_name:
        return 0.0

    ocr_words = _words(ocr_text)
    author_words = _words(
        candidate.author_name
    )

    if not ocr_words or not author_words:
        return 0.0

    scores = []

    for author_word in author_words:

        if len(author_word) < 3:
            continue

        best = _best_word_match(
            author_word,
            ocr_words,
        )

        if best >= 75:
            scores.append(best)
        else:
            scores.append(0.0)

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


def _score_candidate(
    ocr_text: str,
    candidate: BookCandidate,
) -> float:

    title_words = _words(
        candidate.title
    )

    ocr_words = _useful_ocr_words(
        ocr_text
    )

    if not title_words or not ocr_words:
        return 0.0

    # --------------------------------------------------
    # TITLE SIGNAL
    # --------------------------------------------------

    exact_ratio = _exact_title_word_ratio(
        ocr_words,
        title_words,
    )

    word_score = _title_word_score(
        ocr_words,
        title_words,
    )

    phrase_score = _phrase_similarity(
        ocr_text,
        candidate.title,
    )

    # --------------------------------------------------
    # AUTHOR SIGNAL
    # --------------------------------------------------

    author_exact = _author_exact_score(
        ocr_text,
        candidate,
    )

    author_fuzzy = _author_fuzzy_score(
        ocr_text,
        candidate,
    )

    # --------------------------------------------------
    # IMPORTANT:
    #
    # A one-word title such as "Taken" should NOT
    # receive 100 just because "Taken" occurs in
    # the tagline.
    #
    # Multi-word titles get much more credit when
    # multiple title words are actually present.
    # --------------------------------------------------

    if len(title_words) == 1:

        # A single title word matching the OCR is weak
        # evidence because taglines commonly contain
        # ordinary words such as:
        #
        # taken
        # tortured
        # ransom
        # love
        # life
        # death
        #
        title_component = min(
            word_score * 0.20,
            25.0,
        )

        if (
                word_score >= 90
                and author_exact >= 100
        ):
            title_component = word_score * 0.75

    else:

        title_component = (
            word_score * 0.45
            + exact_ratio * 0.35
            + phrase_score * 0.10
        )

    # --------------------------------------------------
    # AUTHOR
    #
    # Author is useful for identifying the correct
    # author's catalog, but must NOT overwhelm title
    # evidence.
    # --------------------------------------------------

    author_component = (
        author_exact * 0.08
        + author_fuzzy * 0.02
    )

    score = (
        title_component
        + author_component
    )

    # --------------------------------------------------
    # Strong multi-word title evidence
    # --------------------------------------------------

    if (
        len(title_words) >= 2
        and exact_ratio >= 75
    ):
        score += 15

    if (
        len(title_words) >= 2
        and exact_ratio >= 90
    ):
        score += 10

    # --------------------------------------------------
    # Strong author evidence
    #
    # Useful only as a supporting signal.
    # --------------------------------------------------

    if author_exact >= 100:
        score += 10

    elif author_exact >= 50:
        score += 5

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