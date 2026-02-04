import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable

from pypdf import PdfReader, PdfWriter


class PdfMergerWindow:
    def __init__(self, parent: tk.Tk, on_close: Callable[[], None]) -> None:
        self.on_close = on_close
        self.window = tk.Toplevel(parent)
        self.window.title("PDF Tools - Merge PDFs")
        self.window.geometry("680x460")
        self.window.minsize(560, 400)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.files: list[str] = []

        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Label(
            self.window,
            text="Select PDFs to merge",
            font=("Helvetica", 14, "bold"),
        )
        header.pack(pady=(14, 6))

        frame = tk.Frame(self.window)
        frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self.listbox = tk.Listbox(frame, selectmode=tk.EXTENDED)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = tk.Scrollbar(frame, command=self.listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scroll.set)

        controls = tk.Frame(self.window)
        controls.pack(fill=tk.X, padx=16, pady=6)

        tk.Button(controls, text="Add PDFs", command=self.add_files).pack(side=tk.LEFT)
        tk.Button(controls, text="Remove Selected", command=self.remove_selected).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(controls, text="Move Up", command=self.move_up).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(controls, text="Move Down", command=self.move_down).pack(
            side=tk.LEFT, padx=6
        )
        tk.Button(controls, text="Clear", command=self.clear_files).pack(
            side=tk.LEFT, padx=6
        )

        actions = tk.Frame(self.window)
        actions.pack(fill=tk.X, padx=16, pady=(4, 10))

        tk.Button(actions, text="Back to Tools", command=self.close).pack(
            side=tk.LEFT
        )
        tk.Button(actions, text="Merge PDFs", command=self.merge_pdfs).pack(side=tk.RIGHT)

        self.status = tk.Label(self.window, text="0 files selected", anchor="w")
        self.status.pack(fill=tk.X, padx=16, pady=(0, 12))

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not paths:
            return

        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.listbox.insert(tk.END, os.path.basename(path))
        self._update_status()

    def remove_selected(self) -> None:
        selection = list(self.listbox.curselection())
        if not selection:
            return

        for index in reversed(selection):
            self.listbox.delete(index)
            self.files.pop(index)
        self._update_status()

    def move_up(self) -> None:
        selection = list(self.listbox.curselection())
        if not selection:
            return

        for index in selection:
            if index == 0:
                continue
            self.files[index - 1], self.files[index] = (
                self.files[index],
                self.files[index - 1],
            )
            label = self.listbox.get(index)
            self.listbox.delete(index)
            self.listbox.insert(index - 1, label)
            self.listbox.selection_set(index - 1)
        self._update_status()

    def move_down(self) -> None:
        selection = list(self.listbox.curselection())
        if not selection:
            return

        for index in reversed(selection):
            if index == len(self.files) - 1:
                continue
            self.files[index + 1], self.files[index] = (
                self.files[index],
                self.files[index + 1],
            )
            label = self.listbox.get(index)
            self.listbox.delete(index)
            self.listbox.insert(index + 1, label)
            self.listbox.selection_set(index + 1)
        self._update_status()

    def clear_files(self) -> None:
        self.files.clear()
        self.listbox.delete(0, tk.END)
        self._update_status()

    def merge_pdfs(self) -> None:
        if len(self.files) < 2:
            messagebox.showwarning("Need at least 2 files", "Add two or more PDFs.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Save merged PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="merged.pdf",
        )
        if not output_path:
            return

        writer = PdfWriter()
        try:
            for path in self.files:
                reader = PdfReader(path)
                for page in reader.pages:
                    writer.add_page(page)

            with open(output_path, "wb") as handle:
                writer.write(handle)
        except Exception as exc:
            messagebox.showerror("Merge failed", f"Error: {exc}")
            return

        messagebox.showinfo(
            "Merge complete", f"Saved merged PDF to:\n{output_path}"
        )

    def _update_status(self) -> None:
        count = len(self.files)
        suffix = "file" if count == 1 else "files"
        self.status.config(text=f"{count} {suffix} selected")

    def close(self) -> None:
        self.window.destroy()
        self.on_close()
