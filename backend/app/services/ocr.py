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

def _prepare_image(image_bytes: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(image_bytes))

    # Grayscale removes color information Tesseract does not need.
    image = ImageOps.grayscale(image)

    # Autocontrast helps with uneven lighting on book covers.
    image = ImageOps.autocontrast(image)

    return image

def extract_text(image_bytes: bytes) -> str:
    image = _prepare_image(image_bytes)

    raw_text = pytesseract.image_to_string(image)

    return raw_text.strip()


def extract_words(image_bytes: bytes) -> list[OCRWord]:
    image = _prepare_image(image_bytes)

    data = pytesseract.image_to_data(
        image,
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
    text = re.sub(r"^[^\w']+|[^\w']+$", "", text)

    return text

def extract_title(image_bytes: bytes) -> str:
    words = extract_words(image_bytes)

    if not words:
        return ""

    usable_words = [
        word
        for word in words
        if word.confidence >= 35 and _clean_word(word.text)
    ]

    if not usable_words:
        usable_words = words

    heights = sorted(word.height for word in usable_words)
    median_height = heights[len(heights) // 2]

    large_words = [
        word
        for word in usable_words
        if word.height >= max(20, median_height * 1.35)
    ]

    if not large_words:
        large_words = sorted(
            usable_words,
            key=lambda word: word.confidence,
            reverse=True,
        )[:8]

    large_words.sort(key=lambda word: (word.y, word.x))

    lines: list[list[OCRWord]] = []

    for word in large_words:
        word_center_y = word.y + word.height / 2
        placed = False

        for line in lines:
            line_center_y = sum(
                item.y + item.height / 2 for item in line
            ) / len(line)

            average_height = sum(
                item.height for item in line
            ) / len(line)

            if abs(word_center_y - line_center_y) <= average_height * 0.6:
                line.append(word)
                placed = True
                break

        if not placed:
            lines.append([word])

    for line in lines:
        line.sort(key=lambda word: word.x)

    def line_score(line: list[OCRWord]) -> float:
        average_height = sum(
            word.height for word in line
        ) / len(line)

        average_confidence = sum(
            word.confidence for word in line
        ) / len(line)

        word_count_bonus = min(len(line), 5) * 8

        return (
            average_height * 1.5
            + average_confidence * 0.4
            + word_count_bonus
        )

    lines.sort(key=line_score, reverse=True)

    # Start with the strongest title line.
    best_line = lines[0]

    title_words = [
        _clean_word(word.text)
        for word in best_line
        if _clean_word(word.text)
    ]

    # If the next line is visually similar in size and is directly below
    # the strongest line, it may be part of a multi-line title.
    if len(lines) > 1:
        second_line = lines[1]

        first_height = sum(
            word.height for word in best_line
        ) / len(best_line)

        second_height = sum(
            word.height for word in second_line
        ) / len(second_line)

        first_bottom = max(
            word.y + word.height for word in best_line
        )

        second_top = min(
            word.y for word in second_line
        )

        height_ratio = second_height / first_height

        vertical_gap = second_top - first_bottom

        if (
            height_ratio >= 0.75
            and vertical_gap <= first_height * 1.5
            and len(second_line) >= 1
        ):
            second_words = [
                _clean_word(word.text)
                for word in second_line
                if _clean_word(word.text)
            ]

            title_words.extend(second_words)

    title = " ".join(title_words)

    # Remove common decorative OCR leftovers.
    title = re.sub(r"[»>]+$", "", title)
    title = re.sub(r"\.{2,}$", "", title)

    # Remove trailing whitespace and normalize spacing.
    title = re.sub(r"\s+", " ", title).strip()

    return title