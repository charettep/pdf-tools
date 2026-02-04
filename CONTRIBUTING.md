# Contributing

Thanks for contributing! This repo is intentionally small and focused.

## Quick Start
1. Create and activate a virtualenv (see README for OS-specific steps).
2. Install dependencies: `pip install -r requirements.txt -r requirements-dev.txt`.
3. Run the app: `python -m pdf_tools`.
4. Optional: install editable package `pip install -e .`.

## Expectations
- Keep changes minimal and consistent with existing style in `src/pdf_tools/`.
- Update `build/metadata.json` if you change versioning or build metadata.
- Avoid committing generated artifacts in `build/` or `dist/`.

## Validation
- Run `python scripts/validate-metadata.py` before opening a PR.
 - Alternatively: `make validate`.
 - Windows: `.\scripts\windows\tasks.ps1 -Task validate`.

## Pull Requests
- Provide a clear summary of what changed and why.
- Include screenshots for UI changes.
