from app.services.matching import rank_candidates, _score_candidate
from app.services.metadata_models import BookCandidate


def test_single_word_title_exact_match_with_author_scores_high():
    """
    A single-word title backed by a confirmed author match is a
    real match, not a tagline coincidence, and should score high
    (previously capped at ~40 regardless of match quality).
    """
    dune = BookCandidate(
        title="Dune",
        author_name="Frank Herbert",
        isbn=None,
        cover_url=None,
        publication_year=1965,
        page_count=412,
    )

    score = _score_candidate("DUNE FRANK HERBERT", dune)

    assert score >= 85.0


def test_single_word_title_tagline_coincidence_stays_capped():
    """
    A single-word title that only coincidentally matches a word in
    a tagline, with no matching author present, should stay low
    confidence so it doesn't win over the real book.
    """
    taken = BookCandidate(
        title="Taken",
        author_name="Some Other Author",
        isbn=None,
        cover_url=None,
        publication_year=2010,
        page_count=300,
    )

    score = _score_candidate(
        "Taken Tortured Ransomed Wilbur Smith",
        taken,
    )

    assert score <= 30.0


def test_single_word_title_strong_word_but_wrong_author_stays_capped():
    """
    Even a perfect single-word title match should NOT get the lift
    if the author doesn't also match -- both signals must agree.
    """
    dune_wrong_author = BookCandidate(
        title="Dune",
        author_name="Someone Else",
        isbn=None,
        cover_url=None,
        publication_year=1965,
        page_count=412,
    )

    score = _score_candidate("DUNE FRANK HERBERT", dune_wrong_author)

    assert score <= 30.0


def test_multi_word_title_scoring_unaffected():
    """
    The single-word fix should not change scoring for multi-word
    titles at all.
    """
    hobbit = BookCandidate(
        title="The Hobbit",
        author_name="J.R.R. Tolkien",
        isbn=None,
        cover_url=None,
        publication_year=1937,
        page_count=310,
    )

    score = _score_candidate("THE HOBBIT J.R.R. TOLKIEN", hobbit)

    assert score == 100.0


def test_rank_candidates_puts_true_positive_single_word_title_first():
    dune = BookCandidate(
        title="Dune",
        author_name="Frank Herbert",
        isbn=None,
        cover_url=None,
        publication_year=1965,
        page_count=412,
    )
    unrelated = BookCandidate(
        title="Something Else Entirely",
        author_name="Nobody Related",
        isbn=None,
        cover_url=None,
        publication_year=2000,
        page_count=100,
    )

    results = rank_candidates(
        "DUNE FRANK HERBERT",
        [unrelated, dune],
        top_n=2,
    )

    assert results[0].candidate.title == "Dune"
    assert results[0].confidence > results[1].confidence