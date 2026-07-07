import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import filer


class FilerTests(unittest.TestCase):
    def test_find_doc_type_config_skips_entries_without_name(self):
        doc_types = [
            {"_comment": "placeholder"},
            {"name": "Invoices", "date_format": "month_year"},
        ]

        config = filer.find_doc_type_config(doc_types, "Invoices")

        self.assertEqual(config["name"], "Invoices")


if __name__ == "__main__":
    unittest.main()
