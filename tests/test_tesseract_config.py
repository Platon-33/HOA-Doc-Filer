import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pdf_matcher


def test_configure_tesseract_uses_default_windows_path(monkeypatch):
    monkeypatch.setattr(pdf_matcher, "load_settings", lambda: {})
    monkeypatch.setattr(os.path, "exists", lambda path: path == r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe")

    pdf_matcher._configure_tesseract()

    assert pdf_matcher.pytesseract.pytesseract.tesseract_cmd == r"C:\Program Files\Tesseract-OCR\tesseract.exe"
