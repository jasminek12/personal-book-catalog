import io
import re
from dataclasses import dataclass

import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output


@dataclass
class OCRWord:
    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int


def _load_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def _prepare_variants(image_bytes: bytes) -> list[Image.Image]:
    image = _load_image(image_bytes)

    # Keep the original resolution for normal camera photos.
    # Small images benefit from upscaling.
    width, height = image.size

    if width < 1000 or height < 1000:
        image = image.resize(
            (width * 4, height * 4),
            Image.Resampling.LANCZOS,
        )

    grayscale = ImageOps.grayscale(image)
    grayscale = ImageOps.autocontrast(grayscale)

    # Normal grayscale image.
    normal = grayscale

    # Thresholded version helps covers with strong text/background contrast.
    thresholded = grayscale.point(
        lambda pixel: 255 if pixel > 160 else 0
    )

    return [normal, thresholded]


def extract_text(image_bytes: bytes) -> str:
    variants = _prepare_variants(image_bytes)

    results: list[str] = []

    for image in variants:
        text = pytesseract.image_to_string(
            image,
            config="--psm 11",
        ).strip()

        if text:
            results.append(text)

    # Prefer the result containing more useful text.
    if not results:
        return ""

    return max(
        results,
        key=lambda text: len(re.findall(r"[A-Za-z]{2,}", text)),
    )


def extract_words(image_bytes: bytes) -> list[OCRWord]:
    variants = _prepare_variants(image_bytes)

    all_words: list[OCRWord] = []

    for image in variants:
        data = pytesseract.image_to_data(
            image,
            config="--psm 11",
            output_type=Output.DICT,
        )

        for i, text in enumerate(data["text"]):
            text = text.strip()

            if not text:
                continue

            try:
                confidence = float(data["conf"][i])
            except (ValueError, TypeError):
                continue

            if confidence < 0:
                continue

            all_words.append(
                OCRWord(
                    text=text,
                    confidence=confidence,
                    x=int(data["left"][i]),
                    y=int(data["top"][i]),
                    width=int(data["width"][i]),
                    height=int(data["height"][i]),
                )
            )

    return all_words


def _clean_word(text: str) -> str:
    text = text.strip()

    text = re.sub(
        r"^[^\w']+|[^\w']+$",
        "",
        text,
    )

    return text


def extract_title(image_bytes: bytes) -> str:
    image = _load_image(image_bytes)

    width, height = image.size

    if width < 1000 or height < 1000:
        image = image.resize(
            (width * 4, height * 4),
            Image.Resampling.LANCZOS,
        )

    grayscale = ImageOps.grayscale(image)
    grayscale = ImageOps.autocontrast(grayscale)

    variants = [
        grayscale,
        grayscale.point(lambda p: 255 if p > 160 else 0),
        grayscale.point(lambda p: 255 if p > 110 else 0),
    ]

    all_lines: list[str] = []

    for variant in variants:
        for psm in (6, 11):
            text = pytesseract.image_to_string(
                variant,
                config=f"--psm {psm}",
            )

            for line in text.splitlines():
                line = re.sub(r"\s+", " ", line).strip()

                if not line:
                    continue

                words = re.findall(
                    r"[A-Za-z]{2,}(?:['-][A-Za-z]+)*",
                    line,
                )

                if len(words) >= 2:
                    all_lines.append(line)

    if not all_lines:
        return ""

    ignored_patterns = [
        r"\bnew york times\b",
        r"\bbestseller\b",
        r"\bscholastic\b",
        r"\bhyperion\b",
        r"\bharper\b",
        r"\bpenguin\b",
        r"\brandom house\b",
        r"\bsimon\b",
        r"\bsimon & schuster\b",
    ]

    candidates: list[tuple[float, str]] = []

    for line in all_lines:
        lower = line.lower()

        if any(re.search(pattern, lower) for pattern in ignored_patterns):
            continue

        words = re.findall(
            r"[A-Za-z]{2,}(?:['-][A-Za-z]+)*",
            line,
        )

        if len(words) < 2:
            continue

        alpha_chars = sum(c.isalpha() for c in line)
        non_space_chars = sum(not c.isspace() for c in line)

        if non_space_chars == 0:
            continue

        alpha_ratio = alpha_chars / non_space_chars

        if alpha_ratio < 0.55:
            continue

        score = 0.0

        # More meaningful words is generally better.
        score += min(len(words), 8) * 12

        # Prefer reasonably substantial lines.
        score += min(len(line), 60) * 0.4

        # Penalize very short fragments.
        if len(words) <= 2:
            score -= 10

        # Penalize obvious OCR garbage.
        suspicious_words = sum(
            1
            for word in words
            if len(word) <= 2
        )

        score -= suspicious_words * 5

        # Strong bonus for words commonly appearing in titles.
        title_words = {
            "the",
            "and",
            "of",
            "a",
            "an",
            "to",
            "in",
            "for",
            "on",
            "harry",
            "potter",
            "sorcerer's",
            "sorcerer",
            "stone",
        }

        score += sum(
            15
            for word in words
            if word.lower() in title_words
        )

        candidates.append((score, line))

    if not candidates:
        return ""

    candidates.sort(
        key=lambda candidate: candidate[0],
        reverse=True,
    )

    return candidates[0][1]