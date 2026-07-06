import runpy
from pathlib import Path


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "hoa-doc-filer" / "src" / "pdf_matcher.py"
    runpy.run_path(str(target), run_name="__main__")
