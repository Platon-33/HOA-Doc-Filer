"""
config_editor.py

Lets the review window add new properties or document types on the fly
and save them back to the JSON config files - so "this is a new HOA
client" or "I need a new document category" doesn't require manually
editing a file, but the result is remembered permanently either way.
"""

import json
import os

import paths


def _load(filename):
    path = os.path.join(paths.get_base_dir(), "config", filename)
    with open(path, "r") as f:
        return json.load(f), path


def _save(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def add_property(name, aliases=None):
    """Add a new property to properties.json (skips it if a property
    with this name already exists) and return the updated list."""
    data, path = _load("properties.json")
    existing_names = [p["name"].lower() for p in data["properties"]]

    if name.lower() not in existing_names:
        data["properties"].append({
            "name": name,
            "aliases": aliases or [],
        })
        _save(data, path)

    return data["properties"]


def add_doc_type(name, keywords=None, date_format=None, subfolder=True, manual_filename=True):
    """Add a new document type to doc_types.json (skips it if one with
    this name already exists) and return the updated list. Defaults to
    the safest option: no auto-date, its own subfolder, and a manually
    typed filename each time - you can tune this later by editing
    doc_types.json directly if a type turns out to need a date pattern."""
    data, path = _load("doc_types.json")
    existing_names = [d["name"].lower() for d in data["doc_types"]]

    if name.lower() not in existing_names:
        new_entry = {
            "name": name,
            "keywords": keywords or [],
            "date_format": date_format,
            "subfolder": subfolder,
        }
        if manual_filename:
            new_entry["manual_filename"] = True
        data["doc_types"].append(new_entry)
        _save(data, path)

    return data["doc_types"]