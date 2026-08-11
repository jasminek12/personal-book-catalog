import io
import pytesseract
from PIL import Image, ImageOps

def extract_text(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))

    # Grayscale removes color noise Tesseract doesn't need.
    image = ImageOps.grayscale(image)

    # Autocontrast helps with uneven lighting on the cover.
    image = ImageOps.autocontrast(image)

    raw_text = pytesseract.image_to_string(image)
    return raw_text.strip()
