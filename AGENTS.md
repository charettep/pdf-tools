# Repository Guidelines

## Project Structure & Module Organization
- `app.py` holds the Tkinter GUI and PDF merge logic.
- `build/metadata.json` stores build metadata validated in CI.
- `scripts/` contains build helpers and validation scripts, with OS-specific subfolders:
- `scripts/linux/build-linux.sh` for Linux builds.
- `scripts/windows/build-win.ps1` and `scripts/windows/installer.iss` for Windows builds.
- `dist/` contains built artifacts (generated).
- `pdf-tools.spec` is the PyInstaller spec file.
- `.github/workflows/ci.yml` runs metadata validation in CI.

## Build, Test, and Development Commands
- `python -m venv .venv` and `source .venv/bin/activate` to create/activate a virtualenv.
- `pip install -r requirements.txt` to install runtime dependencies.
- `python app.py` to run the GUI locally.
- `./scripts/linux/build-linux.sh` to build a Linux standalone executable.
- `./scripts/windows/build-win.ps1` to build a Windows `.exe` and installer (requires Inno Setup).
- `python scripts/validate-metadata.py` to validate `build/metadata.json` (CI uses this).

## Coding Style & Naming Conventions
- Python code uses 4-space indentation and type hints (see `app.py`).
- Naming follows `snake_case` for functions/variables and `CamelCase` for classes.
- No formatter or linter is configured; keep changes consistent with existing style.

## Testing Guidelines
- There is no automated test suite in this repository right now.
- Use `python scripts/validate-metadata.py` as a lightweight check.
- If adding tests in the future, keep them in a `tests/` directory and name files `test_*.py`.

## Commit & Pull Request Guidelines
- This checkout does not include Git history, so there is no established commit convention.
- Use concise, imperative commit summaries (e.g., "Add merge error handling").
- For pull requests, include:
- A short description of the change and why it’s needed.
- Any relevant build or validation commands run (e.g., `python scripts/validate-metadata.py`).
- Screenshots for UI changes.

## Configuration Tips
- Update `build/metadata.json` when changing app name/version/publisher.
- Keep `requirements.txt` in sync with runtime dependencies like `pypdf`.
