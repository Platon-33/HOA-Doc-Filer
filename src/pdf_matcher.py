"""
pdf_matcher.py

Reads text out of a scanned PDF and suggests a likely property name and
document type by checking that text against the aliases/keywords in
config/properties.json and config/doc_types.json.

For speed, this only looks at page 1, and only the header and footer
bands of that page (not the full page) - property names and doc-type
clues almost always live in a letterhead or footer, so we don't need
to read the whole document just to make this suggestion.

This does NOT decide anything on its own - it just proposes a best
guess. A human (you) still confirms or corrects it in the review step.
"""

import json
import os
import io
import re
from datetime import datetime
import pdfplumber
import fitz  # pymupdf
import pytesseract
from PIL import Image

import paths


def _config_path(filename):
    return os.path.join(paths.get_base_dir(), "config", filename)


def load_settings():
    with open(_config_path("settings.json"), "r") as f:
        return json.load(f)


def load_properties():
    with open(_config_path("properties.json"), "r") as f:
        return json.load(f)["properties"]


def load_doc_types():
    with open(_config_path("doc_types.json"), "r") as f:
        return json.load(f)["doc_types"]


def _configure_tesseract():
    """Point pytesseract at the installed Tesseract executable, using the
    path from settings.json so it's editable without touching code."""
    settings = load_settings()
    default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    tesseract_path = settings.get("tesseract_path")

    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    elif os.name == "nt" or os.path.exists(default_path):
        pytesseract.pytesseract.tesseract_cmd = default_path


def _correct_orientation(image):
    """Detect if the page is rotated (e.g. scanned upside-down) and fix
    it before OCR. Tesseract can read its own orientation confidence via
    image_to_osd - if that fails for any reason (blank page, very little
    text), we just use the image as-is rather than crashing."""
    try:
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        rotation = osd.get("rotate", 0)
        if rotation:
            image = image.rotate(-rotation, expand=True)
    except Exception:
        pass
    return image


def _get_crop_fractions(settings=None):
    if settings is None:
        settings = load_settings()
    return (
        settings.get("header_fraction", 0.25),
        settings.get("footer_fraction", 0.15),
    )


def extract_header_footer_text_layer(pdf_path, settings=None):
    """Try the fast path: read the embedded text layer (if the scanner
    software included one), cropped to just the header and footer bands
    of page 1."""
    header_fraction, footer_fraction = _get_crop_fractions(settings)

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        width, height = page.width, page.height

        header_box = (0, 0, width, height * header_fraction)
        footer_box = (0, height * (1 - footer_fraction), width, height)

        header_text = page.crop(header_box).extract_text() or ""
        footer_text = page.crop(footer_box).extract_text() or ""

    return f"{header_text}\n{footer_text}"


def ocr_header_footer(pdf_path, settings=None):
    """Fallback for scans with no embedded text: render just page 1 (not
    every page), correct its orientation, then crop to the header/footer
    bands before running OCR - keeps the OCR pass fast since Tesseract
    only has to read a small slice of the page instead of the whole
    thing."""
    _configure_tesseract()
    header_fraction, footer_fraction = _get_crop_fractions(settings)

    doc = fitz.open(pdf_path)
    page = doc[0]
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    doc.close()

    image = _correct_orientation(image)

    width, height = image.size
    header_crop = image.crop((0, 0, width, int(height * header_fraction)))
    footer_crop = image.crop((0, int(height * (1 - footer_fraction)), width, height))

    header_text = pytesseract.image_to_string(header_crop)
    footer_text = pytesseract.image_to_string(footer_crop)

    return f"{header_text}\n{footer_text}"


def extract_text(pdf_path):
    """Pull header/footer text out of page 1. Tries the fast path first
    (embedded text layer). If that comes back empty, falls back to OCR
    on just the header/footer crop of page 1."""
    settings = load_settings()

    text = extract_header_footer_text_layer(pdf_path, settings)

    if text.strip():
        return text

    return ocr_header_footer(pdf_path, settings)


def suggest_property(text, properties=None):
    """Return the best-matching property name, or None if nothing matched.
    Matching is simple substring search across the property's name and
    all its aliases - good enough for a first pass, tune aliases in
    properties.json as you see real-world variations."""
    if properties is None:
        properties = load_properties()

    text_lower = text.lower()

    for prop in properties:
        candidates = [prop["name"]] + prop.get("aliases", [])
        for candidate in candidates:
            if candidate.lower() in text_lower:
                return prop["name"]

    return None


def suggest_doc_type(text, doc_types=None):
    """Return the doc type with the most keyword hits in the text, or
    None if nothing matched at all."""
    if doc_types is None:
        doc_types = load_doc_types()

    text_lower = text.lower()

    best_match = None
    best_score = 0

    for doc_type in doc_types:
        keywords = doc_type.get("keywords", []) or []
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > best_score:
            best_score = score
            best_match = doc_type.get("name")

    return best_match


def suggest_date(text):
    """Look for the first recognizable date in the text (e.g. '07/06/2022'
    or '7/6/22') and normalize it to YYYY-MM-DD for the filename. Returns
    None if nothing date-like is found - the review window will let you
    type one in by hand in that case."""
    # Matches things like 7/6/2022, 07/06/22, 12-31-2022
    pattern = r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"
    match = re.search(pattern, text)
    if not match:
        return None

    month, day, year = match.groups()
    if len(year) == 2:
        year = "20" + year  # assume 2000s - fine for HOA docs in practice

    try:
        parsed = datetime(int(year), int(month), int(day))
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        return None


def suggest(pdf_path):
    """Convenience function: given a PDF path, return a dict with the
    extracted header/footer text (trimmed for preview) plus suggested
    property/doc type/date. Note: suggested_property is meant for
    choosing the destination FOLDER, not the filename."""
    text = extract_text(pdf_path)
    return {
        "pdf_path": pdf_path,
        "text_preview": text[:800],
        "has_text_layer": bool(text.strip()),
        "suggested_property": suggest_property(text),
        "suggested_doc_type": suggest_doc_type(text),
        "suggested_date": suggest_date(text),
    }


if __name__ == "__main__":
    # Quick manual test: python src/pdf_matcher.py path/to/file.pdf
    import sys
    import time

    if len(sys.argv) != 2:
        print("Usage: python src/pdf_matcher.py <path_to_pdf>")
    else:
        start = time.time()
        result = suggest(sys.argv[1])
        elapsed = time.time() - start

        print(f"Has text layer:     {result['has_text_layer']}")
        print(f"Suggested property: {result['suggested_property']}")
        print(f"Suggested doc type: {result['suggested_doc_type']}")
        print(f"Suggested date:     {result['suggested_date']}")
        print(f"Time taken:         {elapsed:.2f}s")
        print("\n--- Text preview (header + footer only) ---")
        print(result["text_preview"])