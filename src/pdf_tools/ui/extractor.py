import os
import platform
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from pdf_tools.extraction.engine import ExtractionOptions, extract_transactions, write_csv
from pdf_tools.extraction.schema import TRANSACTION_FIELDS


class PdfExtractorWindow:
    def __init__(self, parent: tk.Tk, on_close: Callable[[], None]) -> None:
        self.on_close = on_close
        self.window = tk.Toplevel(parent)
        self.window.title("PDF Tools - Extract Data")
        self.window.geometry("980x620")
        self.window.minsize(820, 520)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.input_paths: list[str] = []
        self.extracted_rows: list[dict[str, str]] = []
        self._edit_entry: tk.Entry | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Label(
            self.window,
            text="Extract transaction data from PDF statements",
            font=("Helvetica", 14, "bold"),
        )
        header.pack(pady=(12, 6))

        controls = tk.Frame(self.window)
        controls.pack(fill=tk.X, padx=16, pady=6)

        tk.Label(controls, text="Source PDFs:", width=12, anchor="w").pack(
            side=tk.LEFT
        )
        self.input_label = tk.Label(controls, text="No files selected", anchor="w")
        self.input_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(controls, text="Choose PDFs", command=self.select_pdfs).pack(
            side=tk.RIGHT
        )

        options = tk.Frame(self.window)
        options.pack(fill=tk.X, padx=16, pady=(4, 6))

        self.use_pdfplumber = tk.BooleanVar(value=True)
        self.use_camelot = tk.BooleanVar(value=True)
        self.use_tesseract = tk.BooleanVar(value=True)
        self.use_ollama = tk.BooleanVar(value=True)
        self.use_glm_ocr_sdk = tk.BooleanVar(value=False)

        pdfplumber_row = tk.Frame(options)
        pdfplumber_row.pack(fill=tk.X)
        self.pdfplumber_check = tk.Checkbutton(
            pdfplumber_row,
            text="Use PDF table extraction (pdfplumber)",
            variable=self.use_pdfplumber,
        )
        self.pdfplumber_check.pack(side=tk.LEFT, anchor="w")
        self.pdfplumber_status = tk.Label(pdfplumber_row, text="Unknown", width=10, anchor="w")
        self.pdfplumber_status.pack(side=tk.LEFT, padx=8)

        camelot_row = tk.Frame(options)
        camelot_row.pack(fill=tk.X)
        self.camelot_check = tk.Checkbutton(
            camelot_row,
            text="Use table extraction fallback (camelot)",
            variable=self.use_camelot,
        )
        self.camelot_check.pack(side=tk.LEFT, anchor="w")
        self.camelot_status = tk.Label(camelot_row, text="Unknown", width=10, anchor="w")
        self.camelot_status.pack(side=tk.LEFT, padx=8)

        camelot_flavor_row = tk.Frame(options)
        camelot_flavor_row.pack(fill=tk.X)
        tk.Label(camelot_flavor_row, text="Camelot flavor:", width=16, anchor="w").pack(
            side=tk.LEFT
        )
        self.camelot_flavor = tk.StringVar(value="lattice")
        ttk.Combobox(
            camelot_flavor_row,
            textvariable=self.camelot_flavor,
            values=["lattice", "stream"],
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT)

        tesseract_row = tk.Frame(options)
        tesseract_row.pack(fill=tk.X)
        self.tesseract_check = tk.Checkbutton(
            tesseract_row,
            text="Use OCR fallback (Tesseract)",
            variable=self.use_tesseract,
        )
        self.tesseract_check.pack(side=tk.LEFT, anchor="w")
        self.tesseract_status = tk.Label(tesseract_row, text="Unknown", width=10, anchor="w")
        self.tesseract_status.pack(side=tk.LEFT, padx=8)

        ocr_row = tk.Frame(options)
        ocr_row.pack(fill=tk.X)
        tk.Label(ocr_row, text="OCR language:", width=16, anchor="w").pack(
            side=tk.LEFT
        )
        self.ocr_lang = tk.StringVar(value="eng+fra")
        tk.Entry(ocr_row, textvariable=self.ocr_lang, width=16).pack(side=tk.LEFT)
        tk.Label(ocr_row, text="PSM:", padx=8).pack(side=tk.LEFT)
        self.ocr_psm = tk.StringVar(value="6")
        tk.Entry(ocr_row, textvariable=self.ocr_psm, width=4).pack(side=tk.LEFT)

        ollama_row = tk.Frame(options)
        ollama_row.pack(fill=tk.X)
        self.ollama_check = tk.Checkbutton(
            ollama_row,
            text="Use AI OCR fallback (Ollama glm-ocr)",
            variable=self.use_ollama,
        )
        self.ollama_check.pack(side=tk.LEFT, anchor="w")
        self.ollama_status = tk.Label(ollama_row, text="Unknown", width=10, anchor="w")
        self.ollama_status.pack(side=tk.LEFT, padx=8)

        glm_row = tk.Frame(options)
        glm_row.pack(fill=tk.X)
        self.glm_check = tk.Checkbutton(
            glm_row,
            text="Use GLM-OCR SDK (glmocr CLI)",
            variable=self.use_glm_ocr_sdk,
        )
        self.glm_check.pack(side=tk.LEFT, anchor="w")
        self.glm_status = tk.Label(glm_row, text="Unknown", width=10, anchor="w")
        self.glm_status.pack(side=tk.LEFT, padx=8)

        action_row = tk.Frame(self.window)
        action_row.pack(fill=tk.X, padx=16, pady=(4, 6))
        self.extract_button = tk.Button(
            action_row, text="Extract Data", command=self.extract_data, state=tk.DISABLED
        )
        self.extract_button.pack(side=tk.LEFT)
        self.export_button = tk.Button(
            action_row, text="Export CSV", command=self.export_csv, state=tk.DISABLED
        )
        self.export_button.pack(side=tk.LEFT, padx=8)
        tk.Button(action_row, text="Dependencies Help", command=self.show_dependency_help).pack(
            side=tk.LEFT
        )
        tk.Button(action_row, text="Recheck Dependencies", command=self.refresh_dependency_status).pack(
            side=tk.LEFT, padx=8
        )
        tk.Button(action_row, text="Back to Tools", command=self.close).pack(
            side=tk.RIGHT
        )

        table_frame = tk.Frame(self.window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 10))

        self.tree = ttk.Treeview(
            table_frame,
            columns=TRANSACTION_FIELDS,
            show="headings",
            selectmode="browse",
        )
        for field in TRANSACTION_FIELDS:
            self.tree.heading(field, text=field)
            self.tree.column(field, width=120, anchor="w")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.start_edit)

        self.status = tk.Label(self.window, text="Ready", anchor="w")
        self.status.pack(fill=tk.X, padx=16, pady=(0, 12))

        self.refresh_dependency_status()

    def select_pdfs(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not paths:
            return
        self.input_paths = list(paths)
        if len(self.input_paths) == 1:
            label = os.path.basename(self.input_paths[0])
        else:
            label = f"{len(self.input_paths)} files selected"
        self.input_label.config(text=label)
        self.status.config(text="PDFs selected")
        self.extract_button.config(state=tk.NORMAL)

    def extract_data(self) -> None:
        if not self.input_paths:
            messagebox.showwarning(
                "Select PDFs", "Choose one or more PDFs to extract from."
            )
            return

        missing = self.check_missing_dependencies()
        if missing:
            messagebox.showwarning(
                "Missing OCR Tools",
                "Some OCR/table tools are missing:\n"
                + "\n".join(f"- {name}" for name in missing)
                + "\n\nYou can still continue, but OCR/table fallbacks may be limited.",
            )

        options = ExtractionOptions(
            use_pdfplumber=self.use_pdfplumber.get(),
            use_camelot=self.use_camelot.get(),
            use_tesseract=self.use_tesseract.get(),
            use_ollama=self.use_ollama.get(),
            use_glm_ocr_sdk=self.use_glm_ocr_sdk.get(),
            tesseract_lang=self.ocr_lang.get().strip() or "eng+fra",
            tesseract_psm=self.ocr_psm.get().strip() or "6",
            camelot_primary_flavor=self.camelot_flavor.get(),
        )

        try:
            rows, notes = extract_transactions(
                self.input_paths,
                output_dir="",
                combined_csv_path=None,
                options=options,
            )
        except Exception as exc:
            messagebox.showerror("Extraction failed", f"Error: {exc}")
            return

        self.extracted_rows = rows
        self.populate_table(rows)
        self.export_button.config(state=tk.NORMAL if rows else tk.DISABLED)

        summary = f"Extracted {len(rows)} rows."
        if notes:
            summary += "\n\n" + "\n".join(notes)
        self.status.config(text="Extraction complete")
        messagebox.showinfo("Extraction complete", summary)

    def check_missing_dependencies(self) -> list[str]:
        missing: list[str] = []
        if self.use_tesseract.get() and not shutil.which("tesseract"):
            missing.append("tesseract (OCR)")
        if (self.use_tesseract.get() or self.use_camelot.get()) and not shutil.which("pdftoppm"):
            missing.append("poppler (pdftoppm)")
        if self.use_camelot.get() and not shutil.which("gs"):
            missing.append("ghostscript (gs)")
        if self.use_glm_ocr_sdk.get() and not shutil.which("glmocr"):
            missing.append("glmocr (GLM-OCR SDK CLI)")
        return missing

    def refresh_dependency_status(self) -> None:
        def set_status(label: tk.Label, ok: bool) -> None:
            label.config(text="OK" if ok else "Missing", fg="#0b6623" if ok else "#a12a2a")

        pdfplumber_ok = True
        camelot_ok = shutil.which("gs") is not None and shutil.which("pdftoppm") is not None
        tesseract_ok = shutil.which("tesseract") is not None
        ollama_ok = True
        glm_ok = shutil.which("glmocr") is not None

        set_status(self.pdfplumber_status, pdfplumber_ok)
        set_status(self.camelot_status, camelot_ok)
        set_status(self.tesseract_status, tesseract_ok)
        set_status(self.ollama_status, ollama_ok)
        set_status(self.glm_status, glm_ok)

        self.pdfplumber_check.config(state=tk.NORMAL if pdfplumber_ok else tk.DISABLED)
        self.camelot_check.config(state=tk.NORMAL if camelot_ok else tk.DISABLED)
        self.tesseract_check.config(state=tk.NORMAL if tesseract_ok else tk.DISABLED)
        self.ollama_check.config(state=tk.NORMAL if ollama_ok else tk.DISABLED)
        self.glm_check.config(state=tk.NORMAL if glm_ok else tk.DISABLED)

        if not camelot_ok:
            self.use_camelot.set(False)
        if not tesseract_ok:
            self.use_tesseract.set(False)
        if not glm_ok:
            self.use_glm_ocr_sdk.set(False)

    def show_dependency_help(self) -> None:
        system = platform.system().lower()
        instructions = [
            "Required system tools for OCR/table extraction:",
            "1. Tesseract OCR: required for pytesseract OCR fallback.",
            "2. Poppler (pdftoppm): required for pdf2image conversions.",
            "3. Ghostscript (gs): required for Camelot lattice mode.",
            "4. GLM-OCR SDK CLI (glmocr): optional advanced OCR backend.",
            "",
        ]
        if "linux" in system:
            instructions += [
                "Linux install (Ubuntu/Debian):",
                "1. sudo apt-get update",
                "2. sudo apt-get install -y tesseract-ocr poppler-utils ghostscript",
            ]
        elif "windows" in system:
            instructions += [
                "Windows install:",
                "1. Install Tesseract OCR and add it to PATH.",
                "2. Install Poppler and add the bin folder to PATH.",
                "3. Install Ghostscript and add it to PATH.",
            ]
        elif "darwin" in system:
            instructions += [
                "macOS install (Homebrew):",
                "1. brew install tesseract poppler ghostscript",
            ]
        else:
            instructions += [
                "Install the tools for your OS and ensure they are on PATH.",
            ]

        instructions += [
            "",
            "GLM-OCR SDK setup:",
            "1. Clone https://github.com/zai-org/GLM-OCR",
            "2. pip install -r requirements.txt",
            "3. pip install -e .",
            "4. Ensure `glmocr` is on PATH.",
        ]

        messagebox.showinfo("Dependency Setup", "\n".join(instructions))

    def populate_table(self, rows: list[dict[str, str]]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            values = [row.get(field, "") for field in TRANSACTION_FIELDS]
            self.tree.insert("", tk.END, values=values)

    def export_csv(self) -> None:
        if not self.extracted_rows:
            messagebox.showwarning("No data", "Run extraction before exporting.")
            return
        path = filedialog.asksaveasfilename(
            title="Save CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="transactions.csv",
        )
        if not path:
            return
        rows = self.collect_rows_from_table()
        try:
            write_csv(path, rows)
        except Exception as exc:
            messagebox.showerror("Export failed", f"Error: {exc}")
            return
        self.status.config(text=f"Saved CSV to {os.path.basename(path)}")
        messagebox.showinfo("Export complete", f"Saved CSV to:\n{path}")

    def collect_rows_from_table(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")
            row = {field: values[index] if index < len(values) else "" for index, field in enumerate(TRANSACTION_FIELDS)}
            rows.append(row)
        return rows

    def start_edit(self, event: tk.Event) -> None:
        if self._edit_entry is not None:
            self._edit_entry.destroy()
            self._edit_entry = None

        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        if not row_id or not column_id:
            return
        column_index = int(column_id.replace("#", "")) - 1
        if column_index < 0:
            return

        bbox = self.tree.bbox(row_id, column_id)
        if not bbox:
            return
        x, y, width, height = bbox
        value = self.tree.set(row_id, column=column_id)

        entry = tk.Entry(self.tree)
        entry.insert(0, value)
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus()

        def save_edit(_: tk.Event | None = None) -> None:
            self.tree.set(row_id, column=column_id, value=entry.get())
            entry.destroy()
            self._edit_entry = None

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        self._edit_entry = entry

    def close(self) -> None:
        self.window.destroy()
        self.on_close()
