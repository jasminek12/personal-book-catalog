from io import BytesIO
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont
from app.services.metadata import BookCandidate
from pathlib import Path

def _make_cover_image(title: str) -> bytes:
    image = Image.new("RGB", (1200, 800), "white")
    draw = ImageDraw.Draw(image)

    font_candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]

    font = None

    for font_path in font_candidates:
        if font_path.exists():
            font = ImageFont.truetype(str(font_path), 100)
            break

    if font is None:
        raise RuntimeError(
            "No suitable TrueType font found for OCR test image generation."
        )

    bbox = draw.textbbox((0, 0), title, font=font)

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (image.width - text_width) // 2
    y = (image.height - text_height) // 2

    draw.text(
        (x, y),
        title,
        fill="black",
        font=font,
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    return buffer.getvalue()

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
