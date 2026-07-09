import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

import paths


def collect_sorted_entries(root_path, recursive=True):
    if not os.path.isdir(root_path):
        return []

    entries = []
    if recursive:
        for current_root, dir_names, file_names in os.walk(root_path):
            dir_names.sort(key=str.lower)
            file_names.sort(key=str.lower)
            for name in dir_names + file_names:
                full_path = os.path.join(current_root, name)
                entries.append({
                    "name": name,
                    "path": full_path,
                    "is_dir": os.path.isdir(full_path),
                })
        return entries

    for child in sorted(os.scandir(root_path), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
        entries.append({
            "name": child.name,
            "path": child.path,
            "is_dir": child.is_dir(),
        })
    return entries


class SortedBrowserPanel:
    def __init__(self, parent, root_dir=None, close_callback=None):
        self.parent = parent
        self.root_dir = root_dir or os.path.join(paths.get_base_dir(), "sorted")
        self.close_callback = close_callback
        self.frame = ttk.Frame(parent, padding=12)

        self._build_ui()
        self._refresh_tree()

    def _build_ui(self):
        main = ttk.Frame(self.frame)
        main.pack(fill="both", expand=True)

        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Refresh", command=self._refresh_tree).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Open This Folder", command=self._open_current_folder).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Open Selected Folder", command=self._open_selected_folder).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Move Selected Folder", command=self._move_selected_folder).pack(side="left", padx=(0, 6))
        if self.close_callback is not None:
            ttk.Button(toolbar, text="Close", command=self.close_callback).pack(side="right")

        self.path_var = tk.StringVar(value=self.root_dir)
        ttk.Entry(main, textvariable=self.path_var, state="readonly").pack(fill="x", pady=(0, 8))

        self.tree = ttk.Treeview(main, columns=("type", "path"), show="tree headings")
        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("path", text="Path")
        self.tree.column("#0", width=280, anchor="w")
        self.tree.column("type", width=120, anchor="w")
        self.tree.column("path", width=480, anchor="w")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<<TreeviewOpen>>", self._on_expand)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.path_var.set(self.root_dir)

        if not os.path.isdir(self.root_dir):
            messagebox.showwarning("Missing folder", f"The sorted folder was not found at:\n{self.root_dir}", parent=self.frame.winfo_toplevel())
            return

        self._populate_tree(self.tree, "", self.root_dir)

    def _populate_tree(self, tree, parent_id, directory):
        for entry in collect_sorted_entries(directory, recursive=False):
            node_id = tree.insert(parent_id, "end", text=entry["name"], values=("Folder" if entry["is_dir"] else "File", entry["path"]))
            if entry["is_dir"]:
                tree.insert(node_id, "end", text="", values=("", ""))

    def _on_expand(self, event=None):
        item_id = self.tree.focus()
        if not item_id:
            return

        path = self.tree.item(item_id, "values")[1]
        if not path or not os.path.isdir(path):
            return

        children = self.tree.get_children(item_id)
        if not children:
            return

        first_child = children[0]
        if self.tree.item(first_child, "text") == "":
            self.tree.delete(*children)
            self._populate_tree(self.tree, item_id, path)

    def _on_double_click(self, event=None):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        path = self.tree.item(item_id, "values")[1]
        if not path:
            return
        if os.path.isdir(path):
            self._open_folder(path)

    def _open_current_folder(self):
        self._open_folder(self.root_dir)

    def _open_selected_folder(self):
        item_id = self.tree.focus()
        if not item_id:
            return

        path = self.tree.item(item_id, "values")[1]
        if path and os.path.isdir(path):
            self._open_folder(path)
        elif path:
            self._open_folder(os.path.dirname(path))

    def _move_selected_folder(self):
        item_id = self.tree.focus()
        if not item_id:
            messagebox.showwarning("Nothing selected", "Select a folder first.", parent=self.frame.winfo_toplevel())
            return

        path = self.tree.item(item_id, "values")[1]
        if not path or not os.path.isdir(path):
            messagebox.showwarning("Not a folder", "Select a folder to move.", parent=self.frame.winfo_toplevel())
            return

        destination = filedialog.askdirectory(
            title="Choose destination folder",
            initialdir=self.root_dir,
            parent=self.frame.winfo_toplevel(),
        )
        if not destination:
            return

        if os.path.abspath(path) == os.path.abspath(destination):
            messagebox.showwarning("Same location", "Choose a different destination folder.", parent=self.frame.winfo_toplevel())
            return

        try:
            destination_path = os.path.join(destination, os.path.basename(path))
            if os.path.exists(destination_path):
                raise FileExistsError(f"A folder named '{os.path.basename(path)}' already exists in the destination.")
            shutil.move(path, destination_path)
            self._refresh_tree()
            messagebox.showinfo("Move complete", f"Moved:\n{path}\n\nTo:\n{destination_path}", parent=self.frame.winfo_toplevel())
        except Exception as exc:
            messagebox.showerror("Move failed", str(exc), parent=self.frame.winfo_toplevel())

    def _open_folder(self, path):
        if not os.path.exists(path):
            messagebox.showwarning("Missing folder", f"This path no longer exists:\n{path}", parent=self.frame.winfo_toplevel())
            return

        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    panel = SortedBrowserPanel(root)
    panel.frame.pack(fill="both", expand=True)
    root.mainloop()
