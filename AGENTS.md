# Repository Guidelines

## Project Structure & Module Organization
- `src/pdf_tools/` holds the application logic and UI windows.
- `src/pdf_tools/main.py` is the main entrypoint for the GUI.
- `src/pdf_tools/extraction/` contains the extraction pipeline and schema.
- `app.py` is a thin launcher that forwards to `pdf_tools.main`.
- `build/metadata.json` stores build metadata validated in CI.
- `scripts/` contains build helpers and validation scripts, with OS-specific subfolders.
- `scripts/linux/build-linux.sh` builds the Linux standalone executable.
- `scripts/windows/build-win.ps1` and `scripts/windows/installer.iss` handle Windows build + installer.
- `scripts/windows/tasks.ps1` provides quick Windows task shortcuts.
- `dist/` contains built artifacts (generated).
- `pdf-tools.spec` is the PyInstaller spec file.
- `.github/workflows/ci.yml` installs the package and runs metadata validation.

## Build, Test, and Development Commands
- `python -m venv .venv` and `source .venv/bin/activate` to create/activate a virtualenv (Linux/macOS).
- `python -m venv .venv` and `scripts\\windows\\Activate.ps1` to activate a virtualenv (Windows).
- `pip install -r requirements.txt -r requirements-dev.txt` to install dependencies.
- `pip install -e .` to install the package in editable mode.
- `python -m pdf_tools` to run the GUI locally.
- `python app.py` to run the legacy launcher.
- `./scripts/linux/build-linux.sh` to build a Linux standalone executable.
- `./scripts/windows/build-win.ps1` to build a Windows `.exe` and installer (requires Inno Setup).
- `python scripts/validate-metadata.py` to validate `build/metadata.json` (CI uses this).

## Coding Style & Naming Conventions
- Python code uses 4-space indentation and type hints (see `src/pdf_tools/`).
- Naming follows `snake_case` for functions/variables and `CamelCase` for classes.
- No formatter or linter is configured; keep changes consistent with existing style.

## Testing Guidelines
- There is no automated test suite in this repository right now.
- Use `python scripts/validate-metadata.py` as a lightweight check.
- If adding tests in the future, keep them in a `tests/` directory and name files `test_*.py`.

## Commit & Pull Request Guidelines
- This checkout does not include Git history, so there is no established commit convention.
- Use concise, imperative commit summaries (e.g., "Add merge error handling").
- For pull requests, include a short description of the change and why it’s needed.
- For pull requests, include any relevant build or validation commands run (e.g., `python scripts/validate-metadata.py`).
- For pull requests, include screenshots for UI changes.

## Configuration Tips
- Update `build/metadata.json` when changing app name/version/publisher.
- Keep `requirements.txt` in sync with runtime dependencies like `pypdf`.
- Keep `pyproject.toml` version aligned with `build/metadata.json`.
- OCR + table extraction requires external tools (Tesseract, Poppler, Ghostscript).
