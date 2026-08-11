import io
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont
from app.services.metadata import BookCandidate

def _make_cover_image(text: str) -> bytes:
    img = Image.new("RGB", (400, 600), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            r"C:\Windows\Fonts\Arial.ttf", 36
        )
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 250), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_identify_extracts_text_from_real_image(client):
    image_bytes = _make_cover_image("THE HOBBIT")

    fake_candidates = [
        BookCandidate("The Hobbit", "J.R.R. Tolkien", None, None, 1937, 310)
    ]
    with patch("app.api.scan.search_by_title", return_value=fake_candidates):
        r = client.post(
            "/scan/identify",
            files={"image": ("cover.png", image_bytes, "image/png")},
        )

    assert r.status_code == 200
    body = r.json()
    assert "HOBBIT" in body["raw_ocr_text"].upper()
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["title"] == "The Hobbit"
    assert body["candidates"][0]["confidence"] > 50

def test_identify_rejects_bad_content_type(client):
    r = client.post(
        "/scan/identify",
        files={"image": ("notes.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 400

def test_identify_with_no_metadata_matches(client):
    image_bytes = _make_cover_image("XQZPLMK")  # gibberish, no real book

    with patch("app.api.scan.search_by_title", return_value=[]):
        r = client.post(
            "/scan/identify",
            files={"image": ("cover.png", image_bytes, "image/png")},
        )

    assert r.status_code == 200
    assert r.json()["candidates"] == []

def test_confirm_creates_book_with_ocr_provenance(client):
    r = client.post(
        "/scan/confirm",
        json={
            "title": "Dune",
            "author_name": "Frank Herbert",
            "genre_names": ["Sci-Fi"],
            "publication_year": 1965,
            "raw_ocr_text": "DUNE",
            "ocr_confidence": 97.5,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["identification_method"] == "ocr_single"
    assert body["ocr_confidence"] == 97.5
    assert body["raw_ocr_text"] == "DUNE"
    assert body["author"]["name"] == "Frank Herbert"

def test_confirm_book_appears_in_library(client):
    client.post(
        "/scan/confirm",
        json={"title": "Neuromancer", "raw_ocr_text": "NEUROMANCER", "ocr_confidence": 90.0},
    )
    r = client.get("/books", params={"search": "neuromancer"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["identification_method"] == "ocr_single"
