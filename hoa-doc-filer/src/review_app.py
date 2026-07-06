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


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


class ReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HOA Doc Filer - Review")
        self.root.geometry("700x520")

        project_root = os.path.join(os.path.dirname(__file__), "..")
        config_dir = os.path.join(project_root, "config")

        self.settings = load_json(os.path.join(config_dir, "settings.json"))
        self.properties = load_json(os.path.join(config_dir, "properties.json"))["properties"]
        self.doc_types = load_json(os.path.join(config_dir, "doc_types.json"))["doc_types"]

        self.download_dir = os.path.join(project_root, self.settings["download_folder"])
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
            main, textvariable=self.property_var, values=self.property_names,
            width=38, state="readonly"
        )
        self.property_combo.grid(row=3, column=1, sticky="w", pady=(0, 12))

        ttk.Label(main, text="Document Type:").grid(row=4, column=1, sticky="w")
        self.doc_type_var = tk.StringVar()
        self.doc_type_combo = ttk.Combobox(
            main, textvariable=self.doc_type_var, values=self.doc_type_names,
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

    def _on_doc_type_change(self, event=None):
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
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
            doc.close()
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            image.thumbnail((320, 440))
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