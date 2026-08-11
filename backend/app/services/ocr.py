import io
import re
from dataclasses import dataclass
import pytesseract
from PIL import Image, ImageFilter, ImageOps
from pytesseract import Output

@dataclass
class OCRWord:
    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int


OCR_CONFIG = "--psm 11"

MIN_OCR_WIDTH = 1600


def _prepare_image(image_bytes: bytes) -> Image.Image:
    """
    Prepare a camera image for OCR.

    Book-cover photographs are usually much less OCR-friendly than
    scanned documents, so we:
      1. Normalize to RGB.
      2. Convert to grayscale.
      3. Upscale smaller images.
      4. Improve contrast.
      5. Apply mild sharpening.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    image = ImageOps.grayscale(image)

    if image.width < MIN_OCR_WIDTH:
        scale = MIN_OCR_WIDTH / image.width

        image = image.resize(
            (
                int(image.width * scale),
                int(image.height * scale),
            ),
            Image.Resampling.LANCZOS,
        )

    image = ImageOps.autocontrast(image)

    image = image.filter(ImageFilter.SHARPEN)

    return image

def _create_threshold_variant(image: Image.Image) -> Image.Image:
    """
    Create a second OCR variant.

    This can help with high-contrast black/white text, while the
    normal grayscale image remains the primary OCR source.
    """
    return image.point(
        lambda pixel: 255 if pixel >= 170 else 0
    )

def _ocr_image(image: Image.Image) -> str:
    return pytesseract.image_to_string(
        image,
        config=OCR_CONFIG,
    ).strip()

def extract_text(image_bytes: bytes) -> str:
    """
    Extract text using more than one OCR representation.

    The normal image is preferred because book covers often contain
    stylized/colorful text that can be damaged by thresholding.
    """
    image = _prepare_image(image_bytes)

    results: list[str] = []

    normal_text = _ocr_image(image)

    if normal_text:
        results.append(normal_text)

    threshold_image = _create_threshold_variant(image)
    threshold_text = _ocr_image(threshold_image)

    if threshold_text:
        results.append(threshold_text)

    if not results:
        return ""

    # Keep both OCR passes available to downstream title extraction.
    return "\n".join(results)

def extract_words(image_bytes: bytes) -> list[OCRWord]:
    """
    Extract word-level OCR information from the primary image.

    The normal grayscale/sharpened image is used here because it
    produces more useful bounding boxes than aggressively thresholded
    variants.
    """
    image = _prepare_image(image_bytes)

    data = pytesseract.image_to_data(
        image,
        config=OCR_CONFIG,
        output_type=Output.DICT,
    )

    words: list[OCRWord] = []

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

        words.append(
            OCRWord(
                text=text,
                confidence=confidence,
                x=int(data["left"][i]),
                y=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
            )
        )

    return words

def _clean_word(text: str) -> str:
    text = text.strip()

    # Remove OCR punctuation surrounding a word.
    text = re.sub(
        r"^[^\w']+|[^\w']+$",
        "",
        text,
    )

    return text

def _build_lines(words: list[OCRWord]) -> list[list[OCRWord]]:
    """
    Group OCR words into approximate visual lines.
    """
    lines: list[list[OCRWord]] = []

    sorted_words = sorted(
        words,
        key=lambda word: (word.y, word.x),
    )

    for word in sorted_words:
        word_center_y = word.y + word.height / 2
        placed = False

        for line in lines:
            line_center_y = sum(
                item.y + item.height / 2
                for item in line
            ) / len(line)

            average_height = sum(
                item.height
                for item in line
            ) / len(line)

            if (
                abs(word_center_y - line_center_y)
                <= average_height * 0.6
            ):
                line.append(word)
                placed = True
                break

        if not placed:
            lines.append([word])

    for line in lines:
        line.sort(key=lambda word: word.x)

    return lines

def _line_text(line: list[OCRWord]) -> str:
    words = [
        _clean_word(word.text)
        for word in line
        if _clean_word(word.text)
    ]

    return " ".join(words)

def _looks_like_author_or_noise(text: str) -> bool:
    """
    Reject common non-title lines.

    This is intentionally conservative. Metadata matching later
    provides another layer of validation.
    """
    normalized = text.lower().strip()

    if not normalized:
        return True

    author_patterns = [
        r"^by\s+",
        r"^\d{1,4}$",
        r"^a\s+novel$",
        r"^a\s+novel\s+by\s+",
        r"^with\s+an\s+introduction",
        r"^introduction\s+by\s+",
        r"^foreword\s+by\s+",
    ]

    for pattern in author_patterns:
        if re.search(pattern, normalized):
            return True

    # ISBNs and mostly numeric lines are unlikely to be titles.
    alphanumeric = re.sub(r"[^a-z0-9]", "", normalized)

    if len(alphanumeric) >= 8 and alphanumeric.isdigit():
        return True

    return False

def extract_title(image_bytes: bytes) -> str:
    """
    Extract the most likely book title from OCR word positions.

    The algorithm favors:
      - larger text
      - higher OCR confidence
      - multiple words on the same line
      - coherent visual lines

    It also attempts to combine adjacent lines for multi-line titles.
    """
    words = extract_words(image_bytes)

    if not words:
        return ""

    usable_words = [
        word
        for word in words
        if word.confidence >= 35
        and _clean_word(word.text)
    ]

    if not usable_words:
        usable_words = [
            word
            for word in words
            if _clean_word(word.text)
        ]

    if not usable_words:
        return ""

    heights = sorted(
        word.height
        for word in usable_words
        if word.height > 0
    )

    if not heights:
        return ""

    median_height = heights[len(heights) // 2]

    large_words = [
        word
        for word in usable_words
        if word.height >= max(
            20,
            median_height * 1.25,
        )
    ]

    if not large_words:
        large_words = sorted(
            usable_words,
            key=lambda word: (
                word.confidence,
                word.height,
            ),
            reverse=True,
        )[:10]

    lines = _build_lines(large_words)

    if not lines:
        return ""

    candidate_lines = []

    for line in lines:
        text = _line_text(line)

        if not text:
            continue

        if _looks_like_author_or_noise(text):
            continue

        average_height = (
            sum(word.height for word in line)
            / len(line)
        )

        average_confidence = (
            sum(word.confidence for word in line)
            / len(line)
        )

        word_count_bonus = min(
            len(line),
            6,
        ) * 8

        # Favor large, confident, multi-word lines.
        score = (
            average_height * 1.5
            + average_confidence * 0.5
            + word_count_bonus
        )

        candidate_lines.append(
            (
                score,
                line,
            )
        )

    if not candidate_lines:
        candidate_lines = [
            (
                word.height * 1.5
                + word.confidence * 0.5,
                [word],
            )
            for word in usable_words
        ]

    candidate_lines.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_line = candidate_lines[0][1]

    title_words = [
        _clean_word(word.text)
        for word in best_line
        if _clean_word(word.text)
    ]

    if not title_words:
        return ""

    # Look for a second line that is visually connected to the title.
    best_line_height = (
        sum(word.height for word in best_line)
        / len(best_line)
    )

    first_bottom = max(
        word.y + word.height
        for word in best_line
    )

    for _, second_line in candidate_lines[1:]:
        second_text = _line_text(second_line)

        if not second_text:
            continue

        if _looks_like_author_or_noise(second_text):
            continue

        second_height = (
            sum(word.height for word in second_line)
            / len(second_line)
        )

        second_top = min(
            word.y
            for word in second_line
        )

        height_ratio = (
            second_height / best_line_height
        )

        vertical_gap = second_top - first_bottom

        if (
            height_ratio >= 0.70
            and vertical_gap <= best_line_height * 1.5
        ):
            second_words = [
                _clean_word(word.text)
                for word in second_line
                if _clean_word(word.text)
            ]

            title_words.extend(second_words)
            break

    title = " ".join(title_words)

    # Remove common decorative OCR leftovers.
    title = re.sub(
        r"[»>]+$",
        "",
        title,
    )

    title = re.sub(
        r"\.{2,}$",
        "",
        title,
    )

    title = re.sub(
        r"\s+",
        " ",
        title,
    ).strip()

    return title