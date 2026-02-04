#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export REPO_ROOT

python "$REPO_ROOT/scripts/validate-metadata.py"

cd "$REPO_ROOT"

APP_NAME="$(python - <<'PY'
import json
import os
repo_root = os.environ.get("REPO_ROOT", ".")
with open(os.path.join(repo_root, 'build', 'metadata.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data['app_name'])
PY
)"
APP_AUTHOR="charettep"

python -m pip install -r requirements.txt -r requirements-dev.txt

# Create a single-file executable in dist/
pyinstaller \
  --noconfirm \
  --onefile \
  --name "$APP_NAME" \
  --windowed \
  src/pdf_tools/main.py

printf "\nBuild complete. Executable: dist/%s\n" "$APP_NAME"
