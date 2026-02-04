import tkinter as tk

try:
    import pypdf  # noqa: F401
except Exception as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit(
        "Missing dependency 'pypdf'. Install with: pip install -r requirements.txt"
    ) from exc


def main() -> None:
    from pdf_tools.ui.tool_selector import ToolSelectorApp

    root = tk.Tk()
    app = ToolSelectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
