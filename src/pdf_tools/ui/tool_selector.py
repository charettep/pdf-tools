import tkinter as tk

from pdf_tools.ui.extractor import PdfExtractorWindow
from pdf_tools.ui.merger import PdfMergerWindow


class ToolSelectorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF Tools")
        self.root.geometry("520x360")
        self.root.minsize(480, 320)

        self.merger_window: PdfMergerWindow | None = None
        self.extractor_window: PdfExtractorWindow | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Label(
            self.root,
            text="PDF Tools",
            font=("Helvetica", 16, "bold"),
        )
        header.pack(pady=(18, 6))

        subtitle = tk.Label(
            self.root,
            text="Choose a tool to get started.",
            font=("Helvetica", 11),
        )
        subtitle.pack(pady=(0, 18))

        buttons = tk.Frame(self.root)
        buttons.pack(pady=6)

        tk.Button(
            buttons,
            text="Merge PDFs",
            width=22,
            height=2,
            command=self.open_merger,
        ).pack(pady=6)

        tk.Button(
            buttons,
            text="Extract data from PDFs",
            width=22,
            height=2,
            command=self.open_extractor,
        ).pack(pady=6)

        footer = tk.Label(
            self.root,
            text="Version 1.1.0",
            font=("Helvetica", 9),
            anchor="center",
        )
        footer.pack(side=tk.BOTTOM, pady=(0, 12))

    def open_merger(self) -> None:
        self.root.withdraw()
        if self.merger_window is None or not self._window_exists(self.merger_window.window):
            self.merger_window = PdfMergerWindow(self.root, self.show_main)
        else:
            self.merger_window.window.deiconify()
            self.merger_window.window.lift()

    def open_extractor(self) -> None:
        self.root.withdraw()
        if self.extractor_window is None or not self._window_exists(
            self.extractor_window.window
        ):
            self.extractor_window = PdfExtractorWindow(self.root, self.show_main)
        else:
            self.extractor_window.window.deiconify()
            self.extractor_window.window.lift()

    def show_main(self) -> None:
        self.root.deiconify()
        self.root.lift()

    @staticmethod
    def _window_exists(window: tk.Toplevel) -> bool:
        try:
            return bool(window.winfo_exists())
        except tk.TclError:
            return False
