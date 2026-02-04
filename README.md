# Minimal PDF Merger

A tiny, minimalist GUI tool to select multiple PDF files and merge them into a single PDF.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## User Guide

1. Click `Add PDFs` to select two or more PDF files.
2. Reorder the list with `Move Up` / `Move Down` to control the merge order.
3. Use `Remove Selected` or `Clear` to adjust the list.
4. Click `Merge PDFs`, choose a save location, and confirm to write the merged file.

Notes:
- The app will prompt if fewer than two PDFs are selected.
- The status bar shows how many files are currently selected.

## Build a Standalone App

This uses PyInstaller to create a single-file executable in `dist/`.

## Repo Structure

- Build scripts live in `scripts/` with OS-specific subfolders.
- Shared build metadata lives in `build/metadata.json`.
- Windows installer script lives at `scripts/windows/installer.iss`.

## Scripts

- `scripts/linux/build-linux.sh`: Build the Linux standalone executable (PyInstaller).
- `scripts/windows/build-win.ps1`: Build the Windows standalone `.exe` and the Inno Setup installer.
- `scripts/validate-metadata.py`: Validate required fields in `build/metadata.json`.

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
./scripts/linux/build-linux.sh
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\windows\build-win.ps1
```

This creates `dist\pdf-tools.exe` and `dist\pdf-tools-setup.exe`.
Ensure Inno Setup is installed and `ISCC.exe` is on PATH.

## Notes

- The merge order matches the list order in the UI.
- Use Move Up / Move Down to reorder before merging.
