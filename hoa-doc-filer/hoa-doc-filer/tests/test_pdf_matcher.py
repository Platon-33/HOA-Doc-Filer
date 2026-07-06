import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pdf_matcher import suggest_doc_type


def test_suggest_doc_type_ignores_entries_without_keywords():
    doc_types = [
        {"name": "Comment placeholder"},
        {"name": "Invoices", "keywords": ["invoice"]},
    ]

    assert suggest_doc_type("Please pay this invoice", doc_types) == "Invoices"
