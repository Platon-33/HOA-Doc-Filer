import sys
sys.path.insert(0, "src")
import pdf_matcher

path = sys.argv[1]
text = pdf_matcher.extract_full_first_page_text(path)
print("--- FULL PAGE 1 TEXT ---")
print(text)
print("\n--- SUGGESTED LOT NUMBER ---")
print(pdf_matcher.suggest_lot_number(path))