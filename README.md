# PDF Tools

A minimalist GUI toolkit for common PDF workflows like merging and text extraction.

## Quick Start

### Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
python -m pdf_tools
```

### Windows
```powershell
python -m venv .venv
.\scripts\windows\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
python -m pdf_tools
```

## Install & Run (Linux)

### Prerequisites
1. Python 3.10+ installed and on PATH.
2. `pip` available (comes with most Python installs).
3. OCR + PDF tools (recommended for extraction):
   - `tesseract-ocr`
   - `poppler-utils`
   - `ghostscript`

Example (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils ghostscript
```

### Create and Activate a Virtualenv
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
```

### Run
```bash
python -m pdf_tools
```
You can also run `python app.py` for backwards compatibility.

## Install & Run (Windows)

### Prerequisites
1. Python 3.10+ installed and on PATH.
2. PowerShell (built-in on Windows).
3. OCR + PDF tools (recommended for extraction):
   - Tesseract OCR
   - Poppler
   - Ghostscript (required for Camelot)

### Create and Activate a Virtualenv
```powershell
python -m venv .venv
.\scripts\windows\Activate.ps1
```
If script execution is blocked, run:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Install Dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
```

### Run
```powershell
python -m pdf_tools
```
You can also run `python app.py` for backwards compatibility.

## Standalone Builds

### Linux
```bash
./scripts/linux/build-linux.sh
```
Outputs `dist/pdf-tools`.

### Windows
```powershell
.\scripts\windows\build-win.ps1
```
Outputs `dist\pdf-tools.exe` and `dist\pdf-tools-setup.exe`.
Requires Inno Setup (`ISCC.exe`) on PATH for the installer build.

## User Guide

1. Launch the app to see the tool selector window.
2. Choose `Merge PDFs` or `Extract data from PDFs`.
3. Use the tool window's `Back to Tools` button to return to the selector.

### Merge PDFs
1. Click `Add PDFs` to select two or more PDF files.
2. Reorder the list with `Move Up` / `Move Down` to control the merge order.
3. Use `Remove Selected` or `Clear` to adjust the list.
4. Click `Merge PDFs`, choose a save location, and confirm to write the merged file.

### Extract Transaction Data
1. Click `Choose PDFs` and select one or more statement PDFs.
2. Leave the OCR/AI checkboxes enabled to use all fallbacks.
3. Click `Extract Data` to run the scan and preview the extracted table.
4. Edit any cell directly in the preview table.
5. Click `Export CSV` to choose a filename and save the CSV.

Optional AI OCR setup (Ollama + `glm-ocr`):
1. Install Ollama and ensure the local server is running on `127.0.0.1:11434`.
2. Pull the model with `ollama run glm-ocr` (this model requires Ollama 0.15.5 pre-release).
3. The app sends page images via Ollama's `/api/chat` endpoint using base64 image payloads.

Optional AI OCR setup (GLM-OCR SDK):
1. Clone `https://github.com/zai-org/GLM-OCR` and install dependencies with `pip install -r requirements.txt` and `pip install transformers`.
2. Install the SDK in editable mode with `pip install -e .`.
3. Confirm the CLI works by running `glmocr parse input_image.png --output output_dir`.
4. Enable the `Use GLM-OCR SDK (glmocr CLI)` checkbox in the app.

### CSV Schema
The extractor writes UTF-8 CSV with these columns:
1. `institution`
2. `account_type`
3. `account_name`
4. `account_number`
5. `statement_period_start`
6. `statement_period_end`
7. `statement_date`
8. `transaction_date`
9. `posted_date`
10. `description`
11. `category`
12. `transaction_code`
13. `amount`
14. `amount_direction`
15. `currency`
16. `balance`
17. `fee`
18. `reward`
19. `source_file`
20. `source_page`

## Repo Structure

- Source code lives under `src/pdf_tools/` with a thin launcher in `app.py`.
- Build scripts live in `scripts/` with OS-specific subfolders.
- Shared build metadata lives in `build/metadata.json`.
- Windows installer script lives at `scripts/windows/installer.iss`.
- PyInstaller spec file lives at `pdf-tools.spec`.
- Developer helpers live in `Makefile` and `scripts/windows/tasks.ps1`.

## Scripts

- `scripts/linux/build-linux.sh`: Build the Linux standalone executable (PyInstaller).
- `scripts/windows/build-win.ps1`: Build the Windows standalone `.exe` and the Inno Setup installer.
- `scripts/validate-metadata.py`: Validate required fields in `build/metadata.json`.

## Developer Helpers

### Makefile Helpers (Linux/macOS)
```bash
make venv
make install
make run
make validate
make build-linux
```

### Windows Task Helpers
```powershell
.\scripts\windows\tasks.ps1 -Task venv
.\scripts\windows\tasks.ps1 -Task install
.\scripts\windows\tasks.ps1 -Task run
.\scripts\windows\tasks.ps1 -Task validate
.\scripts\windows\tasks.ps1 -Task build
```

## Notes

- The merge order matches the list order in the UI.
- Use Move Up / Move Down to reorder before merging.
