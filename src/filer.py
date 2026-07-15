"""
filer.py

Takes a PDF plus a confirmed property, doc type, and (if needed) date,
and moves it into the right folder with the right name, following each
doc type's own naming convention:

  - Invoices           -> Invoices 7.2022.pdf          (month.year)
  - Meeting Minutes    -> Meeting Minutes 2.25.2013.pdf (full date)
  - Tax Returns        -> Tax Returns 2022.pdf          (year only)
  - Lot Files          -> LOT 1008.pdf                  (extracted lot number)
  - Governing Documents, Insurance, Violations,
    Correspondence     -> whatever exact title you type in
                           (these are one-off documents, not a
                           repeating pattern, so there's no sensible
                           way to auto-name them)

Some doc types file directly into the community's root folder instead
of their own subfolder (see 'subfolder': false in doc_types.json) -
matches how Tax Returns / Annual Report sit loose in your real
folders rather than in their own subfolder.
"""

import os
import re
import shutil

import paths


INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]'


def sanitize_filename(name):
    """Strip characters Windows won't allow in a filename."""
    return re.sub(INVALID_FILENAME_CHARS, "", name).strip()


def make_unique_path(path):
    """If the target filename already exists, add ' (1)', ' (2)', etc.
    so we never silently overwrite an existing document."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while True:
        candidate = f"{base} ({counter}){ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def _format_date_component(date_format, date_str):
    """date_str is an ISO date like '2022-07-01'. Returns the date
    portion of the filename in this doc type's convention. No leading
    zeros on month/day, matching how these are named by hand (e.g.
    '7.2022' not '07.2022')."""
    if not date_format or not date_str:
        return None

    year, month, day = date_str.split("-")
    year, month, day = int(year), int(month), int(day)

    if date_format == "month_year":
        return f"{month}.{year}"
    elif date_format == "full_date":
        return f"{month}.{day}.{year}"
    elif date_format == "year":
        return f"{year}"
    return None


def build_filename(doc_type_config, date_str=None, manual_name=None, lot_number=None):
    """Build the final filename for this doc type.

    - If 'filename_source' is 'lot_number', build 'LOT {number}.pdf'
      from the extracted lot number.
    - If the doc type is 'manual_filename', use whatever title was
      typed in during review (manual_name) instead of auto-building one.
    - Otherwise, build '{Doc Type} {date}.pdf' using this doc type's
      date_format, or just '{Doc Type}.pdf' if it doesn't use a date.
    - Returns None if a required piece (date, manual name, or lot
      number) wasn't provided - the caller should prompt for one in
      that case rather than guessing.
    """
    if doc_type_config.get("filename_source") == "lot_number":
        if not lot_number:
            return None
        return sanitize_filename(f"LOT {lot_number}.pdf")

    if doc_type_config.get("manual_filename"):
        if not manual_name:
            return None
        filename = f"{manual_name}.pdf" if not manual_name.lower().endswith(".pdf") else manual_name
        return sanitize_filename(filename)

    name = doc_type_config["name"]
    date_format = doc_type_config.get("date_format")

    if date_format:
        date_component = _format_date_component(date_format, date_str)
        if date_component is None:
            return None
        filename = f"{name} {date_component}.pdf"
    else:
        filename = f"{name}.pdf"

    return sanitize_filename(filename)


def get_destination_folder(output_root, property_name, doc_type_config):
    base = os.path.join(output_root, sanitize_filename(property_name))
    if doc_type_config.get("subfolder", True):
        return os.path.join(base, sanitize_filename(doc_type_config["name"]))
    return base


def _resolve_output_root(settings):
    output_root = settings["output_root"]
    if not os.path.isabs(output_root):
        output_root = os.path.join(paths.get_base_dir(), output_root)
    return output_root


def file_document(pdf_path, property_name, doc_type_config, settings, date_str=None, manual_name=None, lot_number=None):
    """Move a PDF into the correct community/doctype folder with the
    correctly-built filename. Raises ValueError if the filename can't
    be built (missing date, manual name, or lot number) - the review
    step should catch this and prompt rather than let it crash."""
    output_root = _resolve_output_root(settings)

    destination_folder = get_destination_folder(output_root, property_name, doc_type_config)
    os.makedirs(destination_folder, exist_ok=True)

    filename = build_filename(doc_type_config, date_str=date_str, manual_name=manual_name, lot_number=lot_number)
    if filename is None:
        raise ValueError(
            f"Couldn't build a filename for doc type '{doc_type_config['name']}' - "
            "a date, manual title, or lot number is required but wasn't provided."
        )

    destination_path = make_unique_path(os.path.join(destination_folder, filename))
    shutil.move(pdf_path, destination_path)
    return destination_path


def file_as_unsorted(pdf_path, settings):
    """Move a PDF that couldn't be confidently matched into the fallback
    folder, keeping its original filename (since we don't have reliable
    doc type/date info to build a proper one)."""
    output_root = _resolve_output_root(settings)

    unsorted_folder = os.path.join(output_root, settings["unsorted_folder_name"])
    os.makedirs(unsorted_folder, exist_ok=True)

    original_name = os.path.basename(pdf_path)
    destination_path = make_unique_path(os.path.join(unsorted_folder, original_name))

    shutil.move(pdf_path, destination_path)
    return destination_path


if __name__ == "__main__":
    # Quick manual test:
    #   python src/filer.py downloads/1636_001.pdf "University Hills" "Invoices" "2022-07-01"
    import sys
    import json

    if len(sys.argv) != 5:
        print(
            "Usage: python src/filer.py <pdf_path> <property_name> <doc_type_name> <date (YYYY-MM-DD) or 'none'>"
        )
    else:
        config_dir = os.path.join(paths.get_base_dir(), "config")

        with open(os.path.join(config_dir, "settings.json"), "r") as f:
            settings = json.load(f)
        with open(os.path.join(config_dir, "doc_types.json"), "r") as f:
            doc_types = json.load(f)["doc_types"]

        _, pdf_path, property_name, doc_type_name, date_str = sys.argv
        if date_str.lower() == "none":
            date_str = None

        doc_type_config = next(dt for dt in doc_types if dt["name"] == doc_type_name)

        result_path = file_document(
            pdf_path, property_name, doc_type_config, settings, date_str=date_str
        )
        print(f"Filed to: {result_path}")