"""
debug_render_page.py

Renders page 1 of a PDF to a PNG file so we can visually check what
Tesseract is actually seeing, and tests OCR against it directly.

Run with: python src/debug_render_page.py downloads/1636_001.pdf
"""

import sys
import fitz
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

pdf_path = sys.argv[1]

doc = fitz.open(pdf_path)
page = doc[0]
pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
pixmap.save("debug_page.png")
doc.close()

print(f"Saved rendered page as debug_page.png ({pixmap.width}x{pixmap.height})")

image = Image.open("debug_page.png")
text = pytesseract.image_to_string(image)
print(f"OCR text length: {len(text)}")
print("--- OCR output ---")
print(text)