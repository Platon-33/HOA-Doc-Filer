"""
review_app.py

The one-click review window. Shows each PDF sitting in your downloads
folder one at a time, with a preview image and the OCR-suggested
property/doc type/date pre-filled. Confirm or correct, then click
"File It" to actually rename and move the PDF - or "Send to Needs
Review" if you'd rather deal with it manually later.

Run with: python src/review_app.py
"""

import os
import io
import glob
import json
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import fitz

import pdf_matcher
import filer
import paths
import config_editor

ADD_NEW_PROPERTY = "+ Add New Property..."
ADD_NEW_DOC_TYPE = "+ Add New Document Type..."


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


class ReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HOA Doc Filer - Review")
        self.root.geometry("1100x820")
        self.root.minsize(1000, 750)

        base_dir = paths.get_base_dir()
        config_dir = os.path.join(base_dir, "config")

        self.settings = load_json(os.path.join(config_dir, "settings.json"))
        self.properties = load_json(os.path.join(config_dir, "properties.json"))["properties"]
        self.doc_types = load_json(os.path.join(config_dir, "doc_types.json"))["doc_types"]

        self.download_dir = os.path.join(base_dir, self.settings["download_folder"])
        self.pdf_queue = sorted(glob.glob(os.path.join(self.download_dir, "*.pdf")))
        self.queue_index = 0

        self.property_names = [p["name"] for p in self.properties]
        self.doc_type_names = [d["name"] for d in self.doc_types]

        self._build_ui()
        self._load_current_pdf()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=15)
        main.pack(fill="both", expand=True)

        # Left side: page preview image
        self.preview_label = ttk.Label(main)
        self.preview_label.grid(row=0, column=0, rowspan=10, padx=(0, 20), sticky="n")

        # Right side: filename + controls
        ttk.Label(main, text="File:", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w")
        self.filename_label = ttk.Label(main, text="", wraplength=280)
        self.filename_label.grid(row=1, column=1, sticky="w", pady=(0, 15))

        ttk.Label(main, text="Property:").grid(row=2, column=1, sticky="w")
        self.property_var = tk.StringVar()
        self.property_combo = ttk.Combobox(
            main, textvariable=self.property_var, values=self.property_names + [ADD_NEW_PROPERTY],
            width=38, state="readonly"
        )
        self.property_combo.grid(row=3, column=1, sticky="w", pady=(0, 12))
        self.property_combo.bind("<<ComboboxSelected>>", self._on_property_change)

        ttk.Label(main, text="Document Type:").grid(row=4, column=1, sticky="w")
        self.doc_type_var = tk.StringVar()
        self.doc_type_combo = ttk.Combobox(
            main, textvariable=self.doc_type_var, values=self.doc_type_names + [ADD_NEW_DOC_TYPE],
            width=38, state="readonly"
        )
        self.doc_type_combo.grid(row=5, column=1, sticky="w", pady=(0, 12))
        self.doc_type_combo.bind("<<ComboboxSelected>>", self._on_doc_type_change)

        # Date field (shown only when the doc type needs one)
        self.date_label = ttk.Label(main, text="Date (YYYY-MM-DD):")
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(main, textvariable=self.date_var, width=40)

        # Manual title field (shown only when the doc type needs one)
        self.manual_label = ttk.Label(main, text="Exact document title:")
        self.manual_var = tk.StringVar()
        self.manual_entry = ttk.Entry(main, textvariable=self.manual_var, width=40)

        # Buttons
        button_frame = ttk.Frame(main)
        button_frame.grid(row=9, column=1, sticky="w", pady=(20, 0))

        ttk.Button(button_frame, text="File It", command=self._on_file_it).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="Send to Needs Review", command=self._on_needs_review).pack(side="left")

        self.status_label = ttk.Label(main, text="", foreground="gray")
        self.status_label.grid(row=10, column=1, sticky="w", pady=(15, 0))

    def _on_property_change(self, event=None):
        if self.property_var.get() == ADD_NEW_PROPERTY:
            self._prompt_add_property()

    def _prompt_add_property(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Property")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Property (folder) name:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=40).grid(row=1, column=0, padx=10, pady=(0, 10))

        ttk.Label(dialog, text="Aliases (comma-separated, optional):").grid(row=2, column=0, sticky="w", padx=10)
        aliases_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=aliases_var, width=40).grid(row=3, column=0, padx=10, pady=(0, 10))

        def on_save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Missing name", "Please enter a property name.", parent=dialog)
                return
            aliases = [a.strip() for a in aliases_var.get().split(",") if a.strip()]
            self.properties = config_editor.add_property(name, aliases)
            self.property_names = [p["name"] for p in self.properties]
            self.property_combo["values"] = self.property_names + [ADD_NEW_PROPERTY]
            self.property_var.set(name)
            dialog.destroy()

        def on_cancel():
            self.property_var.set("")
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=4, column=0, pady=(0, 10))
        ttk.Button(button_frame, text="Save", command=on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side="left")
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    def _prompt_add_doc_type(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Document Type")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Document type name:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=40).grid(row=1, column=0, padx=10, pady=(0, 10))

        ttk.Label(dialog, text="Keywords to auto-detect this type (comma-separated, optional):").grid(row=2, column=0, sticky="w", padx=10)
        keywords_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=keywords_var, width=40).grid(row=3, column=0, padx=10, pady=(0, 10))

        note = ("New types default to: no auto-date, own subfolder, and you'll\n"
                "type the exact filename each time (safest default). You can\n"
                "fine-tune this later by editing config/doc_types.json.")
        ttk.Label(dialog, text=note, foreground="gray").grid(row=4, column=0, sticky="w", padx=10, pady=(0, 10))

        def on_save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Missing name", "Please enter a document type name.", parent=dialog)
                return
            keywords = [k.strip() for k in keywords_var.get().split(",") if k.strip()]
            self.doc_types = config_editor.add_doc_type(name, keywords)
            self.doc_type_names = [d["name"] for d in self.doc_types]
            self.doc_type_combo["values"] = self.doc_type_names + [ADD_NEW_DOC_TYPE]
            self.doc_type_var.set(name)
            dialog.destroy()
            self._on_doc_type_change()

        def on_cancel():
            self.doc_type_var.set("")
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=5, column=0, pady=(0, 10))
        ttk.Button(button_frame, text="Save", command=on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side="left")
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    def _on_doc_type_change(self, event=None):
        if self.doc_type_var.get() == ADD_NEW_DOC_TYPE:
            self._prompt_add_doc_type()
            return

        doc_type_config = self._get_doc_type_config(self.doc_type_var.get())
        needs_date = bool(doc_type_config and doc_type_config.get("date_format"))
        needs_manual = bool(doc_type_config and doc_type_config.get("manual_filename"))

        if needs_date:
            self.date_label.grid(row=6, column=1, sticky="w")
            self.date_entry.grid(row=7, column=1, sticky="w", pady=(0, 12))
        else:
            self.date_label.grid_remove()
            self.date_entry.grid_remove()

        if needs_manual:
            self.manual_label.grid(row=6, column=1, sticky="w")
            self.manual_entry.grid(row=7, column=1, sticky="w", pady=(0, 12))
        else:
            self.manual_label.grid_remove()
            self.manual_entry.grid_remove()

    def _get_doc_type_config(self, name):
        for d in self.doc_types:
            if d.get("name") == name:
                return d
        return None

    def _load_current_pdf(self):
        if self.queue_index >= len(self.pdf_queue):
            self.preview_label.config(image="", text="")
            self.filename_label.config(text="")
            self.property_var.set("")
            self.doc_type_var.set("")
            self.status_label.config(text="All done! No more PDFs to review.")
            messagebox.showinfo("Done", "All PDFs in the downloads folder have been reviewed.")
            return

        pdf_path = self.pdf_queue[self.queue_index]
        self.current_pdf_path = pdf_path
        self.filename_label.config(text=os.path.basename(pdf_path))
        self.status_label.config(text=f"Reviewing {self.queue_index + 1} of {len(self.pdf_queue)}")

        # Render a page 1 thumbnail so you can actually see the document
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
            doc.close()
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            image.thumbnail((600, 700))
            self.preview_image = ImageTk.PhotoImage(image)  # kept as attribute - Tkinter needs the reference to persist
            self.preview_label.config(image=self.preview_image, text="")
        except Exception as e:
            self.preview_label.config(image="", text=f"(preview unavailable)\n{e}")

        # Get the OCR-based suggestion
        try:
            result = pdf_matcher.suggest(pdf_path)
        except Exception as e:
            result = {"suggested_property": None, "suggested_doc_type": None, "suggested_date": None}
            messagebox.showwarning("Couldn't read this PDF", f"OCR/text extraction failed:\n{e}")

        self.property_var.set(result.get("suggested_property") or "")
        self.doc_type_var.set(result.get("suggested_doc_type") or "")
        self.date_var.set(result.get("suggested_date") or "")
        self.manual_var.set("")

        self._on_doc_type_change()

    def _on_file_it(self):
        property_name = self.property_var.get()
        doc_type_name = self.doc_type_var.get()

        if not property_name or not doc_type_name:
            messagebox.showerror("Missing info", "Please select both a property and a document type.")
            return

        doc_type_config = self._get_doc_type_config(doc_type_name)

        try:
            result_path = filer.file_document(
                self.current_pdf_path,
                property_name,
                doc_type_config,
                self.settings,
                date_str=self.date_var.get().strip() or None,
                manual_name=self.manual_var.get().strip() or None,
            )
        except ValueError as e:
            messagebox.showerror("Can't file yet", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Something went wrong:\n{e}")
            return

        self.queue_index += 1
        self._load_current_pdf()

    def _on_needs_review(self):
        try:
            filer.file_as_unsorted(self.current_pdf_path, self.settings)
        except Exception as e:
            messagebox.showerror("Error", f"Couldn't move file:\n{e}")
            return
        self.queue_index += 1
        self._load_current_pdf()


if __name__ == "__main__":
    root = tk.Tk()
    app = ReviewApp(root)
    root.mainloop()